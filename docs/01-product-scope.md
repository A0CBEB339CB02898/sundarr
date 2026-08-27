# 产品范围

本文档定义 Sundarr 的产品目标、MVP 范围和明确不做事项。

---

## 1. 项目定位

Sundarr 是为 Homelab 打造的媒体发现与远程媒体库同步工具。

核心目标：

```text
通过搜索、筛选、热门、分类和关注列表发现媒体
-> 查看媒体详情和候选资源
-> 提取网盘链接
-> 用户手动保存到网盘
-> 网盘通过 SMB 暴露为远程媒体库
-> 将远程媒体库同步到本地媒体库
-> 校验文件
-> 删除来源文件和空目录
```

Sundarr 不是：

```text
BT 下载器
盗版资源分发系统
网盘破解工具
OpenList 替代品
完整 NAS 文件管理器
完整本地媒体库 UI / 播放器 / 观影进度
```

---

## 2. 目标用户场景

目标用户是个人 NAS 用户。

典型流程：

```text
用户在 Web Console 搜索媒体资源。
用户也可以通过热门资源、分类资源、筛选条件和关注列表发现媒体。
Sundarr 从多个已配置来源聚合搜索结果。
用户可以在收藏模块中收藏资源，或收藏某条具体资源链接。
用户选择候选资源和目标媒体库。
用户手动将资源保存到网盘。
NAS 或挂载服务将网盘远程挂载为目录，并通过 SMB 暴露给 Sundarr。
Sundarr 根据同步绑定，将远程媒体库中的文件同步到对应本地媒体库目录。
下载期间写入 .downloading 临时文件。
校验成功后 rename 为正式文件。
最后按配置删除来源文件和空目录。
```

---

## 3. MVP 必须做

MVP 必须完成最小可用闭环。

功能范围：

```text
FastAPI API 后端
React + Vite 轻量 Web Console
PostgreSQL 持久化
Redis 缓存和实时进度辅助
多源 Source Adapter 框架
媒体发现中心，支持筛选、热门、分类、详情、关注列表和发现型海报墙
Cloud Link Extractor
收藏模块，统一管理资源收藏和资源链接收藏
Mock/Local Cloud Provider
远程媒体库同步到本地媒体库规范
本地媒体库管理，支持创建 movie / series / unclassified 等本地媒体库
本地媒体库绑定到某个 SMB 连接下的本地 NAS 目录
远程媒体库绑定到某个 SMB 连接下的远程目录（如网盘挂载目录）
同步绑定连接远程媒体库（来源）和本地媒体库（目标）
应用内 SmbWriter
LocalWriter 测试实现
Transfer Worker
.downloading 临时文件
大小校验
成功后 rename
Cloud Provider / cloud staging 保留为可选扩展和测试抽象
成功后删除挂载来源文件和空目录
任务取消和重试
多个 SMB 连接查看、修改、测试连接、目录浏览
媒体源配置管理
```

媒体发现中心已经纳入当前 MVP 和当前优先任务，但仍处于设计阶段，不得标记为已实现。

---

## 4. Web Console 范围

MVP 包含轻量 Web Console。

必须覆盖：

```text
搜索资源
通过筛选、热门、分类、关注列表和海报展示发现媒体
查看媒体详情
展示候选结果
收藏模块
在收藏模块中查看资源收藏和资源链接收藏
查看资源详情
管理已安装搜索源
查看和修改多个 SMB 连接
测试 SMB 连接
浏览 SMB 目录
创建和管理媒体库
创建归档任务
查看任务状态和进度
取消 / 重试任务
显示 STORAGE_CONFIG_CHANGED 中断提示
配置远程媒体库到本地媒体库的同步绑定
配置未分类目录
```

不做：

```text
完整本地媒体库 UI
本地媒体库海报墙
播放器和观影进度
完整文件管理器
拖拽式管理
任意 NAS 文件删除
登录注册
多用户权限
```

---

## 5. 权限范围

MVP 按个人自用项目处理。

不做：

```text
用户注册
用户登录
多用户权限
角色管理
OAuth
API token 管理
审计系统
```

仍保留最低误操作保护：

```text
不能删除 cloud staging 根目录之外的路径
不能删除挂载来源根目录之外的路径
不能写入 SMB 配置允许范围之外的路径
cookie/token/password 不写入日志
校验失败不清理 cloud staging
校验失败不删除挂载来源文件
默认不覆盖已有正式文件
```

---

## 6. 媒体源范围

多源即时搜索是核心能力。Sundarr 要做的是从真实媒体网站即时搜索资源，而不是要求用户维护本地资源表。

已确认的长期产品范围还包括媒体发现中心：支持带筛选条件的搜索、热门资源、分类资源、发现型海报墙、媒体详情和关注列表入口。该模块展示的是“可以发现和获取什么”，不是“本地媒体库里已经有什么”，不承担播放、观影进度或完整本地媒体管理。

媒体发现中心以规范媒体实体 `MediaSubject` 表示一部电影、剧集或其他媒体对象。`MediaSubject` 使用 Sundarr 内部 UUID，并可同时绑定 TMDb、豆瓣、IMDb 等多个外部 ID，避免产品数据与任何单一目录平台绑定。

MVP 使用 TMDb 作为媒体发现主目录数据提供方，负责搜索、筛选、热门、分类、详情和海报；豆瓣目录作为可选补充，用于提供中文别名、豆瓣评分、中文内容热度和豆瓣榜单等来源明确的数据。两者均以 `CATALOG_PROVIDER` 插件接入，豆瓣目录失败不得阻断 TMDb 目录浏览和其他发现入口。

豆瓣想看不是目录能力，而是独立的 `WATCHLIST_PROVIDER` 插件，用于产生用户关注条目。定时调度、同步游标、重试和持久状态由 Core 管理。一个豆瓣外部仓库可以同时交付 `douban-catalog` 和 `douban-watchlist` 两个插件实例，但二者必须能够独立配置、启停、测试和报错。

媒体发现数据采用 A+ 持久化策略：PostgreSQL 永久保存规范媒体身份、外部 ID、最小展示快照和用户产生的关注/想看状态；简介、演员、类型、各平台评分、完整图片信息、搜索结果、热门和分类列表只作为可过期缓存。缓存清空不得删除媒体身份或用户状态，外部 Provider 失败时使用最后可用最小快照明确降级。MVP 不下载或永久保存海报二进制文件。

媒体发现采用统一产品模块而不是多个顶级页面：`/app/discover` 承载目录搜索、筛选、热门、分类、关注入口和海报墙，`/app/discover/:media_subject_id` 展示详情。`/app/search` 保持为具体资源链接搜索入口，不与目录搜索混用。

发现首页默认是分区内容流：顶部目录搜索和快捷筛选，下方展示热门电影、热门剧集、分类推荐和关注更新。用户提交搜索或筛选后，主体切换为统一海报网格；状态写入 URL query，保证刷新、返回和分享 URL 时可以恢复。

媒体发现 MVP 的基础筛选固定为：媒体类型（全部 / 电影 / 剧集）、题材、地区、年份或年份范围、排序（热度 / 评分 / 上映时间）。语言、评分区间、演员、导演、目录平台来源和复杂布尔组合属于后续高级筛选，不进入当前 MVP。题材与地区采用单选还是简单多选仍待确认。

搜索结果默认不入库。用户主动收藏资源或收藏某条具体链接时，才写入资源收藏库。

收藏库不是 `/search` 的替代数据源。用户点击搜索时，系统始终实时调用 Source Adapter，并在返回结果中标记哪些资源或链接已收藏。

媒体源近期主线：

```text
真实网站 Source Adapter 框架
每个真实网站通过一个 Adapter 接入
多个 Adapter 并发搜索
结果统一进入 Search Pipeline
搜索源统一由 Adapter 代码定义，不由用户在 Web Console 创建配置型源
```

Source Adapter 必须通过代码实现和部署，不允许在 Web Console 中在线编辑 Python 代码。

当前已开始接入真实搜索源，首个实现为 `SeedHubSource`。

Phase 0-7 已覆盖：

```text
Source Adapter 抽象
外部 Source Adapter 注册框架和首个 SeedHub 插件验收
Search Pipeline
sources 管理 API
Web Console Sources 页面
```

Phase 0-7 未覆盖：

```text
真实站点爬虫
真实网站 Adapter SDK 完整开发体验
多个真实网站 Adapter 并发搜索验收
站点分页和反爬策略
通过 Web Console 配置复杂爬虫
真实媒体源手动验收
```

真实媒体源开发属于后续独立大阶段，不作为 Phase 0-7 或 Phase 8 Download To Local 的阻塞项。

后续可单独实验：

```text
文档型网站是否存在可通用读取模式
文档型网站是否值得抽象为专用 Adapter 模板
```

该实验不等于承诺实现通用在线文档读取，也不要求用户维护本地文档。

---

## 7. SMB 范围

MVP 不依赖系统 SMB mount。

正式 NAS 写入方式：

```text
应用内 SmbWriter
```

测试和开发方式：

```text
LocalWriter
```

SMB 配置支持多个连接，并可在 Web Console 修改和热加载。

修改某个 SMB 连接配置时：

```text
关闭旧 SMB 连接
中断使用旧配置的运行中任务
任务进入 failed
错误码 STORAGE_CONFIG_CHANGED
retryable = true
保留 .downloading 文件
保留 cloud staging
使用该连接的新任务和重试任务使用最新 SMB 配置
```

媒体库管理模块只能引用已配置的 SMB 连接和目录，不重复填写 SMB host、share、username、password。

媒体库在 Sundarr 中指本地 NAS 上的逻辑媒体目录，例如 movie、series、unclassified。MVP 需要提供媒体库管理模块，用于创建媒体库并绑定到某个 SMB 连接下的本地目录。

同步模块不直接重复配置目标 SMB 目录，而是通过同步绑定连接远程媒体库（来源）和本地媒体库（目标）。Worker 定时扫描这些绑定，并将稳定文件同步到绑定的本地媒体库目录。

媒体库管理是目录绑定管理能力，不等于完整本地媒体库 UI、播放器、观影进度或本地媒体库刮削。媒体发现中心的海报墙属于资源发现界面，不展示本地入库状态或提供播放能力。

---

## 8. MVP 不做事项

MVP 不做：

```text
BT / 磁力 / 种子下载
盗版资源分发或资源托管
绕过网盘限制、破解会员、绕过验证码
复杂 Web UI
完整本地媒体库 UI
多用户权限系统
本地媒体库刮削
本地媒体库海报墙
播放器和观影进度
NFO 生成
Playwright 重型抓取
OpenList 核心搬运层
rclone 核心传输层
多 provider 一次性全量接入
国内封闭网盘直接下载作为 MVP 核心搬运层
将网盘直链下载（Cloud Direct Download）纳入 MVP 或近期主线
绕过网盘 App、验证码、会员或风控限制
真实媒体源通用爬虫框架
通过 Web Console 配置复杂网站爬虫
要求用户维护本地文档/表格作为主要媒体源
```

---

## 9. 后续扩展

MVP 稳定后可考虑：

```text
完整 Web UI
AI Agent 深度集成
更多目录和元数据提供方
NFO 生成
订阅搜索
多 NAS 目标
多云盘 provider
Sundarr 内配置挂载网盘
保存到网盘
网盘直链下载（Cloud Direct Download，高级功能）
AI / 外部数据辅助自动分类
rclone driver
OpenList 可选后端
Prometheus metrics
OpenTelemetry tracing
```

---

## 10. 插件运行时与 Cordis 边界

已确认：

```text
Sundarr Core 保持 Python + FastAPI，不迁移到 Cordis / Node.js。
当前 Source Adapter 继续使用 Python 运行时协议。
插件系统借鉴 Cordis 的显式能力依赖、Activation、可逆副作用清理、候选加载和原子切换语义。
Cordis 启发的生命周期层不替代 PostgreSQL 任务事实来源、Alembic 迁移、Redis、SMB 连接池或 Worker 状态机。
Phase 11 AI Friendly API 稳定后，可提供可选 Cordis / DeepSeek Harness 桥接插件。
桥接插件只调用公开 Sundarr API，不直接访问数据库、SMB 凭据、NAS 文件或 Worker 内部对象。
```

当前阶段不做：

```text
使用 Cordis 重写 Sundarr 后端。
把 React Web Console 改造成 Cordis UI 插件树。
同时维护 Python 和 TypeScript 两套 Source Adapter SDK。
把 Cordis 当作外部插件代码沙箱；外部插件仍属于用户显式信任代码。
```
