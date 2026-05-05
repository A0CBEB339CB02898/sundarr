# Sundarr

Sundarr 是个人自用的网盘媒体资源搜索、暂存、搬运与 NAS 归档自动化系统。

当前状态：Phase 4 Storage Writer 已收口，Phase 5 Transfer Worker 尚未开始。

## 技术栈

```text
Backend: Python + FastAPI
Web Console: React + Vite
Database: PostgreSQL
Cache: Redis
Storage: 应用内 SmbWriter
```

## 本地开发

安装后端依赖：

```bash
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
```

运行后端测试：

```bash
.venv\Scripts\python -m pytest
```

启动完整项目：

```bash
.venv\Scripts\sundarr start
```

`start` 会自动检查数据库、执行必要迁移、初始化默认业务配置，并在缺少前端依赖时执行 `npm install`，随后启动 API 和 Web Console。

查看状态、重启和停止：

```bash
.venv\Scripts\sundarr status
.venv\Scripts\sundarr restart
.venv\Scripts\sundarr stop
```

启动后访问：

```text
API Docs: http://localhost:8080/docs
Web Console: http://localhost:5173
```

构建前端：

```bash
cd web
npm run build
```

单独启动前端仅用于高级调试。日常开发请使用 `.venv\Scripts\sundarr start` 启动完整项目：

```bash
cd web
npm run dev
```

## 文档入口

```text
AGENTS.md
docs/01-product-scope.md
docs/02-architecture-decisions.md
docs/03-mvp-roadmap.md
```
