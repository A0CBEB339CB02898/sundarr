"""Manifest v2 仓库级候选切换测试。"""

from pathlib import Path

import pytest

from sundarr.app.plugins.activator import PluginActivator
from sundarr.app.plugins.coordinator import RepositoryActivationCoordinator, RepositoryActivationError
from sundarr.app.plugins.loader import PluginLoader
from sundarr.app.plugins.runtime import ActivationStatus
from sundarr.app.plugins.runtime_registry import (
    catalog_provider_registry,
    source_registry,
    watchlist_provider_registry,
)


pytestmark = pytest.mark.anyio
FIXTURE_REPO = Path(__file__).parent / "fixtures" / "v2-plugin-repository"


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
def clear_runtime_registries():
    source_registry.clear()
    catalog_provider_registry.clear()
    watchlist_provider_registry.clear()
    yield
    source_registry.clear()
    catalog_provider_registry.clear()
    watchlist_provider_registry.clear()


def _coordinator(tmp_path: Path) -> tuple[RepositoryActivationCoordinator, PluginLoader]:
    loader = PluginLoader(repos_dir=tmp_path / "cache")
    activator = PluginActivator(loader=loader, extra_capabilities={"core.http.v1": object()})
    return RepositoryActivationCoordinator(activator=activator), loader


def _configs(*, healthy: bool = True, user_id: str = "user-1") -> dict[str, dict[str, object]]:
    return {
        "fixture-catalog": {"api_key": "secret", "health_ok": healthy},
        "fixture-watchlist": {"user_id": user_id},
    }


async def test_repository_activates_all_three_types_and_disposes(tmp_path: Path) -> None:
    coordinator, loader = _coordinator(tmp_path)
    result = await coordinator.activate_repository(
        repository_id="repo-1",
        commit_hash="commit-a",
        repo_path=FIXTURE_REPO,
        manifests=loader.parse_manifests(FIXTURE_REPO),
        configs=_configs(),
    )

    assert set(result.plugin_ids) == {
        "fixture-source",
        "fixture-catalog",
        "fixture-watchlist",
    }
    assert all(item.status == ActivationStatus.ACTIVE for item in result.activations)
    assert len(source_registry) == len(catalog_provider_registry) == len(watchlist_provider_registry) == 1

    assert await coordinator.deactivate_repository("repo-1") == 3
    assert len(source_registry) == len(catalog_provider_registry) == len(watchlist_provider_registry) == 0
    assert all(item.status == ActivationStatus.DISPOSED for item in result.activations)


async def test_failed_candidate_keeps_old_repository_version(tmp_path: Path) -> None:
    coordinator, loader = _coordinator(tmp_path)
    manifests = loader.parse_manifests(FIXTURE_REPO)
    first = await coordinator.activate_repository(
        repository_id="repo-1",
        commit_hash="commit-a",
        repo_path=FIXTURE_REPO,
        manifests=manifests,
        configs=_configs(user_id="old-user"),
    )
    old_instances = {item.plugin_id: item.instance for item in first.activations}

    with pytest.raises(RepositoryActivationError, match="健康检查失败"):
        await coordinator.activate_repository(
            repository_id="repo-1",
            commit_hash="commit-b",
            repo_path=FIXTURE_REPO,
            manifests=manifests,
            configs=_configs(healthy=False, user_id="new-user"),
        )

    assert source_registry.require("fixture-source") is old_instances["fixture-source"]
    assert catalog_provider_registry.require("fixture-catalog") is old_instances["fixture-catalog"]
    assert watchlist_provider_registry.require("fixture-watchlist") is old_instances["fixture-watchlist"]
    assert coordinator.get("fixture-source").commit_hash == "commit-a"


async def test_successful_switch_replaces_all_and_cleans_old(tmp_path: Path) -> None:
    coordinator, loader = _coordinator(tmp_path)
    manifests = loader.parse_manifests(FIXTURE_REPO)
    first = await coordinator.activate_repository(
        repository_id="repo-1",
        commit_hash="commit-a",
        repo_path=FIXTURE_REPO,
        manifests=manifests,
        configs=_configs(user_id="old-user"),
    )
    second = await coordinator.activate_repository(
        repository_id="repo-1",
        commit_hash="commit-b",
        repo_path=FIXTURE_REPO,
        manifests=manifests,
        configs=_configs(user_id="new-user"),
    )

    assert all(item.status == ActivationStatus.DISPOSED for item in first.activations)
    assert all(item.status == ActivationStatus.ACTIVE for item in second.activations)
    assert source_registry.require("fixture-source") is coordinator.get("fixture-source").instance
    assert watchlist_provider_registry.require("fixture-watchlist").user_id == "new-user"


async def test_disabled_plugin_is_removed_during_repository_switch(tmp_path: Path) -> None:
    coordinator, loader = _coordinator(tmp_path)
    manifests = loader.parse_manifests(FIXTURE_REPO)
    await coordinator.activate_repository(
        repository_id="repo-1",
        commit_hash="commit-a",
        repo_path=FIXTURE_REPO,
        manifests=manifests,
        configs=_configs(),
    )

    result = await coordinator.activate_repository(
        repository_id="repo-1",
        commit_hash="commit-b",
        repo_path=FIXTURE_REPO,
        manifests=manifests,
        configs={"fixture-catalog": {"api_key": "secret"}},
        enabled_plugin_ids={"fixture-source", "fixture-catalog"},
    )

    assert set(result.plugin_ids) == {"fixture-source", "fixture-catalog"}
    assert watchlist_provider_registry.get("fixture-watchlist") is None
    assert coordinator.get("fixture-watchlist") is None
