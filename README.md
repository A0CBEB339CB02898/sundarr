# Sundarr

Sundarr 是个人自用的网盘媒体资源搜索、暂存、搬运与 NAS 归档自动化系统。

当前状态：Phase 0 项目骨架。

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

启动 API：

```bash
.venv\Scripts\python -m sundarr.app.cli
```

如果已重新安装 editable 包，也可以使用命令入口：

```bash
.venv\Scripts\sundarr-api
```

启动后访问 `http://localhost:8080/docs`。

安装和构建前端：

```bash
cd web
npm install
npm run build
```

启动前端开发服务：

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
