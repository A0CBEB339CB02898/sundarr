"""Plugin Activation 生命周期测试。"""

import asyncio
import logging

import pytest

from sundarr.app.plugins.base import PluginManifest, PluginType
from sundarr.app.plugins.runtime import (
    ActivationStatus,
    MissingCapabilityError,
    PluginActivation,
    PluginContext,
    PluginContextClosedError,
)

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def manifest() -> PluginManifest:
    return PluginManifest(
        id="example-source",
        name="示例搜索源",
        version="1.0.0",
        plugin_type=PluginType.SOURCE,
        description="用于测试 Activation 生命周期",
        author="Sundarr",
        homepage_url="https://example.com",
        adapter_api_version="1.0",
        entry="example:create_source",
        config_schema={},
    )


async def test_context_require_provide_and_config_are_read_only() -> None:
    http_client = object()
    context = PluginContext(
        "example-source",
        capabilities={"http_client": http_client},
        plugin_config={"base_url": "https://example.com"},
    )

    assert context.require("http_client") is http_client
    assert context.plugin_config["base_url"] == "https://example.com"

    context.provide("source.example", "source-instance")
    assert context.require("source.example") == "source-instance"
    assert context.provided_capabilities == {"source.example": "source-instance"}

    with pytest.raises(TypeError):
        context.plugin_config["base_url"] = "https://invalid.example"  # type: ignore[index]
    with pytest.raises(ValueError, match="能力名称冲突"):
        context.provide("http_client", object())


async def test_activation_waits_when_required_capability_is_missing(
    manifest: PluginManifest,
) -> None:
    context = PluginContext(manifest.id)
    activation = PluginActivation(
        manifest=manifest,
        context=context,
        required_capabilities=["source_registry", "http_client"],
    )

    with pytest.raises(MissingCapabilityError) as error:
        activation.begin_validation()

    assert error.value.missing == ("http_client", "source_registry")
    assert activation.status == ActivationStatus.WAITING
    assert "http_client" in (activation.error or "")


async def test_activation_success_seals_context(manifest: PluginManifest) -> None:
    context = PluginContext(
        manifest.id,
        capabilities={"source_registry": object()},
    )
    activation = PluginActivation(
        manifest=manifest,
        context=context,
        repository_id="repo-1",
        commit_hash="abc123",
        required_capabilities=["source_registry"],
    )

    activation.begin_validation()
    context.provide("source.example", "source-instance")
    activation.activate("plugin-instance")

    assert activation.status == ActivationStatus.ACTIVE
    assert activation.instance == "plugin-instance"
    assert activation.provided_capabilities["source.example"] == "source-instance"
    assert activation.activated_at is not None
    with pytest.raises(PluginContextClosedError):
        context.register_cleanup(lambda: None)


async def test_dispose_runs_cleanup_once_in_lifo_order(
    manifest: PluginManifest,
) -> None:
    calls: list[str] = []
    context = PluginContext(manifest.id)

    async def async_cleanup() -> None:
        calls.append("async-second")

    context.register_cleanup(lambda: calls.append("sync-first"))
    context.register_cleanup(async_cleanup)
    activation = PluginActivation(manifest=manifest, context=context)
    activation.begin_validation()
    activation.activate(object())

    await activation.dispose()
    await activation.dispose()

    assert calls == ["async-second", "sync-first"]
    assert activation.status == ActivationStatus.DISPOSED
    assert activation.disposed_at is not None
    assert context.cleanup_count == 0


async def test_concurrent_dispose_waits_for_same_cleanup(
    manifest: PluginManifest,
) -> None:
    calls: list[str] = []
    cleanup_started = asyncio.Event()
    allow_cleanup = asyncio.Event()
    context = PluginContext(manifest.id)

    async def cleanup() -> None:
        cleanup_started.set()
        await allow_cleanup.wait()
        calls.append("cleanup")

    context.register_cleanup(cleanup)
    activation = PluginActivation(manifest=manifest, context=context)
    activation.begin_validation()
    activation.activate(object())

    first = asyncio.create_task(activation.dispose())
    await cleanup_started.wait()
    second = asyncio.create_task(activation.dispose())
    await asyncio.sleep(0)
    assert not second.done()

    allow_cleanup.set()
    await asyncio.gather(first, second)

    assert calls == ["cleanup"]
    assert activation.status == ActivationStatus.DISPOSED


async def test_cleanup_failure_does_not_block_remaining_callbacks(
    manifest: PluginManifest,
    caplog: pytest.LogCaptureFixture,
) -> None:
    calls: list[str] = []
    context = PluginContext(manifest.id)
    context.register_cleanup(lambda: calls.append("first"))

    def failing_cleanup() -> None:
        calls.append("failing")
        raise RuntimeError("清理失败")

    context.register_cleanup(failing_cleanup)
    context.register_cleanup(lambda: calls.append("last"))
    activation = PluginActivation(manifest=manifest, context=context)
    activation.begin_validation()
    activation.activate(object())

    with caplog.at_level(logging.ERROR):
        await activation.dispose()

    assert calls == ["last", "failing", "first"]
    assert len(activation.cleanup_errors) == 1
    assert str(activation.cleanup_errors[0]) == "清理失败"
    assert activation.status == ActivationStatus.DISPOSED


async def test_failed_candidate_cleans_side_effects(manifest: PluginManifest) -> None:
    calls: list[str] = []
    context = PluginContext(manifest.id)
    context.register_cleanup(lambda: calls.append("cleanup"))
    activation = PluginActivation(manifest=manifest, context=context)
    activation.begin_validation()

    await activation.fail(RuntimeError("健康检查失败"))

    assert calls == ["cleanup"]
    assert activation.status == ActivationStatus.FAILED
    assert activation.error == "健康检查失败"
    with pytest.raises(PluginContextClosedError):
        context.provide("late", object())


async def test_context_and_manifest_plugin_id_must_match(
    manifest: PluginManifest,
) -> None:
    with pytest.raises(ValueError, match="必须与 manifest.id 一致"):
        PluginActivation(
            manifest=manifest,
            context=PluginContext("another-plugin"),
        )
