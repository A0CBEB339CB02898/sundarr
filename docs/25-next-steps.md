# 下一步执行清单

更新时间：2026-08-27。完整路线见 `docs/24-implementation-roadmap.md`。

## 当前目标

完成 Phase 10.1 媒体发现中心的设计和最小 MVP 闭环，并恢复目录和想看插件所需的最小加载、注册和健康检查。完整插件热更新与原子切换后续收口。

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

## 下一交付单元

```text
1. 收口 MediaSubject 与现有 Resource / ResourceLink 的最小关联，不提前引入 ResourceOffer / Artifact。
2. 一次性定义 CATALOG_PROVIDER / WATCHLIST_PROVIDER 的 Core 方法合同、能力描述和 Mock。
3. 实现 PluginType 与通用 Manifest v2 解析，保持 flat v1 SOURCE 测试兼容。
4. 完成 Phase 10.1 最小 API、Web Console 和测试闭环。
```

以上属于一个实现包，不再把分页、默认页大小或单个详情字段拆成逐项产品提问；只有发生产品范围、持久化边界或任务状态机变化时再请求确认。

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
通用 Manifest v2 多声明解析、requires/provides、类型专用注册、健康检查、原子切换和启动加载待实现。
```

## 环境限制

```text
当前运行时没有配置外部插件仓库，因此搜索源为 0。
当前 Windows 主机没有 Docker，Compose 运行验收需要其他 Docker 环境。
真实 SMB 完整搬运需要专用测试目录和用户已有测试环境。
```
