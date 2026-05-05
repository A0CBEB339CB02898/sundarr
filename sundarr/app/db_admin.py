from pathlib import Path

import psycopg
from alembic import command
from alembic.config import Config
from psycopg import sql
from sqlalchemy.engine import make_url

from sundarr.app.config import get_settings, redact_url_password


def initialize_database() -> None:
    database_url = get_settings().database_url
    print(f"数据库配置：{redact_url_password(database_url)}")
    create_database_if_missing(database_url)
    run_migrations()


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


def _build_maintenance_url(database_url: str) -> str:
    url = make_url(database_url)
    return url.set(drivername="postgresql", database="postgres").render_as_string(hide_password=False)
