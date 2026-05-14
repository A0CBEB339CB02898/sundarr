# 外部搜索源仓库接入规范

本文档定义 Sundarr 后续接入外部 Git 搜索源仓库的目标架构、改造步骤和验收标准。

---

## 1. 目标

Sundarr Core 与真实搜索源代码分离：

```text
Sundarr Core 只保留 Source Adapter SDK、加载框架、搜索管线和 Web Console。
真实搜索源代码集中放在独立 Git 仓库中。
Sundarr 只保存搜索源仓库地址、分支和锁定 commit。
系统从本地缓存中的已锁定 commit 加载搜索源，不默认执行远程最新代码。
Web Console 负责配置仓库、检查更新、应用更新、回滚、测试和诊断。
```

该模式命名为：

```text
Git Source Repository 模式
```

---

## 2. 设计边界

允许：

```text
用户配置一个或多个可信 Git 搜索源仓库。
系统 clone / fetch 搜索源仓库到本地缓存目录。
系统读取仓库清单和单个搜索源清单。
系统动态加载清单声明的 Adapter 入口。
系统把加载成功的 SourceModel 注入运行时 Source Registry。
Web Console 展示加载成功、加载失败、来源仓库、来源 commit 和测试日志。
```

不允许：

```text
Web Console 上传 Python 文件。
Web Console 在线编辑 Source Adapter。
数据库保存可执行 Python 代码。
配置文件保存可执行 Python 代码。
启动时无条件 pull 远程 main 并执行最新代码。
搜索源 Adapter 直接访问 Sundarr 内部数据库、服务对象或任务状态机。
```

---

## 3. 模型分层

外部仓库接入不直接扩展当前 `SourceModel` 承载所有信息，而是分三层：

```text
SourceManifest
  来自 source.toml，描述搜索源 id、名称、入口、兼容版本和运行约束。

LoadedSource
  系统加载后的结果，描述来源仓库、commit、路径、加载状态、错误和 SourceModel。

SourceModel
  SearchService 真正调用的最小执行接口，只包含 id、展示字段和 search/test 函数。
```

原因：

```text
SearchService 不需要 repo_url、commit、加载错误或更新状态。
加载失败时可能无法得到 SourceModel。
配置 schema、来源信息和执行函数生命周期不同。
保持 SourceModel 轻量可以兼容现有 SeedHub 和搜索管线。
```

---

## 4. 外部仓库结构

推荐独立仓库名：

```text
sundarr-sources
```

当前确认的远程仓库地址：

```text
https://github.com/A0CBEB339CB02898/sundarr-sources.git
```

推荐结构：

```text
sundarr-sources/
  sundarr_sources.toml
  sources/
    example/
      source.toml
      adapter.py
      tests/
        fixtures/
  docs/
```

根清单示例：

```toml
version = 1
name = "sundarr-sources"
description = "Sundarr 外部搜索源仓库。"

[sources.example]
path = "sources/example"
enabled = true
```

单源清单示例：

```toml
id = "example"
name = "示例搜索源"
description = "用于验证加载流程的示例源。"
homepage_url = "https://example.invalid"
adapter_api_version = 1
entry = "adapter:get_source"

[compatibility]
min_sundarr_version = "0.1.0"

[runtime]
timeout_seconds = 10
rate_limit_per_minute = 60
```

---

## 5. Adapter API v1

当前 `SourceModel` 作为 Adapter API v1 的运行时协议：

```python
@dataclass(frozen=True)
class SourceModel:
    id: str
    name: str
    description: str
    homepage_url: str
    search_function: SearchFunction
    test_function: SourceTestFunction | None = None
```

入口函数允许：

```python
def get_source() -> SourceModel: ...
def get_sources() -> list[SourceModel]: ...
```

加载规则：

```text
adapter_api_version 必须受当前 Sundarr 支持。
entry 必须是 module:function 格式。
入口返回值必须是 SourceModel 或 list[SourceModel]。
SourceModel.id 必须与 source.toml 中的 id 一致。
RawSearchItem.source_id 必须与 SourceModel.id 一致。
搜索源 id 全局唯一，冲突时后加载项不得覆盖先加载项。
```

---

## 6. Sundarr Core 改造步骤

### 6.1 新增配置模型

新增 `SourceRepositoryConfig`：

```text
id
name
repo_url
branch
current_commit
previous_commit
auto_update
enabled
last_checked_at
last_loaded_at
last_error
```

配置可以保存到 settings 或后续独立表。MVP 初版可先支持一个仓库。

### 6.2 新增仓库管理器

新增 `SourceRepositoryManager`：

```text
clone_repo
fetch_repo
checkout_commit
get_current_commit
check_updates
rollback
```

规则：

```text
本地缓存目录不得位于应用代码目录内。
checkout 必须使用明确 commit。
fetch 不等于应用更新。
应用更新必须显式切换 current_commit。
```

### 6.3 新增清单解析器

新增 `SourceManifestParser`：

```text
读取 sundarr_sources.toml。
读取每个 source.toml。
校验必填字段。
校验路径不能越界。
校验 entry 格式。
```

### 6.4 新增加载器

新增 `SourceLoader`：

```text
把搜索源目录加入受控 import 范围。
加载 entry 指向的函数。
调用 get_source() 或 get_sources()。
校验 SourceModel。
生成 LoadedSource。
记录加载失败原因。
```

### 6.5 改造注册入口

`sundarr.app.sources.registry.get_registered_sources()` 保持返回 `list[SourceModel]`，来源改为：

```text
内置源
外部仓库加载成功的源
```

现有 `SearchService` 不需要感知仓库、commit 或加载错误。

### 6.6 改造 SourceService 和 Web Console

SourceService 后续需要读取 `LoadedSource`：

```text
已加载搜索源列表
加载失败搜索源列表
来源仓库
来源 commit
source_path
adapter_api_version
load_status
load_error
测试搜索日志
```

Web Console 后续页面：

```text
搜索源仓库设置
检查更新
应用更新
回滚
刷新加载
已加载搜索源
加载失败搜索源
测试搜索
```

---

## 7. 安全策略

默认策略：

```text
只加载用户显式配置的仓库。
只执行本地缓存中已 checkout 的锁定 commit。
不默认自动更新并执行远程最新代码。
加载失败不影响 API 启动。
单个搜索源异常不影响整体搜索。
日志不得输出 Cookie、Token、密码或私有链接。
```

后续增强：

```text
支持仓库允许列表。
支持插件签名或 checksum。
支持 Adapter 独立进程隔离。
支持 per-source timeout 和熔断。
```

---

## 8. 验收标准

外部搜索源仓库模式完成时必须满足：

```text
可配置搜索源仓库地址和分支。
可 clone / fetch 仓库。
可记录并展示 current_commit。
可读取 sundarr_sources.toml。
可读取 source.toml。
可加载 adapter_api_version = 1 的 SourceModel。
加载失败时 API 仍可启动。
加载失败原因可在 Web Console 或 API 中查看。
SearchService 可聚合外部搜索源结果。
SourceService 可测试外部搜索源。
更新失败时可回滚 previous_commit。
数据库和配置不保存可执行 Python 代码。
默认不自动执行远程最新 commit。
pytest 覆盖 manifest 解析、路径越界防护、加载失败、id 冲突和搜索聚合。
```

---

## 9. 当前交付状态

截至本文档创建时：

```text
已在上层目录创建 sundarr-sources 独立项目模板。
已包含 README、LICENSE、pyproject.toml、仓库清单、示例源和开发文档。
Sundarr Core 尚未实现 Git 仓库加载器。
当前 SourceModel 可作为 Adapter API v1 保留。
后续实现应优先保持 SearchService 兼容，不破坏现有内置源。
```
