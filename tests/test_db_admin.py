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
