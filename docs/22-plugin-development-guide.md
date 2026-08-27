# 外部插件开发指南

本文档面向 Sundarr 外部 Python 插件仓库开发者；当前可运行示例仍以 SOURCE 为主。更新时间：2026-08-27。

当前可运行 SDK 只承诺 flat v1 SOURCE 插件。通用 Manifest v2 已可解析和校验，但 v2 Activation、CATALOG_PROVIDER 和 WATCHLIST_PROVIDER 执行协议尚未接入；TRANSFER_DRIVER 和 NOTIFICATION 是后续扩展。

---

## 1. 最小结构

```text
my-source-repository/
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

## 2. 当前 flat v1 清单

```toml
id = "example-source"
name = "示例搜索源"
version = "0.1.0"
plugin_type = "source"
description = "用于演示 Sundarr Source Adapter。"
entry = "my_source.adapter:create_source"
adapter_api_version = 1

```

当前可运行模板继续使用 flat v1。新仓库可以按 `manifest_version = 2` 和 `[[plugins]]` 编写并通过静态解析，但在 v2 Activation 落地前不能实际启用；目标格式及版本化 `requires/provides` 以 `docs/20-plugin-manifest-spec.md` 为准。

---

## 3. 入口协议

入口可以返回一个或多个 `SourceModel`：

```python
def create_source() -> SourceModel:
    ...

def create_sources() -> list[SourceModel]:
    ...
```

每个 Source 必须返回 `RawSearchItem`，不能返回 ORM `Resource`、`ResourceLink` 或 `TransferTask`。

---

## 4. 职责边界

插件负责：

```text
请求目标站点。
解析列表页和必要详情页。
输出 RawSearchItem。
提供离线 fixture 测试。
对站点异常给出可诊断错误。
```

Core 负责：

```text
链接提取、标准化、去重和排序。
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

Phase 10.1 后，插件应通过 `PluginContext` 获取受控服务并注册清理：

```python
def apply(context, config):
    source = create_source(context.http_client, config)
    context.register_source(source)
```

插件不得在 import 阶段启动线程、创建长期连接、注册全局回调或执行网络请求。所有长期副作用必须发生在 Activation 内，并有对应 cleanup。

---

## 6. 测试要求

```text
默认测试只使用 fixture，不访问实时网站。
覆盖正常解析、空结果、页面变化、超时和无效链接。
覆盖 SourceModel.id 与 RawSearchItem.source_id 一致性。
多 Source 仓库覆盖全部入口返回值。
不得把 tests/test_*.py 写成导入时执行真实 HTTP 请求的脚本。
实时站点测试放入显式集成测试或独立手动命令。
```

---

## 7. 发布和更新

```text
仓库使用正常 Git commit。
Sundarr 只运行数据库中锁定的 current_commit。
fetch/check-update 不等于应用更新。
候选 commit 通过验证后才切换。
失败时必须允许继续使用 previous/current 稳定版本。
```
