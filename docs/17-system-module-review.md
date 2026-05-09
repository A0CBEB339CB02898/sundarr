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
Source 配置只保存参数，不保存可执行 Python 代码。
Web Console 只管理已安装 Adapter 的启用、禁用、参数、测试和错误查看。
```

关联：媒体源通过统一接口暴露给搜索模块。

### 1.2 搜索

职责：在多个媒体源中并发搜索，聚合结果。

```text
搜索是媒体源的统一调用入口。
一次搜索同时查询所有已启用的媒体源。
结果经过标准化、去重、排序后返回。
搜索结果可进入资源库，供后续下载使用。
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
│   ├── download_to_local.py       # Binding, SeenFile         ⚠ 需重构为"同步绑定"
│   └── ingest.py                  # IngestBinding 等          ✗ 旧模块，待删除
├── services/                      # 业务逻辑
│   ├── search_service.py          # 搜索聚合                  ✓ 已实现
│   ├── resource_library_service.py # 资源管理                 ✓ 已实现
│   ├── transfer_service.py        # TransferTask CRUD         ✓ 已实现
│   ├── storage_config_service.py  # 旧单 SMB 配置             ✗ 旧模块，待删除
│   ├── smb_connection_service.py  # 多 SMB 连接               ✓ 已实现
│   ├── media_library_service.py   # 本地媒体库管理            ✓ 已实现
│   ├── download_to_local_service.py # 下载绑定+扫描+任务创建  ⚠ 需重构
│   ├── ingest_service.py          # 旧模块                    ✗ 旧模块，待删除
│   └── source_service.py          # Source CRUD               ✓ 已实现
├── api/                           # API 路由
│   ├── search.py                  # 搜索                      ✓
│   ├── resources.py               # 资源                      ✓
│   ├── transfers.py               # 任务                      ✓
│   ├── storage.py                 # 旧单 SMB 配置             ✗ 旧，待删除
│   ├── smb_connections.py         # 多 SMB 连接               ✓
│   ├── media_libraries.py         # 本地媒体库                ✓
│   ├── download_to_local.py       # 下载绑定                  ⚠ 需重构
│   ├── ingest.py                  # 旧模块                    ✗ 旧，待删除
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
│   ├── base.py                    # BaseSource ABC            ✓
│   └── example.py                 # ExampleSource             ✓
└── parsers/
    └── link_extractor.py          # 网盘链接提取              ✓
```

### 2.2 当前数据流

```text
存储管理 (smb_connections)
    │
    ├──> 本地媒体库 (media_libraries) ──> 绑定到 SMB 连接 + 本地目录
    │
    └──> 远程媒体库 (通过 download_to_local_bindings.source_connection_id + source_path)
              │
              ▼
         下载管理 (download_to_local_bindings)
              │
              ├── scan() -> download_to_local_seen_files
              └── create_tasks() -> transfer_tasks (mode=download_to_local)
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

### 3.1 Ingest 模块是旧实现，但仍完整保留

| 文件 | 状态 |
|---|---|
| `models/ingest.py` | 旧，SMB 配置以 JSON 存在 binding 内 |
| `services/ingest_service.py` | 旧，与 download_to_local_service 高度重复 |
| `api/ingest.py` | 旧，仍注册在 main.py |
| `worker.py` process_ingest_task | 旧，与 process_dtl_task 几乎相同 |
| Web Console `/app/ingest` | 旧，与 `/app/download-to-local` 并存 |

**问题**：用户不知道该用哪个，代码维护两份。

### 3.2 两套 SMB 配置系统并存

| 模块 | 存储方式 | 用途 |
|---|---|---|
| `storage_config_service.py` | `settings` 表 `storage.smb` | 旧单连接，JSON 存储 |
| `smb_connection_service.py` | `smb_connections` 表 | 新多连接，独立表 |

**问题**：旧 `storage.smb` 仍可写入，新功能用 `smb_connections`，两套中断逻辑各自独立。

### 3.3 Worker 有 3 条处理路径，代码重复

```python
process_transfer_task()   # mode=copy，CloudProvider -> StorageWriter
process_ingest_task()     # mode=ingest，SMB -> SMB（旧）
process_dtl_task()        # mode=download_to_local，SMB -> SMB（新）
```

`process_ingest_task` 和 `process_dtl_task` 逻辑几乎完全相同。

### 3.4 `TransferTask.ingest_seen_file_id` 字段名不合理

这个字段同时被 ingest 和 download_to_local 使用，但名字叫 `ingest_seen_file_id`，语义不清。

### 3.5 TransferTask 没有直接关联 binding_id

任务创建时把 SMB 配置快照存入 JSON，但没有记录来源 binding_id。

### 3.6 远程媒体库没有独立模型

当前远程媒体库的信息散落在 `download_to_local_bindings` 的 `source_connection_id + source_path` 中，没有独立的"远程媒体库"概念。

### 3.7 媒体库命名不清晰

当前 `MediaLibrary` 只代表本地媒体库，但名字没有区分本地/远程。

---

## 4. 重构目标

### 4.1 模块重构

| 重构项 | 说明 |
|---|---|
| 删除 Ingest 模块 | 移除 model/service/api/Worker 测试 |
| 删除旧 storage_config_service | 移除 `settings.storage.smb` 相关代码 |
| 新增远程媒体库模型 | `RemoteMediaLibrary`，绑定 SMB 连接 + 目录 |
| 重构下载绑定 | `SyncBinding` 引用：remote_library_id -> local_library_id |
| 重命名 seen_file_id | `ingest_seen_file_id` -> `sync_seen_file_id` |
| TransferTask 增加 binding_id | 直接记录来源绑定 |
| 统一 Worker 处理路径 | 合并 process_ingest_task 和 process_dtl_task |

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
删除 models/ingest.py
删除 services/ingest_service.py
删除 api/ingest.py
删除 tests/test_ingest.py
删除 Worker 中 process_ingest_task 相关代码
删除 Web Console 中 /app/ingest 页面
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
重构 models/download_to_local.py -> models/sync.py (SyncBinding, SyncSeenFile)
新增迁移 0007_rename_sync_tables
重构 schemas/download_to_local.py -> schemas/sync.py
重构 services/download_to_local_service.py -> services/sync_service.py
重构 api/download_to_local.py -> api/sync.py
重构 tests/test_download_to_local.py -> tests/test_sync.py
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
合并 process_ingest_task 和 process_dtl_task 为 process_sync_task
统一清理配置读取逻辑
统一中断逻辑
更新 tests/test_worker.py
```

#### Phase 9.7: 更新 Web Console

```text
删除 /app/ingest 页面
新增 /app/remote-libraries 页面
重构 /app/download-to-local -> /app/sync
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
| test_sources.py | Source CRUD 测试 |

### 7.2 重构后测试

```text
- 删除 test_ingest.py
- 删除 test_storage_config.py
- 新增 test_remote_media_libraries.py
- 重构 test_download_to_local.py -> test_sync.py
- 更新 test_worker.py（移除 ingest 测试，统一 sync 测试）
```
