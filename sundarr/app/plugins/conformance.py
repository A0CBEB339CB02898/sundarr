"""供外部插件仓库复用的公共合同回归入口。"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from sundarr.app.plugins.contracts import (
    CatalogItem,
    CatalogOperation,
    CatalogPage,
    CatalogProvider,
    CatalogQuery,
    MediaType,
    WatchlistPage,
    WatchlistProvider,
    WatchlistPullRequest,
)


class PluginConformanceError(RuntimeError):
    """插件声明能力与真实调用结果不一致。"""


@dataclass(frozen=True)
class CatalogConformanceProbe:
    """由真实插件测试提供的查询和详情样本。"""

    query: CatalogQuery
    detail_external_id: str | None = None
    detail_media_type: MediaType | None = None


@dataclass(frozen=True)
class ConformanceReport:
    plugin_id: str
    checks: Mapping[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "checks", MappingProxyType(dict(self.checks)))


async def run_catalog_provider_conformance(
    provider: CatalogProvider,
    probe: CatalogConformanceProbe,
) -> ConformanceReport:
    """按 Provider 实际声明能力执行真实请求并校验公共返回类型。"""

    if not isinstance(provider, CatalogProvider):
        raise PluginConformanceError("运行实例不符合 CatalogProvider 合同")
    capabilities = provider.describe_capabilities()
    if not capabilities.identity_namespaces:
        raise PluginConformanceError("真实目录插件必须声明至少一个 identity_namespace")
    checks: dict[str, int] = {}
    for operation in sorted(capabilities.operations, key=lambda item: item.value):
        try:
            if operation is CatalogOperation.SEARCH:
                if not probe.query.keyword:
                    raise PluginConformanceError("验证 search 时必须提供真实 keyword")
                page = await provider.search(probe.query)
            elif operation is CatalogOperation.TRENDING:
                page = await provider.trending(probe.query)
            elif operation is CatalogOperation.CATEGORIES:
                page = await provider.categories(probe.query)
            else:
                if not probe.detail_external_id:
                    raise PluginConformanceError("验证 detail 时必须提供真实 external_id")
                item = await provider.get_detail(
                    probe.detail_external_id,
                    probe.detail_media_type,
                )
                _validate_item(
                    item,
                    "detail",
                    identity_namespaces=capabilities.identity_namespaces,
                )
                checks[operation.value] = 1
                continue
        except PluginConformanceError:
            raise
        except Exception as exc:
            raise PluginConformanceError(
                f"插件 {provider.id} 的 {operation.value} 真实调用失败：{exc}"
            ) from exc
        checks[operation.value] = _validate_page(
            page,
            operation.value,
            identity_namespaces=capabilities.identity_namespaces,
        )
    return ConformanceReport(plugin_id=provider.id, checks=checks)


async def run_watchlist_provider_conformance(
    provider: WatchlistProvider,
    request: WatchlistPullRequest | None = None,
) -> ConformanceReport:
    """执行一次真实想看拉取并校验条目与游标合同。"""

    if not isinstance(provider, WatchlistProvider):
        raise PluginConformanceError("运行实例不符合 WatchlistProvider 合同")
    try:
        page = await provider.pull(request or WatchlistPullRequest())
    except Exception as exc:
        raise PluginConformanceError(f"插件 {provider.id} 的 pull 真实调用失败：{exc}") from exc
    if not isinstance(page, WatchlistPage):
        raise PluginConformanceError("pull 必须返回 WatchlistPage")
    for index, item in enumerate(page.items):
        _validate_item(item.subject, f"pull.items[{index}].subject")
    return ConformanceReport(plugin_id=provider.id, checks={"pull": len(page.items)})


def _validate_page(
    page: object,
    operation: str,
    *,
    identity_namespaces: frozenset[str],
) -> int:
    if not isinstance(page, CatalogPage):
        raise PluginConformanceError(f"{operation} 必须返回 CatalogPage")
    for index, item in enumerate(page.items):
        _validate_item(
            item,
            f"{operation}.items[{index}]",
            identity_namespaces=identity_namespaces,
        )
    return len(page.items)


def _validate_item(
    item: object,
    location: str,
    *,
    identity_namespaces: frozenset[str] | None = None,
) -> None:
    if not isinstance(item, CatalogItem):
        raise PluginConformanceError(f"{location} 必须是 CatalogItem")
    if identity_namespaces is not None:
        if item.external_id_provider is None:
            raise PluginConformanceError(f"{location} 必须声明 external_id_provider")
        if item.external_id_provider not in identity_namespaces:
            raise PluginConformanceError(
                f"{location} 的 external_id_provider 未包含在 Provider identity_namespaces 中"
            )
