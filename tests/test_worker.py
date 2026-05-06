from sundarr.app.models import Setting
from sundarr.app.worker import load_worker_settings


def test_load_worker_settings_uses_defaults(db_session) -> None:
    settings = load_worker_settings(db_session)

    assert settings.enabled is True
    assert settings.concurrency == 2


def test_load_worker_settings_reads_database_values(db_session) -> None:
    db_session.add(Setting(key="worker.enabled", value_json={"enabled": False}, is_sensitive=False))
    db_session.add(Setting(key="worker.concurrency", value_json={"value": 4}, is_sensitive=False))
    db_session.commit()

    settings = load_worker_settings(db_session)

    assert settings.enabled is False
    assert settings.concurrency == 4


def test_load_worker_settings_clamps_concurrency(db_session) -> None:
    db_session.add(Setting(key="worker.concurrency", value_json={"value": 0}, is_sensitive=False))
    db_session.commit()

    settings = load_worker_settings(db_session)

    assert settings.concurrency == 1
