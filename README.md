<div align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/assets/brand/logo-dark.svg">
    <source media="(prefers-color-scheme: light)" srcset="docs/assets/brand/logo-light.svg">
    <img src="docs/assets/brand/logo-light.svg" alt="Sundarr" width="120" height="120">
  </picture>
  <br>
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/assets/brand/wordmark-dark.svg">
    <source media="(prefers-color-scheme: light)" srcset="docs/assets/brand/wordmark-light.svg">
    <img src="docs/assets/brand/wordmark-light.svg" alt="Sundarr" width="350">
  </picture>
  <p>为 Homelab 打造的远程媒体库同步工具</p>
  
  ![Python 3.12+](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)
  ![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
  ![React](https://img.shields.io/badge/React-61DAFB?logo=react&logoColor=black)
  ![Vite](https://img.shields.io/badge/Vite-646CFF?logo=vite&logoColor=white)
  ![PostgreSQL](https://img.shields.io/badge/PostgreSQL-336791?logo=postgresql&logoColor=white)
  ![Redis](https://img.shields.io/badge/Redis-DC382D?logo=redis&logoColor=white)
  ![License](https://img.shields.io/badge/License-GPL--3.0-blue)
</div>

---

## 核心功能

Sundarr 为 Homelab 打造的媒体发现与远程媒体库同步工具，专注于：

- **多源搜索**：从多个已配置来源聚合搜索结果
- **媒体发现**：当前 MVP 规划支持筛选、热门、分类、详情、关注列表和发现型海报墙
- **SMB 存储**：通过 SMB 协议连接 NAS，支持多个连接配置
- **远程同步**：将远程媒体库（如网盘挂载目录）同步到本地 NAS 媒体库
- **任务管理**：完整任务状态机，支持取消、重试和恢复
- **Web Console**：暖色操作台风格的管理界面

## 技术栈

| 层 | 技术 | 用途 |
|---|---|---|
| **后端** | Python 3.12 + FastAPI | RESTful API 后端 |
| **前端** | React + Vite | 轻量 Web Console |
| **数据库** | PostgreSQL | 数据持久化 |
| **缓存** | Redis | 实时进度辅助 |
| **存储** | SmbWriter | 应用内 SMB 写入 |

## 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/your-username/sundarr.git
cd sundarr
```

### 2. 安装依赖

```bash
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
```

### 3. 配置环境

复制环境配置文件并修改：

```bash
cp .env.example .env
```

### 4. 启动服务

**方式一：使用 Docker Compose（推荐）**

```bash
docker-compose up -d
```

**方式二：本地开发**

```bash
.venv\Scripts\sundarr start
```

`start` 命令会自动：
- 检查并初始化 PostgreSQL 数据库
- 执行数据库迁移
- 初始化默认业务配置
- 安装前端依赖（如果缺少）
- 启动 API、Web Console 和 Worker

### 5. 访问应用

| 服务 | 地址 | 说明 |
|---|---|---|
| **API 文档** | http://localhost:8080/docs | FastAPI 自动生成的 API 文档 |
| **Web Console** | http://localhost:5173/app/search | 主控制台界面 |

## 项目结构

```
sundarr/
├── sundarr/                 # 后端核心代码
│   ├── app/                 # FastAPI 应用
│   └── worker.py           # 后台 Worker 进程
├── web/                     # React 前端
│   ├── src/                # 源代码
│   └── public/             # 静态资源
├── migrations/             # 数据库迁移
├── tests/                  # 测试文件
├── docs/                   # 项目文档
└── docker-compose.yml      # Docker 配置
```

## Web Console 页面

| 路由 | 功能 | 说明 |
|---|---|---|
| `/app/search` | 搜索资源 | 实时调用外部 Adapter 并收藏候选结果 |
| `/app/favorites` | 收藏 | 统一管理收藏资源和收藏链接 |
| `/app/transfers` | 任务管理 | 查询任务、查看日志、取消和重试 |
| `/app/storage` | 存储配置 | 管理 SMB 配置、测试连接、目录浏览 |
| `/app/libraries` | 本地媒体库 | 管理 movie / series / unclassified 目录绑定 |
| `/app/remote-libraries` | 远程媒体库 | 管理远程媒体库目录绑定 |
| `/app/sources` | 媒体源 | 查看和测试已安装的外部 Source Adapter |
| `/app/status` | 系统状态 | 查看 API、Worker、PostgreSQL 和 Redis 状态 |

## CLI 命令

```bash
# 查看帮助
.venv\Scripts\sundarr --help

# 启动完整项目
.venv\Scripts\sundarr start

# 查看状态
.venv\Scripts\sundarr status

# 重启服务
.venv\Scripts\sundarr restart

# 停止服务
.venv\Scripts\sundarr stop

# 前台运行（查看实时日志）
.venv\Scripts\sundarr run
```

## 开发指南

### 运行测试

```bash
# 后端测试
.venv\Scripts\python -m pytest

# 前端构建检查
cd web
npm run build
```

### 项目文档

完整的项目文档位于 `docs/` 目录：

| 文档 | 说明 |
|---|---|
| `01-product-scope.md` | 产品范围和 MVP 边界 |
| `02-architecture-decisions.md` | 技术选型和架构理由 |
| `03-mvp-roadmap.md` | 开发路线和阶段验收 |
| `12-local-development.md` | 本地开发详细指南 |
| `13-web-console-spec.md` | Web Console 规格说明 |
| `16-design-system.md` | 前端设计系统 |

### 设计系统

Sundarr 采用暖色操作台风格设计：

- **主色调**：Terracotta（#d97642 暗色 / #b05623 亮色）
- **字体**：Inter + JetBrains Mono
- **主题**：支持亮色、暗色、跟随系统三种模式
- **设计原则**：信息密度优先，150-220ms 动效，功能至上

更多设计细节请查看 [设计系统文档](docs/16-design-system.md)。

## 核心概念

### 远程媒体库
绑定 SMB 连接下的远程目录（如网盘挂载目录），作为同步的来源。

### 本地媒体库
绑定 SMB 连接下的本地 NAS 目录，支持 movie / series / unclassified 类型。

### 同步绑定
连接远程媒体库（来源）和本地媒体库（目标），Worker 定时扫描并同步内容。

### SMB 存储
应用内 SmbWriter，支持多个 SMB 连接配置，可在 Web Console 中修改并热加载。

## 当前状态

**Phase 0-9.5 已完成**：项目骨架、持久化模型、搜索与收藏、SMB 写入、任务管理、Web Console、远程媒体库同步和模块重构已经落地。

**Phase 10.0 已完成**：默认 pytest、Alembic 迁移链、Windows 真实服务 PID 语义和 SMB 错误码均已收口；当前基线为后端 204 项测试通过、前端生产构建通过、API / Web / Worker 连续两轮启停冒烟通过。

**Phase 10 进行中**：Core 已移除内置真实站点，搜索源统一来自外部 Python 插件仓库；Activation 生命周期内核已建立，仍需完成能力声明、候选健康检查、原子切换、启动自动加载、Web Console 仓库管理和首个外部 SeedHub 端到端验收。

**媒体发现中心是当前优先任务**：当前处于设计阶段，MVP 将支持筛选、热门、分类、详情、关注列表和发现型海报墙；不做本地媒体库播放、观影进度或完整媒体管理 UI。Phase 10 插件闭环在稳定测试节点暂停，后续恢复。

媒体发现中心计划使用 TMDb 作为主目录数据提供方，豆瓣想看作为可选独立接入；外部服务不可用时必须支持缓存或明确降级。

**Phase 11 未开始**：稳定 AI Tool API 完成后，可提供可选 Cordis / DeepSeek Harness 桥接插件。Sundarr Core 保持 Python + FastAPI，不改为 Cordis/Node.js 运行时。

## 不做的事情

- ❌ BT/磁力/种子下载
- ❌ 登录注册、多用户权限
- ❌ 完整本地媒体库 UI / 本地媒体库海报墙 / 播放器 / 观影进度
- ❌ 本地媒体库刮削和 NFO 生成
- ❌ 重型网页抓取（Playwright）

## 许可证

本项目基于 [GNU General Public License v3.0](LICENSE) 开源。

详见 [LICENSE](LICENSE) 文件。

---

<div align="center">
  <p>用 Terracotta 构建的温暖操作台</p>
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/assets/brand/logo-dark.svg">
    <source media="(prefers-color-scheme: light)" srcset="docs/assets/brand/logo-light.svg">
    <img src="docs/assets/brand/logo-light.svg" alt="Sundarr" width="32" height="32">
  </picture>
</div>
