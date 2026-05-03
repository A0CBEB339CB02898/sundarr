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
```

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

---

## Phase 5: Transfer Worker

目标：实现搬运任务执行主链路。

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
```

验收标准：

```text
可以创建 transfer task。
Worker 可以从 cloud stream 写入 StorageWriter。
任务进度可查询。
文件大小校验成功后 rename。
失败时记录 error_code、error_message、retryable。
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
