from datetime import datetime

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from sundarr.app.api import health as health_api
from sundarr.app.config import redact_url_password
from sundarr.app.main import create_app


def test_health_returns_ok() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    class FakeRedis:
        def ping(self) -> bool:
            return True

    original_get_engine = health_api.get_engine
    original_redis_from_url = health_api.Redis.from_url
    original_worker_status = health_api._worker_status
    health_api.get_engine = lambda: engine
    health_api.Redis.from_url = lambda *args, **kwargs: FakeRedis()
    health_api._worker_status = lambda: "ok"
    client = TestClient(create_app())

    try:
        response = client.get("/health")
    finally:
        health_api.get_engine = original_get_engine
        health_api.Redis.from_url = original_redis_from_url
        health_api._worker_status = original_worker_status

    assert response.status_code == 200
    body = response.json()
    # Scalar fields (legacy contract, docs/07-接口契约.md §2).
    assert body["status"] == "ok"
    assert body["database"] == "ok"
    assert body["redis"] == "ok"
    assert body["worker"] == "ok"
    # Per-component block with its own checked_at timestamp so the web
    # console can surface staleness per component.
    assert set(body["components"].keys()) == {"api", "database", "redis", "worker"}
    for name, component in body["components"].items():
        assert component["status"] in {"ok", "error", "unknown"}, name
        # Timestamps must parse as ISO-8601 UTC (`...Z` suffix).
        timestamp = component["checked_at"]
        assert timestamp.endswith("Z"), timestamp
        datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    # Top-level checked_at is kept as a convenience (last probe timestamp).
    assert body["checked_at"].endswith("Z")


def test_worker_status_unknown_without_pid(monkeypatch) -> None:
    monkeypatch.setattr(health_api, "_read_pid", lambda service: None)

    assert health_api._worker_status() == "unknown"


def test_worker_status_error_with_dead_pid(monkeypatch) -> None:
    monkeypatch.setattr(health_api, "_read_pid", lambda service: 123)
    monkeypatch.setattr(health_api, "_is_process_running", lambda pid: False)

    assert health_api._worker_status() == "error"


def test_redact_url_password() -> None:
    assert redact_url_password("postgresql+psycopg://user:secret@host:5432/db") == "postgresql+psycopg://user:***@host:5432/db"
    assert redact_url_password("redis://:secret@host:6379/0") == "redis://:***@host:6379/0"
