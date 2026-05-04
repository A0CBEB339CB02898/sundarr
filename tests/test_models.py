from pathlib import Path

from sqlalchemy.dialects.postgresql import JSONB

from sundarr.app.core.database import Base
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
        "type",
        "enabled",
        "legal_note",
        "trust_level",
        "created_by_user",
        "config_json",
        "last_error_code",
        "last_error_message",
        "last_checked_at",
        "created_at",
        "updated_at",
    ]:
        assert name in columns


def test_runtime_settings_use_jsonb() -> None:
    value_column = Base.metadata.tables["settings"].columns["value_json"]

    assert isinstance(value_column.type, JSONB)


def test_initial_migration_exists() -> None:
    migration_path = Path("migrations/versions/0001_create_core_tables.py")

    assert migration_path.exists()
