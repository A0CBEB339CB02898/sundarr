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
  "worker": "ok"
}
```

`worker` 允许值：

```text
ok: 本地 Worker pid 存在且进程运行中。
error: 本地 Worker pid 存在但进程不存在。
unknown: 当前环境没有 Worker pid，或无法判断 Worker 状态。
```

---

## 3. Sources

```http
GET /sources
POST /sources/create
GET /sources/{source_id}
POST /sources/{source_id}/update
POST /sources/{source_id}/enable
POST /sources/{source_id}/disable
POST /sources/{source_id}/test
```

规则：

```text
Web Console 只能创建和编辑 configurable / document source。
code source 只读展示，不允许在线编辑。
test endpoint 返回 RawSearchItem 预览和错误信息。
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
已实现 POST /transfers 和 GET /transfers/{task_id} 的最小入口。
已实现 Worker 本地成功路径和失败状态写入。
尚未实现 logs API、eta 和复杂 current_file 详情。
cancel、retry 和 worker startup recovery 属于 Phase 6 Cleanup And Recovery 范围。
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

```http
GET  /storage/config
POST /storage/config/save
POST /storage/config/test
GET  /storage/browse?path=Movies
```

规则：

```text
GET 不返回 password 明文，只返回 password_set。
POST /storage/config/save 保存后热加载 SMB 配置。
POST /storage/config/save 中 password 为空表示保留旧 password。
SMB 配置修改必须中断旧配置运行中任务。
GET /storage/browse 只能浏览允许范围。
POST /storage/config/test 会验证配置结构、路径合法性，并尝试真实 SMB 连接和根路径访问。
```

---

## 8. 错误码

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
```

---

## 9. 验收标准

API 完成时必须满足：

```text
OpenAPI schema 可访问。
错误响应格式统一。
Web Console 所需 API 可用。
Transfer 控制 API 可用。
Storage settings API 不泄露 password。
SMB 配置修改返回 STORAGE_CONFIG_CHANGED 相关任务影响。
```
