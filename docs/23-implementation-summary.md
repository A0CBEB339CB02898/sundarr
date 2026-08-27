# Sundarr 当前实施总结

本文档是当前实现状态的派生摘要。阶段事实来源以 `docs/03-mvp-roadmap.md` 为准，插件运行时事实来源以 `docs/20-plugin-system.md` 为准。

更新时间：2026-08-27。

---

## 1. 当前结论

```text
Phase 0-9.5 已完成。
Phase 10.0 质量基线收口已完成。
Phase 10.1 媒体发现中心当前优先、尚未实现。
Phase 10.1 将恢复目录和想看插件所需的最小加载、注册和健康检查；Phase 10.2 继续完成热更新、原子切换和失败回滚。
Phase 10.3 外部真实搜索源随后执行。
Phase 11 AI Friendly API 未开始。
Phase 12 Cloud Direct Download 非 MVP、非近期主线。
媒体发现中心已进入当前 MVP 并成为当前优先任务；当前尚未实现。
```

Sundarr 已具备 API、Web Console、Worker、PostgreSQL、Redis、SMB 多连接、本地/远程媒体库、同步绑定、任务状态机、搜索管线和收藏模块。Core 内已无真实站点 Adapter；搜索源统一从用户信任的外部 Python 插件仓库加载。

媒体发现中心的计划范围包括筛选、热门、分类、详情、关注列表和发现型海报墙。它不等于本地媒体库 UI，不包含播放、观影进度或完整本地媒体管理。

媒体身份已确认使用 Sundarr 内部 UUID 的 `MediaSubject`，并允许同时绑定多个外部平台 ID；具体表结构尚未实现。

媒体发现的数据来源与插件分类已确认：TMDb 是主 `CATALOG_PROVIDER`，豆瓣目录是可选补充 `CATALOG_PROVIDER`，豆瓣想看是独立 `WATCHLIST_PROVIDER`。同一豆瓣仓库可以交付两个独立插件实例；具体方法签名尚未设计，代码尚未实现。

媒体发现持久化边界已确认采用 A+：PostgreSQL 保存规范身份、外部 ID、最小展示快照和用户状态，Redis 保存可重建目录详情和列表缓存。该数据模型尚未实现。

媒体发现顶层信息架构已确认：`/app/discover` 是统一发现入口，`/app/discover/:media_subject_id` 是详情，现有 `/app/search` 保持为具体资源搜索。发现路由尚未实现。

发现首页交互已确认采用双模式：默认分区内容流，搜索/筛选后统一海报网格，状态进入 URL query。

基础筛选已确认：媒体类型、题材、地区、年份范围和热度/评分/上映时间排序。题材和地区在 MVP 界面均为单选，Core 使用列表查询结构。分页交互作为实现细节处理，不进入插件 Manifest。

通用插件分类已收口：当前 MVP 是 `SOURCE`、`CATALOG_PROVIDER`、`WATCHLIST_PROVIDER`，未来保留 `TRANSFER_DRIVER`、`NOTIFICATION`。插件类型不是所有任务必须经过的阶段；当前 SMB 同步仍由 Core 内置状态机和 SmbWriter 执行。Manifest v2 多插件解析和 flat v1 SOURCE 兼容已实现，v2 Activation 尚未实现。

---

## 2. 已实现能力

### 2.1 Core

```text
FastAPI API 与 OpenAPI 文档
React + Vite Web Console
PostgreSQL + SQLAlchemy + Alembic
Redis 健康检查和辅助能力
sundarr start / restart / stop / status
API / Web / Worker 三进程管理
```

### 2.2 远程媒体库同步

```text
多个 SMB 连接及连接测试、目录浏览
SMB 连接池、重试和错误恢复基础
本地媒体库和远程媒体库目录绑定
SyncBinding、扫描、稳定性判断和任务创建
.downloading、size 校验、rename、失败恢复
成功后按配置删除源文件和空目录
```

真实 SMB 环境的完整端到端同步仍属于发布前手动集成验收项。

### 2.3 搜索和收藏

```text
SourceModel / RawSearchItem / Search Pipeline
多源并行、失败隔离、标准化、去重、排序和链接检测
搜索结果默认不持久化
收藏资源和收藏资源链接
实时搜索结果附加收藏标记
Web Console 单一收藏入口
```

### 2.4 Python 插件框架

```text
PluginRepository / PluginConfig / PluginLog
PluginLoader / PluginManager / PluginRegistry
Git clone / fetch / checkout 基础能力
锁定 current_commit、更新和回滚 API
SOURCE 插件入口返回 SourceModel 或 list[SourceModel]
PluginContext / PluginActivation 生命周期内核
能力依赖、只读配置、状态流转和可逆 cleanup
SeedHub 已从 Core 移出
```

---

## 3. 尚未闭环的能力

```text
应用启动不会自动加载已配置插件仓库。
插件更新没有完整候选 Activation 和原子切换语义。
Web Console 没有插件仓库新增、更新、回滚和诊断页面。
当前环境未配置插件仓库，运行时搜索源为 0。
外部 SeedHub 尚未完成 Core 侧端到端验收。
CATALOG_PROVIDER / WATCHLIST_PROVIDER 已加入代码枚举和 v2 Manifest 解析，但类型专用执行协议、Registry 和 Activation 尚未实现。
Docker Compose 未在当前 Windows 环境实跑。
```

---

## 4. 2026-08-26 至 2026-08-27 验证结果

```text
前端 npm run build：通过。
API / Web / Worker 进程级启动：通过。
GET /health：API、PostgreSQL、Redis、Worker 全部 ok。
GET /docs 和 Web /app/search：HTTP 200。
停止后测试端口释放：通过。
默认 pytest：220 passed。
前端 npm run build：通过。
Alembic heads/current：唯一 head 和当前版本均为 0008。
连续两轮 CLI 冒烟：API / Web / Worker 启动、health、PID 对齐、停止清理均通过。
Plugin Activation 生命周期：8 项新增测试通过。
Docker Compose：当前机器未安装 Docker，未执行运行验收。
```

---

## 5. 已确认的新架构方向

Sundarr 不使用 Cordis 重写后端。Python 插件系统借鉴 Cordis 的以下语义：

```text
PluginContext：向插件暴露稳定、受控的能力。
requires / provides：显式声明依赖和提供能力。
PluginActivation：跟踪插件实例、状态、commit 和清理栈。
可逆副作用：卸载时按 LIFO 顺序释放注册、连接和定时器。
候选加载：新版本先加载和测试，不直接覆盖旧版本。
原子切换：候选通过后再替换旧 Activation。
失败回滚：候选失败时旧版本继续工作。
```

该生命周期不替代 PostgreSQL 任务事实来源、Worker 状态机、Redis、Alembic 或 SMB 连接池。

Phase 11 完成后，可以提供可选 Cordis / DeepSeek Harness 桥接插件；桥接插件只调用公开 Sundarr HTTP API。

---

## 6. 当前工作区说明

文档中的“已实现”和“目标设计”必须继续分开标注。当前后端验证基线为 220 项测试，并已完成 flat v1 示例插件加载与 OpenAPI 插件接口冒烟；前端构建及 API/Web/Worker 进程冒烟仍沿用 2026-08-26 的已通过结果。Manifest v2 当前只完成解析和静态校验，不代表 v2 插件已经可激活。
