# 插件管理 API 规范

本文档记录当前 API 和 Phase 10 目标扩展。更新时间：2026-08-27。

基础前缀：`/plugins`。

---

## 1. 当前已实现接口

```text
GET    /plugins/repositories
POST   /plugins/repositories
PUT    /plugins/repositories/{repo_id}
POST   /plugins/repositories/{repo_id}/rollback
DELETE /plugins/repositories/{repo_id}

GET    /plugins/plugins
GET    /plugins/plugins/{plugin_id}
PUT    /plugins/plugins/{plugin_id}/config
POST   /plugins/plugins/{plugin_id}/enable
POST   /plugins/plugins/{plugin_id}/disable

GET    /plugins/stats
POST   /plugins/load-all
```

当前限制：

```text
POST /repositories 在多 Source 仓库返回列表时响应处理尚未完全兼容。
load-all 需要手动调用，应用启动不会自动执行。
接口尚未暴露 Activation、依赖和 cleanup 状态。
Web Console 尚未提供对应页面。
当前响应按 flat v1 单插件假设实现，尚未支持通用 Manifest v2 的同仓库多声明。
```

---

## 2. 仓库响应目标格式

```json
{
  "id": "repo_01",
  "name": "sundarr-sources",
  "repo_url": "https://github.com/example/sundarr-sources.git",
  "branch": "main",
  "current_commit": "abc123",
  "previous_commit": "def456",
  "enabled": true,
  "status": "loaded",
  "last_error": null,
  "loaded_plugin_ids": ["seedhub"],
  "last_checked_at": null,
  "last_loaded_at": "2026-08-26T10:00:00Z"
}
```

`repo_url` 指向用户信任代码来源。API 不接受 Python 源码内容。

---

## 3. Phase 10 Activation 扩展

新增只读诊断接口：

```text
GET /plugins/activations
GET /plugins/activations/{plugin_id}
GET /plugins/plugins/{plugin_id}/logs
POST /plugins/repositories/{repo_id}/check-update
POST /plugins/repositories/{repo_id}/test-candidate
```

Activation 响应：

```json
{
  "plugin_id": "seedhub",
  "repository_id": "repo_01",
  "commit_hash": "abc123",
  "status": "active",
  "requires": ["source_registry", "http_client"],
  "provides": ["source.search.v1"],
  "cleanup_count": 2,
  "error": null,
  "activated_at": "2026-08-26T10:00:00Z"
}
```

对外响应不得暴露 Python module 对象、函数引用、密码、Cookie、Token 或完整私有链接。

---

## 4. 更新与回滚语义

`check-update`：

```text
允许 fetch 元数据。
不修改 current_commit。
不执行新代码。
返回远程候选 commit。
```

`test-candidate`：

```text
checkout 明确候选 commit。
创建临时候选 Activation。
执行 manifest/config/依赖/健康测试。
完成后清理候选副作用。
不替换当前 active 插件。
```

`PUT /repositories/{repo_id}` 应用更新：

```text
候选验证成功后原子切换。
成功时 current_commit -> previous_commit，候选 -> current_commit。
失败时 current_commit 和旧 Activation 保持不变。
```

`rollback` 使用相同候选和原子切换流程，不能直接修改数据库 commit 后再尝试加载。

---

## 5. 错误码

```text
PLUGIN_REPOSITORY_NOT_FOUND
PLUGIN_REPOSITORY_UNTRUSTED
PLUGIN_CLONE_FAILED
PLUGIN_COMMIT_NOT_FOUND
PLUGIN_MANIFEST_INVALID
PLUGIN_ENTRY_INVALID
PLUGIN_DEPENDENCY_MISSING
PLUGIN_CONFIG_INVALID
PLUGIN_HEALTH_CHECK_FAILED
PLUGIN_ACTIVATION_FAILED
PLUGIN_CLEANUP_FAILED
PLUGIN_ID_CONFLICT
```

单插件错误默认返回该操作失败，不应使 API 进程退出。

---

## 6. 验收标准

```text
仓库 CRUD、更新、回滚、启停和配置有 API 测试。
多 Source 仓库响应正确返回全部 plugin_id。
通用 v2 仓库响应按声明返回全部 plugin_id，插件配置和错误状态彼此独立。
候选测试没有残留 registry 项或资源。
更新失败保留旧 active 插件。
日志和响应不泄露凭据。
```
