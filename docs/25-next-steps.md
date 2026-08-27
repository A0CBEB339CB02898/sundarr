# 下一步执行清单

更新时间：2026-08-28。完整路线见 `docs/24-implementation-roadmap.md`。

## 当前目标

完成 Phase 10.1 通用插件框架收口并做第一次技术验收。媒体发现 Core 后移到 Phase 10.2；TMDb、SeedHub、豆瓣等真实插件统一在独立官方仓库于 Phase 10.3 逐个交付。

## 已完成的架构收口

```text
1. 已确认媒体身份使用内部 UUID + 多个外部平台 ID
2. 已确认 TMDb 与豆瓣目录使用 CATALOG_PROVIDER，豆瓣想看使用 WATCHLIST_PROVIDER
3. 已确认 A+：核心身份和最小快照持久化，易变目录详情缓存
4. 已确认 /app/discover 统一入口和 /app/search 资源搜索边界
5. 已确认默认内容流、搜索后海报网格和 URL 状态恢复
6. 已确认媒体类型、题材、地区、年份范围和基础排序
7. 已确认题材/地区 UI 单选、Core 列表结构
8. 已确认分页交互不进入 Manifest，Provider 使用不透明 continuation token
9. 已确认插件类型按稳定业务合同划分，不是强制任务流水线
10. 已确认通用 Manifest v2、同仓库多插件和 flat v1 SOURCE 兼容边界
```

## 当前交付顺序

```text
1. 已实现 PluginType、Manifest v2 多声明解析和 flat v1 SOURCE 兼容。
2. 已定义 SOURCE、CATALOG_PROVIDER、WATCHLIST_PROVIDER 公共协议和类型专用 Runtime Registry。
3. 已接入 v2 单 Manifest Activation、requires/provides 隔离与校验、配置校验和健康检查。
4. 下一步完成仓库内多候选编排、原子切换和失败保留旧版本，再处理启动恢复和多仓库 API。
5. 使用本地 fixture 仓库完成框架初步验收后暂停。
6. 验收通过后再实现 MediaSubject、发现 API/Web Console 和测试 Mock。
7. 最后迁移官方外部仓库并逐个实现真实插件。
```

当前不并行实现媒体发现 UI 或真实插件，避免业务实现反向固化不完整的插件框架。

## 官方外部插件仓库

```text
当前迁移起点：https://github.com/A0CBEB339CB02898/sundarr-sources.git
默认分支：master
当前事实：公开仓库存在，但仍是 SOURCE-only / flat v1 历史布局。
目标：迁移为 Manifest v2 多类型官方插件仓库，集中维护 TMDb、SeedHub、豆瓣目录和豆瓣想看。
未确认：是否把仓库改名为 sundarr-plugins；未确认前不创建新地址、不重命名、不 push。
```

Core 仍支持多个 `PluginRepository`，因此官方插件集中仓库不会阻止用户加载其他可信第三方仓库。

## 已确认边界

```text
媒体发现中心属于当前 MVP。
TMDb 负责 MVP 的目录、搜索、筛选、热门、分类、详情和海报。
豆瓣目录作为可选补充 CATALOG_PROVIDER，失败不得阻断媒体发现中心。
豆瓣想看是独立 WATCHLIST_PROVIDER，由 Core 调度。
PostgreSQL 保存 MediaSubject 身份、外部 ID、最小展示快照和用户状态。
Redis 缓存详情、评分、图片信息、搜索、热门和分类；缓存清空不得丢失用户状态。
/app/discover 统一承载目录搜索、筛选、热门、分类、关注入口和海报墙。
/app/discover/:media_subject_id 展示媒体详情；/app/search 专门搜索具体资源链接。
/app/discover 默认显示热门电影、热门剧集、分类推荐和关注更新；搜索或筛选后显示海报网格并保留 URL 状态。
MVP 筛选只包含媒体类型、题材、地区、年份范围和热度/评分/上映时间排序。
题材和地区在界面中均为单选，Core 预留列表结构。
提供筛选、热门、分类、详情、关注列表和发现型海报墙。
不做本地媒体库海报墙。
不做播放器和观影进度。
不做完整本地媒体管理。
发现、外部想看、资源搜索和搬运是独立业务流；只有明确传输意图才创建 TransferTask。
当前 SMB 同步由 Core 内置状态机和 SmbWriter 执行，不是外部插件。
未来统一搬运扩展点是 TRANSFER_DRIVER，但不进入当前 MVP。
Manifest v2 只保存静态插件声明，不保存 UI 分页、调度游标或任务状态。
```

## 暂停点

```text
PluginContext、PluginActivation、ActivationStatus 已实现。
LIFO cleanup、失败续跑和并发幂等释放已测试。
通用 Manifest v2 多声明解析、三类公共运行协议、Runtime Registry、单 Manifest v2 入口 Activation、声明能力隔离、配置校验、类型健康检查和失败 cleanup 已实现；仓库级多候选原子切换、启动加载和管理 API 接入待实现。
完成上述缺口并通过本地三类型 fixture 仓库、重启恢复、失败保留旧版本和插件 API/Worker 冒烟后，立即暂停做第一次技术验收。
```

## 环境限制

```text
当前运行时没有配置外部插件仓库，因此搜索源为 0。
当前 Windows 主机没有 Docker，Compose 运行验收需要其他 Docker 环境。
真实 SMB 完整搬运需要专用测试目录和用户已有测试环境。
```
