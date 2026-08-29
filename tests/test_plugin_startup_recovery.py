"""插件恢复失败不得阻断 API 主服务。"""

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import sundarr.app.api.health as health_api
import sundarr.app.main as main_module


class _FailingRestoreManager:
    def __init__(self) -> None:
        self.restored = False
        self.disposed = False

    async def load_all_repositories(self, session):
        self.restored = True
        return {
            "total": 1,
            "loaded": 0,
            "error": 1,
            "errors": [{"repository_id": "broken", "error": "候选健康检查失败"}],
        }

    async def dispose_all(self) -> None:
        self.disposed = True


class _HealthyRedis:
    def ping(self) -> bool:
        return True


def test_api_health_survives_plugin_restore_failure(monkeypatch) -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    manager = _FailingRestoreManager()

    monkeypatch.setattr(main_module, "get_engine", lambda: engine)
    monkeypatch.setattr(main_module, "get_session_factory", lambda: factory)
    monkeypatch.setattr(main_module, "plugin_manager", manager)
    monkeypatch.setattr(main_module.Redis, "from_url", lambda *args, **kwargs: _HealthyRedis())
    monkeypatch.setattr(health_api, "_check_database", lambda: "ok")
    monkeypatch.setattr(health_api, "_check_redis", lambda: "ok")
    monkeypatch.setattr(health_api, "_worker_status", lambda: "unknown")

    with TestClient(main_module.create_app()) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        assert manager.restored is True

    assert manager.disposed is True
    engine.dispose()
