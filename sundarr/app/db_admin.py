from pathlib import Path
from typing import Any

import psycopg
from alembic import command
from alembic.config import Config
from psycopg import sql
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from sundarr.app.config import get_settings, redact_url_password
from sundarr.app.models import Setting

DEFAULT_SETTINGS: dict[str, dict[str, Any]] = {
    "worker.enabled": {"enabled": True},
    "worker.concurrency": {"value": 2},
    "cloud.local": {"staging_root": "/Sundarr/_staging"},
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

    with psycopg.connect(maintenance_url, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (database_name,))
            if cursor.fetchone() is not None:
                print(f"数据库已存在：{database_name}")
                return
            cursor.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database_name)))
            print(f"数据库已创建：{database_name}")


def run_migrations() -> None:
    config_path = Path("alembic.ini")
    if not config_path.exists():
        raise FileNotFoundError("找不到 alembic.ini，请在项目根目录执行命令。")
    command.upgrade(Config(str(config_path)), "head")
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
