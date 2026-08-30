# 配置规范

本文档定义 Sundarr 的配置来源、运行时配置和热加载规则。

---

## 1. 配置分层

配置分为两类：

```text
Bootstrap 启动配置
运行时配置
```

启动配置来自：

```text
.env
environment variables
后续 Docker Compose 内部服务名和 secrets
```

运行时配置来自：

```text
settings table
sources table
```

---

## 2. 启动配置

Bootstrap 启动配置只用于让 Sundarr 找到基础设施。业务配置不得长期放在 env 中。

示例：

```env
SUNDARR_DATABASE_URL=postgresql+psycopg://sundarr:change_me@postgres:5432/sundarr
SUNDARR_REDIS_URL=redis://:change_me@redis:6379/0
```

规则：

```text
SUNDARR_DATABASE_URL 和 SUNDARR_REDIS_URL 属于 bootstrap 启动配置。
修改启动配置通常需要重启。
cloud staging root、sync 配置、worker concurrency、SMB connections、source、media_libraries、remote_media_libraries 等业务配置保存到数据库。
```

密码位置：

```text
PostgreSQL 密码写在 SUNDARR_DATABASE_URL 中：
postgresql+psycopg://用户名:密码@主机:端口/数据库名

Redis 无密码写法：
redis://主机:端口/数据库编号

Redis 有密码写法：
redis://:密码@主机:端口/数据库编号
```

示例：

```env
SUNDARR_DATABASE_URL=postgresql+psycopg://sundarr:change_me@postgres:5432/sundarr
SUNDARR_REDIS_URL=redis://:change_me@redis:6379/0
```

如果 Redis 不设置密码：

```env
SUNDARR_REDIS_URL=redis://redis:6379/0
```

本地开发阶段，PostgreSQL / Redis 可以运行在远程 Linux Docker 机器或本机 Docker 中，Windows 开发机通过 `.env` 中的 URL 连接。

---

## 2.1 Docker Compose 部署配置

成熟部署方式应提供完整 Docker Compose，而不是要求用户在宿主机安装 PostgreSQL 和 Redis，也不要求用户手动配置数据库地址。

Compose 应包含：

```text
sundarr-api
sundarr-worker
sundarr-web
postgres
redis
数据库迁移/初始化步骤
持久化 volumes
```

部署原则：

```text
API / Worker / Web 打包为 Sundarr 应用镜像。
PostgreSQL 使用官方 postgres 镜像，不打进 Sundarr 应用镜像。
Redis 使用官方 redis 镜像，不打进 Sundarr 应用镜像。
数据库和 Redis 通过 Docker network 内部服务名访问，例如 postgres / redis。
PostgreSQL 数据目录必须挂载 volume。
Redis 如承载重要队列或缓存，可按后续需要挂载 volume。
Compose 部署中 API / Worker 默认使用固定内部服务名连接 PostgreSQL 和 Redis。
Compose 阶段的 .env 只用于部署级 secret 和必要端口覆盖，不保存 SMB、source、worker 并发、staging root 等业务配置。
```

媒体发现缓存即使配置 Redis volume，也只能视为可重建数据。Redis 重启、淘汰或主动清空后，`MediaSubject` 身份、外部 ID、最小展示快照和用户关注状态必须仍可从 PostgreSQL 恢复。

首次启动数据库初始化策略：

```text
postgres 容器负责创建空数据库、用户和初始密码。
Sundarr 必须在 API/Worker 正式运行前执行 alembic upgrade head。
推荐使用单独的一次性 migration service 执行迁移。
API 和 Worker 应依赖 migration 成功完成后再启动。
```

Sundarr 本地启动会自动检查数据库状态，在目标数据库不存在时创建数据库，并执行 Alembic 迁移和默认 settings seed。Docker Compose 的 `sundarr-migrate` 服务后续应复用同一套内部初始化逻辑，而不是要求用户手动执行额外命令。

不推荐把数据库文件或 Redis 数据打入应用镜像。镜像应保持无状态，数据由 volume 保存。

---

## 3. 运行时配置

运行时配置保存到数据库。

包括：

```text
smb_connections 表
cloud.local.staging_root
sync 全局配置
sync bindings
media_libraries（本地媒体库）
remote_media_libraries（远程媒体库）
worker.enabled
worker.concurrency，默认 2
transfer 参数
source configuration
```

运行时配置可以由 Web Console 修改。

开发阶段也可以直接通过 API 创建 SMB connection：

```http
POST /storage/smb-connections/create
```

不建议直接手工修改数据库，除非是在排查 settings 表持久化问题。

本地后台启动时，CLI 直接启动真实 API / Web / Worker 进程，PID 文件记录真实服务进程，不使用日志包装进程。API / Worker 在本地 CLI 模式下通过 `SUNDARR_LOG_TO_FILE=true` 写入滚动日志文件；Docker Compose 模式默认写 stdout/stderr，由 Docker logging driver 管理日志大小。

本地文件日志默认单文件最大 100MB。可用环境变量覆盖：

```env
SUNDARR_LOG_TO_FILE=true
SUNDARR_LOG_FILE=.sundarr/sundarr-api.log
SUNDARR_LOG_MAX_BYTES=104857600
```

该限制适用于本地 CLI 启动的 API / Worker 文件日志。超过限制时当前日志会被清空后继续写入，避免开发环境磁盘被无限增长的日志占满。Web/Vite 属于本地开发服务，CLI 仍将其输出写入 `.sundarr/sundarr-web.log`。

Docker Compose 日志限制应通过 Compose `logging` 配置完成，例如 `max-size` 和 `max-file`。Docker 模式不应依赖 `.sundarr/*.log` 作为主日志。

---

## 4. SMB 配置

SMB 配置支持多个连接。新功能必须使用 SMB connection 表或等价 API；旧 `storage.smb` 兼容入口已在 Phase 9 删除。

SMB connection 配置结构：

```json
{
  "id": "media_library",
  "name": "本地媒体库",
  "enabled": true,
  "host": "nas.example.invalid",
  "port": 445,
  "share": "media",
  "username": "user",
  "password": "password",
  "domain": "",
  "base_path": "/"
}
```

规则：

```text
password 不回显明文。
password 留空表示保留旧值。
保存 SMB connection 后必须热加载。
保存某个 SMB connection 会中断使用该连接旧配置的运行中任务。
真实 SMB 可用于本地手动开发测试。
自动化测试仍不得依赖真实 SMB 服务器。
远程媒体库和本地媒体库只能引用 SMB connection 和目录，不重复填写 SMB 凭据。
```

本地手动测试时，推荐先准备以下信息：

```text
host: SMB 主机，例如 nas.example.invalid
port: 通常是 445
share: SMB 共享名，例如 media
username: SMB 用户名
password: SMB 密码
domain: 可为空
base_path: Sundarr 可写入的共享内相对根路径，例如 / 或 /SundarrManualTest
```

可以通过 FastAPI `/docs` 或命令行提交配置。示例：

```bash
curl -X POST http://localhost:8080/storage/smb-connections/create \
  -H "Content-Type: application/json" \
  -d '{
    "id": "manual_test",
    "name": "手动测试",
    "enabled": true,
    "host": "nas.example.invalid",
    "port": 445,
    "share": "media",
    "username": "your_user",
    "password": "your_password",
    "domain": "",
    "base_path": "/SundarrManualTest"
  }'
```

不要把真实密码写入项目文档、测试文件、提交信息或 `.env.example`。

---

## 5. Transfer 配置

MVP 默认值由数据库 settings seed 写入：

```text
worker.enabled = true
worker.concurrency = 2
cloud.local.staging_root = /Sundarr/_staging
```

Phase 5 实现 Worker 时，固定启动 1 个 Worker 进程，并从 settings 表读取 worker.concurrency 控制并行 TransferTask 数量。

MVP 不开放 worker process 数量配置。后续如需多个 Worker 进程，必须先补充跨进程任务领取锁，避免重复执行同一 TransferTask。

---

## 6. 远程媒体库同步配置

远程媒体库同步配置保存到数据库 settings 表、media_libraries 表、remote_media_libraries 表和 sync_bindings 表。`download_to_local` 仅保留少量历史默认配置 key，业务模型和 API 已统一为 remote media library / sync；该默认 key 清理由配置迁移单独处理，不能重新引入旧模块。

全局配置建议：

```json
{
  "delete_source_after_success": true,
  "delete_empty_source_dirs": true,
  "scan_interval_seconds": 60,
  "stable_seconds": 120,
  "unclassified_library_id": "library_unclassified"
}
```

媒体库配置建议：

```json
{
  "name": "电影",
  "media_type": "movie",
  "enabled": true,
  "connection_id": "media_library",
  "base_path": "Movies"
}
```

Binding 配置建议：

```json
{
  "name": "电影同步",
  "enabled": true,
  "media_type": "movie",
  "remote_library_id": "remote_movie",
  "target_library_id": "library_movie",
  "delete_source_after_success": null,
  "delete_empty_source_dirs": null
}
```

规则：

```text
本地媒体库 connection_id 必须引用已配置 SMB connection。
本地媒体库 base_path 是对应 SMB connection base_path 内的本地 NAS 目录。
远程媒体库 connection_id 必须引用已配置 SMB connection。
远程媒体库 base_path 是来源 SMB connection base_path 内的相对路径。
remote_library_id 必须引用已配置远程媒体库。
target_library_id 必须引用已配置媒体库。
media_type 支持 movie / series / unclassified。
binding 不明确时进入 unclassified 媒体库。
delete_source_after_success 和 delete_empty_source_dirs 可由 binding 覆盖全局默认。
真实 SMB 密码不写入 .env.example，不写入文档，不进入日志。
```

---

## 7. Source 配置

搜索源配置不保存到数据库；`sources` 表仅保存由 Source Adapter 代码同步得到的目录信息。

Web Console 可管理：

```text
已安装搜索源列表
测试搜索
测试步骤日志和预览结果
```

真实网站 Source Adapter 通过 Python 代码实现和部署，不通过前端在线编辑。MVP 不通过 Web Console 管理 base_url、timeout、rate_limit、user_agent 等 Adapter 参数，不保存可执行 Python 代码。

Git Plugin Repository 模式已进入 Phase 10：系统保存仓库配置和锁定 commit，但仍不得保存可执行 Python 代码。

通用 Manifest v2 已允许插件仓库声明 `SOURCE`、`CATALOG_PROVIDER` 和 `WATCHLIST_PROVIDER`。同一豆瓣仓库可以声明 `douban-catalog` 和 `douban-watchlist` 两个独立插件实例；两者分别保存 `PluginConfig`、启用状态和脱敏错误状态。Phase 10.1 运行框架与 Phase 10.2 Core 通用消费框架已完成结构性收口；Phase 10.3 接入真实平台配置并持续执行真实数据回归。TMDb API 密钥以及未来可能使用的豆瓣 cookie 均属于敏感配置；API 以 `***` 返回敏感字段，更新时 `***` 表示保留原值，持久错误和受控插件 logger 会替换已知敏感值。

媒体发现 Core 缓存配置使用环境变量，不进入插件 Manifest：

```text
SUNDARR_CATALOG_CACHE_TTL_SECONDS=900
SUNDARR_CATALOG_DETAIL_CACHE_TTL_SECONDS=21600
SUNDARR_CATALOG_STALE_TTL_SECONDS=604800
```

新鲜 TTL 决定普通请求何时重新访问 Provider；stale TTL 只决定 Provider 故障时最多允许使用多旧的 Redis 降级响应。`refresh=true` 可以绕过新鲜缓存，但不能绕过敏感配置保护。

Worker 的想看同步周期保存在数据库 Setting `discovery.watchlist_sync_interval_seconds`，默认 900 秒，最小 60 秒。插件只实现单次 `pull`，不得创建自己的永久轮询线程。

通用 Manifest v2 只声明 `config_schema`，不保存配置值。Web Console 的分页方式、Provider 运行中 continuation token、想看同步游标和重试状态也不属于 Manifest；分页状态属于前端/API，游标和调度状态由 Core 持久化。

当前单 Manifest 候选 Activation 已实现 `string`、`password`、`integer`、`boolean`、`select` 的最小配置校验，支持 required、default、min/max 和 options；未声明字段会明确拒绝。校验错误只报告字段名和规则，不回显敏感配置值。数据库配置解码、API 脱敏响应和 Web Console 表单仍在后续 Manager/API 接入阶段完成。

仓库配置字段建议：

```text
repo_url
branch
current_commit
previous_commit
auto_update
enabled
last_checked_at
last_loaded_at
last_error
```

配置规则：

```text
repo_url 和 branch 是用户配置。
current_commit 是实际执行的锁定版本。
fetch 远程更新不等于应用更新。
默认不自动切换到远程最新 commit。
更新失败时必须保留 previous_commit 以便回滚。
Phase 10.1 后，候选更新失败时 current_commit 和旧 PluginActivation 都必须保持不变。
启动只加载 enabled 仓库的 current_commit，不自动 fetch 或切换到远程最新版本。
WATCHLIST_PROVIDER 只保存连接参数和读取配置；调度周期、同步游标和重试状态由 Core 管理。
数据库、settings 和 Web Console 不保存可执行 Python 代码。
```

目录缓存配置后续至少区分搜索/热门/分类的短期缓存、详情的较长期缓存和失败负缓存。具体 TTL 尚未确认；配置必须设置安全默认值，不能要求用户理解每个 Provider 的内部端点。

---

## 8. 敏感信息规则

MVP 不实现复杂 secret backend。

必须做到：

```text
不提交 .env。
不在日志输出 password/token/cookie。
API 不返回 password 明文。
Web Console 不展示 password 明文。
```

---

## 9. 验收标准

配置系统完成时必须满足：

```text
API 和 Worker 可读取启动配置。
可保存多个 SMB connection。
Web Console 可通过列表和弹出表单修改 SMB connection。
SMB connection 修改无需重启。
SMB connection 修改中断旧配置运行中任务。
媒体库配置可持久化，并绑定到 SMB connection 下的目录。
Source 配置可持久化。
远程媒体库同步配置可持久化。
敏感字段不会明文返回。
```
