"""通用 v2 PluginManager、API 和进程恢复验收测试。"""

from __future__ import annotations

import shutil
import subprocess
import asyncio
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

import sundarr.app.api.plugins as plugin_api
from sundarr.app.core.database import get_db
from sundarr.app.models.plugin import PluginConfig, PluginRepository
from sundarr.app.plugins.activator import PluginActivator
from sundarr.app.plugins.coordinator import RepositoryActivationCoordinator, RepositoryActivationError
from sundarr.app.plugins.loader import PluginLoader
from sundarr.app.plugins.manager import PluginManager, PluginProcessRole
from sundarr.app.plugins.registry import plugin_registry
from sundarr.app.plugins.runtime_registry import (
    catalog_provider_registry,
    source_registry,
    watchlist_provider_registry,
)
from sundarr.app.worker import WorkerRuntime


pytestmark = pytest.mark.anyio
FIXTURE_REPO = Path(__file__).parent / "fixtures" / "v2-plugin-repository"


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
def clear_registries():
    plugin_registry.clear()
    source_registry.clear()
    catalog_provider_registry.clear()
    watchlist_provider_registry.clear()
    yield
    plugin_registry.clear()
    source_registry.clear()
    catalog_provider_registry.clear()
    watchlist_provider_registry.clear()


def _git(args: list[str], cwd: Path) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _create_origin(tmp_path: Path) -> tuple[Path, str]:
    # Windows 上 Git 对象可能带只读属性；每次使用唯一目录，避免上轮失败残留干扰。
    origin = tmp_path / f"origin-repo-{uuid4().hex}"
    shutil.copytree(FIXTURE_REPO, origin, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    _git(["init", "-b", "main"], origin)
    _git(["config", "user.name", "Sundarr Test"], origin)
    _git(["config", "user.email", "test@sundarr.invalid"], origin)
    _git(["add", "."], origin)
    _git(["commit", "-m", "fixture v1"], origin)
    return origin, _git(["rev-parse", "HEAD"], origin)


def _manager(tmp_path: Path, role: PluginProcessRole = PluginProcessRole.ALL) -> PluginManager:
    loader = PluginLoader(repos_dir=tmp_path / "cache")
    activator = PluginActivator(loader=loader)
    coordinator = RepositoryActivationCoordinator(activator=activator)
    return PluginManager(loader=loader, coordinator=coordinator, process_role=role)


def _configs() -> dict[str, dict[str, object]]:
    return {
        "fixture-catalog": {"api_key": "super-secret", "health_ok": True},
        "fixture-watchlist": {"user_id": "user-1"},
    }


async def test_manager_installs_multi_plugin_repo_and_redacts_config(db_session, tmp_path: Path) -> None:
    origin, first_commit = _create_origin(tmp_path)
    manager = _manager(tmp_path)
    result = await manager.add_repository(
        db_session,
        repo_url=origin.as_posix(),
        branch="main",
        configs=_configs(),
    )

    assert result.commit_hash == first_commit
    assert set(result.plugin_ids) == {"fixture-source", "fixture-catalog", "fixture-watchlist"}
    repository = db_session.get(PluginRepository, result.repository_id)
    assert repository.current_commit == first_commit
    assert repository.previous_commit is None
    assert len(repository.configs) == 3
    assert manager.get_plugin_config(db_session, "fixture-catalog") == {
        "api_key": "***",
        "health_ok": True,
    }

    await manager.update_plugin_config(
        db_session,
        "fixture-catalog",
        {"api_key": "***", "health_ok": True},
    )
    row = db_session.query(PluginConfig).filter(PluginConfig.plugin_id == "fixture-catalog").one()
    assert row.config_data.startswith("fernet:v1:")
    assert "super-secret" not in row.config_data
    assert "***" not in row.config_data
    assert manager._decode_config(row.config_data)["api_key"] == "super-secret"


async def test_manager_installs_missing_required_config_as_disabled(db_session, tmp_path: Path) -> None:
    origin, _ = _create_origin(tmp_path)
    manager = _manager(tmp_path)

    result = await manager.add_repository(db_session, repo_url=origin.as_posix(), branch="main")

    assert set(result.plugin_ids) == {"fixture-source"}
    rows = {item.plugin_id: item for item in db_session.query(PluginConfig).all()}
    assert rows["fixture-source"].enabled is True
    assert rows["fixture-catalog"].enabled is False
    assert rows["fixture-watchlist"].enabled is False
    assert source_registry.get("fixture-source") is not None
    assert catalog_provider_registry.get("fixture-catalog") is None
    assert watchlist_provider_registry.get("fixture-watchlist") is None


async def test_failed_update_keeps_locked_commit_and_old_instances(db_session, tmp_path: Path) -> None:
    origin, first_commit = _create_origin(tmp_path)
    manager = _manager(tmp_path)
    result = await manager.add_repository(
        db_session,
        repo_url=origin.as_posix(),
        configs=_configs(),
    )
    old_source = source_registry.require("fixture-source")
    old_catalog = catalog_provider_registry.require("fixture-catalog")

    plugin_file = origin / "fixture_plugins.py"
    code = plugin_file.read_text(encoding="utf-8")
    plugin_file.write_text(
        code.replace(
            'health_ok=context.plugin_config["health_ok"],',
            "health_ok=False,",
        ),
        encoding="utf-8",
    )
    _git(["add", "fixture_plugins.py"], origin)
    _git(["commit", "-m", "fixture unhealthy"], origin)
    failed_commit = _git(["rev-parse", "HEAD"], origin)

    with pytest.raises(RepositoryActivationError, match="健康检查失败"):
        await manager.update_repository(db_session, result.repository_id, failed_commit)

    repository = db_session.get(PluginRepository, result.repository_id)
    db_session.refresh(repository)
    assert repository.current_commit == first_commit
    assert repository.previous_commit is None
    assert source_registry.require("fixture-source") is old_source
    assert catalog_provider_registry.require("fixture-catalog") is old_catalog
    assert _git(["rev-parse", "HEAD"], manager.loader.repository_path(origin.as_posix())) == first_commit
    failed_config = db_session.query(PluginConfig).filter(PluginConfig.plugin_id == "fixture-catalog").one()
    assert failed_config.status == "error"
    assert "super-secret" not in (failed_config.last_error or "")


async def test_database_commit_failure_rolls_back_new_runtime(
    db_session,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    origin, _ = _create_origin(tmp_path)
    manager = _manager(tmp_path)
    real_commit = db_session.commit
    calls = 0

    def fail_once() -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("模拟数据库提交失败")
        real_commit()

    monkeypatch.setattr(db_session, "commit", fail_once)
    with pytest.raises(RuntimeError, match="模拟数据库提交失败"):
        await manager.add_repository(
            db_session,
            repo_url=origin.as_posix(),
            configs=_configs(),
        )

    assert manager.coordinator.snapshot() == {}
    assert len(source_registry) == len(catalog_provider_registry) == len(watchlist_provider_registry) == 0
    assert db_session.query(PluginRepository).count() == 0


async def test_api_and_worker_restore_only_their_locked_plugin_types(db_session, tmp_path: Path) -> None:
    origin, _ = _create_origin(tmp_path)
    api_manager = _manager(tmp_path, PluginProcessRole.API)
    installed = await api_manager.add_repository(
        db_session,
        repo_url=origin.as_posix(),
        configs=_configs(),
    )
    assert set(installed.plugin_ids) == {"fixture-source", "fixture-catalog"}
    assert len(watchlist_provider_registry) == 0
    await api_manager.dispose_all()

    unavailable_origin = tmp_path / f"origin-offline-{uuid4().hex}"
    origin.rename(unavailable_origin)
    worker_manager = _manager(tmp_path, PluginProcessRole.WORKER)
    stats = await worker_manager.load_all_repositories(
        db_session,
        process_role=PluginProcessRole.WORKER,
    )
    assert stats == {"total": 1, "loaded": 1, "error": 0, "errors": []}
    assert len(source_registry) == len(catalog_provider_registry) == 0
    assert watchlist_provider_registry.require("fixture-watchlist").user_id == "user-1"

    await api_manager.disable_plugin(db_session, "fixture-watchlist")
    reconcile = await worker_manager.reconcile_repositories(
        db_session,
        process_role=PluginProcessRole.WORKER,
    )
    assert reconcile["reloaded"] == 1
    assert watchlist_provider_registry.get("fixture-watchlist") is None


async def test_successful_update_rollback_and_delete_are_repository_scoped(db_session, tmp_path: Path) -> None:
    origin, first_commit = _create_origin(tmp_path)
    manager = _manager(tmp_path)
    installed = await manager.add_repository(
        db_session,
        repo_url=origin.as_posix(),
        configs=_configs(),
    )
    manifest_file = origin / "sundarr_plugin.toml"
    manifest_file.write_text(
        manifest_file.read_text(encoding="utf-8").replace('version = "0.1.0"', 'version = "0.2.0"'),
        encoding="utf-8",
    )
    _git(["add", "sundarr_plugin.toml"], origin)
    _git(["commit", "-m", "fixture v2"], origin)
    second_commit = _git(["rev-parse", "HEAD"], origin)

    updated = await manager.update_repository(db_session, installed.repository_id, second_commit)
    repository = db_session.get(PluginRepository, installed.repository_id)
    db_session.refresh(repository)
    assert updated.commit_hash == second_commit
    assert repository.current_commit == second_commit
    assert repository.previous_commit == first_commit

    rolled_back = await manager.rollback_repository(db_session, installed.repository_id)
    db_session.refresh(repository)
    assert rolled_back.commit_hash == first_commit
    assert repository.current_commit == first_commit
    assert repository.previous_commit == second_commit

    cache_path = manager.loader.repository_path(origin.as_posix())
    await manager.remove_repository(db_session, installed.repository_id)
    assert db_session.get(PluginRepository, installed.repository_id) is None
    assert db_session.query(PluginConfig).count() == 0
    assert not cache_path.exists()
    assert len(source_registry) == len(catalog_provider_registry) == len(watchlist_provider_registry) == 0


async def test_plugin_api_returns_multi_plugin_results_and_diagnostics(
    db_session,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    origin, _ = _create_origin(tmp_path)
    manager = _manager(tmp_path)
    monkeypatch.setattr(plugin_api, "plugin_manager", manager)
    app = FastAPI()
    app.include_router(plugin_api.router)

    def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as client:
        response = client.post(
            "/plugins/repositories",
            json={"repo_url": origin.as_posix(), "branch": "main", "configs": _configs()},
        )
        assert response.status_code == 200, response.text
        payload = response.json()
        assert set(payload["plugin_ids"]) == {"fixture-source", "fixture-catalog", "fixture-watchlist"}

        config_response = client.get("/plugins/plugins/fixture-catalog/config")
        assert config_response.status_code == 200
        assert config_response.json()["config_data"]["api_key"] == "***"

        diagnostics = client.get("/plugins/activations")
        assert diagnostics.status_code == 200
        assert {item["plugin_id"] for item in diagnostics.json()} == set(payload["plugin_ids"])

        old_catalog = catalog_provider_registry.require("fixture-catalog")
        failed_config = client.put(
            "/plugins/plugins/fixture-catalog/config",
            json={"config_data": {"api_key": "***", "health_ok": False}},
        )
        assert failed_config.status_code == 400
        assert "super-secret" not in failed_config.text
        assert catalog_provider_registry.require("fixture-catalog") is old_catalog

        disable_response = client.post("/plugins/plugins/fixture-source/disable")
        assert disable_response.status_code == 200
        assert source_registry.get("fixture-source") is None


def test_worker_entry_restores_locked_watchlist_and_exits_cleanly(
    db_session,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    origin, _ = _create_origin(tmp_path)
    api_manager = _manager(tmp_path, PluginProcessRole.API)
    asyncio.run(
        api_manager.add_repository(
            db_session,
            repo_url=origin.as_posix(),
            configs=_configs(),
        )
    )
    asyncio.run(api_manager.dispose_all())

    factory = sessionmaker(bind=db_session.get_bind(), autoflush=False, autocommit=False)
    monkeypatch.setattr("sundarr.app.worker.get_session_factory", lambda: factory)
    worker_manager = _manager(tmp_path, PluginProcessRole.WORKER)
    runtime = WorkerRuntime(poll_interval_seconds=0, plugin_manager=worker_manager)
    runtime._running = False
    runtime.run()

    output = capsys.readouterr().out
    assert "Worker 插件恢复完成：成功 1，失败 0" in output
    assert "Sundarr Worker 已停止" in output
    assert len(watchlist_provider_registry) == 0
