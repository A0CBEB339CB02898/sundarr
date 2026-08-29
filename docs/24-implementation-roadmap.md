# Sundarr 当前实施路线

本文档把 `docs/03-mvp-roadmap.md` 的阶段计划转换为当前可执行交付顺序。更新时间：2026-08-28。

---

## 路线原则

```text
保持 Python + FastAPI Core，不切换到 Cordis / Node.js 后端。
可信质量基线已经恢复。
当前先完成通用插件框架，再做媒体发现 Core，最后在独立官方仓库逐个交付真实插件。
先自动化和本地替身验收，再执行真实 SMB / 真实站点手动验收。
Phase 11 API 稳定后才开发可选 Cordis / DeepSeek Harness 桥接。
Cloud Direct Download、Alist 和真实网盘 Provider 不属于 MVP 或近期主线。
```

---

## 里程碑 A：Phase 10.0 质量基线收口

状态：已完成。

任务：

```text
A1 已将实时搜索 API 检查移出 pytest 默认收集。
A2 已配置异步 SMB 连接池测试执行方式。
A3 已透传 SmbStorageError 具体错误码。
A4 已对齐 CLI PID 测试和真实服务进程语义。
A5 已验证插件迁移 down_revision 链。
A6 已完成 Alembic 图、启动、健康检查和停止冒烟。
```

验收门：

```text
python -m pytest 全部通过。
npm run build 通过。
alembic heads/current/upgrade head 通过。
sundarr start / status / stop 连续两轮通过。
PID 文件、端口和子进程均无残留。
```

---

## 里程碑 B：Phase 10.1 通用插件框架收口

状态：当前优先；Manifest v2 解析和生命周期内核已完成。B5-B9 作为同一验收批次执行，完成仓库切换、进程恢复、管理闭环和本地 fixture 验收后再暂停。

任务：

```text
B1 已定义 PluginContext、PluginActivation、ActivationStatus 和幂等 LIFO cleanup。
B2 已实现目标 PluginType、通用 Manifest v2 多插件解析和 flat v1 SOURCE 兼容。
B3 已实现 SOURCE、CATALOG_PROVIDER、WATCHLIST_PROVIDER 类型合同与 Runtime Registry。
B4 已实现 v2 单 Manifest 入口调用、requires/provides 隔离与校验、配置校验和类型专用健康检查。
B5 已实现候选加载、仓库级原子切换、失败保留旧 Activation 和确定清理语义。
B6 API 与 Worker 启动时分别恢复 enabled 仓库的 locked current_commit。
B7 修复 PluginManager 和 API 对同仓库多插件结果的完整支持。
B8 使用本地 fixture 仓库完成三类插件调用、禁用、更新、回滚、重启和失败诊断。
B9 确认敏感配置和日志脱敏，不依赖真实网络、GitHub、TMDb、豆瓣或 NAS。
```

验收门：

```text
三类 MVP 插件均可从本地 v2 fixture 仓库激活、调用和释放。
候选失败时旧版本继续服务，current_commit 不切换。
API 与 Worker 重启只恢复已启用的锁定版本。
单插件失败不影响其他插件和 /health。
pytest、插件 API 和 Worker 冒烟通过。
```

达到该验收门即可暂停，进行第一次插件框架技术验收。

---

## 里程碑 C：Phase 10.2 媒体发现 Core 与 Mock 垂直切片

状态：B 验收后执行；产品边界已确认，尚未实现。

任务：

```text
C1 实现 MediaSubject、外部 ID、最小快照和关注状态数据模型。
C2 实现 CATALOG_PROVIDER / WATCHLIST_PROVIDER Core 查询和同步服务。
C3 使用测试 Mock 覆盖搜索、热门、分类、详情、想看和降级，不发布生产 Mock 插件。
C4 实现 `/app/discover` API、详情 API 和基础筛选。
C5 实现 Web Console 内容流、海报网格、详情和资源搜索跳转。
C6 验证 PostgreSQL/Redis 分层、Provider 失败隔离和 URL 状态恢复。
```

验收门：

```text
不连接真实 TMDb 或豆瓣即可完成发现中心产品垂直切片验收。
Mock 不进入生产插件目录或官方外部仓库发布物。
缓存清空不丢失媒体身份和用户状态。
前后端回归、构建和页面冒烟通过。
```

---

## 里程碑 D：Phase 10.3 官方外部插件仓库与真实插件

状态：B/C 完成后执行。

任务：

```text
D1 以当前 `sundarr-sources` master 作为迁移起点，升级为通用 Manifest v2 官方插件仓库；改名需用户另行确认。
D2 首先实现 TMDb CATALOG_PROVIDER，完成媒体发现真实主目录验收。
D3 实现 SeedHub SOURCE，恢复具体资源链接搜索。
D4 实现豆瓣 CATALOG_PROVIDER 作为可选补充。
D5 实现豆瓣 WATCHLIST_PROVIDER，并由 Core 调度持久游标。
D6 每个真实插件独立配置、启停、fixture、健康检查、错误和显式实时验收。
D7 Web Console 增加多仓库管理、检查更新、应用、回滚和诊断。
```

验收门：

```text
Core 仓库不包含 TMDb、豆瓣、SeedHub 平台实现或平台 fixture。
官方仓库可从锁定 commit 加载全部已启用插件。
每个插件失败不阻断其他插件，仓库更新失败保留旧版本。
TMDb 支持发现中心真实主目录，SeedHub 支持资源搜索，豆瓣能力可独立降级。
系统继续允许添加其他可信第三方插件仓库。
```

---

## 里程碑 E：真实 SMB 同步发布门

状态：D 前后均可准备，但必须在 MVP 发布前完成。

任务：

```text
E1 使用专用测试目录完成 SMB source -> SMB target。
E2 验证 .downloading、size、rename 和目录结构。
E3 验证断线重试、错误码、目标冲突和重复扫描。
E4 验证成功后删除源文件/空目录和失败时保留源文件。
E5 记录手动验收结果，不把真实凭据写入仓库。
```

---

## 里程碑 F：Phase 11 AI Friendly API

状态：A-E 稳定后执行。

任务：

```text
F1 固化 search_media / favorite / transfer / status 工具契约。
F2 增加 user_action_required、候选解释和幂等规则。
F3 发布 OpenAPI/tool schema 和调用示例。
F4 开发可选 Cordis / DeepSeek Harness 桥接插件。
```

Cordis 桥接边界：

```text
桥接插件运行在外部 Agent 宿主。
只调用 Sundarr HTTP API。
不加载 Sundarr Python Source 插件。
不访问数据库、SMB、NAS 或 Worker 私有状态。
```

---

## 暂不排期

```text
Cloud Direct Download
Alist 集成
真实网盘 CloudProviderPlugin
通知渠道插件
TRANSFER_DRIVER 及 qBittorrent 等下载客户端接入
完整本地媒体库 UI、本地媒体库海报墙、播放器和观影进度
```
