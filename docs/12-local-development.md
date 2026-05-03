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

示例命令：

```bash
uvicorn sundarr.app.main:app --reload
```

实际命令以后端项目结构为准。

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
POST /settings/storage/test
```

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
