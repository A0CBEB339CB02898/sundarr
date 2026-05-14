# API 契约

本文档定义 Sundarr MVP 的后端 API 契约。

---

## 1. 通用规则

FastAPI 只作为 API 后端。

响应格式必须稳定，供 Web Console、AI Tool 和 API Client 调用。

MVP API 风格：

```text
读取使用 GET。
创建、更新、启用、禁用、测试、取消、重试等修改或动作统一使用 POST。
MVP 不使用 PUT / PATCH / DELETE。
```

统一错误响应：

```json
{
  "error": {
    "code": "NAS_WRITE_FAILED",
    "message": "Failed to write target file",
    "retryable": true
  }
}
```

---

## 2. Health

```http
GET /health
```

响应：

```json
{
  "status": "ok",
  "database": "ok",
  "redis": "ok",
  "worker": "ok",
  "checked_at": "2026-05-10T12:34:56.789Z",
  "components": {
    "api":      { "status": "ok", "checked_at": "2026-05-10T12:34:56.780Z" },
    "database": { "status": "ok", "checked_at": "2026-05-10T12:34:56.784Z" },
    "redis":    { "status": "ok", "checked_at": "2026-05-10T12:34:56.786Z" },
    "worker":   { "status": "ok", "checked_at": "2026-05-10T12:34:56.789Z" }
  }
}
```

`worker` 允许值：

```text
ok: 本地 Worker pid 存在且进程运行中。
error: 本地 Worker pid 存在但进程不存在。
unknown: 当前环境没有 Worker pid，或无法判断 Worker 状态。
```

顶层标量字段（`status` / `database` / `redis` / `worker`）与旧契约保持兼容，供外部监控和 smoke test 使用。`components` 用于 Web Console 展示每个组件自己的 `checked_at`（ISO-8601 UTC，后缀 `Z`）。

---

## 3. Sources

```http
GET /sources
GET /sources/{source_id}
POST /sources/{source_id}/test
```

规则：

```text
搜索源统一从代码注册表加载。
Web Console 只读展示 code source，不允许在线创建、编辑、启用或禁用。
test endpoint 接收 keyword / result_type / limit，返回 RawSearchItem 预览、错误信息和逐步测试日志。
响应字段只包含 id、name、type、description；不返回 enabled、legal_note 或数据库错误状态。
```

---

## 4. Search

```http
GET /search?q=interstellar&type=movie&year=2014
```

响应：

```json
{
  "query": "interstellar",
  "count": 1,
  "results": [
    {
      "id": "res_001",
      "title": "星际穿越",
      "original_title": "Interstellar",
      "type": "movie",
      "year": 2014,
      "quality": "1080p",
      "score": 0.94,
      "explanation": "Title and year matched",
      "links": [
        {
          "id": "link_001",
          "provider": "quark",
          "code": null,
          "valid": true,
          "risk_level": "unknown"
        }
      ]
    }
  ],
  "source_results": [
    {
      "source_id": "seedhub",
      "source_name": "SeedHub",
      "count": 0,
      "results": [],
      "error": null
    }
  ]
}
```

---

## 5. Resources

```http
GET /resources
GET /resources/{resource_id}
```

资源详情必须包含 links，但不得返回敏感 provider 凭据。

---

## 6. Transfers

当前实现状态：

```text
已实现 POST /transfers、GET /transfers 和 GET /transfers/{task_id}。
已实现 Worker 本地成功路径和失败状态写入。
已实现 cancel、retry、logs 和 worker startup recovery。
尚未实现 eta 和复杂 current_file 详情。
```

创建任务：

```http
POST /transfers
```

请求：

```json
{
  "link_id": "link_001",
  "mode": "copy",
  "target_type": "smb",
  "target_library": "movies",
  "target_path": "Movies/Interstellar.mkv"
}
```

响应：

```json
{
  "id": "task_001",
  "resource_id": "res_001",
  "link_id": "link_001",
  "status": "pending",
  "mode": "copy",
  "cloud_staging_path": null,
  "target_type": "smb",
  "target_library": "movies",
  "target_path": "Movies/Interstellar.mkv",
  "source_type": null,
  "source_path": null,
  "sync_seen_file_id": null,
  "total_bytes": 0,
  "done_bytes": 0,
  "progress": 0,
  "current_file": null,
  "error_code": null,
  "error_message": null,
  "retryable": null,
  "retry_count": 0
}
```

查询任务：

```http
GET /transfers
GET /transfers/{task_id}
```

任务列表响应建议：

```json
[
  {
    "id": "task_001",
    "status": "downloading",
    "target_library": "movies",
    "target_path": "Movies/Interstellar.mkv",
    "done_bytes": 5368709120,
    "total_bytes": 12582912000,
    "progress": 42.66,
    "current_file": "Interstellar.mkv",
    "error_code": null,
    "retryable": null,
    "updated_at": "2026-05-07T00:00:01"
  }
]
```

列表规则：

```text
默认按 updated_at desc 排序。
默认返回最近任务和运行中任务，具体分页参数在实现时确定。
响应不得包含 password、token、cookie、secret 等敏感信息。
```

任务详情：

```http
GET /transfers/{task_id}
```

响应：

```json
{
  "id": "task_001",
  "status": "downloading",
  "done_bytes": 5368709120,
  "total_bytes": 12582912000,
  "progress": 42.66,
  "current_file": "Interstellar.mkv",
  "error_code": null,
  "error_message": null,
  "retryable": null
}
```

控制：

```http
POST /transfers/{task_id}/cancel
POST /transfers/{task_id}/retry
GET  /transfers/{task_id}/logs
```

当前已实现 `POST /transfers/{task_id}/cancel`、`POST /transfers/{task_id}/retry` 和 `GET /transfers/{task_id}/logs`。

Phase 6 控制接口收口顺序：

```text
Phase 6.1: POST /transfers/{task_id}/cancel
Phase 6.2: POST /transfers/{task_id}/retry
Phase 6.5: GET /transfers/{task_id}/logs
```

取消和重试接口响应仍返回 `TransferResponse`。日志接口响应按 `created_at` 升序返回 transfer_logs，且不得包含 password、token、cookie、secret 等敏感信息。

日志响应：

```json
[
  {
    "id": "log_001",
    "task_id": "task_001",
    "level": "info",
    "event": "worker_task_claimed",
    "message": "Worker 已领取任务。",
    "data": {"worker_concurrency": 2},
    "created_at": "2026-05-07T00:00:01"
  }
]
```

---

## 7. Storage Settings

状态：已实现（含多 SMB connection API）。

```http
GET  /storage/config
POST /storage/config/save
POST /storage/config/test
GET  /storage/browse?path=Movies
GET  /storage/smb-connections
POST /storage/smb-connections/create
GET  /storage/smb-connections/{connection_id}
POST /storage/smb-connections/{connection_id}/update
POST /storage/smb-connections/{connection_id}/enable
POST /storage/smb-connections/{connection_id}/disable
POST /storage/smb-connections/{connection_id}/test
POST /storage/smb-connections/{connection_id}/test-new
GET  /storage/smb-connections/{connection_id}/browse?path=Movies
```

规则：

```text
GET 不返回 password 明文，只返回 password_set。
POST /storage/config/save 保存后热加载 SMB 配置。
POST /storage/config/save 中 password 为空表示保留旧 password。
SMB 配置修改必须中断旧配置运行中任务。
GET /storage/browse 只能浏览允许范围。
POST /storage/config/test 会验证配置结构、路径合法性，并尝试真实 SMB 连接和根路径访问。
POST /storage/smb-connections/{connection_id}/test 会记录最近一次测试结果。
POST /storage/smb-connections/{connection_id}/test-new 使用编辑表单中的当前配置测试，不覆盖数据库配置。
最近一次测试明确失败的 SMB connection 不能启用，也不能作为同步任务的有效连接使用。
新功能优先使用多 SMB connection API；旧 storage/config API 可作为默认连接兼容入口，后续收口时再移除。
```

---

## 8. Remote Media Library Sync

远程媒体库同步 API 用于管理“远程媒体库 -> 本地媒体库”的同步规则，并触发扫描和任务创建。`download-to-local` API 属于历史实现命名，Phase 9 需要继续清理。

媒体库 API 用于创建 movie / series / unclassified 等本地 NAS 逻辑媒体库，并将媒体库绑定到 Storage 模块中已配置的 SMB connection 和目录。

远程媒体库和同步模块不得重复填写 SMB host/share/username/password。来源必须选择已配置远程媒体库，目标必须选择已配置本地媒体库。

建议接口：

```http
GET  /media-libraries
POST /media-libraries/create
GET  /media-libraries/{library_id}
POST /media-libraries/{library_id}/update
POST /media-libraries/{library_id}/enable
POST /media-libraries/{library_id}/disable
POST /media-libraries/{library_id}/test
GET  /remote-media-libraries
POST /remote-media-libraries/create
GET  /remote-media-libraries/{library_id}
POST /remote-media-libraries/{library_id}/update
POST /remote-media-libraries/{library_id}/enable
POST /remote-media-libraries/{library_id}/disable
POST /remote-media-libraries/{library_id}/test
GET  /sync/config
POST /sync/config/save
GET  /sync/bindings
POST /sync/bindings/create
GET  /sync/bindings/{binding_id}
POST /sync/bindings/{binding_id}/update
POST /sync/bindings/{binding_id}/enable
POST /sync/bindings/{binding_id}/disable
POST /sync/bindings/{binding_id}/test
POST /sync/scan
GET  /sync/discovered
POST /sync/tasks/create
```

规则：

```text
media-libraries 和 remote-media-libraries 的 test 接口会验证对应 SMB 连接下的目标目录是否可访问，不只是验证 SMB 连接存在。
本地媒体库 base_path 统一保存为带前导斜杠的路径。
列表响应返回 last_test_ok / last_test_error_code / last_test_error_message，用于 Web Console 状态列展示测试结果和失败详情。
最近一次测试明确失败的本地媒体库、远程媒体库不能启用，也不能作为同步任务的有效来源或目标使用。
POST /sync/scan 支持传入 remote_library_id；当远程媒体库已绑定本地媒体库时，系统会使用该远程媒体库对应的同步绑定执行扫描。
```

全局配置响应示例：

```json
{
  "delete_source_after_success": true,
  "delete_empty_source_dirs": true,
  "scan_interval_seconds": 60,
  "stable_seconds": 120,
  "unclassified_library_id": "library_unclassified"
}
```

媒体库响应示例：

```json
{
  "id": "library_movie",
  "name": "电影",
  "media_type": "movie",
  "enabled": true,
  "connection_id": "media_library",
  "base_path": "Movies"
}
```

Binding 响应示例：

```json
{
  "id": "binding_movie",
  "name": "电影同步",
  "enabled": true,
  "media_type": "movie",
  "remote_library_id": "remote_movie",
  "target_library_id": "library_movie",
  "delete_source_after_success": null,
  "delete_empty_source_dirs": null
}
```

规则：

```text
API 不返回 SMB password 明文。
media-libraries/test 接口由后端执行，验证媒体库目录可写。
sync/bindings/test 接口由后端执行，验证远程媒体库目录可读和本地媒体库目录可写。
scan 接口只触发扫描或返回扫描结果，不绕过网盘限制。
tasks/create 接口只为 stable 且未绑定 task 的 discovered file 创建下载任务。
同步任务复用 transfer_tasks，目标 mode 为 sync，link_id 为空，source_type 为 smb。
binding 不明确时创建指向 unclassified 本地媒体库的同步任务。
```

创建下载任务响应示例：

```json
{
  "created_count": 1,
  "skipped_count": 0,
  "tasks": [
    {
      "id": "task_001",
      "resource_id": null,
      "link_id": null,
      "status": "pending",
      "mode": "sync",
      "cloud_staging_path": null,
      "target_type": "smb",
      "target_library": "movie",
      "target_path": "Movie/Movie.mkv",
      "source_type": "smb",
      "source_path": "Movie/Movie.mkv",
      "sync_seen_file_id": "seen_001",
      "total_bytes": 0,
      "done_bytes": 0,
      "progress": 0,
      "current_file": null,
      "error_code": null,
      "error_message": null,
      "retryable": null,
      "retry_count": 0
    }
  ]
}
```

---

## 9. 错误码

MVP 错误码：

```text
SEARCH_SOURCE_TIMEOUT
SEARCH_SOURCE_FAILED
SOURCE_CONFIG_INVALID
LINK_PARSE_FAILED
CLOUD_SAVE_FAILED
CLOUD_FILE_LIST_FAILED
CLOUD_RANGE_NOT_SUPPORTED
CLOUD_STREAM_FAILED
STORAGE_CONFIG_INVALID
STORAGE_CONFIG_CHANGED
SMB_CONNECT_FAILED
SMB_AUTH_FAILED
SMB_PATH_INVALID
SMB_PATH_OUTSIDE_ROOT
SMB_CLIENT_NOT_INSTALLED
SMB_NO_SPACE
SMB_WRITE_FAILED
SMB_RENAME_FAILED
TARGET_EXISTS
VERIFY_FAILED
RENAME_FAILED
CLOUD_CLEANUP_FAILED
TASK_CANCELLED
WORKER_RECOVERY_REQUIRED
SYNC_BINDING_NOT_FOUND
SYNC_SOURCE_NOT_STABLE
SYNC_SOURCE_PATH_INVALID
SYNC_SOURCE_DELETE_FAILED
SYNC_UNCLASSIFIED_REQUIRED
SMB_CONNECTION_NOT_FOUND
MEDIA_LIBRARY_NOT_FOUND
MEDIA_LIBRARY_UNCLASSIFIED_REQUIRED
```

---

## 10. 验收标准

API 完成时必须满足：

```text
OpenAPI schema 可访问。
错误响应格式统一。
Web Console 所需 API 可用。
Transfer 控制 API 可用。
Storage settings API 不泄露 password。
SMB 配置修改返回 STORAGE_CONFIG_CHANGED 相关任务影响。
Storage API 可管理多个 SMB connection，且不泄露 SMB password。
Media library API 可管理媒体库、测试本地目录并不泄露 SMB password。
Sync API 可管理远程媒体库到本地媒体库的 binding、测试来源/目标目录并触发扫描。
```
