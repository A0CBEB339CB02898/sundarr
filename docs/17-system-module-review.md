# 系统模块梳理

本文档描述 2026-08-26 的实际模块边界。历史 Phase 9 重构已经完成。

---

## 1. 模块总览

```text
Web Console
  -> FastAPI API
       -> Search / Favorites
            -> Source Registry
                 -> Python Plugin Activation Runtime
       -> Storage / Local Library / Remote Library / Sync
            -> TransferTask
                 -> Worker
                      -> SMB source -> .downloading -> verify -> rename -> cleanup

PostgreSQL：配置、目录、收藏和任务事实来源
Redis：健康、缓存和实时辅助，不是任务事实来源
```

---

## 2. Core 模块

### 2.1 API 与配置

```text
sundarr/app/main.py       FastAPI app、路由和生命周期
sundarr/app/config.py     bootstrap 配置
sundarr/app/db_admin.py   数据库创建、Alembic、默认设置和目录同步
sundarr/app/cli.py        API / Web / Worker 本地进程管理
```

Windows PID 文件已指向真实 API / Web / Worker 服务进程，停止逻辑会校验 Sundarr 进程树，避免误杀 PID 复用的外部进程。

### 2.2 搜索和收藏

```text
sources/base.py                 SourceModel 执行协议
sources/registry.py             运行时 Source 查询；当前无内置真实站点
services/search_service.py      并行搜索、标准化、去重、排序和链接检测
services/resource_library_service.py  收藏、取消收藏、收藏标记和刷新
api/search.py / api/resources.py
```

边界：搜索实时调用 Adapter；只有用户主动收藏才写 Resource / ResourceLink。

### 2.3 插件系统

```text
models/plugin.py          PluginRepository / PluginConfig / PluginLog
plugins/base.py           PluginType / PluginManifest / LoadedPlugin
plugins/loader.py         Git 缓存、commit checkout、manifest 和 Python entry
plugins/registry.py       运行时注册中心
plugins/manager.py        仓库和插件生命周期入口
api/plugins.py            插件管理 API
```

已完成：基础模型、加载、注册、仓库 CRUD、更新、回滚、配置和 SOURCE 列表展开。

待完成：PluginContext、PluginActivation、LIFO cleanup、候选验证、原子切换、启动自动恢复和 Web Console。

### 2.4 SMB 和媒体库

```text
storage/base.py / local.py / smb.py / pool.py
models/smb_connection.py
models/media_library.py
models/remote_media_library.py
services/smb_connection_service.py
services/media_library_service.py
services/remote_media_library_service.py
```

本地媒体库和远程媒体库都只引用 SMB connection 和目录，不重复保存凭据。

### 2.5 同步与 Worker

```text
models/sync.py              SyncBinding / SyncSeenFile
services/sync_service.py    扫描、稳定性判断和任务创建
models/transfer.py          TransferTask / TransferFile / TransferLog
services/transfer_service.py
worker.py                   process_sync_task 唯一同步执行路径
```

历史 Ingest、Download To Local 和单一 `storage.smb` 主链路已经删除。

---

## 3. Web Console

当前页面：

```text
/app/sources
/app/search
/app/favorites
/app/storage
/app/libraries
/app/remote-libraries
/app/transfers
/app/status
```

远程媒体库页面承载远程库和同步操作；当前没有独立 `/app/sync` 页面。插件仓库管理页面尚未实现。

---

## 4. 当前数据流

### 4.1 搜索

```text
enabled PluginRepository.current_commit
  -> PluginLoader
  -> PluginActivation（Phase 10.1）
  -> Source Registry
  -> SearchService
  -> ResourceCandidate / ResourceLinkResult
  -> 收藏标记
  -> API / Web Console
```

当前运行时尚不会在启动时自动完成前三步；数据库未配置仓库时搜索源为 0。

### 4.2 同步

```text
RemoteMediaLibrary
  -> SyncBinding
  -> scan / SyncSeenFile
  -> TransferTask(mode=sync)
  -> Worker
  -> source SMB stream
  -> target .downloading
  -> size verify
  -> rename
  -> optional source cleanup
```

---

## 5. 当前风险

```text
真实站点外部 Source 尚未完成端到端验收。
应用启动尚未自动激活 enabled 插件仓库。
插件更新尚未具备候选加载、健康检查、原子切换和失败回滚闭环。
真实 SMB 发布门仍需在目标 NAS 环境重复验收。
插件更新不是候选验证后的原子切换。
插件副作用没有统一清理栈。
Web Console 无法配置外部插件仓库。
README、历史汇总和部分规格曾存在状态漂移，已在本轮统一。
```

---

## 6. 下一步边界

```text
Phase 10.0：已完成质量基线收口。
Phase 10.1：当前执行 Python Plugin Activation Runtime。
Phase 10.2：外部 SeedHub 和 Web Console 仓库管理闭环。
发布前：真实 SMB 同步手动验收。
Phase 11：AI Friendly API 和可选 Cordis / DeepSeek Harness HTTP 桥接。
```

不进入近期主线：Alist、真实网盘 Provider、Cloud Direct Download、通知和 Crawler 插件。
