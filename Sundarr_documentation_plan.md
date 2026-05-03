# Sundarr 待编写文档清单

> 用途：本文件用于规划后续需要拆分和编写的项目文档。当前只定义文档列表、优先级、目的和主要内容，不展开完整正文。待审核确认后，再逐份编写。

---

## 1. 已对齐结论

### 1.1 项目目标

Sundarr 是一个个人自用的网盘媒体资源自动化归档系统。

核心目标：

```text
搜索合法资源
-> 提取网盘链接
-> 转存到个人网盘临时目录
-> 下载到 NAS
-> 校验文件
-> 清理云端临时目录
```

### 1.2 当前产品定位

```text
个人自用
API 优先
MVP 包含轻量 Web Console
无多用户权限 MVP
不依赖系统 SMB 挂载
内置 SMB Writer 写入 NAS
```

### 1.3 技术方向

当前推荐技术栈：

```text
Python
FastAPI
React
Vite
PostgreSQL
Redis
Worker
SMB client library
Mock/Local Provider for testing
```

选择理由：

```text
Python 更适合网页解析、文本处理、AI/模型接入和快速构建后端自动化系统。
FastAPI 作为 API 后端，适合提供清晰的 REST API、OpenAPI 文档，并可在后续封装为 media search tool 供 AI 调用。
React + Vite 适合作为后续完整前端的基础，同时 MVP 只实现轻量 Web Console。
PostgreSQL 更适合 JSONB、任务状态、资源索引和后续模糊搜索扩展。
Redis 用于缓存、搜索加速和实时进度辅助，不作为任务状态事实来源。
```

### 1.4 搜索框架方向

聚合搜索必须做成多源可扩展框架。

核心要求：

```text
统一 Source Adapter 接口
统一 SearchQuery 输入
统一 RawSearchItem 输出
支持配置型源
支持代码型源
支持文档/表格型源
单个源失败不影响整体搜索
聚合后统一解析、提取、标准化、去重、排序
```

### 1.5 存储目标判断

MVP 不依赖模型判断资源类型和存储目录。

推荐顺序：

```text
规则优先
用户确认
后续再接模型辅助
```

模型可在后续用于：

```text
资源类型推断
目录推荐
候选资源解释
低置信度时辅助判断
```

### 1.6 安全范围

MVP 按个人项目处理，暂时忽略权限系统。

暂不做：

```text
用户注册
用户登录
多用户权限
角色管理
OAuth
API token 管理
审计日志
复杂密钥系统
```

仍保留最低误操作保护：

```text
不能删除 cloud staging 根目录之外的路径
不能写入 SMB 允许根目录之外的路径
cookie/token/password 不写入日志
校验失败不清理 cloud staging
默认不覆盖已有正式文件
```

### 1.7 前端范围

MVP 包含轻量 Web Console。

Web Console 使用：

```text
React
Vite
FastAPI API
```

MVP Web Console 只覆盖核心操作：

```text
搜索资源
展示候选结果
媒体源配置管理
SMB 配置查看和修改
SMB 连接测试
SMB 目录浏览
创建归档任务
任务进度查看
取消 / 重试任务
```

MVP Web Console 不做完整媒体库 UI、海报墙、播放器、登录注册、多用户权限和完整文件管理器。

FastAPI `/docs` 仍保留为开发调试入口，但不是主要操作界面。

### 1.8 SMB 配置热加载

SMB 配置通过 Web Console 修改并保存到数据库。修改后无需重启 API 或 Worker。

规则：

```text
保存新 SMB 配置
关闭旧 SMB 连接
运行中且使用旧 SMB 配置的任务进入 failed
错误码 STORAGE_CONFIG_CHANGED
retryable = true
保留 .downloading 文件
保留 cloud staging
新任务和重试任务使用最新 SMB 配置
```

### 1.9 AI Tool 方向

FastAPI 后续可封装为 media search tool / AI tool API。

规则：

```text
AI 不直接抓网页
AI 不直接操作 NAS
AI 只调用 Sundarr API
Sundarr API 负责搜索、候选解释、创建任务和查询任务状态
```

---

## 2. 当前文档命名调整

已将当前总纲文档从：

```text
Sundarr_system_plan.md
```

调整为：

```text
Sundarr_mvp_architecture_and_agent_spec.md
```

原因：该文档现在不仅是系统规划，还包含 MVP 架构、Agent 约束、开发顺序、状态机、数据模型、API 契约和实现边界。

---

## 3. 推荐文档结构

后续建议整理为以下结构：

```text
AGENTS.md
README.md
docs/
  01-product-scope.md
  02-architecture-decisions.md
  03-mvp-roadmap.md
  04-source-adapter-spec.md
  05-search-pipeline-spec.md
  06-storage-writer-spec.md
  07-transfer-state-machine.md
  08-data-model.md
  09-api-contract.md
  10-configuration.md
  11-test-plan.md
  12-local-development.md
  13-web-console-spec.md
  14-ai-tool-api-spec.md
```

---

## 4. 待编写文档列表

### P0: AGENTS.md

目的：定义 Agent 在本项目中的工作规则。

主要内容：

```text
必须先读哪些文档
MVP 开发顺序
禁止提前实现的功能
代码风格
测试要求
遇到不确定问题时如何处理
个人项目约束
不做权限系统
MVP 包含 React + Vite Web Console
不依赖系统 SMB mount
每次任务前汇报当前目标、进度、交付物、验收标准
持续从对话中提取已确认决策并同步文档
```

优先级：最高。

### P0: docs/01-product-scope.md

目的：明确 Sundarr 的产品目标、边界和 MVP 范围。

主要内容：

```text
项目目标
核心用户场景
MVP 做什么
MVP 不做什么
个人自用定位
前端范围
权限范围
最低误操作保护
```

优先级：最高。

### P0: docs/02-architecture-decisions.md

目的：固定关键技术决策，避免后续 Agent 反复重新选择技术栈。

主要内容：

```text
为什么选择 Python
为什么选择 FastAPI
为什么选择 React + Vite
为什么选择 PostgreSQL
为什么使用 Redis
为什么不选 Node.js 作为主后端
为什么不选 Jinja2 / HTMX 作为 MVP 前端
为什么不做权限系统
为什么使用应用内 SMB Writer
为什么先做 Mock/Local Provider
为什么 FastAPI 后续可作为 AI tool API
```

优先级：最高。

### P0: docs/03-mvp-roadmap.md

目的：把开发过程拆成可执行阶段。

主要内容：

```text
Phase 0: Project Skeleton
Phase 1: Persistence Models
Phase 2: Source Adapter Framework
Phase 3: Search Pipeline
Phase 4: Mock/Local Cloud Provider
Phase 5: SMB Storage Writer
Phase 6: Transfer Worker
Phase 7: Verification And Cleanup
Phase 8: Web Console
Phase 9: AI Friendly API
Phase 10: API Polish
```

每个阶段需要包含：

```text
目标
交付物
不做什么
涉及模块
验收标准
测试要求
```

优先级：最高。

### P0: docs/04-source-adapter-spec.md

目的：定义多源搜索接入框架，保证新源接入方便、快捷、格式统一。

主要内容：

```text
Source 类型
BaseSource 接口
SearchQuery 结构
RawSearchItem 结构
配置型源规范
代码型源规范
文档/表格型源规范
超时
错误隔离
失败熔断
并发策略
新增源接入步骤
```

优先级：最高。

### P0: docs/05-search-pipeline-spec.md

目的：定义从多源搜索到资源库入库的统一处理管线。

主要内容：

```text
aggregate search
parser
cloud link extractor
normalizer
deduper
ranker
resource library persistence
结果解释字段
低置信度处理
```

优先级：最高。

### P0: docs/06-storage-writer-spec.md

目的：定义不依赖系统挂载的 NAS 写入层。

主要内容：

```text
StorageWriter 抽象接口
SmbWriter 规范
LocalWriter 测试用途
SMB 配置格式
远端目录创建
.downloading 写入
远端文件大小检查
断点续传
rename
默认不覆盖
路径规范化
连接失败重试
SMB 配置热加载
STORAGE_CONFIG_CHANGED 中断规则
```

优先级：最高。

### P0: docs/07-transfer-state-machine.md

目的：定义搬运任务和文件状态机，避免误删和不可恢复失败。

主要内容：

```text
transfer_tasks.status
transfer_files.status
正常流转
失败流转
重试规则
取消规则
worker 启动恢复
什么时候保留 staging
什么时候允许 cleanup
SMB 配置变更如何中断运行中任务
```

优先级：最高。

### P1: docs/08-data-model.md

目的：定义数据库模型和字段约束。

主要内容：

```text
sources
resources
resource_links
transfer_tasks
transfer_files
transfer_logs
settings
字段类型
必填字段
默认值
索引
状态枚举
JSONB 字段用途
```

优先级：高。

### P1: docs/09-api-contract.md

目的：定义后端 API 契约，供 Agent、用户和后续 UI 调用。

主要内容：

```text
GET /health
GET /sources
POST /sources
GET /search
GET /resources/{id}
POST /transfers
GET /transfers/{id}
POST /transfers/{id}/cancel
POST /transfers/{id}/retry
GET /transfers/{id}/logs
GET /settings/storage
PUT /settings/storage
POST /settings/storage/test
GET /storage/browse
统一错误响应
请求示例
响应示例
```

优先级：高。

### P1: docs/10-configuration.md

目的：定义配置结构和环境变量覆盖规则。

主要内容：

```text
app
database
redis
search
cloud
storage.smb
settings table
transfer
runtime settings table
SMB 热加载
环境变量命名
本地开发默认值
敏感字段不入日志
```

优先级：高。

### P1: docs/11-test-plan.md

目的：定义 MVP 必须覆盖的测试范围。

主要内容：

```text
config loading
source adapter
link extractor
normalizer
deduper
SMB writer mock
path normalization
transfer state machine
resume logic
verification failure keeps staging
cleanup guard
API error response
```

优先级：高。

### P2: docs/12-local-development.md

目的：定义本地开发和启动方式。

主要内容：

```text
Python 版本
依赖安装
Docker Compose
启动 API
启动 Worker
运行测试
使用 FastAPI /docs
Mock/Local Provider 使用方法
SMB 测试配置
React + Vite 前端启动
```

优先级：中。

### P1: docs/13-web-console-spec.md

目的：定义 React + Vite Web Console 的 MVP 范围、页面和交互。

主要内容：

```text
React + Vite 技术栈
FastAPI API 后端边界
搜索页
任务页
Storage / SMB 设置页
Sources 设置页
运行状态页
SMB 配置热加载交互
运行中任务中断提示
不做完整媒体库 UI
不做登录和权限
```

优先级：高。

### P1: docs/14-ai-tool-api-spec.md

目的：定义 Sundarr 后续如何作为 AI / Agent 可调用的 media search tool。

主要内容：

```text
AI 不直接抓网页
AI 不直接操作 NAS
search_media
get_resource
create_transfer
get_transfer_status
cancel_transfer
retry_transfer
候选解释字段
低置信度确认机制
```

优先级：高。

### P2: README.md

目的：给人类读者的项目入口说明。

主要内容：

```text
Sundarr 是什么
当前状态
如何启动
如何测试
文档入口
MVP 范围
```

优先级：中。

---

## 5. 建议先编写的最小集合

为了尽快进入 Agent 全流程开发，建议先编写以下 7 份：

```text
AGENTS.md
docs/01-product-scope.md
docs/02-architecture-decisions.md
docs/03-mvp-roadmap.md
docs/04-source-adapter-spec.md
docs/06-storage-writer-spec.md
docs/07-transfer-state-machine.md
docs/13-web-console-spec.md
```

原因：这些文档能先固定产品边界、技术选型、开发顺序、多源搜索框架、SMB 写入方式、任务状态机和 MVP 前端边界。

其余文档可在进入对应开发阶段前补齐。

---

## 6. 已确认决策

以下决策已确认：

1. MVP 包含轻量 React + Vite Web Console。
2. FastAPI 只作为 API 后端，不做 Jinja2 页面渲染。
3. FastAPI 后续可封装为 media search tool 供 AI 调用。
4. MVP 不做登录、注册、多用户、权限系统。
5. MVP 使用 Python + FastAPI。
6. MVP 使用 PostgreSQL + Redis。
7. MVP 不依赖系统 SMB mount，而是实现应用内 `SmbWriter`。
8. SMB 配置修改后无需重启，并会中断当前使用旧 SMB 配置的运行中任务。
9. 被 SMB 配置变更中断的任务进入 `failed`，错误码为 `STORAGE_CONFIG_CHANGED`，`retryable=true`。
10. 被中断任务保留 `.downloading` 文件和 cloud staging。
11. MVP 先使用 Mock/Local Provider 跑通流程，再接真实网盘 provider。
12. 多源搜索支持配置型源、代码型源、文档/表格型源。
13. Web Console 只支持管理配置型源和文档/表格型源，不支持在线编辑代码型 Source Adapter。
14. Web Console 只做核心控制台，不做完整媒体库 UI。

下一步建议先编写：

```text
AGENTS.md
docs/01-product-scope.md
docs/02-architecture-decisions.md
docs/03-mvp-roadmap.md
```
