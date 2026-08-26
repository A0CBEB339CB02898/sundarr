# Sundarr 当前实施路线

本文档把 `docs/03-mvp-roadmap.md` 的阶段计划转换为当前可执行交付顺序。更新时间：2026-08-26。

---

## 路线原则

```text
保持 Python + FastAPI Core，不切换到 Cordis / Node.js 后端。
先恢复可信质量基线，再扩展插件功能。
先完成 SOURCE 插件闭环，不提前实现 Cloud Provider、通知或爬虫插件。
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

## 里程碑 B：Phase 10.1 Python Plugin Activation Runtime

状态：当前执行；B1 和 B3 的生命周期内核已完成。

任务：

```text
B1 已定义 PluginContext、PluginActivation、ActivationStatus。
B2 manifest 增加可选 requires / provides，未知能力加载失败但不影响 API。
B3 已实现通用 cleanup callback、同步/异步 LIFO、失败续跑和并发幂等释放；Source 注册动作待接入。
B4 新 commit 先创建候选 Activation 并运行配置校验和健康测试。
B5 候选成功后原子替换；失败时旧 Activation 保持 active。
B6 disable / rollback / remove_repository 释放旧 Activation。
B7 应用启动时读取数据库，只加载 enabled 仓库的 current_commit。
B8 插件加载完成后同步 sources 目录表。
```

验收门：

```text
单插件加载失败不影响 API 和其他插件。
依赖缺失插件处于 waiting/error，不执行 apply。
更新失败时旧 Source 仍可搜索。
禁用或删除后 Source 从运行时注册中心消失且 cleanup 只执行一次。
重启后锁定 commit 自动恢复，不自动执行远程最新 commit。
```

---

## 里程碑 C：Phase 10.2 外部搜索源端到端

状态：B 完成后执行。

任务：

```text
C1 配置 sundarr-sources 仓库和锁定 commit。
C2 补齐 SeedHub 外部 Adapter fixture 和离线测试。
C3 修复单仓库多 Source 的新增、更新、回滚和 API 响应。
C4 Web Console 增加仓库列表、新增、检查更新、应用、回滚和诊断。
C5 Web Console 保留已安装 Adapter 启用、禁用、配置、测试和错误查看。
C6 执行一次显式实时 SeedHub 手动集成验收。
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

## 里程碑 D：真实 SMB 同步发布门

状态：C 前后均可准备，但必须在 MVP 发布前完成。

任务：

```text
D1 使用专用测试目录完成 SMB source -> SMB target。
D2 验证 .downloading、size、rename 和目录结构。
D3 验证断线重试、错误码、目标冲突和重复扫描。
D4 验证成功后删除源文件/空目录和失败时保留源文件。
D5 记录手动验收结果，不把真实凭据写入仓库。
```

---

## 里程碑 E：Phase 11 AI Friendly API

状态：A-D 稳定后执行。

任务：

```text
E1 固化 search_media / favorite / transfer / status 工具契约。
E2 增加 user_action_required、候选解释和幂等规则。
E3 发布 OpenAPI/tool schema 和调用示例。
E4 开发可选 Cordis / DeepSeek Harness 桥接插件。
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
豆瓣监控
完整媒体库 UI、海报墙和播放器
```
