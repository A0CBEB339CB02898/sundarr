# MVP 开发路线

本文档定义 Sundarr MVP 的开发阶段、交付物和验收标准。

---

## 总体原则

MVP 的目标是先跑通端到端闭环：

```text
搜索资源
-> 提取网盘链接
-> 用户手动保存到网盘
-> NAS 或挂载服务挂载网盘并通过 SMB 暴露来源目录
-> Sundarr 通过 SMB 下载到本地媒体库
-> 校验
-> rename
-> 删除来源文件和空目录
-> 返回任务状态
```

开发原则：

```text
先后端闭环，后前端完善。
CloudProvider 保留为可选扩展，近期不做真实网盘直接下载。
Phase 10.0 质量基线已收口；当前优先完成 Phase 10.1 媒体发现中心，随后恢复插件生命周期和外部搜索源仓库闭环。
真实挂载目录下载到本地通过手动集成验收验证。
先规则和用户确认，后模型辅助。
先核心控制台，后媒体发现中心；不建设完整本地媒体库 UI。
每个阶段必须可测试。
每个阶段都必须有明确停止条件。
```

停止条件用于判断“做到这里可以暂停、提交、切换任务或等待用户验收”。满足停止条件不代表该阶段所有增强项都完成，只代表当前交付单元已经闭合，不会留下不可验证的半成品。

---

## 当前实现状态

截至 2026-08-27，本项目阶段状态如下：

```text
Phase 0 Project Skeleton: 已完成。
Phase 1 Persistence Models: 已完成。
Phase 2 Search And Resource Library: 已完成。
Phase 3 Cloud Staging: 已完成。
Phase 4 Storage Writer: 已收口，已完成 LocalWriter、Storage 配置 API、目录浏览 API、STORAGE_CONFIG_CHANGED 中断规则、SmbWriter 安全边界和真实 SMB 连接、目录浏览、写入、size、rename 手动验收。
启动与配置精简：sundarr start/restart/stop/status 已管理 API + Web + Worker，并自动执行数据库初始化/迁移、默认 settings seed 和前端依赖安装；Windows PID 文件已指向真实 API / Web / Worker 服务进程。
Phase 5 Transfer Worker: 已完成当前 MVP Worker 主链路，Phase 5.1 到 Phase 5.5 均已完成。
Phase 6 Cleanup And Recovery: 已完成，Phase 6.1 到 Phase 6.5 均已完成。
Phase 7 Web Console: 已完成。
Phase 7.8 Web Console UI Polish: 已完成。
Phase 8 Download To Local: 已实现；真实挂载目录下载到本地仍需手动集成验收。
Phase 9 Module Refactoring: 已完成；旧 DTL 模块已删除，Worker 统一为 process_sync_task 同步路径，远程媒体库和同步绑定已就位。
Phase 9.5 Resource Favorites Refactoring: 已完成；Resource / ResourceLink 已收缩为收藏模型，搜索默认不入库，Web Console 使用单一收藏入口。
Phase 10.0 Quality Baseline Closure: 已完成；当前默认 pytest 204 项通过，前端构建、Alembic 链路和连续两轮 CLI 启停冒烟通过。
Phase 10.1 Media Discovery Center: 当前优先、尚未实现；先完成媒体身份、数据来源、持久化和信息架构设计，再实现筛选、热门、分类、详情、关注列表和发现型海报墙。
Phase 10.2 Plugin Activation Runtime Completion: 已在稳定节点暂停；生命周期内核和 8 项测试已完成，待恢复 manifest 能力声明、Source 注册动作、候选健康检查、原子切换和启动自动加载。
Phase 10.3 External Source End-to-End: Phase 10.2 后执行，完成仓库管理和真实源验收。
Phase 11 AI Friendly API: 未开始，原 Phase 8 后移。
Phase 12 Cloud Direct Download: 非 MVP，高级功能；仅保留规格文档，后续单独实现。
媒体发现中心：已纳入当前 MVP 和当前优先任务；不包括本地媒体库海报墙、播放或观影进度。
```

Phase 0-10.0 已完成。后续插件交付必须持续保持该质量基线。

---

## Phase 0: Project Skeleton

目标：建立可启动、可测试的基础项目。

交付物：

```text
FastAPI app
React + Vite web app skeleton
Dockerfile
docker-compose.yml
PostgreSQL service
Redis service
GET /health
settings loader
pytest baseline
```

不做：

```text
真实搜索源
真实网盘 Provider
SMB 写入
完整前端页面
权限系统
```

验收标准：

```text
API 可以启动。
Web 可以启动。
PostgreSQL 和 Redis 可以通过 compose 启动。
GET /health 返回正常。
pytest smoke test 通过。
```

停止条件：

```text
项目可以被 clone 后安装依赖。
后端 /health smoke test 通过。
前端 npm run build 通过。
基础 Docker Compose 配置存在，无法运行时需说明环境原因。
工作区已提交或明确说明不提交原因。
```

---

## Phase 1: Persistence Models

目标：建立核心持久化模型。

交付物：

```text
Alembic migrations
Source model
Resource model
ResourceLink model
TransferTask model
TransferFile model
TransferLog model
Setting model
database session management
```

验收标准：

```text
数据库迁移可执行。
核心表可创建。
基础 repository 或 service 可读写测试数据。
状态字段和错误字段存在。
```

停止条件：

```text
SQLAlchemy 模型覆盖 docs/08-data-model.md 的核心表。
Alembic 初始迁移存在，并可通过离线迁移校验。
模型测试通过。
数据库 URL、依赖和 Docker 配置已同步。
工作区已提交或明确说明不提交原因。
```

---

## Phase 2: Search And Resource Library

> 历史阶段说明：Phase 2 初版包含“搜索结果入库”。该方向已在 Phase 9.5 调整为“搜索实时返回，用户主动收藏资源或资源链接时才入库”。本节保留历史验收背景，后续实现以 `docs/05-search-pipeline-spec.md`、`docs/08-data-model.md` 和 `docs/09-api-contract.md` 的最新边界为准。

目标：实现多源搜索框架和资源候选结果标准化。

交付物：

```text
SourceModel
SearchQuery
RawSearchItem
one example source
parser pipeline
cloud link extractor
normalizer
deduper
ranker
GET /search
资源/资源链接收藏接口（由 Phase 9.5 收缩重构）
```

验收标准：

```text
一个 source 失败不影响整体搜索。
RawSearchItem 输出格式统一。
可以从文本中提取至少一种 provider 链接。
搜索结果可标准化为 ResourceCandidate / ResourceLinkResult。
用户主动收藏后可写入资源/资源链接收藏库。
重复资源可基础合并。
```

停止条件：

```text
SourceModel / SearchQuery / RawSearchItem 已落地。
至少一个示例 source 可通过 /search 返回候选结果。
Cloud Link Extractor 至少支持一个 provider 的链接和提取码识别。
搜索结果默认不自动持久化到 resources / resource_links。
收藏模块可从数据库读取资源收藏和资源链接收藏详情。
source 失败隔离有测试覆盖。
pytest 通过。
工作区已提交或明确说明不提交原因。
```

阶段内可拆分停止点：

```text
停止点 2A：Source Adapter 框架 + 示例源 + /search 可用。
停止点 2B：Resource Library 持久化 + /resources/{id} 数据库读取可用。
停止点 2C：sources 管理 API 可用，包括列表、新增、编辑、启用、禁用、测试。
```

---

## Phase 3: Cloud Staging

目标：实现 cloud provider 抽象和 mock/local provider。

交付物：

```text
CloudProvider interface
Mock/Local Provider
save_share
list_files
open_file_stream
delete with safe path guard
```

验收标准：

```text
不依赖真实网盘即可创建 staging。
可以列出 staging 文件。
可以从 mock/local 文件流式读取。
只能删除允许的 staging path。
```

停止条件：

```text
CloudProvider 接口已落地。
Mock/Local Provider 可完成 save_share / list_files / open_file_stream / delete。
delete 有 staging path guard 测试。
不依赖真实网盘即可跑通 provider 测试。
pytest 通过。
工作区已提交或明确说明不提交原因。
```

---

## Phase 4: Storage Writer

目标：实现不依赖系统 mount 的 NAS 写入层。

交付物：

```text
StorageWriter interface
SmbWriter
LocalWriter for tests
SMB settings API
SMB connection test
SMB directory browse
SMB config hot reload
STORAGE_CONFIG_CHANGED interruption
```

验收标准：

```text
SmbWriter 可连接 SMB share。
可以创建目录。
可以写入 .downloading。
可以获取远端文件大小。
可以 rename。
SMB 配置修改不需要重启。
SMB 配置修改会中断使用旧配置的运行中任务。
```

停止条件：

```text
StorageWriter 接口已落地。
LocalWriter 有自动化测试覆盖。
SmbWriter 至少完成连接测试、目录浏览、写入、size、rename 的实现或明确 mock 边界。
SMB 配置保存到 settings，并支持热加载。
STORAGE_CONFIG_CHANGED 中断规则有测试覆盖。
pytest 通过；前端如有改动则 npm run build 通过。
工作区已提交或明确说明不提交原因。
```

---

## Phase 5: Transfer Worker

目标：实现搬运任务执行主链路。

Phase 5 有明显复杂度，按以下子阶段推进。每个子阶段都必须能独立测试、独立说明验收结果，不把 Phase 6 的取消、重试、启动恢复提前混入第一轮 Worker 主链路。

交付物：

```text
POST /transfers
GET /transfers/{id}
worker state machine
download to .downloading
progress update
speed calculation
size verification
rename
sundarr start / restart / stop / status 管理 Worker
```

验收标准：

```text
可以创建 transfer task。
Worker 可以从 cloud stream 写入 StorageWriter。
任务进度可查询。
文件大小校验成功后 rename。
失败时记录 error_code、error_message、retryable。
```

停止条件：

```text
POST /transfers 可创建任务。
Worker 可使用 Mock/Local Provider + LocalWriter 跑通下载到 .downloading。
GET /transfers/{id} 可查询状态和进度。
大小校验和 rename 有测试覆盖。
失败路径记录 error_code / error_message / retryable。
sundarr start / restart / stop / status 已同步管理 Worker。
pytest 通过。
工作区已提交或明确说明不提交原因。
```

### Phase 5.1: Worker Skeleton

状态：已完成。

目标：让 Worker 成为可启动、可停止、可观测的后台组件，但先不执行搬运。

交付物：

```text
Worker 进程入口
sundarr start 启动 API + Web + Worker
sundarr stop 停止 API + Web + Worker
sundarr restart 重启 API + Web + Worker
sundarr status 显示 API / Web / Worker 状态
Worker 从 settings 读取 worker.enabled 和 worker.concurrency
Worker 空转 loop 可退出
```

验收标准：

```text
sundarr restart 后 API / Web / Worker 均运行。
sundarr stop 后 API / Web / Worker 均停止。
worker.concurrency 默认值为 2，且来自 settings 表。
Worker disabled 时不领取任务。
```

停止条件：

```text
pytest 覆盖 Worker 配置读取和 CLI 管理 Worker。
实际运行验证 sundarr restart / status / stop。
文档说明 Worker 已纳入完整项目启动。
```

### Phase 5.2: Task Claiming

状态：已完成。

目标：Worker 能安全领取 pending 任务，先不做真实搬运。

交付物：

```text
扫描 pending TransferTask
按 worker.concurrency 领取任务
单 Worker 进程内避免重复领取同一任务
领取后写入运行中状态和 transfer log
```

验收标准：

```text
创建 3 个 pending task，worker.concurrency=2 时最多 2 个进入运行态。
未被领取的任务保持 pending。
已完成或 failed / cancelled 任务不会被领取。
```

停止条件：

```text
pytest 覆盖并发领取上限。
pytest 覆盖非 pending 任务不会被领取。
暂不要求多 Worker 进程抢锁。
```

### Phase 5.3: Local Transfer Happy Path

状态：已完成。

目标：用 LocalCloudProvider + LocalWriter 跑通端到端搬运成功路径。

当前领取和执行范围仅限 `target_type=local` 且 `ResourceLink.provider=local` 的任务。默认 SMB 任务在真实 SMB 搬运实现前不被 Worker 领取，避免任务进入无法完成的运行态。

交付物：

```text
从 cloud stream 读取文件
写入 target_path + .downloading
更新 done_bytes / total_bytes
校验 size
rename 到最终 target_path
task.status = completed
```

验收标准：

```text
POST /transfers 创建任务后，Worker 可执行到 completed。
目标文件存在，.downloading 已 rename。
GET /transfers/{id} 可查询 completed、done_bytes、total_bytes。
```

停止条件：

```text
pytest 使用 Mock/Local Provider + LocalWriter 跑通成功路径。
pytest 不依赖真实网盘、真实 NAS 或真实 SMB。
```

### Phase 5.4: Failure Handling

状态：已完成。

目标：Worker 失败路径可追踪、可解释，不留下不可知状态。

交付物：

```text
cloud stream 读取失败 -> failed
写入失败 -> failed
size mismatch -> failed
target exists -> failed
error_code / error_message / retryable 写入 transfer_tasks
关键事件写入 transfer_logs
```

验收标准：

```text
失败任务可通过 GET /transfers/{id} 查询错误原因。
失败时默认保留 .downloading 和 cloud staging。
失败路径不误删正式文件。
```

停止条件：

```text
pytest 覆盖至少 cloud read failed、size mismatch、target exists 三类失败。
失败日志可查询或至少已写入 transfer_logs。
```

### Phase 5.5: API Status Polish

状态：已完成。

目标：让任务查询结果对 Web Console 和 AI Tool 友好。

交付物：

```text
GET /transfers/{id} 返回 progress
GET /transfers/{id} 返回 current_file 或明确为空
GET /transfers/{id} 返回 error_code / error_message / retryable
GET /health 的 worker 从 unknown 进入可判断状态，或明确说明当前判断边界
```

验收标准：

```text
前端和 AI 可以通过 API 看到任务进度和失败原因。
接口 schema 与 docs/09-api-contract.md 一致。
```

停止条件：

```text
pytest 覆盖 Transfer response schema。
API 文档、状态机文档和测试计划同步更新。
```

---

## Phase 6: Cleanup And Recovery

目标：实现安全清理、取消、重试和恢复。

Phase 6 负责把 Phase 5 已跑通的本地 Worker 主链路变成可取消、可重试、可恢复、可安全清理的任务系统。Phase 6 不扩大到真实网盘 Provider 或完整 Web Console UI。

交付物：

```text
safe cloud cleanup
retry failed task
cancel task
worker startup recovery
transfer logs
cleanup logs
```

验收标准：

```text
只有所有 transfer_files.status == completed 才能清理 cloud staging。
校验失败保留 cloud staging。
cleanup 失败不删除本地已完成文件。
cancel downloading 会保留 .downloading。
retry 使用最新 SMB 配置。
```

停止条件：

```text
cancel / retry API 可用。
cleanup 前置条件严格执行。
worker startup recovery 有保守恢复策略。
校验失败、cleanup 失败、取消下载、重试任务均有测试覆盖。
pytest 通过。
工作区已提交或明确说明不提交原因。
```

### Phase 6.1: Cancel Task

状态：已完成。

目标：提供任务取消入口，并保证取消不会误删 `.downloading` 或 cloud staging。

交付物：

```text
POST /transfers/{task_id}/cancel
pending -> cancelled
staging_to_cloud / downloading / verifying -> cancelled 或保守 failed/cancelled
completed / failed / cancelled 拒绝取消
取消时写入 transfer_logs
取消时保留 .downloading 和 cloud staging
```

验收标准：

```text
pending task 可取消。
running task 可进入 cancelled 或明确失败状态。
completed / failed task 不可取消。
取消不会删除目标正式文件、.downloading 或 cloud staging。
```

停止条件：

```text
pytest 覆盖 pending、running、completed、failed 的取消规则。
API 契约与实际响应一致。
```

### Phase 6.2: Retry Failed Task

状态：已完成。

目标：提供失败任务重试入口，允许可重试任务回到可执行状态。

交付物：

```text
POST /transfers/{task_id}/retry
仅 failed 且 retryable=true 可重试
retry_count + 1
清理 error_code / error_message / retryable
使用最新 storage / SMB 配置快照
写入 transfer_logs
```

验收标准：

```text
retryable=true 的 failed task 可重试。
retryable=false 的 failed task 拒绝重试。
重试不盲目删除 .downloading。
重试任务后续可被 Worker 重新领取。
```

停止条件：

```text
pytest 覆盖 retryable true / false、retry_count、最新配置快照。
不实现复杂 resume，resume 策略可留到后续增强。
```

### Phase 6.3: Safe Cloud Cleanup

状态：已完成。

目标：任务完成后安全清理 cloud staging，同时保证任何失败或未完成状态都不会误删。

交付物：

```text
completed 后进入 cleaning_cloud
cleanup 前置条件检查
删除 cloud staging 子目录
cleanup 成功后 task.status = completed 或保持 completed 并记录 cleanup_completed
cleanup 失败写入 cleanup_failed 日志
```

验收标准：

```text
只有所有 transfer_files.status == completed 才允许 cleanup。
目标文件存在且 size 匹配才允许 cleanup。
cloud_staging_path 必须位于 staging root 子路径。
校验失败、取消、failed、只有 verified 时不 cleanup。
cleanup 失败不删除本地已完成文件。
```

停止条件：

```text
pytest 覆盖 cleanup 成功和至少 3 类拒绝 cleanup 条件。
误删保护有自动化测试。
```

### Phase 6.4: Worker Startup Recovery

状态：已完成。

目标：Worker 启动时扫描未完成运行态任务，并保守恢复或标记为可重试失败。

交付物：

```text
Worker 启动恢复扫描
pending 保持可领取
staging_to_cloud -> failed retryable=true
cloud_ready / downloading / verifying / renaming / cleaning_cloud -> failed retryable=true
恢复事件写入 transfer_logs
```

验收标准：

```text
Worker 重启不会让任务永久卡在运行态。
恢复不会误删 .downloading 或 cloud staging。
恢复策略宁可 failed retryable，也不假装 completed。
```

停止条件：

```text
pytest 覆盖主要运行态恢复规则。
恢复逻辑不依赖真实网盘或真实 NAS。
```

### Phase 6.5: Transfer Logs API

状态：已完成。

目标：提供任务日志查询能力，供 Web Console 和 AI Tool 解释任务过程与失败原因。

交付物：

```text
GET /transfers/{task_id}/logs
返回 transfer_logs 按 created_at 排序
日志不返回 password、token、cookie 等敏感信息
cancel / retry / cleanup / recovery 事件可查询
```

验收标准：

```text
前端和 AI 可查询任务关键事件。
失败任务可通过日志定位失败阶段。
日志响应字段与 API 文档一致。
```

停止条件：

```text
pytest 覆盖日志查询、任务不存在、敏感字段不返回。
API 契约、测试计划和状态机文档同步。
```

---

## Phase 7: Web Console

状态：已完成。

目标：实现 MVP 轻量控制台。

交付物：

```text
React + Vite app
app/search page
resource result list
app/transfers task page
app/storage SMB settings page
SMB connection test
SMB directory browser
app/sources source settings page
running task interruption notice for STORAGE_CONFIG_CHANGED
```

验收标准：

```text
用户可以通过 Web Console 搜索资源。
用户可以修改 SMB 配置并测试连接。
用户可以浏览 SMB 目标目录。
用户可以查看、启用、禁用和测试已安装 Source Adapter。
用户可以创建、查看、取消、重试任务。
SMB 配置变更导致任务中断时，前端有明确提示。
```

停止条件：

```text
Web Console 可启动并完成 npm run build。
搜索页、任务页、Storage 设置页、Sources 设置页具备最小可用交互。
SMB password 不回显明文。
STORAGE_CONFIG_CHANGED 有明确前端提示。
前端不包含登录、多用户、完整本地媒体库 UI。
前端构建通过；涉及后端 API 时 pytest 也必须通过。
工作区已提交或明确说明不提交原因。
```

Phase 7 按以下停止点拆分。每个停止点都必须保持 `npm run build` 通过；涉及后端 API 字段或契约调整时同时运行 pytest。

### Phase 7.1: Web Console Shell

状态：已完成。

目标：建立可扩展的 Web Console 页面框架和 API 调用基础。

交付物：

```text
基础布局和导航
页面路由或等价导航状态
统一 API client
统一 loading / error / empty state 基础组件
保留现有 Vite 构建能力
```

验收标准：

```text
用户可以在 Search / Transfers / Storage / Sources / Status 页面之间切换。
页面框架在桌面和移动端可读。
API 错误有统一展示入口。
```

停止条件：

```text
npm run build 通过。
不接入复杂全局状态库。
不实现具体业务页面深交互。
```

### Phase 7.2: Status Page

状态：已完成。

目标：提供系统状态摘要，验证前端到后端的最小闭环。

交付物：

```text
/app/status 页面
GET /health 调用
API / PostgreSQL / Redis / Worker 状态展示
基础刷新按钮
```

验收标准：

```text
状态页可显示 health 响应。
异常状态有明确提示。
不做复杂监控、图表或历史趋势。
```

停止条件：

```text
npm run build 通过。
页面不依赖真实网盘或真实 NAS。
```

### Phase 7.3: Transfers Page

状态：已完成；手动验收后发现需要补充任务列表 API 和全局浮动任务面板，纳入 Phase 7.8。

目标：提供任务查看和控制能力，优先让 Phase 6 的任务控制 API 可被前端操作。

交付物：

```text
/app/transfers 页面
任务 ID 查询或最小任务列表入口
GET /transfers/{task_id}
GET /transfers/{task_id}/logs
POST /transfers/{task_id}/cancel
POST /transfers/{task_id}/retry
进度、当前文件、错误码、retryable 展示
STORAGE_CONFIG_CHANGED / CLOUD_CLEANUP_FAILED / WORKER_RECOVERY_REQUIRED 明确提示
```

验收标准：

```text
用户可以查看任务状态和日志。
可取消允许取消的任务。
可重试 retryable failed 任务。
不可操作状态的按钮禁用或显示明确错误。
完整任务列表和全局任务面板不属于 Phase 7.3 已完成范围，纳入 Phase 7.8。
```

停止条件：

```text
npm run build 通过。
pytest 通过。
不实现真实 Provider 或真实集成测试。
```

### Phase 7.4: Storage Page

状态：已完成。

目标：提供 SMB 配置管理、连接测试和目录浏览。

交付物：

```text
/app/storage 页面
GET /storage/smb-connections
POST /storage/smb-connections/create
POST /storage/smb-connections/{id}/update
POST /storage/smb-connections/{id}/test
GET /storage/smb-connections/{id}/browse
password 不回显明文
password 留空保留旧值
多个 SMB 连接列表和目录浏览
```

验收标准：

```text
用户可以查看多个 SMB 连接摘要。
用户可以创建、更新、启停并测试连接。
用户可以浏览允许范围内的目录。
保存配置导致任务中断时有 STORAGE_CONFIG_CHANGED 提示。
```

停止条件：

```text
npm run build 通过。
pytest 通过。
不实现完整 NAS 文件管理器。
不提供任意文件删除能力。
```

### Phase 7.5: Search Page

状态：已更新；搜索页已改为聚合搜索结果展示，不再直接创建 Transfer。

目标：提供关键词搜索、结果类型过滤、候选资源查看和链接操作入口。

交付物：

```text
/app/search 页面
GET /search
候选资源列表
结果类型过滤：磁力 / 夸克网盘 / 阿里网盘 / 百度网盘 / 迅雷网盘
链接有效性检测结果
打开链接
保存到网盘入口
复制链接
```

验收标准：

```text
用户可以搜索资源。
用户可以按结果类型过滤。
搜索结果按真实链接去重。
用户可以打开链接、复制链接或点击保存到网盘入口。
Phase 7.5 当前验收范围覆盖搜索页面、代码型源注册表和搜索管线。
```

停止条件：

```text
npm run build 通过。
pytest 通过。
不接入真实供应商开发。
不做完整本地媒体库 UI。
```

### Phase 7.6: Sources Page

状态：已更新；Sources 页面改为搜索源列表和详情弹窗测试入口。

目标：展示已安装搜索源，并提供详情弹窗、测试搜索和步骤日志入口。

交付物：

```text
/app/sources 页面
GET /sources
GET /sources/{source_id}
POST /sources/{source_id}/test
搜索源列表展示
```

验收标准：

```text
用户可以查看和测试已安装搜索源。
Source Adapter 不允许在线编辑。
source 测试失败有明确提示。
通过 Web Console 创建/编辑/启用/禁用 source、配置复杂网站爬虫和在配置中保存可执行 Python 代码不属于当前阶段。
```

停止条件：

```text
npm run build 通过。
pytest 通过。
不上传或执行用户代码。
```

### Phase 7.7: Web Console Polish And Closure

状态：已完成。

目标：收口 Web Console 的一致性、可用性和 MVP 边界。

交付物：

```text
统一错误提示文案
统一空状态和 loading 状态
移动端可读性检查
关键操作二次确认
README / 本地开发文档同步
```

验收标准：

```text
Search / Transfers / Storage / Sources / Status 页面均具备最小可用交互。
前端不包含登录、多用户、完整本地媒体库 UI。
用户不需要接触 SMB password 明文。
```

停止条件：

```text
npm run build 通过。
涉及 API 的 pytest 通过。
Phase 7 文档状态更新为已完成。
工作区已提交或明确说明不提交原因。
```

### Phase 7.8: Web Console UI Polish

状态：已完成。

目标：根据 Phase 0-7 手动验收反馈，修复 Web Console 布局和任务展示体验问题。

交付物：

```text
GET /transfers 任务列表 API
全局右侧浮动任务面板
/app/transfers 完整任务列表和任务详情保留
桌面端布局对齐修复
移动端响应式布局
亮色模式
暗色模式
跟随系统
主题偏好本地持久化
字体、间距、按钮和输入框视觉统一
```

验收标准：

```text
用户可以在任意页面查看当前任务状态摘要。
用户可以进入 /app/transfers 查看完整任务列表、详情和日志。
输入框和按钮对齐一致。
移动端可读、可操作，不出现主要内容遮挡。
主题支持亮色、暗色和跟随系统。
主题切换后刷新页面仍保留偏好。
```

停止条件：

```text
npm run build 通过。
涉及 API 时 pytest 通过。
不引入登录、多用户或完整本地媒体库 UI。
不实现真实媒体源爬虫。
不启动 Phase 8 下载到本地实现。
```

---

## Phase 8: Download To Local（历史命名）

目标：实现“远程媒体库同步到本地媒体库”的基础能力，从已挂载的网盘 SMB 目录读取文件并写入本地 SMB 媒体库目录。

背景：国内封闭网盘直接下载不包含在 MVP 中。当前阶段依赖用户手动保存资源到网盘，由 NAS 或挂载服务负责将网盘远程挂载为目录并通过 SMB 暴露。Phase 8 的“下载到本地”是历史阶段命名，当前规范统一为“远程媒体库同步到本地媒体库”。

### Phase 8.1: SMB 连接和媒体库管理

交付物：

```text
多个 SMB 连接管理（CRUD、test、browse）                     已实现
媒体库管理（CRUD、test，绑定到 SMB 连接下的本地目录）         已实现
download_to_local 全局配置                                   已实现
数据模型：smb_connections、media_libraries                    已实现
迁移：0004_smb_connections_media_libs                         已实现
```

验收标准：

```text
可以配置多个 SMB 连接。
可以创建 movie / series / unclassified 等媒体库，并绑定到 SMB 本地目录。
媒体库只能选择已配置 SMB 连接和目录，不重复填写 SMB 凭据。
SMB 连接密码不回显。
```

### Phase 8.2: 同步绑定和扫描

交付物：

```text
远程媒体库到本地媒体库的同步 binding                           已实现
SMB source scanner，来源只能选择已配置 SMB 连接                已实现
稳定文件/目录判断                                              已实现
sync task 创建                                                已实现
数据模型：sync_bindings、sync_seen_files                        已实现
迁移：0005_download_to_local_bindings                          已实现
```

验收标准：

```text
同步绑定只能选择远程媒体库（来源）和本地媒体库（目标）。
可以扫描 SMB 来源目录。
文件或目录稳定后才开始下载。
重复扫描不重复创建任务。
```

### Phase 8.3: Worker 下载执行

交付物：

```text
SMB source -> SMB target 下载 Worker                              已实现
.downloading 写入、size 校验、rename                               已实现
成功后删除源文件和空目录                                            已实现
未分类 fallback                                                   已实现
```

### Phase 8.4: Web Console 前端

交付物：

```text
Web Console 历史 /app/download-to-local 页面能力                  已合并到 /app/remote-libraries
Web Console /app/libraries 页面或等价媒体库管理入口                 已实现
Web Console /app/remote-libraries 页面                            已实现
```

验收标准：

```text
可以通过 SMB 将文件写入本地媒体库。
同步成功后按配置删除源文件和空目录。
失败时保留源文件、.downloading 和任务日志。
路径绑定不明确时进入 unclassified 本地媒体库。
剧集目录按原目录结构下载，不额外拆分季集。
```

### Phase 8 整体验收标准

```text
默认自动化测试不依赖真实网盘或真实 SMB。
真实挂载目录同步到本地媒体库通过手动集成验收。
docs/15-download-to-local-spec.md 与实际 API / 数据模型一致。
pytest 通过。
涉及前端时 npm run build 通过。
不实现 Sundarr 内挂载网盘。
不实现国内封闭网盘直接下载。
媒体库管理作为 Phase 8 的目录绑定管理能力，不实现完整本地媒体库 UI。
```

验收标准：

```text
可以创建 movie / series / unclassified 等媒体库，并绑定到 SMB 本地目录。
可以配置多个 SMB 连接。
媒体库只能选择已配置 SMB 连接和目录，不重复填写 SMB 凭据。
同步绑定只能选择远程媒体库（来源）和本地媒体库（目标）。
可以配置网盘挂载来源目录为远程媒体库，并绑定到本地媒体库。
路径绑定不明确时进入 unclassified 本地媒体库。
剧集目录按原目录结构下载，不额外拆分季集。
文件或目录稳定后才开始下载。
同步成功后按配置删除源文件和空目录。
失败时保留源文件、.downloading 和任务日志。
默认自动化测试不依赖真实网盘或真实 SMB。
真实挂载目录同步到本地媒体库通过手动集成验收。
```

停止条件：

```text
docs/15-download-to-local-spec.md 与实际 API / 数据模型一致。
pytest 通过。
本阶段新增 API 或 Worker 入口完成最小冒烟测试。
涉及前端时 npm run build 通过。
不实现 Sundarr 内挂载网盘。
不实现 Sundarr 内保存分享链接到网盘。
保存分享链接到网盘的后续模块命名为“保存到网盘”。
不实现国内封闭网盘直接下载。
媒体库管理作为 Phase 8 的目录绑定管理能力，不实现完整本地媒体库 UI。
工作区已提交或明确说明不提交原因。
```

---

## Phase 9: 模块重构

目标：清理旧模块，统一术语，建立远程媒体库模型，重构同步绑定。将系统统一为"远程媒体库同步到本地媒体库"。

背景：Phase 8 完成后，系统存在历史 Ingest / Download To Local 命名和实现残留，以及旧 storage.smb 和新 smb_connections 两套配置系统。需要统一清理。

交付物：

```text
删除历史 Ingest / Download To Local 残留（model/service/api/Worker/Web Console）
删除旧 storage_config_service（settings.storage.smb）
新增远程媒体库模型（RemoteMediaLibrary）
重构同步绑定（SyncBinding 引用 remote_library_id -> local_library_id）
确认 TransferTask.sync_seen_file_id 为唯一 seen file 字段
TransferTask 增加 binding_id 字段
统一 Worker 处理路径（收口 process_dtl_task 为 process_sync_task）
更新 Web Console（远程媒体库和同步操作统一收口到 /app/remote-libraries）
```

验收标准：

```text
系统中不再有 Ingest / Download To Local 历史主链路代码和 API。
系统中不再有 storage.smb 相关代码和 API。
远程媒体库可通过 API 管理。
同步绑定引用远程媒体库和本地媒体库。
Worker 只有一条同步处理路径。
pytest 通过。
npm run build 通过。
```

停止条件：

```text
所有旧模块代码已删除。
新模块 API 和 Worker 入口完成最小冒烟测试。
不实现真实网盘 Provider。
不实现完整本地媒体库 UI。
```

---

## Phase 10: Real Site Source Adapters

目标：实现真实媒体网站即时搜索能力。每个真实网站通过 Source Adapter 接入，多个 Adapter 并发搜索，结果统一进入 Search Pipeline。搜索源统一由 Adapter 代码定义并同步到 `sources` 目录表，不再支持用户通过 Web Console 创建 configurable / document source。真实搜索源代码优先通过外部 Git 搜索源仓库接入，Sundarr Core 只保存仓库地址、分支和锁定 commit。

交付物：

```text
Source Adapter SDK 完整化
代码型 Adapter 插件加载机制
外部 Git 搜索源仓库配置
SourceManifest / LoadedSource / SourceModel 分层
PluginContext / PluginActivation 生命周期
requires / provides 显式能力依赖
候选加载、健康检查、原子切换和可逆清理
仓库 clone / fetch / checkout / rollback
current_commit 锁定和更新检查
统一 HTTP client
站点级 timeout / rate limit
失败隔离和错误码
日志脱敏
HTML / JSON / 文本解析辅助工具
通用网盘链接和提取码提取复用
fixture 测试模板
至少 1 个真实网站 Adapter
首个 Adapter：`SeedHubSource`
搜索页简化为关键词 + 结果类型过滤
按真实链接去重
搜索返回前同步检测链接有效性
Web Console 已安装 Adapter 管理
Web Console 搜索源仓库检查更新、应用更新、回滚和加载诊断
```

运行时边界：

```text
Core 保持 Python + FastAPI，不依赖 Cordis 包或 Node.js 插件宿主。
只借鉴 Cordis 的显式依赖、Activation 和副作用回收语义。
PluginActivation 只管理进程内插件资源，不替代 PostgreSQL、Redis、Worker 或 SMB 状态。
SOURCE 是当前唯一必须端到端完成的插件类型；Cloud Provider、通知和爬虫不是近期主线。
```

验收标准：

```text
至少 1 个真实网站 Adapter 可以即时搜索，当前首个实现参考 seedhub-cli 的列表页 + 详情页抽取方式。
至少 1 个外部 Git 搜索源仓库可以被配置、拉取、锁定 commit 并加载。
Adapter 可以解析搜索结果和必要的详情页。
搜索结果能进入现有 Search Pipeline。
单个 Adapter 失败不会影响其他 Adapter。
每个 Adapter 有超时、限流、错误记录和测试 fixture。
Web Console 可以查看、测试 Adapter 并查看最后错误。
Web Console 可以查看外部仓库 current_commit、加载成功列表和加载失败原因。
应用重启后会从数据库读取已启用仓库，只加载锁定 current_commit，并在加载后同步 sources 目录表。
插件更新失败时旧 Activation 继续提供服务；禁用、回滚和删除会释放已注册能力。
```

停止条件：

```text
pytest 通过。
涉及前端时 npm run build 通过。
不在数据库或 Web Console 中保存可执行 Python 代码。
不在启动时无条件执行远程最新 commit。
外部搜索源加载失败不影响 API 启动。
不实现 Web Console 配置复杂爬虫。
不要求用户维护本地文档/表格作为主要媒体源。
不承诺通用在线文档读取。
```

### Phase 10.0: Quality Baseline Closure

状态：已完成。

交付物：

```text
把 tests/test_search_api.py 移出默认 pytest 收集或改为隔离测试。
为异步 SMB 连接池测试配置正确执行方式。
保留 SmbStorageError 具体错误码，不降级为 SMB_TEST_FAILED。
修复并提交插件迁移的 down_revision 链。
Windows PID 文件指向真实 API / Web / Worker 服务进程。
统一 README、路线图、插件规格和历史汇总文档状态。
```

停止条件：

```text
原始 python -m pytest 全部通过，不使用 --ignore。
npm run build 通过。
alembic heads/current/upgrade head 通过。
sundarr start -> health -> stop 连续执行两次通过，端口和 PID 文件无残留。
```

### Phase 10.1: Media Discovery Center

状态：当前优先，处于逐项设计阶段，尚未实现。

范围：

```text
带筛选条件的媒体搜索
热门资源和分类资源
发现型海报墙
媒体详情
关注列表入口
从媒体条目继续查找候选资源
```

边界：

```text
不做本地媒体库海报墙。
不做播放器和观影进度。
不做完整本地媒体管理。
媒体身份已经确认使用内部 UUID + 多外部 ID；TMDb 是 MVP 主目录，豆瓣想看是可选独立接入；持久化、缓存和任务关联仍需逐项确认。
```

### Phase 10.2: Python Plugin Activation Runtime Completion

状态：生命周期内核首个单元已完成；因媒体发现中心进入当前 MVP，剩余工作暂停，Phase 10.1 最小闭环后恢复。

当前进度：生命周期内核首个单元已完成，已实现 `PluginContext`、`PluginActivation`、`ActivationStatus`、能力依赖检查、只读配置、能力提供、同步/异步 cleanup、LIFO 清理、失败续跑和并发幂等释放。候选健康检查、注册中心原子切换、manifest `requires/provides` 和启动自动激活仍待实现。

交付物：

```text
PluginContext：向插件暴露受控日志、HTTP、配置等能力。
PluginActivation：记录插件实例、状态、commit 和 LIFO cleanup callbacks。
requires / provides：显式声明能力依赖和提供能力。
候选 Activation 通过校验和健康测试后原子替换旧 Activation。
加载、禁用、更新、回滚、仓库删除均有确定的清理语义。
启动时只加载数据库中已启用仓库的 current_commit。
```

### Phase 10.3: External Source End-to-End

状态：Phase 10.2 后执行。

交付物：

```text
sundarr-sources 仓库配置和锁定 commit。
SeedHub 外部 Source Adapter fixture、测试和手动实时验收。
Web Console 仓库新增、检查更新、应用更新、回滚、测试和诊断。
重启恢复搜索源和 sources 目录同步。
```

### Phase 10.x: Document Site Generalization Experiment

状态：后续实验，不作为 Phase 10 主线阻塞项。

目标：验证文档型网站是否存在可通用读取模式。

实验内容：

```text
选择少量文档型网站或在线文档平台样例。
验证是否能稳定读取标题、正文、链接和提取码。
判断是否能抽象为专用 Adapter 模板。
判断哪些平台必须使用专用 connector 或代码型 Adapter。
```

不做：

```text
不要求用户维护本地 CSV / Markdown / plain text。
不承诺通用在线文档读取。
不处理所有在线文档平台的登录、权限和导出格式。
```

---

## Phase 11: AI Friendly API

目标：为 AI / Agent 调用提供稳定工具式接口。

交付物：

```text
stable tool-like endpoints
candidate explanation fields
default target library mapping
low confidence confirmation fields
可选 Cordis / DeepSeek Harness HTTP 桥接插件
```

验收标准：

```text
AI 可以调用 Sundarr API 搜索媒体。
AI 可以获取资源详情。
AI 可以创建 transfer task。
AI 可以查询任务状态。
AI 不需要直接抓网页或操作 NAS。
Cordis / DeepSeek Harness 桥接插件只调用公开 Sundarr API，不访问数据库、SMB 或 Worker 内部对象。
```

停止条件：

```text
AI Tool API 文档和实际 API 字段一致。
search_media / get_resource / create_transfer / get_transfer_status 等工具式接口可被调用或有明确映射。
低置信度候选和目标路径会返回 user_action_required 或等价字段。
AI 不需要接触网页抓取、SMB 凭据或 NAS 文件操作。
pytest 通过。
工作区已提交或明确说明不提交原因。
```

## Phase 12: Cloud Direct Download（后续高级功能，非 MVP）

目标：作为 MVP 之后的高级功能，实现网盘直链下载能力，跳过"保存到网盘 + SMB 挂载"步骤，直接从网盘 CDN 下载文件到本地。

背景：参考 LinkSwift 项目原理，通过调用网盘公开 API 获取文件直链（CDN 地址），结合 aria2 多线程下载，实现更快、更直接的下载体验。详细规范见 `docs/18-cloud-direct-download-spec.md`。

范围说明：本阶段不包含在 MVP 中，不阻塞 Phase 9 模块重构、Phase 10 真实媒体源和 Phase 11 AI Friendly API。

交付物：

```text
aria2 Docker 服务集成
Aria2Client RPC 客户端
CloudAuth 抽象接口 + 夸克实现
DirectLinkExtractor 抽象接口 + 夸克实现
cloud_accounts 数据模型（加密存储 Cookie/Token）
direct_download_tasks 数据模型
网盘账号管理 API（扫码登录、Cookie 验证）
直链提取 API
直链下载任务 API（创建、查询、取消、重试）
任务编排：认证 → 直链提取 → aria2 下载 → 校验 → 归档
Web Console 网盘账号管理页面
Web Console 直链下载任务页面
```

验收标准：

```text
aria2 Docker 服务可通过 docker compose 启动。
可通过 RPC 提交下载任务并获取进度。
夸克网盘扫码登录流程可跑通。
Cookie 加密存储，不以明文返回。
给定有效分享链接 + 有效 Cookie，可提取直链。
直链下载任务可端到端完成：分享链接 → 直链 → 下载 → 本地文件。
下载进度可追踪。
文件大小校验失败时任务标记为 failed。
失败任务可重试。
Web Console 可管理网盘账号和下载任务。
pytest 通过。
```

停止条件：

```text
docs/18-cloud-direct-download-spec.md 与实际 API / 数据模型一致。
aria2 Docker 服务独立启动和 RPC 连接测试通过。
夸克网盘扫码登录 + 直链提取 + 下载完整流程手动验收通过。
Cookie/Token 加密存储有测试覆盖。
任务状态机（pending -> extracting -> downloading -> verifying -> completed）有测试覆盖。
pytest 通过。
涉及前端时 npm run build 通过。
不实现网盘限速破解、绕过会员限制或验证码。
不实现 BT/磁力下载。
工作区已提交或明确说明不提交原因。
```

### Phase 12.1: Aria2 服务集成

状态：未开始。

目标：aria2 作为 Docker 服务接入 Sundarr，可通过 RPC 下载文件。

交付物：

```text
docker-compose.yml 增加 aria2 服务
Aria2Client RPC 客户端
aria2 连接测试 API
aria2 状态查询 API
aria2 配置（RPC 地址、密钥）存入 settings
```

验收标准：

```text
docker compose up -d aria2 可启动 aria2 服务。
POST /api/v1/aria2/test 返回连接成功。
可通过 RPC 提交一个 HTTP 下载任务。
下载文件存入 /downloads 目录。
GET /api/v1/aria2/status 返回 aria2 全局状态。
```

停止条件：

```text
aria2 Docker 服务可独立启动。
Aria2Client 可完成 add_uri + get_status 基础流程。
pytest 通过。
docker-compose.yml 变更不影响现有服务。
```

### Phase 12.2: 夸克网盘认证

状态：未开始。

目标：实现夸克网盘扫码登录和 Cookie 管理。

交付物：

```text
CloudAuth 抽象接口
QuarkAuth 实现
扫码登录 API（获取二维码）
扫码状态轮询 API
Cookie 加密存储
Cookie 有效性验证
cloud_accounts 数据模型和迁移
Web Console 网盘账号管理页面
```

验收标准：

```text
POST /api/v1/cloud-accounts/qr-login 返回二维码图片 URL 或 base64。
用户手机扫码后，轮询 GET /api/v1/cloud-accounts/qr-status 返回成功。
Cookie 自动加密存储到 cloud_accounts 表。
POST /api/v1/cloud-accounts/{id}/validate 可验证 Cookie 有效性。
过期 Cookie 标记为 expired。
Web Console 可查看已添加账号列表。
Web Console 可删除账号。
Cookie 不以明文存储或返回。
```

停止条件：

```text
扫码登录完整流程可跑通。
Cookie 加密存储有测试覆盖。
pytest 通过。
Web Console 构建通过。
```

### Phase 12.3: 夸克直链提取

状态：未开始。

目标：通过分享链接 + Cookie 获取夸克网盘文件直链。

交付物：

```text
DirectLinkExtractor 抽象接口
QuarkExtractor 实现
分享链接解析
share_token 获取
文件元数据获取
直链（download_url）提取
请求头构造（UA、Referer）
直链提取 API
```

验收标准：

```text
给定有效分享链接 + 有效 Cookie，可返回直链 URL。
返回信息包含：直链 URL、文件名、文件大小、请求头。
提取失败时返回明确错误码。
单文件和多文件分享链接均能处理。
提取码分享链接能正确传入提取码。
```

停止条件：

```text
单文件分享链接可成功提取直链。
多文件分享链接可列出文件并逐个提取。
pytest 覆盖成功和失败路径。
不依赖 aria2（纯提取，不含下载）。
```

### Phase 12.4: 直链下载完整流程

状态：未开始。

目标：串联认证 → 直链提取 → aria2 下载 → 文件归档。

交付物：

```text
direct_download_tasks 数据模型和迁移
下载任务编排逻辑
aria2 下载进度轮询
下载完成回调或轮询
文件大小校验
rename 到目标路径
任务状态机：pending -> extracting -> downloading -> verifying -> completed
失败处理和错误码
重试机制
Web Console 直链下载任务页面
```

验收标准：

```text
POST /api/v1/direct-downloads 可创建下载任务。
任务自动完成：提取直链 → aria2 下载 → 校验 → rename。
GET /api/v1/direct-downloads/{id} 可查询进度和状态。
下载完成后文件存在于目标路径。
文件大小校验失败时任务标记为 failed。
失败任务可重试。
Web Console 可查看任务列表和详情。
```

停止条件：

```text
端到端流程：分享链接 → 直链 → 下载 → 本地文件，可跑通。
进度可追踪。
pytest 通过。
Web Console 构建通过。
```

---

## 阶段完成规则

每个 Phase 完成前必须：

```text
更新相关文档
运行该阶段可用测试
检查 git status
说明完成内容和未完成内容
```

不得因为后续阶段需求，提前引入大范围无关实现。

如果一个 Phase 较大，可以按“阶段内可拆分停止点”暂停。暂停前必须满足：

```text
当前停止点有独立测试。
当前停止点没有已知失败测试。
文档已说明未完成的后续停止点。
Git 工作区已提交或明确说明不提交原因。
```
