# 外部搜索源仓库接入规范

本文档定义 Sundarr 正在实施的外部 Git 搜索源仓库架构、生命周期和验收标准。

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
系统读取通用 `sundarr_plugin.toml`；迁移期兼容当前 flat v1 SOURCE 清单。
系统动态加载清单中一个或多个插件声明的入口。
系统把加载成功的 SourceModel 注入运行时 Source Registry。
Web Console 展示加载成功、加载失败、来源仓库、来源 commit 和测试日志。
```

不允许：

```text
Web Console 上传 Python 文件。
Web Console 在线编辑 Source Adapter。
数据库保存可执行 Python 代码。
配置文件保存可执行 Python 代码。
启动时无条件 pull 远程默认分支并执行最新代码。
搜索源 Adapter 直接访问 Sundarr 内部数据库、服务对象或任务状态机。
```

---

## 3. 模型分层

仓库与插件实例不是一对一关系。一个外部仓库可以声明多个插件实例，例如同一个豆瓣仓库可以交付：

```text
douban-catalog    -> PluginType.CATALOG_PROVIDER
douban-watchlist  -> PluginType.WATCHLIST_PROVIDER
```

两个实例必须具有独立配置、启用状态、健康检查和错误状态。每个实例保留一个主 `PluginType`，`provides` 用于声明该类型下的细粒度能力。当前文档后续以已实现的 `SOURCE` 仓库链路为主；Phase 10.1 复用通用仓库与 Activation 基础设施接入另外两种类型。

外部仓库接入不直接扩展当前 `SourceModel` 承载所有信息。持久声明、加载结果、运行 Activation 和执行协议分层：

```text
PluginManifest
  来自 sundarr_plugin.toml；v2 可声明多个插件，描述 id、主类型、入口、兼容版本、配置 schema 和能力。

LoadedPlugin
  单个插件声明的加载结果，描述来源仓库、commit、路径、加载状态、错误和类型运行实例。

PluginActivation
  具体 commit 的运行实例，描述依赖、提供能力、状态、错误和可逆清理栈。

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

### 3.1 Adapter 输出边界

外部搜索源 Adapter 不直接产出数据库模型，也不负责收藏或入库。

Adapter 只负责产出搜索原始项：

```text
RawSearchItem
  source_id
  source_type
  raw_title
  raw_url
  raw_content
  published_at
  fetched_at
  metadata
```

Adapter 可在 `metadata` 中填写约定 key 以提供结构化信息（可选，不强制）：

```text
year       → int，发行年份
quality    → str，画质/版本标签
link_name  → str，具体链接的展示名称
```

Core 优先读取这些 key，缺失时自动 fallback 到正则提取。详见 `docs/04-source-adapter-spec.md` 第 4.1 节。

Sundarr Core 负责：

```text
RawSearchItem -> ResourceCandidate / ResourceLinkResult 标准化
ResourceCandidate / ResourceLinkResult 聚合、去重、链接检测
查询收藏库，为实时搜索结果附加 is_favorited 标记
用户主动收藏时，才写入 Resource / ResourceLink
```

禁止 Adapter：

```text
直接访问数据库。
直接创建 Resource / ResourceLink。
直接读取或修改收藏状态。
直接创建 TransferTask。
```

### 3.2 Resource / ResourceLink 抽象边界

后续资源抽象层采用以下边界：

```text
Resource 表示“这是什么资源”，用于用户收藏资源和作为收藏链接的父记录。
ResourceLink 表示“这个资源的一个具体链接/版本”，用于用户收藏链接。
/search 永远实时调用 Source Adapter，不用收藏库替代搜索。
收藏库只用于收藏列表、收藏详情、刷新收藏项，以及给实时搜索结果打已收藏标记。
```

该边界用于保证外部搜索源仓库接入后：

```text
Adapter SDK 不依赖数据库表结构。
外部源代码不需要知道收藏功能。
SearchService 可以在内置源和外部源之间保持统一管线。
资源收藏与搜索源加载生命周期解耦。
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

通用 v2 目标结构：

```text
sundarr-sources/
  sundarr_plugin.toml
  sources/
    example/
      adapter.py
      tests/
        fixtures/
  docs/
```

清单示例：

```toml
manifest_version = 2

[[plugins]]
id = "example"
name = "示例搜索源"
version = "0.1.0"
plugin_type = "source"
description = "用于验证加载流程的示例源。"
homepage_url = "https://example.invalid"
plugin_api_version = "1.0"
entry = "sources.example.adapter:activate"

[plugins.runtime]
requires = ["core.http.v1", "core.source_registry.v1"]
provides = ["source.search.v1"]
```

当前 `PluginLoader` 已实现仓库根目录 flat v1 与通用 v2 `sundarr_plugin.toml` 解析。flat v1 SOURCE 仍可通过旧入口加载；v2 在类型专用 Activation 接入前只解析和校验，不按 v1 无参数入口执行。

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
flat v1 的 SourceModel.id 必须与 Manifest id 一致；v2 入口通过对应 plugin_id 注册 SourceModel。
RawSearchItem.source_id 必须与 SourceModel.id 一致。
搜索源 id 全局唯一，冲突时后加载项不得覆盖先加载项。
```

---

## 6. Sundarr Core 改造步骤

### 6.1 新增配置模型

已实现为通用插件系统模型（`sundarr/app/models/plugin.py`）：

```text
PluginRepository — 插件仓库配置（原 SourceRepositoryConfig）
  id, name, repo_url, branch, current_commit, previous_commit
  auto_update, enabled, status (pending/loaded/error)
  last_error, last_checked_at, last_loaded_at

PluginConfig — 插件运行时配置
  id, plugin_id, plugin_type, config_data (JSON)
  enabled, status (active/disabled/error), repository_id

PluginLog — 插件日志
  id, plugin_id, level, message, details (JSON), timestamp
```

迁移：`0008_create_plugin_tables.py`

### 6.2 新增仓库管理器

已实现为 `PluginManager`（`sundarr/app/plugins/manager.py`）：

```text
add_repository          — 添加仓库并触发克隆
load_all_repositories   — 加载所有已启用仓库
update_repository       — 更新仓库配置和 commit
rollback_repository     — 回滚到 previous_commit
enable_plugin / disable_plugin
get_plugin_config / update_plugin_config
remove_repository       — 删除仓库及关联插件
```

规则：

```text
本地缓存目录不得位于应用代码目录内。
checkout 必须使用明确 commit。
fetch 不等于应用更新。
应用更新必须显式切换 current_commit。
```

### 6.3 新增清单解析器

将当前单清单解析器演进为通用 `PluginManifestParser`：

```text
识别 manifest_version；缺失时按 flat v1 SOURCE 解析。
读取 v2 的一个或多个 [[plugins]] 声明。
校验必填字段、PluginType、plugin_api_version 和 requires/provides。
校验清单和 entry 路径不能越界。
每个声明生成独立 LoadedPlugin。
```

### 6.4 新增加载器

已实现为 `PluginLoader`（`sundarr/app/plugins/loader.py`）：

```text
从本地缓存目录读取仓库清单。
加载 entry 指向的函数。
校验 PluginType 和必要接口。
生成 LoadedPlugin。
记录加载失败原因。
```

### 6.5 改造注册入口

已实现为 `PluginRegistry`（`sundarr/app/plugins/registry.py`）：

```text
register_builtin / register_external
get_plugin / get_plugins_by_type / get_all_plugins
unregister / clear
```

`sundarr.app.sources.registry.get_registered_sources()` 保持返回 `list[SourceModel]`，来源改为：

```text
外部仓库加载成功的源
```

现有 `SearchService` 不需要感知仓库、commit 或加载错误。

### 6.5.1 搜索源代码整理前置要求

在实现 Git Source Repository 模式前，先整理 Core 内部搜索源相关代码：

```text
保持 SourceModel 作为 Adapter API v1 的最小运行时协议。
保持 Source Adapter 只返回 RawSearchItem，不返回 ORM 模型。
把 ResourceCandidate / ResourceLinkResult 标准化逻辑留在 Core 搜索管线。
把收藏状态标记逻辑放在 Core 服务层，不放进 Adapter。
移除 /search 自动保存候选结果到资源库的行为。
```

验收要求：

```text
SearchService 调用内置源和未来外部源的方式一致。
Adapter 不感知 Resource / ResourceLink 是否入库。
收藏资源 / 收藏链接功能可以在不修改 Adapter 的情况下工作。
```

### 6.6 改造 SourceService 和 Web Console

SourceService 后续从 `LoadedPlugin` 中读取 SOURCE 类型的加载信息：

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

### 6.7 Plugin Activation Runtime

Sundarr Core 保持 Python，不依赖 Cordis 包。运行时借鉴 Cordis 的生命周期语义：

```text
PluginContext 暴露受控能力。
requires / provides 表达显式能力依赖。
PluginActivation 跟踪候选或 active 插件及 LIFO cleanup callbacks。
新 commit 先候选加载、配置校验和健康测试。
候选成功后原子替换旧 Activation。
候选失败时旧 Activation 和 current_commit 保持不变。
disable / rollback / remove / shutdown 必须释放插件副作用。
```

边界：

```text
Activation 只管理 API 进程内插件资源。
不替代 PostgreSQL、Redis、Alembic、Worker 状态机或 SMB 连接池。
外部 Python 插件仍是用户信任代码，不是沙箱代码。
```

媒体发现扩展边界：

```text
SOURCE 产出具体资源链接候选。
CATALOG_PROVIDER 产出规范化前的媒体目录候选。
WATCHLIST_PROVIDER 读取外部列表项，由 Core 负责定时调度、游标、重试和持久状态。
插件不得自行把长期同步循环作为 Activation 内定时器运行。
CATALOG_PROVIDER 必须声明支持的目录筛选能力；不支持的筛选不得静默丢弃。
CATALOG_PROVIDER 接收列表形式的 genres / regions；MVP Core 保证每个列表最多一个值。
目录分页由运行协议使用不透明 continuation token 表达；页码或无限滚动不是 Manifest 字段。
```

通用类型边界以 `docs/20-plugin-system.md` 为准。`CLOUD_PROVIDER`、`CRAWLER`、`LINK_VALIDATOR`、`LINK_EXTRACTOR` 和 `TASK_PROCESSOR` 不再作为 v2 顶层类型；链接提取和验证保留为 Core 或 SOURCE 内部细粒度能力。

### 6.8 启动恢复

```text
完成数据库迁移和 Core 服务初始化。
读取 enabled PluginRepository。
只从本地缓存加载数据库记录的 current_commit。
逐个创建 Activation，失败隔离。
激活完成后同步 sources 目录表。
启动时不自动 fetch 或执行远程最新代码。
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
可兼容读取 flat v1 sundarr_plugin.toml。
可读取通用 v2 sundarr_plugin.toml 的一个或多个插件声明。
可加载 SOURCE plugin_api_version = "1.0" 的 SourceModel。
加载失败时 API 仍可启动。
加载失败原因可在 Web Console 或 API 中查看。
SearchService 可聚合外部搜索源结果。
SourceService 可测试外部搜索源。
更新失败时可回滚 previous_commit。
更新失败时旧 Activation 继续工作，候选副作用全部清理。
禁用、回滚、删除和关闭时 cleanup 只执行一次。
应用重启后自动恢复 locked current_commit，再同步 sources 目录表。
数据库和配置不保存可执行 Python 代码。
默认不自动执行远程最新 commit。
pytest 覆盖 manifest 解析、路径越界防护、加载失败、id 冲突和搜索聚合。
```

---

## 9. 当前交付状态

截至 2026-08-27：

```text
已实现通用插件框架：
  PluginRepository / PluginConfig / PluginLog 数据模型（迁移 0008）
  plugins/ 模块：base.py (PluginType, LoadedPlugin)、registry.py、manager.py、loader.py
  /plugins API（仓库 CRUD、插件列表/详情/启用/禁用/配置、统计、加载全部）
  Git clone / fetch / checkout 基础实现
  SOURCE 入口返回 SourceModel 或 list[SourceModel] 并展开注册
  SeedHub 已从 Sundarr Core 移出
  tests/test_plugin_system.py
  目标 PluginType、通用 Manifest v2 多插件解析和 flat v1 SOURCE 兼容
  manifest_version、plugin_api_version、旧类型、重复 id、entry 和 requires/provides 校验
  tests/test_plugin_manifest.py

已完成：
  Phase 10.0 默认测试、迁移链、SMB 错误码和 Windows PID 质量收口

待实现：
  CATALOG_PROVIDER / WATCHLIST_PROVIDER 类型与最小执行契约
  v2 类型专用 Activation、Registry 和健康检查
  Phase 10.1 所需的最小插件加载、注册和健康检查
  完整候选切换、cleanup 和原子切换闭环
  启动自动加载 enabled 仓库的 locked current_commit
  多 Source 仓库所有 API 路径兼容
  外部 SeedHub 仓库配置、fixture 和端到端验收
  Web Console 插件管理页面
```
