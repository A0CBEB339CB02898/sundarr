from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from sundarr.app.config import get_settings
from sundarr.app.core.database import Base
from sundarr.app import models  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

LEGACY_TABLES = {
    "ingest_bindings",
    "ingest_seen_files",
    "download_to_local_bindings",
    "download_to_local_seen_files",
}
LEGACY_COLUMNS = {
    "resources": {
        "description",
        "episodes",
        "language",
        "metadata_json",
        "poster",
        "quality",
        "score",
        "season",
        "subtitle",
        "type",
    },
    "resource_links": {"risk_level", "visibility"},
}


def include_schema_object(obj, name: str | None, type_: str, reflected: bool, compare_to) -> bool:
    """保留只读历史表/字段，避免自动迁移误删仍可能需要人工导出的旧数据。"""

    if not reflected or compare_to is not None:
        return True
    if type_ == "table" and name in LEGACY_TABLES:
        return False
    if type_ == "column" and name:
        table_name = getattr(getattr(obj, "table", None), "name", None)
        if name in LEGACY_COLUMNS.get(table_name, set()):
            return False
    return True


def get_database_url() -> str:
    return get_settings().database_url


def run_migrations_offline() -> None:
    context.configure(
        url=get_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_schema_object,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_database_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_schema_object,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
