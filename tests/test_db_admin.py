import pytest
import psycopg

from sundarr.app import db_admin
from sundarr.app.db_admin import (
    DEFAULT_SETTINGS,
    _build_maintenance_url,
    encrypt_stored_smb_secrets_for_session,
    seed_default_settings_for_session,
)
from sundarr.app.models import Setting, SmbConnection, TransferTask
from sundarr.app.plugins.secrets import TEXT_ENCRYPTED_PREFIX, decode_secret_text


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


def test_encrypt_stored_smb_secrets_is_idempotent(db_session) -> None:
    db_session.add(
        SmbConnection(
            id="conn",
            name="连接",
            host="nas.example.invalid",
            share="media",
            username="user",
            password="legacy-secret",
            base_path="/",
        )
    )
    db_session.add(
        TransferTask(
            id="task",
            status="pending",
            mode="download_to_local",
            target_type="smb",
            target_path="Movie.mkv",
            source_type="smb",
            source_path="Movie.mkv",
            source_config_snapshot={"connection_id": "conn", "password": "legacy-secret"},
            storage_config_snapshot={"connection_id": "conn", "password": "legacy-secret"},
        )
    )
    db_session.commit()

    assert encrypt_stored_smb_secrets_for_session(db_session) == 3
    db_session.commit()

    connection = db_session.get(SmbConnection, "conn")
    task = db_session.get(TransferTask, "task")
    assert connection is not None and connection.password is not None
    assert connection.password.startswith(TEXT_ENCRYPTED_PREFIX)
    assert decode_secret_text(connection.password) == "legacy-secret"
    assert task is not None
    assert task.source_config_snapshot["password"].startswith(TEXT_ENCRYPTED_PREFIX)
    assert task.storage_config_snapshot["password"].startswith(TEXT_ENCRYPTED_PREFIX)
    assert encrypt_stored_smb_secrets_for_session(db_session) == 0
