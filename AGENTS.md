# Agent 工作规则

本文件定义 Agent 在 Sundarr 项目中的默认工作方式。除非用户明确覆盖，本文件规则优先于普通建议。

---

## 1. 开始任务前必须汇报

Agent 在开始每个非 trivial 任务前，必须先向用户汇报：

```text
当前目标
当前进度
本轮交付物
验收标准
停止条件
```

要求：

1. 汇报必须简洁、具体。
2. 不写空泛计划。
3. 当目标、范围、阻塞或交付物发生变化时，必须及时更新汇报。

---

## 2. 文档同步规则

Agent 必须持续从对话中提取已经确认的长期决策，并及时更新项目文档。

长期决策包括：

```text
产品范围变化
MVP 边界变化
技术选型变化
架构决策
模块职责变化
API、数据模型、状态机变化
开发优先级变化
用户明确偏好
功能进入或移出 MVP
```

不得直接写入文档的内容：

```text
临时头脑风暴
尚未确认的方案
一次性解释
已放弃的想法
闲聊内容
```

规则：

1. 用户明确确认长期决策后，Agent 应在同一轮尽量更新相关文档。
2. 如果一个决策影响多个文档，必须先更新事实来源文档，再更新派生文档。
3. 如果用户只是在比较方案或讨论可能性，必须先总结待确认决策并询问是否写入文档。

---

## 3. 文档归属

文档更新应优先写入对应事实来源：

```text
产品范围和 MVP 边界 -> docs/01-product-scope.md
技术选型和架构理由 -> docs/02-architecture-decisions.md
开发顺序和阶段验收 -> docs/03-mvp-roadmap.md
多源搜索接入规则 -> docs/04-source-adapter-spec.md
搜索处理管线 -> docs/05-search-pipeline-spec.md
SMB / Storage Writer -> docs/06-storage-writer-spec.md
任务状态机 -> docs/07-transfer-state-machine.md
数据模型 -> docs/08-data-model.md
API 契约 -> docs/09-api-contract.md
配置规则 -> docs/10-configuration.md
测试要求 -> docs/11-test-plan.md
本地开发 -> docs/12-local-development.md
Web Console -> docs/13-web-console-spec.md
AI Tool API -> docs/14-ai-tool-api-spec.md
下载到本地 -> docs/15-download-to-local-spec.md
前端设计系统 -> docs/16-design-system.md
系统模块梳理 -> docs/17-system-module-review.md
网盘直链下载 -> docs/18-cloud-direct-download-spec.md
外部搜索源仓库 -> docs/19-source-repository-plugin-spec.md
Agent 工作规则 -> AGENTS.md
```

当前汇总参考文档：

```text
Sundarr_mvp_architecture_and_agent_spec.md
Sundarr_documentation_plan.md
```

---

## 4. 当前固定决策

以下决策已确认，后续实现不得随意改变：

```text
MVP 使用 Python + FastAPI 作为 API 后端。
MVP 使用 React + Vite 作为轻量 Web Console。
FastAPI 只作为 API 后端，不做 Jinja2 页面渲染。
FastAPI 后续可封装为 media search tool 供 AI 调用。
MVP 使用 PostgreSQL + Redis。
MVP 不做登录、注册、多用户、权限系统。
MVP 不依赖系统 SMB mount，使用应用内 SmbWriter。
SMB 配置可在 Web Console 修改并热加载。
SMB 配置修改会中断使用旧 SMB 配置的运行中任务。
被中断任务进入 failed，错误码 STORAGE_CONFIG_CHANGED，retryable=true。
被中断任务保留 .downloading 文件和 cloud staging。
真实网盘直接下载不包含在 MVP 中，仅作为后续高级功能实现，CloudProvider 保留为可选扩展和测试抽象。
Phase 8 “下载到本地”是历史阶段命名；当前规范命名统一为“远程媒体库同步到本地媒体库”。
未来“分享链接保存到网盘”模块命名为“保存到网盘”。
SMB 存储模块必须支持多个 SMB 连接，远程媒体库和本地媒体库只能引用已配置 SMB 连接和目录，不重复填写 SMB 凭据。
本地媒体库指本地 NAS 媒体目录类型，例如 movie / series / unclassified。
本地媒体库管理模块负责创建本地媒体库，并绑定到某个 SMB 连接下的本地目录。
远程媒体库负责绑定 SMB 连接下的远程目录（如网盘挂载目录）。
同步绑定负责连接远程媒体库（来源）和本地媒体库（目标）。
Worker 定时扫描同步绑定，将远程媒体库内容同步到绑定的本地媒体库目录。
同步支持 movie / series / unclassified，绑定不明确时进入 unclassified 本地媒体库。
同步成功后按配置删除来源文件和空目录。
Web Console 中配置类页面默认先展示列表，通过新增按钮打开弹出表单，不默认展开空新增表单。
媒体发现中心已纳入当前 MVP 和当前优先任务，负责带筛选条件的搜索、热门资源、分类资源、详情、关注列表和发现型海报墙。
媒体发现中心使用 Sundarr 内部 UUID 标识规范媒体实体 `MediaSubject`，并允许同时绑定 TMDb、豆瓣、IMDb 等多个外部 ID；任何单一外部平台 ID 都不是数据库主键。
存在相同外部平台 ID 时可以精确匹配；缺少外部 ID 时只能生成标题、年份和类型候选匹配，低可信候选不得静默自动合并。
媒体发现中心 MVP 使用 TMDb 作为主目录数据提供方，负责搜索、筛选、热门、分类、详情和海报；豆瓣目录作为可选补充数据提供方，失败不得阻断媒体发现中心。
TMDb 目录和豆瓣目录均以 CATALOG_PROVIDER 插件接入；豆瓣想看以独立 WATCHLIST_PROVIDER 插件接入，由 Core 负责定时调度和持久游标。
同一外部仓库可以交付多个插件实例；douban-catalog 与 douban-watchlist 必须能够独立配置、启停、测试和报错。
SOURCE 只表示具体资源链接搜索源，不表示影片目录或想看列表。
自动化测试使用 MockCatalogProvider，不依赖 TMDb、豆瓣或其他实时外部服务。
媒体库管理仍是目录绑定管理能力；媒体发现海报墙不等于本地媒体库海报墙、播放器、观影进度或完整媒体管理 UI。
当前已实现的是媒体源框架和示例源，不是真实网站 Adapter。
真实媒体源后续通过代码型 Source Adapter 逐站点接入。
真实搜索源代码可以集中放在独立 Git 仓库中，Sundarr Core 只保存仓库地址、分支和锁定 commit，并从本地缓存中的已锁定 commit 受控加载。
外部搜索源仓库接入采用 SourceManifest / LoadedSource / SourceModel 分层，SourceModel 继续作为最小运行时执行协议。
Web Console 不上传、不编辑、不保存可执行 Python 代码，只负责搜索源仓库配置、检查更新、应用更新、回滚、测试和诊断。
Web Console 只管理已安装 Adapter 的启用、禁用、参数、测试和错误查看，不在线编辑代码型 Source Adapter。
文档型网站是否可通用读取作为后续实验阶段验证。
Web Console 是核心控制台，不做完整本地媒体库 UI。
项目文档、Git commit message、代码注释、报错提示、界面文案和其他项目相关文本原则上使用简体中文。
系统核心功能是"远程媒体库同步到本地媒体库"，不再使用"网盘导入"概念。
远程媒体库绑定 SMB 连接下的远程目录（如网盘挂载目录）。
本地媒体库绑定 SMB 连接下的本地 NAS 目录。
同步绑定连接：远程媒体库（来源） -> 本地媒体库（目标）。
Phase 9 模块重构已完成：已删除 Ingest 模块和旧 storage_config_service，新增远程媒体库模型并统一同步绑定。
Phase 9.5 收藏模型重构已完成：搜索默认不入库，资源和资源链接仅在用户主动收藏时持久化。
Phase 10.0 质量基线收口已完成；当前优先任务调整为 Phase 10.1 媒体发现中心。Phase 10.1 恢复目录和想看插件所需的最小加载、注册和健康检查；完整热更新、原子切换及外部搜索源仓库闭环在后续阶段完成。
Sundarr Core 继续使用 Python + FastAPI，不引入 Cordis 或 Node.js 作为后端运行时。
Python 插件系统采用 Cordis 启发的生命周期语义：显式能力依赖、Activation、可逆清理、候选加载、健康检查、原子切换和失败回滚。
该设计只借鉴 Cordis 的组合思想，不依赖 Cordis 包，不把持久任务状态、数据库事务或 SMB Worker 交给插件运行时。
Phase 11 AI Friendly API 完成后，可以提供可选的 Cordis / DeepSeek Harness 桥接插件；桥接插件只调用 Sundarr API，不直接访问数据库、SMB 或 Worker 内部对象。
前端设计系统基线文档位于 docs/16-design-system.md，在 Phase 7.8 Web Console UI Polish 中落地。
前端视觉基调：暖色操作台风格，强调色为 terracotta（暗色 #d97642 / 亮色 #b05623），字体 Inter + JetBrains Mono，支持亮色 / 暗色 / 跟随系统三种主题。
本地 CLI 启动时 PID 文件必须指向真实 API / Web / Worker 服务进程，不使用日志包装进程改变 PID 语义；Docker Compose 模式日志默认走 stdout/stderr，由 Docker logging driver 控制大小。
搜索结果默认不写入 Resource / ResourceLink；只有用户主动收藏资源或收藏资源链接时才入库。
收藏是独立业务模块，Web Console 只保留一个收藏入口；资源收藏和资源链接收藏是收藏模块下的两类对象，不作为两个独立模块展示。
Resource 表示“这是什么资源”，ResourceLink 表示“这个资源的一个具体链接/版本”。
ResourceLink 可单独收藏；单独收藏链接时写入最小 Resource 父记录，但 Resource 本身不一定收藏。
ResourceLink.name 用于展示具体链接名称，可来自搜索源链接标题，缺失时由资源标题和 quality 兜底生成。
quality 属于 ResourceLink，不属于 Resource；type 获取不稳定，不纳入最小 Resource 模型。
Resource / ResourceLink 收藏库不是 /search 的替代数据源；用户搜索时始终实时调用 Source Adapter，并附加收藏标记。
当前创建任务不依赖 Resource / ResourceLink，任务事实来源仍是远程媒体库扫描结果。
risk_level 和 visibility 不纳入 ResourceLink MVP 最小模型。
```

---

## 4.1 项目文本语言规则

项目内面向人类阅读的文本原则上使用简体中文。

适用范围：

```text
项目文档
Git commit message
代码注释
错误提示
日志事件说明
前端界面文案
README
配置示例说明
测试用例描述
```

例外：

```text
代码标识符
第三方库 API 名称
协议字段
HTTP 标准术语
数据库字段名
枚举值
必须与外部系统保持一致的英文字符串
```

如果英文能显著降低歧义，例如标准错误码 `STORAGE_CONFIG_CHANGED`，可以保留英文枚举值，但对应说明文字应使用简体中文。

---

## 5. MVP 不做事项

除非用户重新确认，MVP 不做：

```text
BT / 磁力 / 种子下载
盗版资源分发或资源托管
绕过网盘限制、破解会员、绕过验证码
登录注册
多用户权限
角色管理
OAuth
复杂审计日志
完整本地媒体库 UI
本地媒体库海报墙
播放器和观影进度
完整 NAS 文件管理器
在线编辑代码型 Source Adapter
本地媒体库刮削 / NFO 生成
Playwright 重型抓取
OpenList 作为核心搬运层
rclone 作为 MVP 核心传输层
国内封闭网盘直接下载作为 MVP 核心搬运层
将网盘直链下载（Cloud Direct Download）纳入 MVP 或近期主线
真实媒体源通用爬虫框架
通过 Web Console 配置复杂网站爬虫
在配置或数据库中保存可执行 Python 代码
要求用户维护本地文档/表格作为主要媒体源
```

---

## 6. 开发顺序

Agent 应按 `docs/03-mvp-roadmap.md` 的 Phase 顺序推进。

默认顺序：

```text
Phase 0: Project Skeleton
Phase 1: Persistence Models
Phase 2: Search And Resource Library
Phase 3: Cloud Staging
Phase 4: Storage Writer
Phase 5: Transfer Worker
Phase 6: Cleanup And Recovery
Phase 7: Web Console
Phase 7.8: Web Console UI Polish
Phase 8: Download To Local
Phase 9: Module Refactoring
Phase 9.5: Resource Favorites Refactoring
Phase 10.0: Quality Baseline Closure
Phase 10: Real Site Source Adapters
Phase 11: AI Friendly API
```

Phase 12 Cloud Direct Download 不包含在 MVP 中，仅作为后续高级功能保留规格文档；Alist、真实网盘 Provider 和直链下载均不是当前或近期主线。

不得提前实现后续阶段的大型功能，除非当前阶段验收需要或用户明确要求。

---

## 7. Git 规则

1. Agent 在完成一个清晰、可验证的交付单元后，应主动创建 commit，不必逐次请示。默认开启自动提交。
2. 创建 commit 前必须检查 `git status`、`git diff` 和近期提交信息，确认范围清晰、无敏感内容。
3. 不要提交 `.env`、凭据、token、cookie、SMB 密码等敏感信息。
4. 不要修改或回滚用户未授权的变更。
5. 不要使用破坏性 Git 命令（push --force、reset --hard、clean -fd、branch -D 等），除非用户明确要求。
6. commit 应保持小而聚焦，信息使用简体中文准确说明本次交付。
7. 默认直接在 master 分支上提交，不为常规改动额外创建功能分支；仅在用户明确要求或改动确实需要 PR 评审时才建新分支。
8. push 到远程默认需要用户明确指示才执行；用户一次性授权后可连续 push，直到任务切换或用户叫停。
9. 如果存在测试失败、范围不清或疑似敏感文件，必须先暂停并向用户说明，不得自动提交。

---

## 8. 测试与验收

实现代码时，Agent 必须优先保证：

```text
可启动
可测试
状态可追踪
失败可恢复
误删有保护
```

MVP 自动化测试不得依赖真实网盘或真实 NAS。必须提供 Mock/Local Provider 和可测试的 Storage Writer 抽象。

每完成一项非文档型开发任务后，Agent 必须执行对应回归测试和冒烟测试，避免技术债积累，并确认本次交付入口真实可用。

最低要求：

```text
后端变更 -> 运行 pytest；再对本次改动的 API、CLI 或 Worker 入口做最小冒烟测试
前端变更 -> 运行 npm run build，必要时运行前端测试；再确认受影响页面或交互可打开、可触发
配置 / Docker 变更 -> 运行相关启动或配置校验；再做对应启动、health 或连接冒烟测试
文档规则变更 -> 检查相关文档是否一致
```

冒烟测试可以是自动化测试、TestClient/API 调用、CLI 命令、启动后访问 `/health`、前端页面本地打开检查，或与本次交付等价的最小端到端验证。冒烟测试不替代回归测试。

如果回归测试或冒烟测试失败，Agent 必须优先修复失败，再继续下一项任务。不得在已知测试失败的情况下继续堆叠新功能，除非用户明确要求暂停修复。

---

## 9. Agent 交付规则

Agent 确认任务目标后，先更新相关文档再动手修改代码。复杂任务可以积极使用子代理并行推进。

每个非文档型交付后必须执行冒烟测试和回归测试，确认入口真实可用。

测试通过后可以分步创建 commit，保持提交聚焦且可回溯。
