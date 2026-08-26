# Python 插件系统与 Activation Runtime

本文档定义 Sundarr 插件系统的当前实现、目标生命周期和边界。更新时间：2026-08-26。

---

## 1. 当前范围

当前必须完成的插件类型只有：

```text
SOURCE — 外部真实搜索源 Adapter。
```

`CLOUD_PROVIDER`、`NOTIFICATION`、`CRAWLER`、`LINK_VALIDATOR`、`LINK_EXTRACTOR` 和 `TASK_PROCESSOR` 可以保留枚举或设计扩展点，但不代表已经实现，更不属于近期主线。

插件代码使用 Python。Sundarr 不依赖 Cordis 包，不运行 Node.js 插件宿主。

---

## 2. 已实现组件

```text
PluginRepository / PluginConfig / PluginLog 数据模型
PluginManifest / LoadedPlugin / PluginType
PluginLoader：Git clone、fetch、checkout、清单解析和 Python entry 加载
PluginManager：仓库新增、加载、更新、回滚、删除、配置和启停
PluginRegistry：运行时注册、查询和注销
PluginContext：只读配置、Core 能力读取、插件能力提供和 cleanup 登记
PluginActivation / ActivationStatus：依赖等待、候选校验、激活、失败和释放状态
同步/异步 cleanup 的 LIFO、失败续跑和并发幂等释放
/plugins API
SOURCE 入口返回 SourceModel 或 list[SourceModel]
```

当前缺口（Phase 10.2 在媒体发现中心最小闭环后恢复）：

```text
启动时未自动加载数据库中的 enabled 仓库。
PluginContext 尚未接入受控 HTTP client 和 source_registry 注册动作。
manifest 尚未解析 requires / provides。
更新过程会直接操作当前注册中心，不是候选验证后的原子切换。
多 Source 仓库的部分 API 响应仍按单 LoadedPlugin 处理。
Web Console 没有仓库管理页面。
当前默认数据库没有仓库，运行时搜索源为 0。
```

---

## 3. Cordis 启发的运行时模型

Cordis 在本项目中是设计思想来源，不是运行时依赖。

### 3.1 PluginContext

`PluginContext` 是插件访问 Core 能力的唯一入口。当前已实现 logger、只读 `plugin_config`、通用 `require/provide` 和 `register_cleanup`；下一单元接入受控 HTTP 与 Source 注册动作：

```text
logger                                             已实现
plugin_config                                      已实现
require(name) / provide(name, value)              已实现
register_cleanup(callback)                        已实现
http_client 或受控 HTTP client factory             待接入
register_source(source) -> cleanup callback       待接入
```

禁止通过 Context 暴露：

```text
任意数据库 Session
SMB 密码或全量敏感配置
Worker 私有函数
全局任务状态机可写对象
```

### 3.2 能力依赖

插件可以声明：

```text
requires — 激活前必须存在的能力。
provides — 激活成功后提供的能力。
```

SOURCE v1 默认要求 `source_registry`，可选要求受控 `http_client`。依赖不满足时不得执行插件入口。

### 3.3 PluginActivation

Activation 是一次具体插件版本的运行实例：

```text
plugin_id
repository_id
commit_hash
manifest
instance
status
provided_capabilities
cleanup_callbacks
error
activated_at
```

推荐状态：

```text
candidate -> validating -> active
candidate/validating -> failed
active -> disposing -> disposed
依赖缺失 -> waiting
```

上述状态已在 `sundarr/app/plugins/runtime.py` 落地；不得把 repository 的下载状态与 Activation 运行状态混为一谈。

### 3.4 可逆清理

插件通过 Context 产生的注册和资源必须返回清理函数。Activation 在以下场景按 LIFO 顺序执行一次清理：

```text
disable
update 成功切换后
rollback 成功切换后
remove_repository
应用关闭
依赖能力撤回
```

cleanup 失败应记录日志并继续清理剩余资源，不能恢复已经完成的旧副作用。

### 3.5 候选加载和原子切换

```text
fetch 远程信息
checkout 明确 commit 到本地缓存
构建 candidate Activation
解析和校验 manifest/config/requires
加载 Python entry
执行插件健康测试
准备提供能力但不覆盖 active
原子替换 registry 映射
释放旧 Activation
提交 current_commit / previous_commit 和状态
```

候选失败时：

```text
旧 active Activation 继续工作。
current_commit 不切换。
候选副作用全部清理。
错误写入 PluginLog / repository last_error。
```

---

## 4. 启动顺序

```text
加载 bootstrap 配置
连接数据库并执行 Alembic
初始化 Core 能力
读取 enabled PluginRepository
从本地缓存加载每个 current_commit
激活成功插件
同步 sources 目录表
启动对外 API ready 状态
```

约束：

```text
启动时不自动 fetch 或执行远程最新 commit。
单个插件失败不阻止 API 启动。
没有 Source 时 API 可以健康启动，但 /health 或插件诊断必须能表达“搜索能力未配置”。
```

---

## 5. 进程边界

API 和 Worker 是不同进程，各自需要明确的插件能力：

```text
API 进程需要 SOURCE 插件执行搜索。
Worker 当前不需要加载 SOURCE 插件。
未来若出现 Worker 插件，必须单独定义跨进程配置和状态恢复，不能复用内存 Activation 假装共享。
```

---

## 6. 安全边界

```text
外部 Python 插件是用户显式信任代码。
锁定 commit 提供可追踪性，不提供沙箱隔离。
数据库和 Web Console 不保存、上传或编辑可执行 Python 代码。
插件日志必须脱敏。
仓库路径、manifest 路径和 entry module 必须有越界保护。
```

如果未来需要运行不可信插件，应使用独立进程/容器和 RPC 协议另行设计，不能把 PluginContext 当安全边界。

---

## 7. 验收标准

```text
默认 pytest 覆盖 Activation 成功、失败、清理顺序、重复清理和原子切换。
更新失败时旧 Source 仍可被 SearchService 调用。
禁用、删除和回滚后 registry 与数据库状态一致。
重启只加载 locked current_commit。
一个仓库返回多个 Source 时全部注册、展示和清理。
插件失败不影响 /health 和其他插件。
```

---

## 8. 与 Cordis / DeepSeek Harness 的关系

Phase 11 后可以维护独立的 TypeScript 桥接插件：

```text
Cordis / DeepSeek Harness plugin -> Sundarr AI Tool HTTP API
```

该桥接不进入 Sundarr Core，不与 Python PluginActivation 共用进程，也不访问数据库、SMB 或 Worker 内部对象。
