from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.pool import StaticPool

from sundarr.app.core.database import Base
from sundarr.app.db_admin import ensure_runtime_schema_for_engine
from sundarr.app import models  # noqa: F401


def test_core_tables_are_registered() -> None:
    expected_tables = {
        "sources",
        "resources",
        "resource_links",
        "transfer_tasks",
        "transfer_files",
        "transfer_logs",
        "settings",
    }

    assert expected_tables.issubset(Base.metadata.tables.keys())


def test_sources_table_matches_required_columns() -> None:
    columns = Base.metadata.tables["sources"].columns

    for name in [
        "id",
        "name",
        "description",
        "homepage_url",
        "registered_at",
        "created_at",
        "updated_at",
    ]:
        assert name in columns

    for removed_name in ["type", "enabled", "legal_note", "trust_level", "config_json", "last_error_code"]:
        assert removed_name not in columns


def test_runtime_settings_use_jsonb() -> None:
    value_column = Base.metadata.tables["settings"].columns["value_json"]

    assert isinstance(value_column.type.dialect_impl(postgresql.dialect()), JSONB)


def test_initial_migration_exists() -> None:
    migration_path = Path("migrations/versions/0001_create_core_tables.py")

    assert migration_path.exists()


def test_runtime_schema_auto_adds_favorite_columns_for_legacy_tables() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE resources (id TEXT PRIMARY KEY, title TEXT NOT NULL, normalized_title TEXT, original_title TEXT, year INTEGER, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)"))
        connection.execute(text("CREATE TABLE resource_links (id TEXT PRIMARY KEY, resource_id TEXT NOT NULL, provider TEXT NOT NULL, url TEXT NOT NULL, code TEXT, source_id TEXT, source_url TEXT, valid BOOLEAN, last_checked_at TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)"))

    ensure_runtime_schema_for_engine(engine)

    inspector = inspect(engine)
    resource_columns = {column["name"] for column in inspector.get_columns("resources")}
    link_columns = {column["name"] for column in inspector.get_columns("resource_links")}

    assert "favorited_at" in resource_columns
    assert "name" in link_columns
    assert "quality" in link_columns
    assert "favorited_at" in link_columns
    assert "published_at" in link_columns
