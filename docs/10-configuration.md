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
cloud staging root、download_to_local 配置、worker concurrency、SMB connections、source、media_libraries 等业务配置保存到数据库。
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
storage.smb（旧默认连接兼容入口）
storage.smb_connections
cloud.local.staging_root
download_to_local 全局配置
download_to_local bindings
media_libraries
worker.enabled
worker.concurrency，默认 2
transfer 参数
source configuration
```

运行时配置可以由 Web Console 修改。

开发阶段也可以直接通过 API 写入运行时配置：

```http
POST /storage/config/save
```

不建议直接手工修改数据库，除非是在排查 settings 表持久化问题。

---

## 4. SMB 配置

SMB 配置支持多个连接。新功能应优先使用 SMB connection 表或等价 API；旧 `storage.smb` 只作为默认连接兼容入口保留。

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
  "base_path": "/",
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
媒体库和下载到本地模块只能引用 SMB connection 和目录，不重复填写 SMB 凭据。
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
curl -X POST http://localhost:8080/storage/config/save \
  -H "Content-Type: application/json" \
  -d '{
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

## 6. 下载到本地配置

下载到本地配置保存到数据库 settings 表、media_libraries 表和 download_to_local bindings 表。

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
  "name": "电影下载",
  "enabled": true,
  "media_type": "movie",
  "source_connection_id": "cloud_mount",
  "source_path": "movie",
  "target_library_id": "library_movie",
  "delete_source_after_success": null,
  "delete_empty_source_dirs": null
}
```

规则：

```text
媒体库 connection_id 必须引用已配置 SMB connection。
媒体库 base_path 是对应 SMB connection base_path 内的本地 NAS 目录。
source_connection_id 必须引用已配置 SMB connection。
source_path 是来源 SMB connection base_path 内的相对路径。
target_library_id 必须引用已配置媒体库。
media_type 支持 movie / series / unclassified。
binding 不明确时进入 unclassified 媒体库。
delete_source_after_success 和 delete_empty_source_dirs 可由 binding 覆盖全局默认。
真实 SMB 密码不写入 .env.example，不写入文档，不进入日志。
```

---

## 7. Source 配置

Source 配置保存到 sources 表。

Web Console 可管理：

```text
已安装代码型 Adapter 的启用 / 禁用
已安装代码型 Adapter 的非代码参数
测试搜索
最后错误和耗时
```

真实网站 Source Adapter 通过 Python 代码实现和部署，不通过前端在线编辑。配置只保存 base_url、timeout、rate_limit、user_agent 等参数，不保存可执行 Python 代码。

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
下载到本地配置可持久化。
敏感字段不会明文返回。
```
