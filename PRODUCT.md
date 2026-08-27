# Sundarr Product Context

## Register

product

## Product Purpose

Sundarr 是为 Homelab 打造的媒体发现与远程媒体库同步工具。它帮助个人 NAS 用户发现媒体资源，并把已保存到网盘、通过 SMB 暴露出来的远程媒体库内容同步到本地 NAS 媒体库目录。

核心闭环：

```text
搜索合法资源
-> 提取网盘链接
-> 用户手动保存到网盘
-> 网盘通过 SMB 暴露为远程媒体库
-> 将远程媒体库同步到本地媒体库
-> 校验文件
-> 删除来源文件和空目录
```

## Primary Users

- 个人 NAS / Homelab 用户。
- 熟悉 SMB、Docker、目录绑定和后台任务的自托管用户。
- 希望用 Web Console 管理搜索、远程媒体库、本地媒体库、同步任务和 SMB 连接的人。

## Core Jobs

- 聚合多个媒体源的搜索结果。
- 提供带筛选、热门、分类、详情、关注列表和海报展示的媒体发现中心；该能力已进入当前 MVP。
- 管理已安装 Source Adapter 的启用、禁用、参数、测试和错误状态。
- 管理多个 SMB 连接，并通过后端测试连接和目录访问。
- 创建本地媒体库，例如 movie / series / unclassified。
- 创建远程媒体库，绑定 SMB 连接下的远程目录（如网盘挂载目录）。
- 通过同步绑定连接远程媒体库（来源）和本地媒体库（目标）。
- Worker 定时扫描同步绑定，将稳定文件写入 `.downloading`，校验后 rename。
- 同步成功后按配置删除来源文件和空目录。
- 跟踪任务状态、日志、失败原因，并支持取消、暂停、恢复和重试。

## MVP Boundary

MVP 必须跑通“媒体发现”和“远程媒体库同步到本地媒体库”两条核心闭环。MVP 包含媒体发现中心、FastAPI 后端、React + Vite Web Console、PostgreSQL、Redis、Source Adapter 框架、Resource Library、应用内 SmbWriter、Transfer Worker、任务控制和状态页。

MVP 不做：

- BT / 磁力 / 种子下载。
- 盗版资源分发或资源托管。
- 绕过网盘限制、破解会员、绕过验证码或风控。
- 登录注册、多用户权限、角色管理、OAuth。
- 完整本地媒体库 UI、本地媒体库海报墙、播放器、观影进度、本地媒体库刮削和 NFO 生成。
- 完整 NAS 文件管理器或任意文件删除。
- Web Console 在线编辑代码型 Source Adapter。
- 真实媒体源通用爬虫框架。
- 网盘直链下载（Cloud Direct Download）作为 MVP 或近期主线。

## Strategic Decisions

- FastAPI 只作为 API 后端，不做 Jinja2 页面渲染。
- React + Vite 是轻量 Web Console，不是完整媒体库产品界面。
- PostgreSQL 是任务、资源和配置事实来源；Redis 只做缓存和实时进度辅助。
- SMB 配置支持多个连接，远程媒体库和本地媒体库只能引用已配置 SMB 连接和目录，不重复填写 SMB 凭据。
- 修改 SMB 配置会中断使用旧配置的运行中任务，任务进入 failed，错误码为 `STORAGE_CONFIG_CHANGED`，`retryable=true`。
- `Phase 8 “下载到本地”` 是历史阶段命名；当前规范统一为“远程媒体库同步到本地媒体库”。
- `Phase 9 Module Refactoring` 和 `Phase 9.5 Resource Favorites Refactoring` 已完成。
- `Phase 10.0 Quality Baseline Closure` 已完成；当前优先任务是媒体发现中心。Phase 10.1 恢复目录和想看插件所需的最小运行时，完整插件生命周期闭环后续完成。
- Sundarr Core 保持 Python + FastAPI；只借鉴 Cordis 的显式依赖、Activation、可逆清理和原子切换语义，不引入 Cordis 作为核心运行时。
- `Phase 11 AI Friendly API` 完成后可提供可选 Cordis / DeepSeek Harness 桥接插件，桥接层只通过 HTTP API 调用 Sundarr。
- `Phase 12 Cloud Direct Download` 不包含在 MVP 中，仅作为后续高级功能保留规格文档。
- 媒体发现中心属于当前 MVP，但不等于本地媒体库 UI。
- 规范媒体实体使用 Sundarr 内部 UUID，并可绑定多个外部平台 ID；不使用单一目录平台 ID 作为主键。
- 媒体发现中心以 TMDb 作为 MVP 主目录数据提供方，豆瓣目录作为可选补充；两者均通过 `CATALOG_PROVIDER` 插件接入。
- 豆瓣想看通过独立 `WATCHLIST_PROVIDER` 插件接入，由 Core 调度，不能成为发现中心可用性的单点依赖。
- 媒体发现采用 A+ 数据策略：PostgreSQL 保存规范身份、外部 ID、最小展示快照和用户状态；易变目录详情、榜单和搜索结果只作为可过期缓存。
- Web Console 使用统一 `/app/discover` 模块承载目录发现，详情使用 `/app/discover/:media_subject_id`；`/app/search` 保留为具体资源链接搜索。

## Product Tone

- 面向开发者和自托管用户，直接、清楚、少废话。
- 优先说明当前状态、下一步动作和可恢复路径。
- 错误提示不道歉，说明发生了什么、影响是什么、用户下一步怎么做。
- 面向人类阅读的项目文本默认使用简体中文；标准协议字段、错误码和 API 名称保留英文。

## Brand Personality

- 温暖但克制。
- 工具感强，可信，适合长时间盯任务。
- Homelab 操作台，不是营销 SaaS。
- 属于 Servarr 家族语境，但不复制 Radarr / Sonarr 的 Bootstrap 视觉。

## Anti-References

- 冷蓝灰企业后台。
- 大面积玻璃拟态、炫光渐变、AI slop 卡片网格。
- 本地媒体库克隆、播放器导向界面，或缺乏信息层级的花哨海报墙。
- 过度营销化的 hero-metric 页面。
- 假装全自动、绕过网盘限制或淡化合规边界的文案。

## Source Documents

- `docs/01-product-scope.md`
- `docs/02-architecture-decisions.md`
- `docs/03-mvp-roadmap.md`
- `docs/13-web-console-spec.md`
- `docs/15-download-to-local-spec.md`
- `docs/16-design-system.md`
- `docs/17-system-module-review.md`
- `docs/18-cloud-direct-download-spec.md`
