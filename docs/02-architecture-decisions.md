# 架构决策

本文档记录 Sundarr 已确认的关键技术决策和理由。

---

## ADR-000.1: 外部 Git 搜索源仓库

状态：已确认。

决策：

```text
真实搜索源代码可以与 Sundarr Core 分离，集中放在独立 Git 仓库中维护。
Sundarr Core 只保存搜索源仓库地址、分支和锁定 commit。
系统从本地缓存中的已锁定 commit 加载 Source Adapter。
Web Console 只负责配置仓库、检查更新、应用更新、回滚、测试和诊断。
Web Console 不上传、不编辑、不保存可执行 Python 代码。
```

理由：

```text
真实搜索源变化频率高，不应要求频繁修改 Sundarr Core。
多个搜索源需要集中维护、测试和复用开发规范。
SourceModel 已适合作为搜索执行协议，但不适合承载仓库来源、commit 和加载状态。
通过 SourceManifest / LoadedSource / SourceModel 分层，可以同时保持搜索管线稳定和插件来源可追踪。
```

约束：

```text
默认不在启动时无条件执行远程最新代码。
必须锁定 current_commit。
加载失败不能影响系统启动。
数据库和配置不得保存可执行 Python 代码。
外部仓库必须视为用户信任代码来源。
```

相关文档：

```text
docs/04-source-adapter-spec.md
docs/19-source-repository-plugin-spec.md
```

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

## ADR-001.1: Python 插件运行时采用 Cordis 启发的生命周期语义

状态：已确认。

决策：

```text
Sundarr 不引入 Cordis 包，也不把 Core 改写为 Node.js / TypeScript。
插件运行时在 Python 中实现 PluginContext、能力依赖、PluginActivation 和清理栈。
插件更新采用“候选加载 -> 配置校验 -> 健康检查 -> 原子切换 -> 释放旧 Activation”。
候选加载失败时继续保留旧 Activation；禁用、回滚和仓库删除必须释放该插件注册的 Source、连接、定时器和其他副作用。
```

理由：

```text
Cordis 的显式服务依赖和可逆副作用适合 Sundarr 的动态 Source Adapter 生命周期。
Sundarr 的持久任务、数据库事务、SMB 流式搬运和跨进程状态不适合迁移到进程内 TypeScript 插件框架。
保留 Python 可以复用现有 FastAPI、SQLAlchemy、smbprotocol、Worker 和测试资产。
```

约束：

```text
PluginActivation 只管理插件进程内资源，不是任务状态事实来源。
外部 Python 插件是用户信任代码；生命周期管理不等于安全沙箱。
插件只能通过 PluginContext 暴露的稳定能力访问 Core，不直接依赖数据库 Session、Worker 私有函数或全局单例。
Phase 10.1 为媒体发现恢复最小插件加载能力，并新增 CATALOG_PROVIDER 与 WATCHLIST_PROVIDER；完整候选切换和通用生命周期闭环仍在 Phase 10.2 完成。
```

参考思想来源：

```text
https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/cordis-primer.md
https://github.com/cordiverse/paper
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
MVP 包含核心控制台和媒体发现中心，但不做完整本地媒体库 UI。媒体发现中心的元数据来源、持久化和页面信息架构仍需逐项确认。
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
媒体目录详情、评分、图片信息、热门和分类缓存
链接有效性缓存
实时进度加速
短期失败源熔断
```

约束：

```text
Redis 不是任务状态事实来源。
transfer_tasks 和 transfer_files 状态必须持久化到 PostgreSQL。
Redis 不是 MediaSubject 身份、外部 ID 或用户关注状态的事实来源。
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
Compose 部署中 API / Worker 使用固定内部服务名 postgres / redis 连接基础设施，不要求用户手动配置数据库地址。
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
Compose 阶段的 .env 只保存部署级 secret 和端口覆盖，不保存普通业务配置。
```

---

## ADR-005.2: env 最小化和业务配置入库

状态：已确认。

决策：

```text
env 只保留数据库和 Redis 这类 bootstrap 连接信息。
cloud staging root、worker 并发、SMB 配置、source 配置、media_libraries 等业务配置保存到数据库 settings / sources / 业务表。
数据库初始化完成后写入默认 settings。
```

默认值：

```text
worker.enabled = true
worker.concurrency = 2
cloud.local.staging_root = /Sundarr/_staging
```

理由：

```text
业务配置需要后续由 Web Console 管理。
env 不适合承载热加载配置和普通业务参数。
数据库连接本身不能只保存在数据库中，因为连接数据库前必须先有 bootstrap 信息。
```

---

## ADR-005.2.1: 本地文件日志与 Docker stdout 日志分离

状态：已确认。

决策：

```text
本地 CLI 启动时，API / Worker 使用应用内滚动文件日志。
Docker Compose 启动时，API / Worker / Web 默认写 stdout/stderr，由 Docker logging driver 控制日志大小和保留数量。
CLI 进程管理不得通过日志包装进程改变 PID 文件语义；PID 文件必须指向真实服务进程。
```

理由：

```text
日志包装进程会让 Windows 下的进程树和 PID 文件语义变复杂，容易出现 PID 文件和端口占用状态不一致。
Docker 已提供成熟日志收集和轮转能力，应用不应在容器内重复维护主日志文件。
本地开发仍需要可查看的文件日志，因此使用应用内滚动文件日志，而不是通过额外父进程包裹服务。
```

---

## ADR-005.3: sundarr 命令启动完整项目

状态：已确认。

决策：

```text
sundarr start / restart / stop / status 面向完整项目，而不是只管理 API。
当前阶段完整项目包含 API + Web Console。
Phase 5 实现 Worker 时，必须同步将 Worker 纳入这些命令。
```

启动规则：

```text
sundarr start 会自动执行数据库初始化/迁移和默认 settings seed。
如果 web/node_modules 不存在，自动执行 npm install。
如果 API 或 Web 端口被本项目旧进程占用，按需清理后重启。
如果端口被其他程序占用，拒绝启动。
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

## ADR-009: 真实网盘直接下载不包含在 MVP 中

状态：已确认。

决策：

```text
国内封闭网盘直接下载不包含在 Sundarr MVP 中。
网盘直链下载（Cloud Direct Download）仅作为后续高级功能保留规格，不进入 MVP 主线。
CloudProvider 保留为可选扩展和测试抽象，但不承诺 MVP 接入真实网盘直接下载。
MVP 主链路统一命名为“远程媒体库同步到本地媒体库”：NAS 或挂载服务挂载网盘后通过 SMB 暴露远程媒体库目录，Sundarr 将远程媒体库绑定到本地媒体库，并由 Worker 定时同步到本地媒体库绑定的 SMB 目录。
```

理由：

```text
国内主流网盘通常不提供稳定、开放、可自动化的大文件下载 API。
绕过 App、验证码、会员或风控限制不属于 Sundarr 范围。
NAS 或挂载服务已能将网盘远程挂载为目录，Sundarr 通过 SMB 处理挂载结果更稳定、边界更清晰。
独立服务器部署 Sundarr 时，可通过 SMB 同时访问网盘挂载目录和 NAS 本地媒体库。
```

配套决策：

```text
Phase 8 “下载到本地”是历史阶段命名；当前规范命名统一为“远程媒体库同步到本地媒体库”。

SMB 连接由 Storage 模块统一管理并支持多个连接；远程媒体库和本地媒体库只引用 SMB connection 和目录，不重复保存 SMB 凭据。
本地媒体库指本地 NAS 逻辑目录类型，例如 movie / series / unclassified。
本地媒体库管理模块负责创建本地媒体库，并绑定到某个 SMB connection 下的本地目录。
远程媒体库负责绑定网盘来源 SMB connection 和远程目录。
同步绑定负责连接远程媒体库（来源）和本地媒体库（目标）。
绑定不明确时进入 unclassified 本地媒体库。
成功后按全局或 binding 配置删除源文件和空目录。
AI Friendly API 后移到后续阶段。
后续大阶段再考虑在 Sundarr 内挂载网盘和保存分享链接到网盘。
```

---

## ADR-010: 多源搜索必须统一适配框架

状态：已确认。

决策：

```text
聚合搜索必须使用 Source Adapter 框架。
每个 source 输出统一 RawSearchItem。
真实媒体源通过 Source Adapter 逐站点接入。
Source 统一由 Adapter 代码定义，并同步到 `sources` 目录表，不再由用户通过 Web Console 创建 configurable / document source。
不得在数据库、配置文件或 Web Console 中保存可执行 Python 代码。
```

近期主线源类型：

```text
Source Adapter
```

规则：

```text
单个源失败不能影响整体搜索。
聚合后统一解析、提取、标准化、去重、排序。
Web Console 展示已安装搜索源列表，并在详情弹窗中提供测试搜索和步骤日志。
Source Adapter 不允许前端在线编辑。
当前已开始接入真实搜索源，首个实现为 `SeedHubSource`。
真实站点爬虫、通用爬虫规则引擎和通过 Web Console 配置复杂网站爬虫需要后续独立大阶段规划。
文档型网站是否可通用读取可作为后续实验阶段验证，不作为当前主线承诺。
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

配套决策：

```text
AI Friendly API 稳定后，可以新增可选 Cordis / DeepSeek Harness 桥接插件。
桥接插件是 Sundarr 的外部客户端，只通过公开 HTTP API 注册 search_media、收藏和任务状态等工具。
桥接插件不得直接加载 Sundarr Python 插件、访问数据库或操作 SMB。
```

---

## ADR-012: 规范媒体实体使用内部 UUID 和多外部 ID

状态：已确认。

决策：

```text
媒体发现中心使用 MediaSubject 表示规范媒体实体。
MediaSubject.id 使用 Sundarr 内部 UUID。
MediaSubject 可以同时绑定 TMDb、豆瓣、IMDb 等多个外部平台 ID。
任何单一外部平台 ID 都不能作为 Sundarr 数据库主键。
```

理由：

```text
避免更换目录或元数据提供方时破坏收藏、任务和历史关联。
允许不同发现入口逐步补齐同一个媒体实体的外部身份。
为电影、剧集、动画和未来其他目录平台保留扩展空间。
```

匹配规则：

```text
相同 provider + external_id 可以作为精确匹配依据。
没有外部 ID 时，只能使用标准化标题、年份和媒体类型生成候选匹配。
低可信候选不得静默合并，必须保持独立或等待用户确认。
```

`MediaSubject` 与现有 `Resource` 的表关系、外部 ID 的具体存储结构仍待后续决策。

---

## ADR-013: 目录提供方与想看列表提供方分离

状态：已确认。

决策：

```text
TMDb 是媒体发现中心 MVP 的主目录数据提供方，以 CATALOG_PROVIDER 插件接入。
豆瓣目录是可选补充数据提供方，同样以 CATALOG_PROVIDER 插件接入。
豆瓣想看以独立 WATCHLIST_PROVIDER 插件接入，只负责产生或同步用户关注条目。
WATCHLIST_PROVIDER 的定时调度、同步游标、重试和持久状态由 Core 管理，插件不自行维护永久后台循环。
SOURCE 只负责搜索具体资源链接，不承担影片目录或想看列表职责。
豆瓣目录或想看接入不可用时，不得阻断 TMDb 目录浏览、用户搜索或其他发现入口。
自动化测试使用 MockCatalogProvider，不实时调用 TMDb、豆瓣或其他外部服务。
```

边界和约束：

```text
外部响应必须映射为 Sundarr 内部发现模型，Core 不直接传播平台私有响应结构。
TMDb 和豆瓣同名字段保留来源，不允许把不同平台评分直接覆盖为单一评分。
一个外部仓库可以声明多个插件实例；douban-catalog 与 douban-watchlist 独立配置、启停、测试和报告错误。
每个插件实例保留一个主 PluginType；manifest 的 provides 声明该类型下的细粒度能力。
API 密钥、cookie 或其他凭据不得写入仓库或日志。
界面和发布方式必须满足所用外部服务的署名、许可及使用条款。
外部请求必须配置超时、缓存和明确降级；外部服务不得成为 Core 可用性的单点依赖。
豆瓣想看的可用接入方式、稳定性和合规边界仍需单独验证，不能假定存在稳定的官方开放 API。
```

尚待后续设计：`CATALOG_PROVIDER`、`WATCHLIST_PROVIDER` 的方法签名、字段级合并优先级、缓存时效和同步游标模型。

---

## ADR-014: 媒体发现采用核心持久化与目录缓存分层

状态：已确认。

决策：

```text
PostgreSQL 永久保存 MediaSubject 内部 UUID、媒体类型、规范标题、年份、外部 ID、最后可用海报地址、来源和更新时间。
用户产生的关注、想看及与 MediaSubject 关联的长期状态必须持久化。
Redis 缓存简介、演员、类型、平台评分、完整图片信息、搜索结果、热门、分类和插件原始响应。
目录原始响应不是业务事实，不写入 PostgreSQL 长期表。
MVP 不下载或永久保存海报二进制文件。
```

降级规则：

```text
Redis 清空不得造成 MediaSubject、外部 ID 或用户状态丢失。
缓存未命中时调用对应 CATALOG_PROVIDER。
Provider 失败且存在最小展示快照时，返回快照并标记 degraded，不把失败或空值覆盖为已知字段。
没有快照且 Provider 不可用时返回明确错误，不伪造完整数据。
不同 Provider 的评分和更新时间分别保留来源，不能合并成无来源的单一值。
```

理由：当前产品是媒体发现与自动化控制台，不是完整本地媒体数据库。该分层保留关注和身份稳定性，同时避免引入全量目录同步、复杂刮削模型和长期数据冲突。

尚待后续设计：具体缓存 TTL、缓存键、外部 ID 表结构、字段级来源结构和 `MediaSubject` 与资源/任务的关系。

---

## ADR-015: 媒体发现使用统一模块并与资源搜索分离

状态：已确认。

决策：

```text
/app/discover 是媒体发现中心的统一入口，承载目录搜索、筛选、热门、分类、关注入口和发现型海报墙。
/app/discover/:media_subject_id 是媒体详情页。
/app/search 继续调用 SOURCE 查找具体资源链接，不承担 TMDb/豆瓣目录搜索。
用户可以从媒体详情进入资源搜索；传递参数、ResourceOffer 关联和任务创建方式在后续决策中确认。
```

理由：目录搜索回答“想看什么”，资源搜索回答“从哪里获取”。二者共享用户旅程但数据模型、Provider、结果结构和失败语义不同，使用独立路由能避免搜索框、筛选项和状态含义混杂。

尚待确认：分页方式、详情信息层级和关注列表的进一步操作。

---

## ADR-016: 发现首页使用内容流与搜索结果双模式

状态：已确认。

决策：

```text
/app/discover 无有效搜索条件时显示分区内容流。
内容流顶部提供目录搜索和快捷筛选，下方展示热门电影、热门剧集、分类推荐和关注更新。
用户提交关键词或筛选条件后，页面主体切换为统一海报网格。
关键词和筛选状态写入 URL query，刷新、浏览器前进后退和分享 URL 时可以恢复。
```

约束：

```text
内容流各分区独立加载和失败，单个 Provider 或分区失败不得清空整页。
搜索模式与内容流模式共享 MediaSubject 卡片和详情入口。
URL 只保存可公开的筛选状态，不保存 token、cookie 或其他敏感插件配置。
当前决策不预设分页/无限滚动方式或详情字段。
```

---

## ADR-017: 媒体发现 MVP 使用基础公共筛选集

状态：已确认。

筛选集：

```text
媒体类型：全部 / 电影 / 剧集。
题材。
地区。
年份：单年或起止年份范围。
排序：热度 / 评分 / 上映时间。
```

不进入当前 MVP：

```text
语言。
评分区间。
演员和导演。
目录 Provider 来源选择。
复杂题材、地区布尔组合。
```

理由：基础筛选覆盖主要发现路径，且更容易映射到多个 `CATALOG_PROVIDER`。高级筛选会显著增加 Provider 能力差异、URL 状态、空结果解释和测试组合，当前收益不足以抵消复杂度。

约束：插件必须声明实际支持的筛选能力。Core 和 Web Console 不得把不支持的筛选静默当作已生效；具体能力协商和降级行为随后续 Provider 方法契约设计。

选择基数：

```text
题材和地区在 MVP Web Console 中均为单选。
Core 查询模型使用列表结构，MVP 校验最多一个题材和一个地区。
传入多个值时返回明确参数错误，不静默取第一个值。
未来启用简单多选时复用同一查询结构，不改变 Provider 方法的参数形状。
```
