from pathlib import Path
from typing import Any

import psycopg
from alembic import command
from alembic.config import Config
from psycopg import sql
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from sundarr.app.config import PROJECT_ROOT, get_settings, redact_url_password
from sundarr.app.models import Setting
from sundarr.app.services.source_service import source_service

DEFAULT_SETTINGS: dict[str, dict[str, Any]] = {
    "worker.enabled": {"enabled": True},
    "worker.concurrency": {"value": 2},
    "cloud.local": {"staging_root": "/Sundarr/_staging"},
    "download_to_local.config": {
        "delete_source_after_success": True,
        "delete_empty_source_dirs": True,
        "scan_interval_seconds": 60,
        "stable_seconds": 120,
        "unclassified_library_id": "",
    },
}


def initialize_database() -> None:
    database_url = get_settings().database_url
    print(f"数据库配置：{redact_url_password(database_url)}")
    create_database_if_missing(database_url)
    run_migrations()
    ensure_runtime_schema(database_url)
    seed_default_settings(database_url)
    seed_registered_sources(database_url)


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


def seed_registered_sources(database_url: str) -> None:
    engine = create_engine(database_url, pool_pre_ping=True)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with session_factory() as session:
        changed = seed_registered_sources_for_session(session)
    engine.dispose()
    print(f"搜索源目录已同步：变更 {changed} 项。")


def seed_default_settings_for_session(session: Session) -> int:
    changed = 0
    for key, value in DEFAULT_SETTINGS.items():
        if session.get(Setting, key) is not None:
            continue
        session.add(Setting(key=key, value_json=value, is_sensitive=False))
        changed += 1
    return changed


def seed_registered_sources_for_session(session: Session) -> int:
    return source_service.sync_registered_sources(session)


def ensure_runtime_schema(database_url: str) -> None:
    engine = create_engine(database_url, pool_pre_ping=True)
    try:
        ensure_runtime_schema_for_engine(engine)
    finally:
        engine.dispose()


def ensure_runtime_schema_for_engine(engine: Engine) -> None:
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    statements: list[str] = []

    if "resources" in table_names:
        columns = {column["name"] for column in inspector.get_columns("resources")}
        if "favorited_at" not in columns:
            statements.append(_add_column_sql(engine, "resources", "favorited_at", "TIMESTAMP"))

    if "resource_links" in table_names:
        columns = {column["name"] for column in inspector.get_columns("resource_links")}
        if "name" not in columns:
            statements.append(_add_column_sql(engine, "resource_links", "name", "TEXT"))
        if "quality" not in columns:
            statements.append(_add_column_sql(engine, "resource_links", "quality", "TEXT"))
        if "favorited_at" not in columns:
            statements.append(_add_column_sql(engine, "resource_links", "favorited_at", "TIMESTAMP"))
        if "published_at" not in columns:
            statements.append(_add_column_sql(engine, "resource_links", "published_at", "TIMESTAMP"))

    if not statements:
        return

    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))
    print(f"运行时 schema 已自修复：补齐 {len(statements)} 个字段。")


def _add_column_sql(engine: Engine, table_name: str, column_name: str, column_type: str) -> str:
    if engine.dialect.name == "postgresql":
        return f'ALTER TABLE "{table_name}" ADD COLUMN IF NOT EXISTS "{column_name}" {column_type}'
    return f'ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}'


def _build_maintenance_url(database_url: str) -> str:
    url = make_url(database_url)
    return url.set(drivername="postgresql", database="postgres").render_as_string(hide_password=False)
