from pathlib import Path
from typing import Any

import psycopg
from alembic import command
from alembic.config import Config
from psycopg import sql
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from sundarr.app.config import PROJECT_ROOT, get_settings, redact_url_password
from sundarr.app.models import Setting
from sundarr.app.services.ingest_service import DEFAULT_INGEST_CONFIG, INGEST_CONFIG_KEY

DEFAULT_SETTINGS: dict[str, dict[str, Any]] = {
    "worker.enabled": {"enabled": True},
    "worker.concurrency": {"value": 2},
    "cloud.local": {"staging_root": "/Sundarr/_staging"},
    INGEST_CONFIG_KEY: DEFAULT_INGEST_CONFIG,
}


def initialize_database() -> None:
    database_url = get_settings().database_url
    print(f"数据库配置：{redact_url_password(database_url)}")
    create_database_if_missing(database_url)
    run_migrations()
    seed_default_settings(database_url)


def create_database_if_missing(database_url: str) -> None:
    url = make_url(database_url)
    database_name = url.database
    if not database_name:
        raise ValueError("DATABASE_NAME_MISSING")
    maintenance_url = _build_maintenance_url(database_url)

    try:
        with psycopg.connect(maintenance_url, autocommit=True) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (database_name,))
                if cursor.fetchone() is not None:
                    print(f"数据库已存在：{database_name}")
                    return
                cursor.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database_name)))
                print(f"数据库已创建：{database_name}")
    except psycopg.OperationalError as exc:
        raise RuntimeError(
            "无法连接 PostgreSQL。请检查项目根目录 .env 中的 SUNDARR_DATABASE_URL，"
            "确认 host、port、用户名、密码和网络连通性正确。"
        ) from exc


def run_migrations() -> None:
    config_path = PROJECT_ROOT / "alembic.ini"
    if not config_path.exists():
        raise FileNotFoundError(f"找不到 alembic.ini：{config_path}")
    config = Config(str(config_path))
    config.set_main_option("script_location", str(PROJECT_ROOT / "migrations"))
    config.set_main_option("prepend_sys_path", str(PROJECT_ROOT))
    command.upgrade(config, "head")
    print("数据库迁移已完成：head")


def seed_default_settings(database_url: str) -> None:
    engine = create_engine(database_url, pool_pre_ping=True)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with session_factory() as session:
        changed = seed_default_settings_for_session(session)
        session.commit()
    engine.dispose()
    print(f"默认业务配置已检查：新增 {changed} 项。")


def seed_default_settings_for_session(session: Session) -> int:
    changed = 0
    for key, value in DEFAULT_SETTINGS.items():
        if session.get(Setting, key) is not None:
            continue
        session.add(Setting(key=key, value_json=value, is_sensitive=False))
        changed += 1
    return changed


def _build_maintenance_url(database_url: str) -> str:
    url = make_url(database_url)
    return url.set(drivername="postgresql", database="postgres").render_as_string(hide_password=False)
