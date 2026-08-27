# 下一步执行清单

更新时间：2026-08-27。完整路线见 `docs/24-implementation-roadmap.md`。

## 当前目标

完成 Phase 10.1 媒体发现中心的设计和最小 MVP 闭环，并恢复目录和想看插件所需的最小加载、注册和健康检查。完整插件热更新与原子切换后续收口。

## 当前决策顺序

```text
1. 已确认媒体身份使用内部 UUID + 多个外部平台 ID
2. 已确认 TMDb 与豆瓣目录使用 CATALOG_PROVIDER，豆瓣想看使用 WATCHLIST_PROVIDER
3. 已确认 A+：核心身份和最小快照持久化，易变目录详情缓存
4. 已确认 /app/discover 统一入口和 /app/search 资源搜索边界
5. 已确认默认内容流、搜索后海报网格和 URL 状态恢复
6. 已确认媒体类型、题材、地区、年份范围和基础排序
7. 当前确认题材/地区选择方式、分页方式和详情信息层级
8. MediaSubject、ResourceOffer、Artifact 与任务的关系
9. 最小 API 和 Web Console 验收范围
```

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
提供筛选、热门、分类、详情、关注列表和发现型海报墙。
不做本地媒体库海报墙。
不做播放器和观影进度。
不做完整本地媒体管理。
```

## 暂停点

```text
PluginContext、PluginActivation、ActivationStatus 已实现。
LIFO cleanup、失败续跑和并发幂等释放已测试。
manifest requires/provides、Source 注册、健康检查、原子切换和启动加载待恢复。
```

## 环境限制

```text
当前运行时没有配置外部插件仓库，因此搜索源为 0。
当前 Windows 主机没有 Docker，Compose 运行验收需要其他 Docker 环境。
真实 SMB 完整搬运需要专用测试目录和用户已有测试环境。
```
