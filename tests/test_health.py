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
    health_api.get_engine = lambda: engine
    health_api.Redis.from_url = lambda *args, **kwargs: FakeRedis()
    client = TestClient(create_app())

    try:
        response = client.get("/health")
    finally:
        health_api.get_engine = original_get_engine
        health_api.Redis.from_url = original_redis_from_url

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["database"] == "ok"
    assert response.json()["redis"] == "ok"


def test_redact_url_password() -> None:
    assert redact_url_password("postgresql+psycopg://user:secret@host:5432/db") == "postgresql+psycopg://user:***@host:5432/db"
    assert redact_url_password("redis://:secret@host:6379/0") == "redis://:***@host:6379/0"
