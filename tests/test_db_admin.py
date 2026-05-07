import pytest
import psycopg

from sundarr.app import db_admin
from sundarr.app.db_admin import DEFAULT_SETTINGS, _build_maintenance_url, seed_default_settings_for_session
from sundarr.app.models import Setting


def test_build_maintenance_url_uses_postgres_database() -> None:
    url = _build_maintenance_url("postgresql+psycopg://user:secret@db.example:5432/sundarr")

    assert url == "postgresql://user:secret@db.example:5432/postgres"


def test_seed_default_settings_is_idempotent(db_session) -> None:
    assert seed_default_settings_for_session(db_session) == len(DEFAULT_SETTINGS)
    db_session.commit()

    assert db_session.get(Setting, "worker.concurrency").value_json == {"value": 2}
    assert db_session.get(Setting, "worker.enabled").value_json == {"enabled": True}
    assert db_session.get(Setting, "cloud.local").value_json == {"staging_root": "/Sundarr/_staging"}
    assert seed_default_settings_for_session(db_session) == 0


def test_create_database_connection_error_is_friendly(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_connect(*args, **kwargs):
        raise psycopg.OperationalError("connection timeout expired")

    monkeypatch.setattr(db_admin.psycopg, "connect", fail_connect)

    with pytest.raises(RuntimeError, match="无法连接 PostgreSQL"):
        db_admin.create_database_if_missing("postgresql+psycopg://user:secret@db.example:5432/sundarr")
