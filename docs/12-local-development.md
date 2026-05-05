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

推荐命令：

```bash
.venv\Scripts\python -m sundarr.app.cli
```

如果已重新安装 editable 包，也可以使用脚本入口：

```bash
.venv\Scripts\sundarr-api
```

可选参数：

```bash
.venv\Scripts\python -m sundarr.app.cli --host 127.0.0.1 --port 8080 --no-reload
```

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
