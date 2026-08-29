"""Manifest v2 单插件候选 Activation 测试。"""

from pathlib import Path

import pytest

from sundarr.app.plugins.activator import CandidateActivationError, PluginActivator
from sundarr.app.plugins.base import PluginManifest, PluginType
from sundarr.app.plugins.config import (
    PluginConfigValidationError,
    validate_plugin_config,
)
from sundarr.app.plugins.contracts import CatalogQuery, WatchlistPullRequest
from sundarr.app.plugins.loader import PluginLoader
from sundarr.app.plugins.runtime import ActivationStatus, MissingCapabilityError
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


def _loader(tmp_path: Path) -> PluginLoader:
    return PluginLoader(repos_dir=tmp_path / "cache")


async def test_v2_three_type_candidates_activate_call_and_dispose(
    tmp_path: Path,
) -> None:
    loader = _loader(tmp_path)
    manifests = {item.id: item for item in loader.parse_manifests(FIXTURE_REPO)}
    http_client = object()
    activator = PluginActivator(
        loader=loader,
        extra_capabilities={"core.http.v1": http_client},
    )

    source_activation = await activator.activate_candidate(
        manifests["fixture-source"],
        FIXTURE_REPO,
    )
    catalog_activation = await activator.activate_candidate(
        manifests["fixture-catalog"],
        FIXTURE_REPO,
        plugin_config={"api_key": "secret"},
    )
    watchlist_activation = await activator.activate_candidate(
        manifests["fixture-watchlist"],
        FIXTURE_REPO,
        plugin_config={"user_id": "user-1"},
    )

    assert source_activation.status == ActivationStatus.ACTIVE
    assert source_activation.context.plugin_config["timeout"] == 30
    assert not source_activation.context.has_capability("core.catalog_registry.v1")
    assert catalog_activation.status == ActivationStatus.ACTIVE
    assert catalog_activation.instance.http_client is http_client
    assert watchlist_activation.status == ActivationStatus.ACTIVE
    assert source_registry.require("fixture-source") is source_activation.instance
    assert (
        catalog_provider_registry.require("fixture-catalog")
        is catalog_activation.instance
    )
    assert (
        watchlist_provider_registry.require("fixture-watchlist")
        is watchlist_activation.instance
    )

    catalog_page = await catalog_activation.instance.search(
        CatalogQuery(keyword="星际穿越")
    )
    watchlist_page = await watchlist_activation.instance.pull(WatchlistPullRequest())
    assert catalog_page.items[0].title == "星际穿越"
    assert watchlist_page.items[0].subject.external_id == "wanted-user-1"
    assert set(catalog_activation.provided_capabilities) == {
        "catalog.search.v1",
        "catalog.trending.v1",
        "catalog.categories.v1",
        "catalog.detail.v1",
    }

    await source_activation.dispose()
    await catalog_activation.dispose()
    await watchlist_activation.dispose()
    assert len(source_registry) == 0
    assert len(catalog_provider_registry) == 0
    assert len(watchlist_provider_registry) == 0


async def test_missing_capability_fails_without_registry_residue(
    tmp_path: Path,
) -> None:
    loader = _loader(tmp_path)
    manifest = next(
        item
        for item in loader.parse_manifests(FIXTURE_REPO)
        if item.id == "fixture-catalog"
    )
    activator = PluginActivator(loader=loader)
    activator.capabilities.pop("core.http.v1")

    with pytest.raises(CandidateActivationError) as error:
        await activator.activate_candidate(
            manifest,
            FIXTURE_REPO,
            plugin_config={"api_key": "secret"},
        )

    assert isinstance(error.value.cause, MissingCapabilityError)
    assert error.value.activation.status == ActivationStatus.FAILED
    assert len(catalog_provider_registry) == 0


async def test_config_validation_applies_defaults_and_rejects_invalid_values(
    tmp_path: Path,
) -> None:
    loader = _loader(tmp_path)
    source_manifest = next(
        item
        for item in loader.parse_manifests(FIXTURE_REPO)
        if item.id == "fixture-source"
    )

    assert validate_plugin_config(source_manifest.config_schema, {}) == {"timeout": 30}
    with pytest.raises(PluginConfigValidationError, match="不能大于"):
        validate_plugin_config(source_manifest.config_schema, {"timeout": 301})
    with pytest.raises(PluginConfigValidationError, match="未声明字段"):
        validate_plugin_config(source_manifest.config_schema, {"unknown": True})

    catalog_manifest = next(
        item
        for item in loader.parse_manifests(FIXTURE_REPO)
        if item.id == "fixture-catalog"
    )
    with pytest.raises(PluginConfigValidationError, match="缺少必填"):
        await PluginActivator(
            loader=loader,
            extra_capabilities={"core.http.v1": object()},
        ).activate_candidate(catalog_manifest, FIXTURE_REPO)
    assert len(catalog_provider_registry) == 0


async def test_health_failure_cleans_candidate_side_effects(tmp_path: Path) -> None:
    loader = _loader(tmp_path)
    manifest = next(
        item
        for item in loader.parse_manifests(FIXTURE_REPO)
        if item.id == "fixture-catalog"
    )
    activator = PluginActivator(
        loader=loader,
        extra_capabilities={"core.http.v1": object()},
    )

    with pytest.raises(CandidateActivationError, match="健康检查失败") as error:
        await activator.activate_candidate(
            manifest,
            FIXTURE_REPO,
            plugin_config={"api_key": "secret", "health_ok": False},
        )

    assert error.value.activation.status == ActivationStatus.FAILED
    assert len(catalog_provider_registry) == 0


async def test_plugin_logger_redacts_manifest_secret_values(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    loader = _loader(tmp_path)
    manifest = next(
        item
        for item in loader.parse_manifests(FIXTURE_REPO)
        if item.id == "fixture-catalog"
    )
    activation = await PluginActivator(loader=loader).activate_candidate(
        manifest,
        FIXTURE_REPO,
        plugin_config={"api_key": "log-secret"},
    )

    with caplog.at_level("INFO", logger="sundarr.plugin.fixture-catalog"):
        activation.context.logger.info("目录密钥=%s", "log-secret")

    assert "log-secret" not in caplog.text
    assert "目录密钥=***" in caplog.text
    await activation.dispose()


async def test_wrong_entry_contract_fails_before_registration(tmp_path: Path) -> None:
    loader = _loader(tmp_path)
    manifest = PluginManifest(
        id="wrong-catalog",
        name="错误目录插件",
        version="0.1.0",
        plugin_type=PluginType.CATALOG_PROVIDER,
        entry="fixture_plugins:activate_source",
        plugin_api_version="1.0",
        manifest_version=2,
        requires=["core.catalog_registry.v1"],
        provides=["catalog.search.v1"],
        config_schema={"timeout": {"type": "integer", "default": 30}},
    )

    with pytest.raises(CandidateActivationError, match="CatalogProvider"):
        await PluginActivator(loader=loader).activate_candidate(
            manifest,
            FIXTURE_REPO,
        )

    assert len(catalog_provider_registry) == 0


async def test_entry_module_must_come_from_repository(tmp_path: Path) -> None:
    manifest = PluginManifest(
        id="outside-source",
        name="越界入口",
        version="0.1.0",
        plugin_type=PluginType.SOURCE,
        entry="json:loads",
        plugin_api_version="1.0",
        manifest_version=2,
        requires=["core.source_registry.v1"],
        provides=["source.search.v1"],
    )

    with pytest.raises(CandidateActivationError, match="不在仓库目录内"):
        await PluginActivator(loader=_loader(tmp_path)).activate_candidate(
            manifest,
            FIXTURE_REPO,
        )

    assert len(source_registry) == 0
