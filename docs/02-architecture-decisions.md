# 架构决策

本文档记录 Sundarr 已确认的关键技术决策和理由。

---

## ADR-001: 使用 Python 作为主后端语言

状态：已确认。

决策：

```text
Sundarr MVP 使用 Python 作为主后端语言。
```

理由：

```text
网页解析生态成熟。
文本处理、标题归一化、链接提取更方便。
AI/模型接入生态更好。
适合快速构建自动化后端系统。
```

不选 Node.js 作为主后端的原因：

```text
Sundarr 第一阶段核心风险在搜索、解析、任务编排和文件流式处理，不是重前端。
Node.js 可用于前端工程，但不作为 MVP 主后端。
```

---

## ADR-002: 使用 FastAPI 作为 API 后端

状态：已确认。

决策：

```text
FastAPI 只作为 API Backend。
FastAPI 不负责 Jinja2 页面渲染。
FastAPI /docs 保留为开发调试入口。
```

理由：

```text
FastAPI 的 OpenAPI 支持清晰，适合 Agent 和前端调用。
Pydantic schema 适合定义稳定 API 契约。
异步 I/O 适合搜索聚合、网盘流式读取和任务状态查询。
后续可封装为 media search tool / AI tool API。
```

---

## ADR-003: 使用 React + Vite 作为 Web Console

状态：已确认。

决策：

```text
MVP 包含轻量 React + Vite Web Console。
```

理由：

```text
用户希望后续有完整前端。
React + Vite 更适合后续扩展和维护。
相比 Jinja2 / HTMX，React + Vite 更适合配置表单、任务状态、目录浏览等复杂交互。
MVP 只做核心控制台，不做完整媒体库 UI。
```

不选 Jinja2 / HTMX 的原因：

```text
Jinja2 / HTMX 适合快速个人后台，但后续演进完整前端时可能重做成本较高。
当前已确认希望保留完整前端演进空间。
```

---

## ADR-004: 使用 PostgreSQL 作为主数据库

状态：已确认。

决策：

```text
MVP 使用 PostgreSQL。
```

理由：

```text
JSONB 适合 source config、provider metadata、settings、task logs 等半结构化数据。
事务和约束适合任务状态持久化。
pg_trgm、full-text search、GIN index 适合后续资源搜索和相似匹配。
Python + SQLAlchemy + PostgreSQL 生态成熟。
```

不选 MySQL 的原因：

```text
MySQL 能实现 MVP，但 PostgreSQL 更适合 Sundarr 的半结构化数据和后续搜索扩展。
```

---

## ADR-005: 使用 Redis 做缓存和实时进度辅助

状态：已确认。

决策：

```text
MVP 使用 Redis。
```

用途：

```text
搜索缓存
链接有效性缓存
实时进度加速
短期失败源熔断
```

约束：

```text
Redis 不是任务状态事实来源。
transfer_tasks 和 transfer_files 状态必须持久化到 PostgreSQL。
```

---

## ADR-005.1: 使用 Docker Compose 交付基础依赖

状态：已确认。

决策：

```text
成熟部署形态使用完整 Docker Compose。
Compose 包含 Sundarr API、Worker、Web、PostgreSQL、Redis 和数据库迁移步骤。
PostgreSQL 和 Redis 不打入 Sundarr 应用镜像，而是作为独立服务运行。
首次启动时必须自动执行 Alembic 数据库迁移。
```

理由：

```text
用户不希望在本机直接安装 PostgreSQL 和 Redis。
Docker Compose 更容易在 Linux 机器、NAS 或小主机上部署和复现。
应用镜像保持无状态，数据库和缓存数据通过 volume 持久化。
数据库初始化由 Compose 编排，减少手动执行迁移导致的遗漏。
```

约束：

```text
开发测试可以使用远程 Linux Docker 机器承载 PostgreSQL 和 Redis。
默认自动化测试仍不依赖真实 PostgreSQL / Redis。
真实部署时数据库密码和 Redis 密码通过环境变量或 secret 注入，不写入镜像。
```

---

## ADR-006: 不实现 MVP 权限系统

状态：已确认。

决策：

```text
Sundarr MVP 按个人自用项目处理，不实现登录、注册、多用户、权限系统。
```

理由：

```text
当前目标是跑通个人自动化归档闭环。
权限系统会显著增加复杂度，但不直接服务 MVP 核心流程。
```

仍保留：

```text
路径保护
删除保护
凭据不进日志
默认不覆盖正式文件
```

---

## ADR-007: 使用应用内 SmbWriter，不依赖系统 mount

状态：已确认。

决策：

```text
MVP 通过应用内 SmbWriter 直接写入 NAS SMB share。
不要求宿主机提前 mount SMB。
```

理由：

```text
用户不希望依赖系统挂载。
Docker / Windows / Linux 部署体验更一致。
Sundarr 可以自己控制写入、进度、rename、错误和热加载。
```

配套决策：

```text
LocalWriter 仅用于开发和测试。
SMB 配置保存到数据库 settings 表或等价运行时配置存储。
SMB 配置可从 Web Console 修改并热加载。
SmbWriter 使用 smbprotocol 包提供的 smbclient 高层接口实现真实 SMB 访问。
```

不选系统 mount 的原因：

```text
部署环境可能是 Windows、Linux、Docker 或 NAS。
系统 mount 会把权限、路径和错误处理外包给宿主机，难以统一实现任务状态、进度、rename 和失败恢复。
```

不选 rclone / OpenList 作为 MVP 核心写入层的原因：

```text
MVP 已确认不把 rclone / OpenList 作为核心搬运层。
Sundarr 需要应用内控制 .downloading、size、rename 和 STORAGE_CONFIG_CHANGED 中断语义。
```

---

## ADR-008: SMB 配置变更中断运行中任务

状态：已确认。

决策：

```text
修改 SMB 配置会中断使用旧 SMB 配置的运行中任务。
```

中断规则：

```text
task.status = failed
error_code = STORAGE_CONFIG_CHANGED
retryable = true
保留 .downloading 文件
保留 cloud staging
新任务和重试任务使用最新 SMB 配置
```

理由：

```text
用户希望 SMB 修改后立即生效。
运行中任务继续使用旧配置会造成行为不直观。
直接中断并允许重试更明确。
```

---

## ADR-009: 先使用 Mock/Local Provider 跑通闭环

状态：已确认。

决策：

```text
MVP 先实现 Mock/Local Provider，用于自动化测试和闭环验证。
真实网盘 Provider 后续接入。
```

理由：

```text
不依赖真实网盘账号即可测试。
避免 provider API 不稳定阻塞架构开发。
便于验证状态机、下载、校验、清理和重试逻辑。
```

---

## ADR-010: 多源搜索必须统一适配框架

状态：已确认。

决策：

```text
聚合搜索必须使用 Source Adapter 框架。
每个 source 输出统一 RawSearchItem。
```

支持源类型：

```text
配置型源
代码型源
文档/表格型源
```

规则：

```text
单个源失败不能影响整体搜索。
聚合后统一解析、提取、标准化、去重、排序。
Web Console 只管理配置型源和文档/表格型源。
代码型 Source Adapter 不允许前端在线编辑。
```

---

## ADR-011: FastAPI 后续作为 AI Tool API

状态：已确认。

决策：

```text
FastAPI 后续可封装为 media search tool / AI tool API。
```

规则：

```text
AI 不直接抓网页。
AI 不直接操作 NAS。
AI 只调用 Sundarr API。
Sundarr API 负责搜索、候选解释、创建任务和查询状态。
```
