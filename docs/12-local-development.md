# 本地开发

本文档定义 Sundarr 本地开发、启动和测试方式。

---

## 1. 运行环境

推荐版本：

```text
Python 3.12
Node.js LTS
PostgreSQL 16
Redis 7
Docker Compose
```

---

## 2. 目录结构

目标结构：

```text
sundarr/
  app/
  web/
  migrations/
  tests/
  docs/
  docker-compose.yml
  Dockerfile
```

---

## 3. 启动后端

首次启动或数据库为空时，先初始化数据库：

```bash
.venv\Scripts\sundarr db init
```

该命令会：

```text
连接到 SUNDARR_DATABASE_URL 指向的 PostgreSQL 服务。
如果目标数据库不存在，则先连接 postgres 维护库并创建目标数据库。
执行 alembic upgrade head 初始化表结构。
```

推荐命令：

```bash
.venv\Scripts\sundarr start
```

查看状态、重启和停止：

```bash
.venv\Scripts\sundarr status
.venv\Scripts\sundarr restart
.venv\Scripts\sundarr stop
```

前台运行，适合直接看实时日志：

```bash
.venv\Scripts\sundarr run
```

可选参数：

```bash
.venv\Scripts\sundarr start --host 127.0.0.1 --port 8080 --reload
```

后台启动日志写入 `.sundarr/sundarr-api.log`。

FastAPI 调试入口：

```text
http://localhost:8080/docs
```

---

## 4. 启动前端

示例命令：

```bash
cd web
npm install
npm run dev
```

Web Console 默认调用 FastAPI API。

---

## 5. Docker Compose

MVP compose 至少包含：

```text
sundarr-api
sundarr-worker
sundarr-web
postgres
redis
```

MVP 不要求宿主机 SMB mount。

开发机不想安装 PostgreSQL / Redis 时，推荐使用 Docker 或远程 Linux Docker 机器运行依赖服务。Windows 本机只运行 API/Web 开发进程即可。

远程 Linux Docker 机器示例：

```text
Linux Docker 机器运行 postgres / redis。
Windows 开发机通过局域网 IP 连接 PostgreSQL / Redis。
Windows 开发机 .env 中填写远程连接 URL。
```

Windows 本机 `.env` 示例：

```env
SUNDARR_DATABASE_URL=postgresql+psycopg://sundarr:change_me@192.168.1.50:5432/sundarr
SUNDARR_REDIS_URL=redis://:change_me@192.168.1.50:6379/0
```

如果 Redis 没有密码：

```env
SUNDARR_REDIS_URL=redis://192.168.1.50:6379/0
```

完整部署时，成熟做法是将 Sundarr 交付为完整 Docker Compose：

```text
sundarr-api: Sundarr API 镜像。
sundarr-worker: Sundarr Worker 镜像。
sundarr-web: Web Console 镜像。
postgres: 官方 PostgreSQL 镜像。
redis: 官方 Redis 镜像。
sundarr-migrate: 一次性迁移任务，执行 alembic upgrade head。
```

数据库初始化规则：

```text
postgres 容器用 POSTGRES_DB / POSTGRES_USER / POSTGRES_PASSWORD 创建初始数据库。
sundarr-migrate 等待 postgres 可用后执行 alembic upgrade head。
sundarr-api 和 sundarr-worker 在 migration 成功后启动。
PostgreSQL 和 Redis 数据通过 Docker volume 持久化。
```

数据库密码位置：

```text
postgres 容器：POSTGRES_PASSWORD
Sundarr API / Worker：SUNDARR_DATABASE_URL 中的 密码 部分
```

Redis 密码位置：

```text
redis 容器：redis-server --requirepass change_me 或等价配置
Sundarr API / Worker：SUNDARR_REDIS_URL=redis://:change_me@redis:6379/0
```

---

## 6. Mock/Local Provider

本地开发默认使用 Mock/Local Provider。

用途：

```text
模拟 cloud staging
模拟文件列表
模拟文件 stream
模拟 cleanup
```

不得把自动化测试绑定到真实网盘。

---

## 7. Storage 测试

本地默认使用 LocalWriter 进行自动化测试。

SmbWriter 可通过 Web Console 或 API 测试连接：

```text
POST /storage/config/test
```

如果准备了真实 SMB 环境，当前应通过运行时配置写入，而不是写入 `.env`：

```http
POST /storage/config/save
```

推荐使用 FastAPI 调试页面：

```text
http://localhost:8080/docs
```

请求体示例：

```json
{
  "host": "fnos.local",
  "port": 445,
  "share": "media",
  "username": "your_user",
  "password": "your_password",
  "domain": "",
  "base_path": "/SundarrTest",
  "libraries": {
    "movies": "Movies",
    "tv": "TV",
    "anime": "Anime"
  }
}
```

`.env.example` 中的 `SUNDARR_DEV_SMB_*` 只用于记录本地手动测试所需字段，不是当前应用读取 SMB 配置的事实来源。真实 `.env` 不要提交。

---

## 8. 运行测试

后端测试：

```bash
pytest
```

前端 smoke：

```bash
npm run build
```

具体命令以后续 package 配置为准。

---

## 9. Git 注意事项

不要提交：

```text
.env
cookie
token
SMB password
真实网盘凭据
node_modules
.venv
dist
```

---

## 10. 验收标准

本地开发文档完成后，开发者应能：

```text
启动 API。
启动 Web Console。
启动 PostgreSQL 和 Redis。
运行后端测试。
运行前端构建或 smoke check。
使用 Mock/Local Provider 跑通测试流程。
```
