# 系统模块梳理

本文档梳理 Sundarr 当前系统各模块的职责、关联关系和已知问题。

---

## 1. 模块清单

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
│   ├── source.py                  # Source（媒体源）
│   ├── resource.py                # Resource, ResourceLink（搜索结果）
│   ├── transfer.py                # TransferTask, TransferFile, TransferLog
│   ├── setting.py                 # Setting（KV 配置）
│   ├── smb_connection.py          # SmbConnection（多 SMB 连接）
│   ├── media_library.py           # MediaLibrary（本地媒体库）
│   ├── download_to_local.py       # DownloadToLocalBinding, DownloadToLocalSeenFile
│   └── ingest.py                  # IngestBinding, IngestSeenFile（旧模块）
├── services/                      # 业务逻辑
│   ├── search_service.py          # 搜索聚合
│   ├── resource_library_service.py # 资源管理
│   ├── transfer_service.py        # TransferTask CRUD
│   ├── storage_config_service.py  # 旧单 SMB 配置（settings 表）
│   ├── smb_connection_service.py  # 新多 SMB 连接（smb_connections 表）
│   ├── media_library_service.py   # 媒体库管理
│   ├── download_to_local_service.py # 下载到本地绑定 + 扫描 + 任务创建
│   ├── ingest_service.py          # 旧模块
│   └── source_service.py          # Source CRUD
├── api/                           # API 路由
│   ├── search.py, resources.py, transfers.py
│   ├── storage.py                 # 旧单 SMB 配置 API
│   ├── smb_connections.py         # 新多 SMB 连接 API
│   ├── media_libraries.py
│   ├── download_to_local.py
│   ├── ingest.py                  # 旧模块 API
│   ├── sources.py
│   └── health.py
├── storage/                       # 存储抽象
│   ├── base.py                    # StorageWriter ABC
│   ├── local.py                   # LocalWriter
│   └── smb.py                     # SmbWriter
├── cloud/                         # 云盘抽象
│   ├── base.py                    # CloudProvider ABC
│   └── local.py                   # LocalCloudProvider
├── sources/                       # Source Adapter 框架
│   ├── base.py                    # BaseSource ABC
│   └── example.py                 # ExampleSource
└── parsers/
    └── link_extractor.py          # 网盘链接提取
```

---

## 2. 数据流关系

### 2.1 搜索到搬运

```text
Sources (BaseSource)
    │
    ▼
SearchService ──> Resource + ResourceLink
    │
    ▼
TransferService ──> TransferTask (mode=copy)
    │
    ▼
Worker (mode=copy)
    │
    ├── CloudProvider.save_share()
    ├── CloudProvider.list_files()
    ├── CloudProvider.open_file_stream()
    └── StorageWriter.open_append() -> size() -> rename()
```

### 2.2 下载到本地（新）

```text
SmbConnection (多连接配置)
    │
    ├──> MediaLibrary (绑定连接 + 本地目录)
    │
    └──> DownloadToLocalBinding (来源连接 + 路径 -> 目标媒体库)
              │
              ▼
         DownloadToLocalService
              │
              ├── scan() -> DownloadToLocalSeenFile
              └── create_tasks() -> TransferTask (mode=download_to_local)
                     │
                     ▼
                Worker (mode=download_to_local)
                     │
                     ├── source_config_snapshot -> SmbWriter (读来源)
                     ├── storage_config_snapshot -> SmbWriter (写目标)
                     └── .downloading -> verify -> rename -> 清理来源
```

### 2.3 导入（旧，待删除）

```text
IngestBinding (source_smb_json / target_smb_json)
    │
    ▼
IngestService
    │
    ├── scan() -> IngestSeenFile
    └── create_tasks() -> TransferTask (mode=ingest)
           │
           ▼
      Worker (mode=ingest)
           │
           └── 与 download_to_local 几乎相同
```

### 2.4 旧单 SMB 配置（待删除）

```text
settings 表 (key=storage.smb)
    │
    ▼
StorageConfigService
    │
    ├── get_config / save_config / test_config
    └── browse()
```

---

## 3. 模块间依赖关系

### 3.1 依赖方向

```text
api/  ──>  services/  ──>  models/
                  │
                  └──>  storage/ (SmbWriter, LocalWriter)
                  └──>  cloud/ (CloudProvider)
                  └──>  sources/ (BaseSource)

worker.py ──>  models/
          ──>  storage/
          ──>  cloud/
          ──>  services/ (download_to_local_service 用于 seen_file 更新)
```

### 3.2 Worker 依赖

Worker 是系统最重的模块，直接依赖：

```text
models:  DownloadToLocalBinding, DownloadToLocalSeenFile,
         IngestBinding, IngestSeenFile,
         ResourceLink, Setting, TransferFile, TransferLog, TransferTask
storage: LocalWriter, SmbConfig, SmbWriter, StorageWriter
cloud:   CloudProvider, LocalCloudProvider
```

---

## 4. 已知问题

### 4.1 Ingest 模块是旧实现，但仍完整保留

| 文件 | 状态 |
|---|---|
| `models/ingest.py` | 旧，SMB 配置以 JSON 存在 binding 内 |
| `services/ingest_service.py` | 旧，与 download_to_local_service 高度重复 |
| `api/ingest.py` | 旧，仍注册在 main.py |
| `worker.py` process_ingest_task | 旧，与 process_dtl_task 几乎相同 |
| Web Console `/app/ingest` | 旧，与 `/app/download-to-local` 并存 |

**问题**：用户不知道该用哪个，代码维护两份。

### 4.2 两套 SMB 配置系统并存

| 模块 | 存储方式 | 用途 |
|---|---|---|
| `storage_config_service.py` | `settings` 表 `storage.smb` | 旧单连接，JSON 存储 |
| `smb_connection_service.py` | `smb_connections` 表 | 新多连接，独立表 |

**问题**：旧 `storage.smb` 仍可写入，新功能用 `smb_connections`，两套中断逻辑各自独立。

### 4.3 Worker 有 3 条处理路径，代码重复

```python
process_transfer_task()   # mode=copy，CloudProvider -> StorageWriter
process_ingest_task()     # mode=ingest，SMB -> SMB（旧）
process_dtl_task()        # mode=download_to_local，SMB -> SMB（新）
```

`process_ingest_task` 和 `process_dtl_task` 逻辑几乎完全相同，只有：
- 清理配置读取不同（`ingest.config` vs `download_to_local.config`）
- seen_file 更新不同（`IngestSeenFile` vs `DownloadToLocalSeenFile`）

### 4.4 `TransferTask.ingest_seen_file_id` 字段名不合理

这个字段同时被 ingest 和 download_to_local 使用，但名字叫 `ingest_seen_file_id`，语义不清。

### 4.5 TransferTask 没有直接关联 binding_id

任务创建时把 SMB 配置快照存入 `source_config_snapshot` / `storage_config_snapshot`，但没有记录来源 binding_id。后续如果要查询"这个任务属于哪个 binding"，只能通过 `seen_file -> binding` 反查。

### 4.6 settings 表承载过多无关配置

```python
DEFAULT_SETTINGS = {
    "worker.enabled": ...,
    "worker.concurrency": ...,
    "cloud.local": ...,
    "ingest.config": ...,           # 旧
    "download_to_local.config": ...,
}
```

`ingest.config` 和 `download_to_local.config` 功能重复。

### 4.7 SMB 连接更新中断逻辑不统一

- `storage_config_service._interrupt_running_tasks`：检查 `target_type == "smb"`
- `smb_connection_service._interrupt_running_tasks`：检查 `source_config_snapshot.connection_id`

两套中断逻辑，可能遗漏某些任务。

---

## 5. 优化建议

### 5.1 高优先级

| 建议 | 说明 |
|---|---|
| 删除 Ingest 模块 | 移除 `ingest.py`（model/service/api）、Worker 中 `process_ingest_task`、Web Console `/app/ingest`。已有的 ingest 任务可通过迁移转为 download_to_local |
| 删除旧 `storage_config_service` | 移除 `settings.storage.smb` 相关代码，统一使用 `smb_connections` 表 |
| 统一 Worker 处理路径 | `process_ingest_task` 和 `process_dtl_task` 合并为一个函数，通过参数区分清理配置来源 |

### 5.2 中优先级

| 建议 | 说明 |
|---|---|
| 重命名 `ingest_seen_file_id` | 改为 `seen_file_id` 或 `dtl_seen_file_id`，通过 migration 处理 |
| TransferTask 增加 `binding_id` | 直接记录来源 binding，方便查询和中断 |

### 5.3 低优先级

| 建议 | 说明 |
|---|---|
| 统一中断逻辑 | SMB 连接更新时，统一检查所有引用该连接的任务 |
| settings 表精简 | 移除 `ingest.config`，只保留 `download_to_local.config` |

---

## 6. 迁移策略

### 6.1 从 ingest 迁移到 download_to_local

```text
1. 将 IngestBinding 的 source_smb_json / target_smb_json 拆分为：
   - SmbConnection 记录（或复用已有）
   - MediaLibrary 记录
   - DownloadToLocalBinding 记录

2. 将 TransferTask (mode=ingest) 改为 mode=download_to_local

3. 将 IngestSeenFile 迁移到 DownloadToLocalSeenFile

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
| test_media_libraries.py | 媒体库 CRUD、引用校验 |
| test_download_to_local.py | 绑定 CRUD、扫描、任务创建 |
| test_ingest.py | 旧 ingest 模块测试 |
| test_storage_config.py | 旧单 SMB 配置测试 |
| test_transfers.py | Transfer API 测试 |
| test_search.py | 搜索测试 |
| test_sources.py | Source CRUD 测试 |

### 7.2 测试覆盖缺口

```text
- delete_to_local worker 完整路径（mock SMB 读写）-> 已覆盖
- 统一中断逻辑测试 -> 需补充
- 迁移路径测试 -> 需补充（删除 ingest 后）
```
