# AI Tool API 规范

本文档定义 Sundarr 后续作为 AI / Agent 可调用 media search tool 的接口方向。

---

## 1. 目标

FastAPI 后续可封装为 AI Tool API。

原则：

```text
AI 不直接抓网页。
AI 不直接操作 NAS。
AI 不直接处理 SMB 凭据。
AI 只调用 Sundarr API。
Sundarr 负责搜索、候选解释、任务创建、状态查询和错误恢复。
```

---

## 2. 工具列表

推荐工具：

```text
search_media(query, type?, year?)
get_resource(resource_id)
create_transfer(resource_id, link_id, target_library, target_path?)
get_transfer_status(task_id)
cancel_transfer(task_id)
retry_transfer(task_id)
```

---

## 3. search_media

输入：

```json
{
  "query": "interstellar",
  "type": "movie",
  "year": 2014
}
```

输出应包含：

```text
resource_id
title
type
year
score
candidate explanation
links summary
confidence
```

AI 应向用户展示候选结果，不应默认自动搬运低置信度结果。

---

## 4. create_transfer

输入：

```json
{
  "resource_id": "res_001",
  "link_id": "link_001",
  "target_library": "movies",
  "target_path": "Interstellar (2014)"
}
```

规则：

```text
如果 target_path 缺失，Sundarr 可用规则生成建议路径。
低置信度路径需要用户确认。
AI 不直接构造 SMB 绝对路径。
```

---

## 5. 状态查询

AI 查询任务状态时，Sundarr 返回：

```text
status
progress
done_bytes
total_bytes
speed
eta
current_file
error_code
retryable
user_action_required
```

对于 `STORAGE_CONFIG_CHANGED`，AI 应提示：

```text
SMB 配置已变更，任务已中断。
.downloading 和 cloud staging 已保留。
确认新 SMB 配置后可重试。
```

---

## 6. 自动执行边界

MVP 默认不做全自动转存。

AI 在以下场景必须请求用户确认：

```text
候选资源低置信度
目标目录低置信度
多个相似候选
目标文件已存在
任务需要重试
```

---

## 7. 验收标准

AI Tool API 完成时必须满足：

```text
AI 可搜索资源。
AI 可获取资源详情。
AI 可创建 transfer。
AI 可查询任务状态。
AI 可取消和重试任务。
AI 不需要直接访问网页、网盘或 SMB。
响应包含足够的解释字段和用户确认信号。
```
