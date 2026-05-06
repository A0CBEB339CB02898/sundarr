# MVP 开发路线

本文档定义 Sundarr MVP 的开发阶段、交付物和验收标准。

---

## 总体原则

MVP 的目标是先跑通端到端闭环：

```text
搜索资源
-> 提取网盘链接
-> 转存到 cloud staging
-> 通过 SmbWriter 下载到 NAS
-> 校验
-> rename
-> 清理 cloud staging
-> 返回任务状态
```

开发原则：

```text
先后端闭环，后前端完善。
先 Mock/Local Provider，后真实网盘 Provider。
先规则和用户确认，后模型辅助。
先核心控制台，后完整媒体库 UI。
每个阶段必须可测试。
每个阶段都必须有明确停止条件。
```

停止条件用于判断“做到这里可以暂停、提交、切换任务或等待用户验收”。满足停止条件不代表该阶段所有增强项都完成，只代表当前交付单元已经闭合，不会留下不可验证的半成品。

---

## 当前实现状态

截至 2026-05-06，本项目阶段状态如下：

```text
Phase 0 Project Skeleton: 已完成。
Phase 1 Persistence Models: 已完成。
Phase 2 Search And Resource Library: 已完成。
Phase 3 Cloud Staging: 已完成。
Phase 4 Storage Writer: 已收口，已完成 LocalWriter、Storage 配置 API、目录浏览 API、STORAGE_CONFIG_CHANGED 中断规则、SmbWriter 安全边界和真实 SMB 连接、目录浏览、写入、size、rename 手动验收。
启动与配置精简：已确认 sundarr start/restart 管理 API + Web，自动执行数据库初始化/迁移、默认 settings seed 和前端依赖安装；Phase 5 实现 Worker 时必须同步纳入完整项目启停。
Phase 5 Transfer Worker: 进行中，Phase 5.1 Worker Skeleton、Phase 5.2 Task Claiming、Phase 5.3 Local Transfer Happy Path 和 Phase 5.4 Failure Handling 已完成；已提前实现 POST /transfers 和 GET /transfers/{id} 入口，真实网盘和 SMB 搬运主链路尚未实现。
Phase 6 Cleanup And Recovery: 未开始。
Phase 7 Web Console: 未开始。
Phase 8 AI Friendly API: 未开始。
```

Phase 4 已满足停止条件，后续可以正式进入 Phase 5。Phase 5 实现 Worker 时，必须同步将 Worker 纳入 `sundarr start / restart / stop / status`。

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

目标：实现多源搜索框架和资源库入库。

交付物：

```text
BaseSource
SearchQuery
RawSearchItem
one example source
parser pipeline
cloud link extractor
normalizer
deduper
ranker
GET /search
GET /resources/{id}
```

验收标准：

```text
一个 source 失败不影响整体搜索。
RawSearchItem 输出格式统一。
可以从文本中提取至少一种 provider 链接。
搜索结果可以入库。
重复资源可基础合并。
```

停止条件：

```text
BaseSource / SearchQuery / RawSearchItem 已落地。
至少一个示例 source 可通过 /search 返回候选结果。
Cloud Link Extractor 至少支持一个 provider 的链接和提取码识别。
搜索结果可持久化到 resources / resource_links。
/resources/{id} 可从数据库读取资源详情。
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

状态：未开始。

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

---

## Phase 7: Web Console

目标：实现 MVP 轻量控制台。

交付物：

```text
React + Vite app
search page
resource result list
transfer task page
SMB settings page
SMB connection test
SMB directory browser
source settings page
running task interruption notice for STORAGE_CONFIG_CHANGED
```

验收标准：

```text
用户可以通过 Web Console 搜索资源。
用户可以修改 SMB 配置并测试连接。
用户可以浏览 SMB 目标目录。
用户可以管理配置型源和文档/表格型源。
用户可以创建、查看、取消、重试任务。
SMB 配置变更导致任务中断时，前端有明确提示。
```

停止条件：

```text
Web Console 可启动并完成 npm run build。
搜索页、任务页、Storage 设置页、Sources 设置页具备最小可用交互。
SMB password 不回显明文。
STORAGE_CONFIG_CHANGED 有明确前端提示。
前端不包含登录、多用户、完整媒体库 UI。
前端构建通过；涉及后端 API 时 pytest 也必须通过。
工作区已提交或明确说明不提交原因。
```

---

## Phase 8: AI Friendly API

目标：为 AI / Agent 调用提供稳定工具式接口。

交付物：

```text
stable tool-like endpoints
candidate explanation fields
default target library mapping
low confidence confirmation fields
```

验收标准：

```text
AI 可以调用 Sundarr API 搜索媒体。
AI 可以获取资源详情。
AI 可以创建 transfer task。
AI 可以查询任务状态。
AI 不需要直接抓网页或操作 NAS。
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
