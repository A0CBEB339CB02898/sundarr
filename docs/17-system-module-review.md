# 系统模块梳理

本文档梳理 Sundarr 当前系统各模块的职责、关联关系和已知问题，并定义目标架构。

---

## 1. 目标模块分类

Sundarr 系统按职责分为以下模块：

### 1.1 媒体源

职责：接入真实媒体网站，提供搜索能力。

```text
每个真实网站通过一个代码型 Source Adapter 接入。
多个 Adapter 并发搜索，结果统一进入搜索模块。
Source 统一从代码注册表加载，不再由用户在 Web Console 中创建或配置。
Web Console 只读展示已安装 Adapter，并提供测试和错误查看入口。
```

关联：媒体源通过统一接口暴露给搜索模块。

### 1.2 搜索

职责：在多个媒体源中并发搜索，聚合结果。

```text
搜索是媒体源的统一调用入口。
一次搜索同时查询所有已启用的媒体源。
结果经过标准化、按真实链接去重、链接有效性检测和排序后返回。
当前搜索页只展示搜索结果，后续可接入保存到网盘和下载流程。
```

关联：搜索调用媒体源接口，结果写入资源库。

### 1.3 存储管理

职责：管理多个 SMB 连接配置。

```text
SMB 连接是媒体库和下载功能的基础。
存储管理不关心连接的用途（远程来源或本地目标），只负责连接的 CRUD、测试和热加载。
修改连接配置会中断使用该连接的运行中任务。
```

关联：媒体库和下载管理都引用存储管理中的 SMB 连接。

### 1.4 媒体库

职责：管理本地 NAS 上的媒体目录。

```text
媒体库是本地 NAS 上的逻辑目录，例如 movie / series / unclassified。
每个媒体库绑定到某个 SMB 连接下的本地目录。
媒体库是下载的目标，也是后续播放器/NFO 等功能的基础。
至少需要一个 unclassified 媒体库作为 fallback。
```

关联：媒体库引用存储管理中的 SMB 连接。远程媒体库通过 `target_library_id` 绑定到本地媒体库。

### 1.5 远程媒体库（网盘库）

职责：管理已挂载的远程目录（如网盘通过 SMB 暴露的目录），并配置同步参数。

```text
远程媒体库是通过 SMB 访问的远程目录，通常是网盘挂载目录。
远程媒体库绑定到某个 SMB 连接下的目录。
远程媒体库是下载的来源。
每个远程媒体库可绑定一个本地媒体库作为同步目标。
远程媒体库自带同步配置：scan_interval_seconds、stable_seconds、delete_source_after_success、delete_empty_source_dirs。
如果 target_library_id 为空，远程媒体库自动禁用同步。
```

关联：远程媒体库引用存储管理中的 SMB 连接，并通过 `target_library_id` 绑定到本地媒体库。

### 1.6 下载管理

职责：将远程媒体库的内容同步到本地媒体库。

```text
下载管理是系统的核心功能。
每个远程媒体库通过 target_library_id 绑定到一个本地媒体库。
Worker 定时扫描启用的远程媒体库，发现稳定文件后创建下载任务。
下载过程：从来源 SMB 读取 -> 写入 .downloading -> 校验 -> rename -> 按配置清理来源。
```

关联：Worker 从远程媒体库读取绑定关系和同步配置，执行下载任务。

### 1.7 系统状态

职责：展示 API、Worker、数据库、Redis 的运行状态。

```text
提供健康检查接口。
提供任务状态查询和日志查看。
提供 Worker 启停控制。
```

### 1.8 模块关系图

```text
┌─────────────┐    ┌──────────────┐
│   媒体源    │───>│     搜索     │
│ (Source     │    │ (Search      │
│  Adapter)   │    │  Service)    │
└─────────────┘    └──────┬───────┘
                          │
                          ▼
                   ┌──────────────┐
                   │   资源库     │
                   │ (Resource)   │
                   └──────────────┘

┌─────────────┐
│  存储管理   │
│ (SMB连接)   │
└──────┬──────┘
       │
       ├──> ┌──────────────┐
       │    │   本地媒体库  │ (NAS 目录)
       │    │ (MediaLib)   │
       │    └──────▲───────┘
       │           │ target_library_id
       │           │
       │    ┌──────┴───────┐    ┌──────────────┐
       │    │  远程媒体库   │───>│    Worker     │
       │    │ (RemoteLib)  │    │ (定时扫描)    │
       │    │ +同步配置    │    └──────────────┘
       │    └──────────────┘
       │           │
       └───────────┘ connection_id
```

---

## 2. 当前实现状态

### 2.1 当前代码结构

```text
sundarr/app/
├── config.py                      # 配置加载
├── cli.py                         # CLI 入口
├── db_admin.py                    # 数据库初始化、迁移、默认配置 seed
├── main.py                        # FastAPI app
├── worker.py                      # Worker 后台进程
├── core/
│   └── database.py                # SQLAlchemy engine/session
├── models/                        # 数据模型
│   ├── source.py                  # Source（媒体源）           ✓ 已实现
│   ├── resource.py                # Resource, ResourceLink    ✓ 已实现
│   ├── transfer.py                # TransferTask 等           ✓ 已实现
│   ├── setting.py                 # Setting（KV 配置）        ✓ 已实现
│   ├── smb_connection.py          # SmbConnection             ✓ 已实现
│   ├── media_library.py           # MediaLibrary              ✓ 已实现（本地）
│   ├── remote_media_library.py    # RemoteMediaLibrary        ✓ 已实现
│   ├── sync.py                    # SyncBinding, SyncSeenFile ✓ 已实现
│   └── download_to_local.py       # 历史 Binding, SeenFile    ✗ 旧模块，待删除
├── services/                      # 业务逻辑
│   ├── search_service.py          # 搜索聚合                  ✓ 已实现
│   ├── resource_library_service.py # 资源管理                 ✓ 已实现
│   ├── transfer_service.py        # TransferTask CRUD         ✓ 已实现
│   ├── smb_connection_service.py  # 多 SMB 连接               ✓ 已实现
│   ├── media_library_service.py   # 本地媒体库管理            ✓ 已实现
│   ├── remote_media_library_service.py # 远程媒体库管理       ✓ 已实现
│   ├── sync_service.py            # 同步绑定+扫描+任务创建    ✓ 已实现
│   ├── download_to_local_service.py # 历史同步实现            ✗ 旧模块，待删除
│   └── source_service.py          # 代码注册源只读查询/测试   ✓ 已实现
├── api/                           # API 路由
│   ├── search.py                  # 搜索                      ✓
│   ├── resources.py               # 资源                      ✓
│   ├── transfers.py               # 任务                      ✓
│   ├── smb_connections.py         # 多 SMB 连接               ✓
│   ├── media_libraries.py         # 本地媒体库                ✓
│   ├── remote_media_libraries.py  # 远程媒体库                ✓
│   ├── sync.py                    # 同步绑定                  ✓
│   ├── download_to_local.py       # 历史同步 API              ✗ 旧，待删除
│   ├── sources.py                 # 媒体源                    ✓
│   └── health.py                  # 健康检查                  ✓
├── storage/                       # 存储抽象
│   ├── base.py                    # StorageWriter ABC         ✓
│   ├── local.py                   # LocalWriter               ✓
│   └── smb.py                     # SmbWriter                 ✓
├── cloud/                         # 云盘抽象（可选扩展）
│   ├── base.py                    # CloudProvider ABC         ✓
│   └── local.py                   # LocalCloudProvider        ✓
├── sources/                       # Source Adapter 框架
│   ├── base.py                    # SourceModel               ✓
│   ├── registry.py                # 代码注册表                ✓
│   └── seedhub.py                 # 首个真实搜索源            ✓
└── parsers/
    └── link_extractor.py          # 网盘链接提取              ✓
```

### 2.2 当前数据流

```text
存储管理 (smb_connections)
    │
    ├──> 本地媒体库 (media_libraries) ──> 绑定到 SMB 连接 + 本地目录
    │
    └──> 远程媒体库 (remote_media_libraries.connection_id + base_path)
              │
              ▼
         同步管理 (sync_bindings)
              │
              ├── scan() -> sync_seen_files
              └── create_tasks() -> transfer_tasks (mode=sync)
                     │
                     ▼
                Worker
                     │
                     ├── 读来源 SMB (source_config_snapshot)
                     ├── 写目标 SMB (storage_config_snapshot)
                     └── .downloading -> verify -> rename -> 清理来源
```

---

## 3. 已知问题

### 3.1 历史 Download To Local / Ingest 模块仍有残留

| 文件 | 状态 |
|---|---|
| `models/download_to_local.py` | 旧，已被 `models/sync.py` 替代 |
| `services/download_to_local_service.py` | 旧，已被 `sync_service.py` 替代 |
| `api/download_to_local.py` | 旧，已被 `api/sync.py` 和 `api/remote_media_libraries.py` 替代 |
| `worker.py` process_dtl_task | 历史命名，需统一为 process_sync_task |
| Web Console 旧 ingest / download-to-local 代码 | 旧，需统一到 `/app/remote-libraries` 和 `/app/sync` |

**问题**：文档和代码命名不统一，后续维护容易误判主链路。

### 3.2 旧 storage.smb 兼容入口仍需清理

| 模块 | 存储方式 | 用途 |
|---|---|---|
| `storage_config_service.py` | `settings` 表 `storage.smb` | 旧单连接，JSON 存储 |
| `smb_connection_service.py` | `smb_connections` 表 | 新多连接，独立表 |

**问题**：旧 `storage.smb` 仍可写入，新功能用 `smb_connections`，两套中断逻辑各自独立。

### 3.3 Worker 仍有历史处理路径命名

```python
process_transfer_task()   # mode=copy，CloudProvider -> StorageWriter（测试/可选扩展）
process_dtl_task()        # 历史命名，实际承担远程媒体库同步
目标：process_sync_task() # mode=sync，SMB -> SMB
```

`process_dtl_task` 名称仍带历史阶段语义，应统一为 `process_sync_task`。

### 3.4 `TransferTask` 字段和 mode 仍需统一

`sync_seen_file_id` 已作为目标字段引入，但任务 `mode`、日志事件和部分代码命名仍带 `download_to_local` / `dtl` 历史语义。

### 3.5 TransferTask 没有直接关联 binding_id

任务创建时把 SMB 配置快照存入 JSON，但没有记录来源 binding_id。

### 3.6 远程媒体库模型已引入，旧文档和代码残留仍需收口

当前已引入 `RemoteMediaLibrary`，但旧 `download_to_local` 代码和文档残留仍需清理。

### 3.7 媒体库命名不清晰

当前 `MediaLibrary` 只代表本地媒体库，但名字没有区分本地/远程。

---

## 4. 重构目标

### 4.1 模块重构

| 重构项 | 说明 |
|---|---|
| 删除历史 Download To Local / Ingest 残留 | 移除历史 model/service/api/Worker/Web Console 代码 |
| 删除旧 storage_config_service | 移除 `settings.storage.smb` 相关代码 |
| 新增远程媒体库模型 | `RemoteMediaLibrary`，绑定 SMB 连接 + 目录 |
| 重构下载绑定 | `SyncBinding` 引用：remote_library_id -> local_library_id |
| 重命名 seen_file_id | `ingest_seen_file_id` -> `sync_seen_file_id` |
| TransferTask 增加 binding_id | 直接记录来源绑定 |
| 统一 Worker 处理路径 | 将历史 process_dtl_task 收口为 process_sync_task |

### 4.2 目标数据模型

```text
smb_connections            # 存储管理：SMB 连接配置
media_libraries            # 本地媒体库：绑定 SMB 连接 + 本地目录
remote_media_libraries     # 远程媒体库：绑定 SMB 连接 + 远程目录（新增）
sync_bindings              # 同步绑定：remote_library -> local_library（重构）
sync_seen_files            # 已见文件：记录扫描过的文件（重构）
transfer_tasks             # 任务：增加 binding_id 字段
transfer_files             # 任务文件
transfer_logs              # 任务日志
sources                    # 媒体源
resources                  # 资源
resource_links             # 资源链接
settings                   # 系统配置（精简）
```

### 4.3 目标 API 结构

```text
# 存储管理
GET/POST /storage/smb-connections              # SMB 连接 CRUD
POST     /storage/smb-connections/{id}/test
GET      /storage/smb-connections/{id}/browse

# 本地媒体库
GET/POST /media-libraries
POST     /media-libraries/{id}/test

# 远程媒体库（新增）
GET/POST /remote-media-libraries
POST     /remote-media-libraries/{id}/test

# 同步绑定（重构自 download-to-local）
GET/POST /sync/bindings
POST     /sync/bindings/{id}/test
POST     /sync/scan
POST     /sync/tasks/create

# 搜索
GET      /search

# 资源
GET      /resources/{id}

# 任务
GET/POST /transfers
POST     /transfers/{id}/cancel
POST     /transfers/{id}/retry
GET      /transfers/{id}/logs

# 媒体源
GET      /sources
POST     /sources/{id}/test

# 系统状态
GET      /health
```

---

## 5. 重构任务拆分

### Phase 9: 模块重构

目标：清理旧模块，统一术语，建立远程媒体库模型，重构同步绑定。

#### Phase 9.1: 清理旧模块

```text
删除 models/download_to_local.py
删除 services/download_to_local_service.py
删除 api/download_to_local.py
删除历史 ingest / download-to-local 前端代码
删除或迁移相关旧测试
删除 db_admin.py 中 INGEST_CONFIG_KEY
从 main.py 移除 ingest_router
```

#### Phase 9.2: 清理旧 storage_config_service

```text
删除 services/storage_config_service.py
删除 api/storage.py
删除 tests/test_storage_config.py
删除 schemas/storage.py
从 db_admin.py 移除 storage.smb 默认配置
从 Worker 移除 load_local_runtime_config 中 storage.local 相关代码
```

#### Phase 9.3: 新增远程媒体库模型

```text
新增 models/remote_media_library.py (RemoteMediaLibrary)
新增迁移 0006_remote_media_libraries
新增 schemas/remote_media_library.py
新增 services/remote_media_library_service.py
新增 api/remote_media_libraries.py
新增 tests/test_remote_media_libraries.py
```

#### Phase 9.4: 重构同步绑定

```text
确认 models/sync.py (SyncBinding, SyncSeenFile) 为唯一同步绑定模型
新增迁移 0007_rename_sync_tables
确认 schemas/sync.py、services/sync_service.py、api/sync.py、tests/test_sync.py 为唯一同步接口
```

#### Phase 9.5: 清理 TransferTask

```text
重命名 ingest_seen_file_id -> sync_seen_file_id
新增 binding_id 字段
迁移 0008_cleanup_transfer_tasks
更新 Worker 和相关 Service
```

#### Phase 9.6: 统一 Worker 处理路径

```text
将 process_dtl_task 重命名并收口为 process_sync_task
统一清理配置读取逻辑
统一中断逻辑
更新 tests/test_worker.py
```

#### Phase 9.7: 更新 Web Console

```text
删除 /app/ingest 页面
新增 /app/remote-libraries 页面
删除历史 /app/download-to-local 代码，保留 /app/remote-libraries 与 /app/sync
更新导航
```

---

## 6. 迁移策略

### 6.1 从 ingest 迁移到 sync

```text
1. 将 IngestBinding 的 source_smb_json / target_smb_json 拆分为：
   - SmbConnection 记录（或复用已有）
   - RemoteMediaLibrary 记录（来源）
   - MediaLibrary 记录（目标）
   - SyncBinding 记录

2. 将 TransferTask (mode=ingest) 改为 mode=sync

3. 将 IngestSeenFile 迁移到 SyncSeenFile

4. 删除 Ingest 模块相关表和代码
```

### 6.2 从 storage.smb 迁移到 smb_connections

```text
1. 读取 settings 表中 storage.smb 的 JSON

2. 创建对应的 SmbConnection 记录

3. 更新所有引用 storage_config_snapshot 的 TransferTask

4. 删除 settings 表中 storage.smb 记录
```

---

## 7. 测试覆盖

### 7.1 已有测试

| 文件 | 覆盖范围 |
|---|---|
| test_worker.py | Worker 配置、领取、本地成功路径、ingest 测试、dtl 测试 |
| test_smb_connections.py | SMB 连接 CRUD、密码不泄露、中断任务 |
| test_media_libraries.py | 本地媒体库 CRUD、引用校验 |
| test_download_to_local.py | 下载绑定 CRUD、扫描、任务创建 |
| test_ingest.py | 旧 ingest 模块测试 |
| test_storage_config.py | 旧单 SMB 配置测试 |
| test_transfers.py | Transfer API 测试 |
| test_search.py | 搜索测试 |
| test_sources.py | 代码注册源列表和测试搜索 |

### 7.2 重构后测试

```text
- 删除 test_ingest.py
- 删除 test_storage_config.py
- 新增 test_remote_media_libraries.py
- 重构 test_download_to_local.py -> test_sync.py
- 更新 test_worker.py（移除 ingest 测试，统一 sync 测试）
```
