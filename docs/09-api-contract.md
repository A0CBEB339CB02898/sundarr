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
  "worker": "unknown"
}
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

创建任务：

```http
POST /transfers
```

请求：

```json
{
  "resource_id": "res_001",
  "link_id": "link_001",
  "target": {
    "type": "smb",
    "library": "movies",
    "path": "Interstellar (2014)"
  },
  "mode": "move_after_verified_download"
}
```

响应：

```json
{
  "task_id": "task_001",
  "status": "pending"
}
```

查询任务：

```http
GET /transfers/{task_id}
```

响应：

```json
{
  "task_id": "task_001",
  "status": "downloading",
  "progress": 42.6,
  "done_bytes": 5368709120,
  "total_bytes": 12582912000,
  "speed_bytes_per_sec": 8388608,
  "eta_seconds": 856,
  "current_file": "Interstellar.2014.1080p.mkv",
  "error": null
}
```

控制：

```http
POST /transfers/{task_id}/cancel
POST /transfers/{task_id}/retry
GET  /transfers/{task_id}/logs
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
SMB_NO_SPACE
SMB_WRITE_FAILED
SMB_RENAME_FAILED
TARGET_EXISTS
VERIFY_FAILED
RENAME_FAILED
CLOUD_CLEANUP_FAILED
TASK_CANCELLED
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
