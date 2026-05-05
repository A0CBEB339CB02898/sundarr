# 配置规范

本文档定义 Sundarr 的配置来源、运行时配置和热加载规则。

---

## 1. 配置分层

配置分为两类：

```text
启动配置
运行时配置
```

启动配置来自：

```text
.env
config.yaml
environment variables
```

运行时配置来自：

```text
settings table
sources table
```

---

## 2. 启动配置

启动配置用于启动 API、Worker 和基础依赖。

示例：

```yaml
app:
  name: Sundarr
  host: 0.0.0.0
  port: 8080

database:
  url: postgresql+psycopg://sundarr:change_me@postgres:5432/sundarr

redis:
  url: redis://:change_me@redis:6379/0

cloud:
  staging_root: /Sundarr/_staging
```

规则：

```text
database.url 和 redis.url 属于启动配置。
修改启动配置通常需要重启。
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

Docker Compose 中的 PostgreSQL 初始密码由 `POSTGRES_PASSWORD` 提供，必须和 `SUNDARR_DATABASE_URL` 中的密码一致。Redis 密码通常通过启动命令或配置文件启用，例如 `redis-server --requirepass change_me`，并同步写入 `SUNDARR_REDIS_URL`。

---

## 2.1 Docker Compose 部署配置

成熟部署方式应提供完整 Docker Compose，而不是要求用户在宿主机安装 PostgreSQL 和 Redis。

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
```

首次启动数据库初始化策略：

```text
postgres 容器负责创建空数据库、用户和初始密码。
Sundarr 必须在 API/Worker 正式运行前执行 alembic upgrade head。
推荐使用单独的一次性 migration service 执行迁移。
API 和 Worker 应依赖 migration 成功完成后再启动。
```

Sundarr 提供统一初始化命令：

```bash
sundarr db init
```

该命令会在目标数据库不存在时先创建数据库，再执行 Alembic 迁移。Docker Compose 的 `sundarr-migrate` 服务应使用该命令作为启动命令。

不推荐把数据库文件或 Redis 数据打入应用镜像。镜像应保持无状态，数据由 volume 保存。

---

## 3. 运行时配置

运行时配置保存到数据库。

包括：

```text
storage.smb
storage.libraries
部分 transfer 参数
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

SMB 配置结构：

```json
{
  "host": "nas.example.invalid",
  "port": 445,
  "share": "media",
  "username": "user",
  "password": "password",
  "domain": "",
  "base_path": "/",
  "libraries": {
    "movies": "Movies",
    "tv": "TV",
    "anime": "Anime"
  }
}
```

规则：

```text
password 不回显明文。
password 留空表示保留旧值。
保存 SMB 配置后必须热加载。
保存 SMB 配置会中断使用旧配置的运行中任务。
真实 SMB 可用于本地手动开发测试。
自动化测试仍不得依赖真实 SMB 服务器。
```

本地手动测试时，推荐先准备以下信息：

```text
host: SMB 主机，例如 nas.example.invalid 或 192.168.1.10
port: 通常是 445
share: SMB 共享名，例如 media
username: SMB 用户名
password: SMB 密码
domain: 可为空
base_path: Sundarr 可写入的共享内相对根路径，例如 / 或 /SundarrManualTest
libraries: movies / tv / anime 等媒体目录映射
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
    "base_path": "/SundarrManualTest",
    "libraries": {
      "movies": "Movies",
      "tv": "TV",
      "anime": "Anime"
    }
  }'
```

不要把真实密码写入项目文档、测试文件、提交信息或 `.env.example`。

---

## 5. Transfer 配置

MVP 默认：

```yaml
transfer:
  max_concurrent_tasks: 2
  max_concurrent_files_per_task: 1
  chunk_size: 8388608
  retry_count: 3
  retry_delay_seconds: 10
  verify_mode: size
  speed_window_seconds: 5
```

部分参数可后续放入 settings 表热加载。

---

## 6. Source 配置

Source 配置保存到 sources 表。

Web Console 可管理：

```text
配置型源
文档/表格型源
```

代码型源通过代码实现，不通过前端在线编辑。

---

## 7. 敏感信息规则

MVP 不实现复杂 secret backend。

必须做到：

```text
不提交 .env。
不在日志输出 password/token/cookie。
API 不返回 password 明文。
Web Console 不展示 password 明文。
```

---

## 8. 验收标准

配置系统完成时必须满足：

```text
API 和 Worker 可读取启动配置。
settings 表可保存 SMB 配置。
Web Console 可修改 SMB 配置。
SMB 配置修改无需重启。
SMB 配置修改中断旧配置运行中任务。
Source 配置可持久化。
敏感字段不会明文返回。
```
