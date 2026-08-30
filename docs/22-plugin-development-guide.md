# 外部插件开发指南

本文档面向 Sundarr 外部 Python 插件仓库开发者。更新时间：2026-08-30。

当前生产仓库管理入口同时支持 flat v1 SOURCE 兼容和通用 Manifest v2。三类 MVP 公共合同、Runtime Registry、仓库级候选原子切换、Manager/API 接入和 API/Worker 启动恢复已由本地 fixture 验证，SOURCE、CATALOG_PROVIDER 和 WATCHLIST_PROVIDER 均可通过生产配置启用。TRANSFER_DRIVER 和 NOTIFICATION 是后续扩展。

---

## 1. 最小结构

```text
my-plugin-repository/
  sundarr_plugin.toml
  my_source/
    __init__.py
    adapter.py
  tests/
    fixtures/
    test_adapter.py
```

参考模板：`examples/source-plugin-template/`。

---

## 2. Manifest 选择

```toml
id = "example-source"
name = "示例搜索源"
version = "0.1.0"
plugin_type = "source"
description = "用于演示 Sundarr Source Adapter。"
entry = "my_source.adapter:create_source"
adapter_api_version = 1

```

flat v1 只用于兼容历史 SOURCE 仓库。所有新插件和官方仓库迁移必须使用 `manifest_version = 2` 与 `[[plugins]]`；v2 已支持真实 Activation、仓库级原子切换和启动恢复。完整格式及版本化 `requires/provides` 以 `docs/20-plugin-manifest-spec.md` 为准。

---

## 3. 入口协议

SOURCE 入口返回 `SourceModel`；CATALOG_PROVIDER 返回 `CatalogProvider`；WATCHLIST_PROVIDER 返回 `WatchlistProvider`。v2 每个声明只有一个主类型和独立 `plugin_id`：

```python
def create_source() -> SourceModel:
    ...

def create_sources() -> list[SourceModel]:
    ...

def create_catalog_provider(context) -> CatalogProvider:
    ...

def create_watchlist_provider(context) -> WatchlistProvider:
    ...
```

每个 Source 必须返回 `RawSearchItem`，不能返回 ORM `Resource`、`ResourceLink` 或 `TransferTask`。

目录 Provider 返回 `CatalogItem` / `CatalogPage`，想看 Provider 返回 `WatchlistItem` / `WatchlistPage`。`CatalogItem.external_id_provider` 应填写稳定身份命名空间，例如 `douban`；TMDb 电影与剧集 ID 应分别使用 `tmdb.movie`、`tmdb.tv`，因为只写 `tmdb` 可能把不同媒体子域的同号 ID 错误合并。目录 Provider 还必须在 `CatalogCapabilities.identity_namespaces` 声明自己能回查的稳定命名空间。Core 同时保存插件 ID 别名，跨插件精确合并依赖 `external_ids` 中相同的稳定平台 ID，不得只靠标题静默合并。

---

## 4. 职责边界

插件负责：

```text
请求目标平台。
解析列表、搜索、详情或想看响应。
输出对应类型的公共合同对象。
提供离线 fixture 测试。
对站点异常给出可诊断错误。
```

Core 负责：

```text
媒体身份匹配、最小快照、缓存降级、想看游标和调度。
SOURCE 链接提取、标准化、去重和排序。
链接有效性检测。
收藏标记和收藏持久化。
任务创建、数据库和 SMB。
```

插件禁止：

```text
直接访问 Sundarr 数据库。
创建或修改任务。
读取 SMB 凭据。
在仓库中保存 Cookie、Token 或真实用户凭据。
依赖 Web Console 在线编辑代码。
```

---

## 5. 生命周期约定

v2 插件入口接收 `PluginContext`，创建并返回合同实例。Registry 注册和按实例身份保护的注销由 Core 完成；插件只登记自己创建的连接、订阅或回调等副作用：

```python
def activate(context):
    client = create_site_client(
        context.require("core.http.v1"),
        context.plugin_config,
    )
    context.register_cleanup(client.close)
    return create_source(client)
```

插件只能 `require()` Manifest 中明确声明的 Core 能力。可选动态健康检查使用无参数 `health_check()`，返回 `PluginHealthResult`；没有动态检查时 Core 仍执行类型合同、ID、能力描述和 provides 一致性检查。

插件不得在 import 阶段启动线程、创建长期连接、注册全局回调或执行网络请求。所有长期副作用必须发生在 Activation 内，并有对应 cleanup。

---

## 6. 测试要求

```text
默认 pytest 使用 fixture 和离线测试替身，不访问实时网站。
覆盖正常解析、空结果、页面变化、超时和无效链接。
覆盖 SourceModel.id 与 RawSearchItem.source_id 一致性。
多 Source 仓库覆盖全部入口返回值。
不得把 tests/test_*.py 写成导入时执行真实 HTTP 请求的脚本。
实时站点测试放入显式集成测试或独立手动命令。
每个真实插件新增或修改后必须运行实时集成测试；首个 TMDb 插件必须覆盖搜索、热门、分类、详情和海报字段。
```

外部仓库可以直接复用 Core 的公共 conformance runner，让真实请求按 Provider 声明能力逐项回归：

```python
from sundarr.app.plugins.conformance import (
    CatalogConformanceProbe,
    run_catalog_provider_conformance,
)
from sundarr.app.plugins.contracts import CatalogQuery, MediaType

report = await run_catalog_provider_conformance(
    provider,
    CatalogConformanceProbe(
        query=CatalogQuery(keyword="黑客帝国"),
        detail_external_id="603",
        detail_media_type=MediaType.MOVIE,
    ),
)
```

该 runner 不制造测试数据；查询词和详情 ID 由插件仓库的显式实时集成测试提供。默认离线 pytest 仍必须独立可重复，实时测试结果则负责发现 Core 合同与平台真实响应之间的偏差。

---

## 7. 发布和更新

```text
仓库使用正常 Git commit。
Sundarr 只运行数据库中锁定的 current_commit。
fetch/check-update 不等于应用更新。
候选 commit 通过验证后才切换。
失败时必须允许继续使用 previous/current 稳定版本。
```
