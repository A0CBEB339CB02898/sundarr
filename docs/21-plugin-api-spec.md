# 插件 API 文档

## 概述

Sundarr 插件系统提供完整的 RESTful API 来管理插件，包括插件仓库管理、插件配置管理、插件状态查询等。

## 基础信息

- **Base URL**: `/plugins`
- **Content-Type**: `application/json`
- **认证**: 当前版本不需要认证

## 插件仓库管理

### 获取所有插件仓库

**GET** `/plugins/repositories`

获取所有已配置的插件仓库列表。

**响应示例**:
```json
[
  {
    "id": "repo-1",
    "name": "quark-provider",
    "repo_url": "https://github.com/sundarr/quark-provider.git",
    "branch": "main",
    "current_commit": "abc123",
    "previous_commit": "def456",
    "auto_update": false,
    "enabled": true,
    "status": "loaded",
    "last_error": null,
    "last_checked_at": "2026-06-25T12:00:00",
    "last_loaded_at": "2026-06-25T12:00:00"
  }
]
```

### 添加插件仓库

**POST** `/plugins/repositories`

添加一个新的插件仓库。

**请求体**:
```json
{
  "repo_url": "https://github.com/sundarr/quark-provider.git",
  "branch": "main",
  "name": "quark-provider",
  "auto_update": false
}
```

**响应示例**:
```json
{
  "status": "success",
  "message": "仓库已添加：夸克网盘 Provider",
  "plugin_id": "quark-provider",
  "commit": "abc123"
}
```

**错误响应**:
```json
{
  "detail": "仓库 URL 无效"
}
```

### 更新插件仓库

**PUT** `/plugins/repositories/{repo_id}`

更新插件仓库到最新或指定 commit。

**路径参数**:
- `repo_id`: 仓库 ID

**请求体**:
```json
{
  "new_commit": "new-commit-hash"  // 可选，如果为空则更新到最新
}
```

**响应示例**:
```json
{
  "status": "success",
  "message": "仓库已更新：夸克网盘 Provider",
  "new_commit": "new-commit-hash"
}
```

### 回滚插件仓库

**POST** `/plugins/repositories/{repo_id}/rollback`

回滚插件仓库到上一个版本。

**路径参数**:
- `repo_id`: 仓库 ID

**响应示例**:
```json
{
  "status": "success",
  "message": "仓库已回滚：夸克网盘 Provider",
  "new_commit": "previous-commit-hash"
}
```

### 删除插件仓库

**DELETE** `/plugins/repositories/{repo_id}`

删除插件仓库。

**路径参数**:
- `repo_id`: 仓库 ID

**响应示例**:
```json
{
  "status": "success",
  "message": "仓库已删除"
}
```

## 插件管理

### 获取所有插件

**GET** `/plugins/plugins`

获取所有已安装的插件列表。

**查询参数**:
- `plugin_type`: 插件类型过滤（可选）
  - 可选值：`source`, `cloud_provider`, `notification`, `crawler`, `link_validator`, `link_extractor`, `task_processor`
- `include_disabled`: 是否包含已禁用的插件（默认为 `false`）

**响应示例**:
```json
[
  {
    "id": "quark-provider",
    "name": "夸克网盘 Provider",
    "version": "1.0.0",
    "plugin_type": "cloud_provider",
    "description": "夸克网盘直链下载支持",
    "author": "Sundarr Team",
    "homepage_url": "https://github.com/sundarr/quark-provider",
    "status": "loaded",
    "error_message": null,
    "commit_hash": "abc123",
    "repo_path": "/home/user/.sundarr/plugins/repos/quark-provider"
  }
]
```

### 获取插件详情

**GET** `/plugins/plugins/{plugin_id}`

获取指定插件的详细信息。

**路径参数**:
- `plugin_id`: 插件 ID

**响应示例**:
```json
{
  "id": "quark-provider",
  "name": "夸克网盘 Provider",
  "version": "1.0.0",
  "plugin_type": "cloud_provider",
  "description": "夸克网盘直链下载支持",
  "author": "Sundarr Team",
  "homepage_url": "https://github.com/sundarr/quark-provider",
  "adapter_api_version": "1.0",
  "entry": "quark_provider.adapter:create_provider",
  "config_schema": {
    "cookie": {
      "type": "password",
      "required": true,
      "label": "Cookie",
      "secret": true
    }
  },
  "dependencies": [],
  "status": "loaded",
  "error_message": null,
  "commit_hash": "abc123",
  "repo_path": "/home/user/.sundarr/plugins/repos/quark-provider"
}
```

### 启用插件

**POST** `/plugins/plugins/{plugin_id}/enable`

启用指定插件。

**路径参数**:
- `plugin_id`: 插件 ID

**响应示例**:
```json
{
  "status": "success",
  "message": "插件已启用"
}
```

### 禁用插件

**POST** `/plugins/plugins/{plugin_id}/disable`

禁用指定插件。

**路径参数**:
- `plugin_id`: 插件 ID

**响应示例**:
```json
{
  "status": "success",
  "message": "插件已禁用"
}
```

### 更新插件配置

**PUT** `/plugins/plugins/{plugin_id}/config`

更新指定插件的配置。

**路径参数**:
- `plugin_id`: 插件 ID

**请求体**:
```json
{
  "config_data": {
    "cookie": "your-quark-cookie",
    "timeout": 30
  }
}
```

**响应示例**:
```json
{
  "status": "success",
  "message": "插件配置已更新"
}
```

## 统计信息

### 获取插件统计

**GET** `/plugins/stats`

获取插件系统的统计信息。

**响应示例**:
```json
{
  "total": 10,
  "builtin": 1,
  "external": 9,
  "loaded": 8,
  "error": 1,
  "disabled": 1,
  "source": 3,
  "cloud_provider": 2,
  "notification": 2,
  "crawler": 1,
  "link_validator": 1,
  "link_extractor": 0,
  "task_processor": 1
}
```

## 加载操作

### 加载所有仓库

**POST** `/plugins/load-all`

加载所有已配置的插件仓库。

**响应示例**:
```json
{
  "status": "success",
  "message": "加载完成：总计 5，成功 4，失败 1",
  "stats": {
    "total": 5,
    "loaded": 4,
    "error": 1,
    "errors": [
      {
        "repo": "bad-plugin",
        "error": "插件清单文件不存在"
      }
    ]
  }
}
```

## 错误处理

所有 API 端点都可能返回以下错误响应：

### 400 Bad Request

请求参数错误。

```json
{
  "detail": "错误描述"
}
```

### 404 Not Found

资源不存在。

```json
{
  "detail": "仓库不存在：repo-id"
}
```

### 500 Internal Server Error

服务器内部错误。

```json
{
  "detail": "内部服务器错误"
}
```

## 使用示例

### 使用 curl

```bash
# 获取所有插件
curl http://localhost:8000/plugins/plugins

# 添加插件仓库
curl -X POST http://localhost:8000/plugins/repositories \
  -H "Content-Type: application/json" \
  -d '{
    "repo_url": "https://github.com/sundarr/quark-provider.git",
    "branch": "main",
    "name": "quark-provider"
  }'

# 更新插件配置
curl -X PUT http://localhost:8000/plugins/plugins/quark-provider/config \
  -H "Content-Type: application/json" \
  -d '{
    "config_data": {
      "cookie": "your-quark-cookie"
    }
  }'
```

### 使用 Python

```python
import requests

base_url = "http://localhost:8000/plugins"

# 获取所有插件
response = requests.get(f"{base_url}/plugins")
plugins = response.json()

# 添加插件仓库
data = {
    "repo_url": "https://github.com/sundarr/quark-provider.git",
    "branch": "main",
    "name": "quark-provider"
}
response = requests.post(f"{base_url}/repositories", json=data)
result = response.json()

# 更新插件配置
config_data = {
    "config_data": {
        "cookie": "your-quark-cookie"
    }
}
response = requests.put(
    f"{base_url}/plugins/quark-provider/config",
    json=config_data
)
result = response.json()
```

## 参考

- [插件系统概述](20-plugin-system.md)
- [插件清单规范](20-plugin-manifest-spec.md)
- [插件开发指南](22-plugin-development-guide.md)
