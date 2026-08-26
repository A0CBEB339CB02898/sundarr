# Sundarr 当前实施路线

本文档把 `docs/03-mvp-roadmap.md` 的阶段计划转换为当前可执行交付顺序。更新时间：2026-08-27。

---

## 路线原则

```text
保持 Python + FastAPI Core，不切换到 Cordis / Node.js 后端。
可信质量基线已经恢复。
当前先完成媒体发现中心，再恢复 SOURCE 插件闭环。
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

## 里程碑 B：Phase 10.1 媒体发现中心

状态：当前优先，处于逐项设计阶段。

任务：

```text
B1 已确认媒体身份使用内部 UUID，并绑定多个外部平台 ID。
B2 已确认 TMDb 和豆瓣目录使用 CATALOG_PROVIDER，豆瓣想看使用独立 WATCHLIST_PROVIDER，调度由 Core 管理。
B3 已确认 A+ 持久化：核心身份、最小快照和用户状态入 PostgreSQL，易变目录详情和列表入 Redis。
B4 当前确认发现页面信息架构、筛选项和详情入口。
B5 确认 MediaSubject、ResourceOffer、Artifact 与任务的关联。
B6 实现最小 API、Web Console 和测试闭环。
B7 在 Phase 10.1 恢复目录和想看插件所需的最小加载、注册和健康检查能力。
```

验收门：

```text
用户可以浏览热门和分类资源。
用户可以按确认的条件筛选并查看媒体详情。
用户可以从媒体条目查找候选资源。
关注列表入口按确认的数据来源工作。
页面不是本地媒体库 UI，不提供播放和观影进度。
```

---

## 里程碑 C：Phase 10.2 Python Plugin Activation Runtime Completion

状态：生命周期内核已完成；剩余工作在 B 最小闭环后恢复。

任务：

```text
C1 已定义 PluginContext、PluginActivation、ActivationStatus。
C2 manifest 增加可选 requires / provides。
C3 已实现通用 cleanup callback、LIFO、失败续跑和并发幂等释放。
C4 接入 Source 注册动作、候选配置校验和健康测试。
C5 实现原子替换、失败保留旧 Activation 和确定清理语义。
C6 启动时加载 enabled 仓库的 locked current_commit。
```

验收门：

```text
单插件失败不影响 API 和其他插件。
更新失败时旧 Source 仍可搜索。
禁用或删除后 cleanup 只执行一次。
重启后锁定 commit 自动恢复。
```

---

## 里程碑 D：Phase 10.3 外部搜索源端到端

状态：C 完成后执行。

任务：

```text
D1 配置 sundarr-sources 仓库和锁定 commit。
D2 补齐 SeedHub 外部 Adapter fixture 和离线测试。
D3 修复单仓库多 Source 的新增、更新、回滚和 API 响应。
D4 Web Console 增加仓库管理和诊断。
D5 执行显式实时 SeedHub 手动集成验收。
```

验收门：

```text
全新数据库可以通过 API 或 Web Console 配置一个可信仓库。
重启后至少一个 Source 自动加载。
/sources 显示来源 commit 和状态。
/search 可以聚合外部 Source 结果。
源失败、更新失败和回滚路径均可诊断。
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
完整本地媒体库 UI、本地媒体库海报墙、播放器和观影进度
```
