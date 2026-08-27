# Sundarr MVP 架构总览

本文件保留为高层架构入口，不再复制编号规格全文。详细事实来源见 `Sundarr_documentation_plan.md`。

更新时间：2026-08-26。

## 产品目标

```text
实时调用外部 Source Adapter 搜索资源。
用户手动保存分享内容到已挂载的远程媒体库。
Sundarr 通过 SMB 扫描远程媒体库并同步到本地媒体库。
Worker 完成 .downloading、校验、rename、失败恢复和可选来源清理。
Web Console 管理搜索、收藏、SMB、媒体库、远程媒体库、任务和系统状态。
```

## 技术架构

```text
Backend：Python 3.12+、FastAPI、SQLAlchemy、Alembic
Frontend：React、Vite、TypeScript
Database：PostgreSQL
Cache / realtime helper：Redis
Storage：应用内 SmbWriter + LocalWriter 测试替身
Worker：Python 独立进程，PostgreSQL 任务为事实来源
Source：外部可信 Git Python 插件仓库
```

## 核心数据流

```text
PluginRepository.current_commit
  -> Python Plugin Activation
  -> Source Registry
  -> SearchService
  -> ResourceCandidate / ResourceLinkResult
  -> user favorite only

RemoteMediaLibrary
  -> SyncBinding
  -> scan / SyncSeenFile
  -> TransferTask
  -> Worker
  -> SMB source -> .downloading -> verify -> rename -> optional cleanup
```

## 插件运行时决策

```text
不使用 Cordis 重写 Sundarr Core。
在 Python 中实现 PluginContext、requires/provides、PluginActivation 和 LIFO cleanup。
更新使用候选加载、健康检查、原子切换和失败保留旧 Activation。
Activation 不替代数据库事务、Worker 状态或 SMB 连接池。
外部 Python 插件是用户信任代码，不是沙箱代码。
```

## AI 集成

Phase 11 提供稳定 AI Tool API。之后可以开发独立 Cordis / DeepSeek Harness 桥接插件，该插件只通过 HTTP 调用 Sundarr，不接触数据库、SMB 或 Worker 私有状态。

## 阶段状态

```text
Phase 0-9.5：已完成。
Phase 10.0：已完成，质量基线已恢复。
Phase 10.1：当前优先，媒体发现中心。
Phase 10.2：恢复并完成 Python Plugin Activation Runtime。
Phase 10.3：外部 Source 和 Web Console 仓库管理闭环。
Phase 11：AI Friendly API。
Phase 12：Cloud Direct Download，非 MVP、非近期主线。
```

媒体发现中心使用内部 UUID 的 `MediaSubject` 作为规范媒体身份，并可绑定多个外部平台 ID；不以任何单一目录平台 ID 作为主键。

媒体发现中心 MVP 以 TMDb 作为主 `CATALOG_PROVIDER`，豆瓣目录作为可选补充 `CATALOG_PROVIDER`；豆瓣想看使用独立 `WATCHLIST_PROVIDER` 并由 Core 调度。豆瓣能力失败不得阻断目录浏览和搜索。

媒体发现采用 A+ 数据策略：PostgreSQL 保存 `MediaSubject` 规范身份、外部 ID、最小展示快照和用户状态；Redis 缓存可重建的目录详情、评分、图片信息和发现列表。缓存丢失不得造成身份或用户状态丢失。

Web Console 使用 `/app/discover` 作为统一媒体发现入口，`/app/discover/:media_subject_id` 作为详情页；`/app/search` 继续承担具体资源链接搜索。

## 不做事项

```text
登录注册和多用户权限
BT / 磁力 / 种子下载
绕过网盘限制、验证码、会员或风控
完整本地媒体库 UI、本地媒体库海报墙、播放器和观影进度
在线编辑或保存可执行 Python 插件代码
Alist、真实网盘 Provider 和 Cloud Direct Download 近期实现
Cordis / Node.js 后端重写
```
