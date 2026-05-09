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
管理多个 SMB 连接
浏览 SMB 目录
管理媒体库
创建归档任务
查看任务进度
取消 / 重试任务
显示关键错误和中断提示
管理下载到本地绑定
手动触发下载到本地来源扫描
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
/app/search       搜索和候选资源
/app/transfers    完整任务列表和任务详情
/app/storage      SMB 连接列表、连接测试、目录浏览
/app/libraries    媒体库管理
/app/sources      媒体源配置
/app/download-to-local 下载到本地配置和扫描
/app/status       API / Worker / DB / Redis 状态摘要
```

Web Console 页面路由使用 `/app/*` 前缀，避免与 FastAPI API 路由 `/search`、`/sources`、`/storage`、`/transfers`、`/health` 在 Vite dev proxy 下冲突。

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
Phase 7.8 Web Console UI Polish
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
查看任务详情
查看任务状态
查看 done_bytes / total_bytes / speed / ETA
查看当前文件
取消任务
重试任务
查看错误码和错误信息
```

任务展示分为两层：

```text
全局右侧浮动任务面板：展示当前所有任务的状态摘要，便于在任意页面查看进度。
/app/transfers 页面：保留为完整任务列表、任务详情、日志、取消和重试操作页面。
```

右侧浮动任务面板规则：

```text
默认显示最近活跃任务和运行中任务。
支持展开查看更多任务。
支持跳转到 /app/transfers 查看详情。
在移动端应降级为底部抽屉或可折叠入口，避免遮挡主要内容。
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
查看 SMB 连接列表
通过新增按钮弹出表单创建 SMB 连接
编辑 host / port / share / username / password / domain / base_path
测试 SMB 连接
浏览 SMB 目录
```

规则：

```text
页面默认展示 SMB 连接列表，不默认展开空新增表单。
新增和编辑使用弹出表单。
password 不回显明文。
password 留空表示保留原值。
保存 SMB 连接后立即热加载。
保存某个 SMB 连接会中断使用该连接旧配置的运行中任务。
目录浏览只能在允许范围内进行。
SMB 连接测试必须由后端执行，验证后端运行环境到 SMB 服务器的网络、DNS、认证和权限。
```

API：

```text
GET  /storage/config
POST /storage/config/save
POST /storage/config/test
GET  /storage/browse
GET  /storage/smb-connections
POST /storage/smb-connections/create
POST /storage/smb-connections/{connection_id}/update
POST /storage/smb-connections/{connection_id}/test
GET  /storage/smb-connections/{connection_id}/browse
```

---

## 7.1 媒体库页面

功能：

```text
查看媒体库列表
通过新增按钮弹出表单创建媒体库
编辑、启用、禁用媒体库
选择媒体库类型：movie / series / unclassified
选择 SMB 连接和本地 NAS 目录
测试媒体库目录可写
```

规则：

```text
媒体库是本地 NAS 上的逻辑目录，不是海报墙、播放器或完整媒体库 UI。
页面默认展示媒体库列表，不默认展开空新增表单。
新增和编辑使用弹出表单。
媒体库表单只能选择已配置 SMB 连接，不重复填写 SMB host/share/username/password。
至少需要一个 unclassified 媒体库作为下载到本地 fallback。
```

API：

```text
GET  /media-libraries
POST /media-libraries/create
GET  /media-libraries/{library_id}
POST /media-libraries/{library_id}/update
POST /media-libraries/{library_id}/enable
POST /media-libraries/{library_id}/disable
POST /media-libraries/{library_id}/test
```

---

## 7.2 下载到本地页面

功能：

```text
查看下载绑定列表
通过新增按钮弹出表单创建绑定
选择来源 SMB 连接和来源目录
选择目标媒体库
手动扫描来源目录
为稳定文件创建下载任务
查看发现文件和关联任务
```

规则：

```text
页面默认展示绑定列表和最近发现文件，不默认展开空新增表单。
绑定表单只能选择已配置来源 SMB 连接和目标媒体库，不重复填写 SMB host/share/username/password。
来源目录通过 SMB 连接目录浏览选择或手动输入相对路径。
目标目录来自媒体库管理模块，不在下载到本地表单中重复配置。
保存分享链接到网盘的后续模块命名为“保存到网盘”，不属于本页面。
```

---

## 8. Sources 页面

功能：

```text
查看 source 列表
查看已安装代码型 Source Adapter
编辑 Adapter 非代码参数
启用 / 禁用 source
测试 source 搜索
查看最后一次错误
查看最近一次搜索耗时和状态
```

限制：

```text
不允许在线编辑代码型 Source Adapter。
不允许上传执行代码。
不在配置或数据库中保存可执行 Python 代码。
不支持通过 Web Console 配置复杂网站爬虫。
不要求用户维护本地文档/表格作为主要媒体源。
```

说明：Sources 页面是已安装代码型 Adapter 的管理入口，不代表真实媒体源接入已完成。真实媒体源需要后续通过代码型 Adapter 逐站点实现。

API：

```text
GET  /sources
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

## 10. 下载到本地页面

功能：

```text
查看下载到本地全局配置
配置 delete_source_after_success
配置 delete_empty_source_dirs
配置 unclassified 目录
查看 binding 列表
通过新增按钮弹出表单创建 binding
编辑 / 启用 / 禁用 binding
选择来源 SMB connection 和来源目录
选择目标 SMB connection 和本地媒体库目录
测试来源目录可读
测试目标目录可写
手动触发扫描
查看最近发现文件和下载任务
```

限制：

```text
不在 Web Console 中挂载网盘。
不在 Web Console 中自动保存分享链接到网盘；后续模块命名为“保存到网盘”。
不显示 SMB password 明文。
页面默认展示列表，不默认展开空新增表单。
绑定表单只选择已配置 SMB connection，不重复填写 SMB 凭据。
删除源文件和空目录必须只发生在下载成功并完成校验之后。
```

---

## 11. 前端状态策略

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

## 12. 主题和响应式

Web Console 需要支持：

```text
亮色模式
暗色模式
跟随系统
```

主题规则：

```text
默认跟随系统。
用户可在 Web Console 中切换主题。
MVP 无多用户系统，主题偏好优先保存在浏览器本地。
```

响应式规则：

```text
桌面端优先保证多列布局和右侧任务面板可用。
移动端必须可读、可操作，不出现输入框和按钮错位。
移动端任务面板应使用底部抽屉或折叠入口。
表单控件、按钮和提示文案需要统一对齐和间距。
```

---

## 13. 验收标准

Web Console 完成时必须满足：

```text
可以搜索资源。
可以创建 transfer task。
可以查看任务进度。
可以取消和重试任务。
可以查看和修改多个 SMB 连接。
可以测试 SMB 连接。
可以浏览 SMB 目标目录。
可以管理已安装代码型 Source Adapter。
可以管理下载到本地绑定。
可以通过全局任务面板查看当前任务状态摘要。
可以在 /app/transfers 查看完整任务列表和详情。
支持亮色、暗色和跟随系统三种主题模式。
桌面端和移动端布局均可用。
SMB 配置变更导致任务中断时有明确提示。
取消、重试、保存 SMB 配置、创建任务、启用或禁用 source 等关键操作需要用户确认。
不提供登录注册和权限管理。
不提供完整媒体库 UI。
```
