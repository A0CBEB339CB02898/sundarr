# Sundarr

Sundarr 是个人自用的网盘媒体资源搜索、暂存、搬运与 NAS 归档自动化系统。

当前状态：Phase 8 Download To Local 进行中。SMB 连接管理、媒体库管理、下载到本地绑定、扫描和任务创建已实现。Worker 下载执行、Web Console 前端页面待实现。

下一阶段主线：下载到本地。Sundarr 不把国内封闭网盘直接下载作为近期主链路，而是通过 SMB 扫描已挂载的网盘目录，再按绑定下载到本地 NAS 媒体库。媒体库指 movie、series、unclassified 等本地 NAS 目录绑定，不是海报墙或播放器。

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

`start` 会自动检查数据库、执行必要迁移、初始化默认业务配置，并在缺少前端依赖时执行 `npm install`，随后启动 API、Web Console 和 Worker。

查看状态、重启和停止：

```bash
.venv\Scripts\sundarr status
.venv\Scripts\sundarr restart
.venv\Scripts\sundarr stop
```

启动后访问：

```text
API Docs: http://localhost:8080/docs
Web Console: http://localhost:5173/app/search
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
docs/12-local-development.md
docs/13-web-console-spec.md
docs/15-download-to-local-spec.md
```

## Web Console

MVP Web Console 提供以下页面：

```text
/app/search       搜索资源并创建搬运任务
/app/transfers    查询任务、查看日志、取消和重试
/app/storage      管理 SMB 配置、测试连接、只读浏览目录
/app/libraries    管理 movie / series / unclassified 等本地媒体库目录绑定
/app/sources      管理配置型和文档/表格型媒体源
/app/download-to-local 管理网盘目录到媒体库的下载绑定
/app/status       查看 API、Worker、PostgreSQL 和 Redis 状态
```

Web Console 不做登录注册、多用户权限、完整媒体库 UI、海报墙、播放器或完整 NAS 文件管理器。
