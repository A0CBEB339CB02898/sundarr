# Web Console 规范

本文档定义 Sundarr MVP Web Console 的范围、页面和交互。

---

## 1. 技术选择

MVP Web Console 使用：

```text
React
Vite
FastAPI API
```

FastAPI 只作为 API 后端，不做 Jinja2 页面渲染。

---

## 2. 设计目标

Web Console 是核心控制台，不是完整媒体库 UI。

目标：

```text
搜索资源
选择候选资源
管理媒体源配置
管理 SMB 配置
浏览 SMB 目标目录
创建归档任务
查看任务进度
取消 / 重试任务
显示关键错误和中断提示
```

---

## 3. 不做事项

MVP Web Console 不做：

```text
登录注册
多用户权限
角色管理
完整媒体库 UI
海报墙
播放器
完整 NAS 文件管理器
拖拽式文件管理
任意 NAS 文件删除
在线编辑代码型 Source Adapter
配置版本回滚
审计日志
```

---

## 4. 页面结构

MVP 页面：

```text
/search       搜索和候选资源
/transfers    任务列表和任务详情
/storage      SMB 配置、连接测试、目录浏览
/sources      媒体源配置
/status       API / Worker / DB / Redis 状态摘要
```

---

## 4.1 开发顺序

Web Console 按可验证停止点推进：

```text
Phase 7.1 Web Console Shell
Phase 7.2 Status Page
Phase 7.3 Transfers Page
Phase 7.4 Storage Page
Phase 7.5 Search Page
Phase 7.6 Sources Page
Phase 7.7 Web Console Polish And Closure
```

顺序理由：

```text
先 Shell，统一导航、API client 和错误展示。
再 Status，用最小 API 调用验证前后端闭环。
再 Transfers，优先把 Phase 6 cancel / retry / logs 暴露给用户。
再 Storage，让用户能配置 SMB 并看到 STORAGE_CONFIG_CHANGED 影响。
再 Search，形成搜索到创建任务的最小前端流程。
最后 Sources 和统一收口，避免过早扩大到供应商开发。
```

Phase 7 期间仍不启动真实供应商开发或真实集成测试；这些工作等 Web Console 具备任务操作界面后再做。

---

## 5. Search 页面

功能：

```text
输入 keyword
选择 type: movie / tv / anime / unknown
可选 year
展示候选结果
展示 source、quality、links、score
选择 link
选择目标 library
选择或输入目标路径
创建 transfer
```

交互规则：

```text
搜索调用 GET /search。
创建任务调用 POST /transfers。
低置信度目标目录应提示用户确认。
```

---

## 6. Transfers 页面

功能：

```text
查看任务列表
查看任务状态
查看 done_bytes / total_bytes / speed / ETA
查看当前文件
取消任务
重试任务
查看错误码和错误信息
```

必须突出显示：

```text
STORAGE_CONFIG_CHANGED
VERIFY_FAILED
CLOUD_CLEANUP_FAILED
NAS_WRITE_FAILED
```

`STORAGE_CONFIG_CHANGED` 提示文案必须说明：

```text
SMB 配置已变更，任务已中断。
.downloading 文件和 cloud staging 已保留。
可在确认新配置后重试。
```

---

## 7. Storage 页面

功能：

```text
查看 SMB 配置摘要
修改 host / port / share / username / password / domain / base_path
配置 library: movies / tv / anime
测试 SMB 连接
浏览 SMB 目录
```

规则：

```text
password 不回显明文。
password 留空表示保留原值。
保存 SMB 配置后立即热加载。
保存 SMB 配置会中断使用旧配置的运行中任务。
目录浏览只能在允许范围内进行。
```

API：

```text
GET  /storage/config
POST /storage/config/save
POST /storage/config/test
GET  /storage/browse
```

---

## 8. Sources 页面

功能：

```text
查看 source 列表
新增配置型源
新增文档/表格型源
编辑 source
启用 / 禁用 source
测试 source 搜索
查看最后一次错误
```

限制：

```text
不允许在线编辑代码型 Source Adapter。
不允许上传执行代码。
```

API：

```text
GET  /sources
POST /sources/create
GET  /sources/{source_id}
POST /sources/{source_id}/update
POST /sources/{source_id}/enable
POST /sources/{source_id}/disable
POST /sources/{source_id}/test
```

---

## 9. Status 页面

功能：

```text
API health
Worker status
PostgreSQL status
Redis status
enabled source count
storage config status
```

Status 页面只显示摘要，不做复杂监控系统。

---

## 10. 前端状态策略

MVP 不引入复杂全局状态方案，除非实现阶段确认需要。

推荐：

```text
React local state
fetch API wrapper
simple polling for transfer progress
```

任务进度刷新：

```text
MVP 使用轮询。
后续可改 WebSocket 或 SSE。
```

---

## 11. 验收标准

Web Console 完成时必须满足：

```text
可以搜索资源。
可以创建 transfer task。
可以查看任务进度。
可以取消和重试任务。
可以查看和修改 SMB 配置。
可以测试 SMB 连接。
可以浏览 SMB 目标目录。
可以管理配置型源和文档/表格型源。
SMB 配置变更导致任务中断时有明确提示。
取消、重试、保存 SMB 配置、创建任务、启用或禁用 source 等关键操作需要用户确认。
不提供登录注册和权限管理。
不提供完整媒体库 UI。
```
