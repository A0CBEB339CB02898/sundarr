# Sundarr MVP 架构说明与 Agent 开发规范

> 项目代号：**Sundarr**  
> 定位：面向合法网盘媒体资源的搜索、暂存、下载、校验与 NAS 归档自动化系统。  
> 一句话目标：搜索云端媒体，临时转存到个人网盘，下载到本地 NAS，校验成功后清理云端临时文件。

---

## 0. Agent 阅读规则

本文件是项目从零开发时的主规范。Agent 在实现代码前必须先读取本文件，并按以下规则执行。

### 0.1 约束等级

```text
MUST     必须实现或遵守；不满足即视为错误。
SHOULD   应优先实现；除非有明确理由，否则不要跳过。
MAY      可选能力；不得影响 MVP 主链路。
MVP      第一阶段必须交付的最小闭环。
LATER    后续增强；不得提前扩大实现范围。
```

### 0.2 实现原则

1. MUST 先实现端到端闭环，再扩展 provider、UI、推荐算法和媒体刮削。
2. MUST 保持模块边界清晰，避免把搜索、转存、下载、校验、清理写成不可恢复的长流程。
3. MUST 所有任务状态持久化；进度可缓存，但数据库是最终事实来源。
4. MUST 对路径、删除、凭据、外部资源源做安全约束。
5. MUST 默认不内置明显侵权资源源，不实现破解、绕过会员、绕过验证码等能力。
6. SHOULD 优先使用简单、可测试、可替换的接口；不要过早抽象复杂插件系统。
7. MAY 在 MVP 后接入 OpenList、rclone、Playwright、TMDb、复杂 UI。

---

## 1. 项目边界

### 1.1 Sundarr 要做什么

Sundarr 负责把用户确认合法的网盘媒体资源归档到 NAS。主流程如下：

```text
搜索资源
  -> 提取网盘链接
  -> 转存到个人网盘临时目录
  -> 从个人网盘流式下载到 NAS
  -> 校验本地文件
  -> 删除云端临时目录
  -> 更新任务结果
```

该流程不是原子移动，而是：

```text
save share to cloud -> download to NAS -> verify -> delete cloud staging
```

系统必须把它建模为可追踪、可重试、可恢复的任务流。

### 1.2 MVP 要做什么

MVP 必须交付：

1. FastAPI API 服务。
2. Worker 任务执行服务。
3. PostgreSQL 持久化。
4. Redis 用于缓存和实时进度加速。
5. Source Adapter 基础接口和至少 1 个示例源。
6. Cloud Link Extractor。
7. Resource Library。
8. 1 个 Cloud Provider Driver。
9. 应用内 SmbWriter；不依赖宿主机 SMB mount。
10. `.downloading` 临时文件、大小校验、成功后 rename。
11. 校验成功后删除 cloud staging 目录。
12. React + Vite 轻量 Web Console。
13. REST API：健康检查、搜索、资源详情、创建任务、查询任务、取消任务、重试任务、SMB 配置、媒体源配置。

### 1.3 第一阶段不做什么

MVP 不做：

1. BT、磁力、种子下载。
2. 盗版资源分发或资源托管。
3. 绕过网盘限制、破解会员、绕过验证码。
4. 复杂 Web UI 和完整媒体库 UI。
5. 多用户权限系统。
6. 媒体刮削、海报墙、NFO 生成。
7. OpenList 作为核心搬运层。
8. FNOS 私有 API 作为核心写入依赖。
9. 容器内直接 mount SMB。
10. Playwright 重型抓取。
11. 多 provider 一次性全量接入。

### 1.4 合规边界

MUST 只允许用户配置其确认合法、授权、公开或自有的资源源。

Source 和 Link 必须保留以下合规字段：

```text
source.enabled
source.legal_note
source.trust_level
source.created_by_user
link.risk_level
link.visibility
```

MUST 默认不内置明显侵权资源源。示例数据只能使用占位 URL 或用户本地测试源。

---

## 2. 核心概念

### 2.1 Resource

Resource 表示一个被标准化后的媒体资源候选项。它不等于本地媒体文件，也不等于单个网盘链接。

Resource 可以包含多个 Link：

```text
Resource: 星际穿越 / Interstellar / 2014 / movie
  Link A: quark share url
  Link B: aliyun share url
```

### 2.2 Link

Link 表示可被转存或下载的网盘分享链接，包含 provider、url、code、有效性、风险等级和来源追踪。

### 2.3 Cloud Staging

Cloud Staging 是个人网盘中的临时中转目录。它不是长期媒体库。

固定路径格式：

```text
/Sundarr/_staging/{task_id}/
```

### 2.4 Transfer Task

Transfer Task 表示一次从 Link 到 NAS 目标目录的归档任务。

MUST 使用模式：

```text
move_after_verified_download
```

语义：

```text
copy/download -> verify -> delete source staging
```

### 2.5 NAS Target

NAS 是最终落盘目标。MVP 中 Sundarr 通过应用内 SmbWriter 直接连接 SMB share，例如：

```text
smb://fnos.local/media/Movies
smb://fnos.local/media/TV
smb://fnos.local/media/Anime
```

Sundarr 不要求宿主机提前 mount SMB。LocalWriter 仅用于开发和测试。

---

## 3. 总体架构

```text
AI Tool / React Web Console / API Client
        |
        v
Sundarr API Gateway
        |
        v
Search & Resource Layer
  - Source Adapter
  - Parser
  - Cloud Link Extractor
  - Normalizer
  - Deduper
  - Ranker
  - Resource Library
        |
        v
Cloud Staging Layer
  - Cloud Provider Driver
  - Share Save
  - Staging Directory
  - Cloud File Listing
  - Cloud Cleanup
        |
        v
Transfer Layer
  - Task Queue
  - Download Worker
  - SmbWriter / LocalWriter
  - Progress Tracker
  - Retry/Resume
  - Verification
        |
        v
NAS SMB share
```

### 3.1 服务拆分

MVP 服务：

```text
sundarr-api      REST API
sundarr-web      React + Vite Web Console
sundarr-worker   task execution
postgres         persistence
redis            cache/progress acceleration
```

### 3.2 推荐技术栈

MVP 使用：

```text
Python 3.12
FastAPI
React
Vite
SQLAlchemy 2.x or SQLModel
Alembic
PostgreSQL
Redis
httpx
selectolax or BeautifulSoup
Pydantic v2
Arq or RQ
Docker Compose
pytest
```

选择理由：Python 适合网页解析、文本处理、AI/模型接入和后端自动化；FastAPI 作为 API 后端，后续可封装为 media search tool 供 AI 调用；React + Vite 能支持 MVP 轻量控制台，并保留后续演进为完整前端的空间。

---

## 4. 模块规范

### 4.1 API Gateway

API Gateway 只负责请求校验、鉴权占位、调用 service、返回稳定响应。不得在路由层直接执行抓取、下载或删除。

MVP API：

```text
GET    /health
GET    /sources
POST   /sources
GET    /search
GET    /resources
GET    /resources/{resource_id}
POST   /transfers
GET    /transfers/{task_id}
POST   /transfers/{task_id}/cancel
POST   /transfers/{task_id}/retry
GET    /transfers/{task_id}/logs
GET    /settings/storage
PUT    /settings/storage
POST   /settings/storage/test
GET    /storage/browse
```

LATER API：

```text
GET    /library
POST   /library/{resource_id}/refresh
POST   /ai/search
POST   /ai/transfer
```

FastAPI 只作为 API 后端，不负责 Jinja2 页面渲染。FastAPI `/docs` 保留为开发调试入口。

### 4.2 Source Adapter

Source Adapter 负责从外部源获取原始候选项。不同源必须输出统一结构。

支持类型：

```text
document
sheet
website
forum
custom
```

基础接口：

```python
class BaseSource:
    name: str
    source_type: str
    enabled: bool

    async def search(self, keyword: str) -> list[dict]:
        raise NotImplementedError
```

原始输出：

```json
{
  "raw_title": "Interstellar 2014 1080p",
  "raw_url": "https://example.invalid/detail/123",
  "raw_content": "share url: https://pan.example.invalid/s/abc code: 1234",
  "source": "example_source",
  "source_type": "website",
  "fetched_at": "2026-05-04T10:00:00Z"
}
```

规则：

1. MUST 设置请求超时。
2. MUST 捕获单个 source 错误，不能让一个源拖垮整体搜索。
3. MUST 记录 source_name、duration、error_code。
4. SHOULD 对失败源做短期熔断。

### 4.3 Parser

Parser 负责从 HTML、文档、表格中提取 raw item。Parser 不负责入库、不负责排序、不负责下载。

MVP 优先级：

```text
HTML text extraction
Markdown/plain text extraction
CSV extraction
```

LATER：

```text
Notion
Google Sheet
Feishu Sheet
Airtable
Playwright rendered pages
```

### 4.4 Cloud Link Extractor

Cloud Link Extractor 负责从文本中识别 provider、url、code 和 confidence。

基础输出：

```json
{
  "provider": "quark",
  "url": "https://pan.example.invalid/s/xxxx",
  "code": null,
  "raw_text": "quark: https://pan.example.invalid/s/xxxx",
  "confidence": 0.95
}
```

MUST 处理：

1. 链接和提取码不在同一行。
2. 同一页面包含多个链接。
3. 一条资源包含多个 provider。
4. 标题、广告、说明文本混杂。
5. 常见提取码模式：`提取码`、`密码`、`访问码`、`code`。

MVP 至少实现一个 provider 的正则识别；其他 provider 预留配置结构。

### 4.5 Normalizer

Normalizer 负责把 raw item 标准化为 Resource 候选。

标准结构：

```json
{
  "id": "res_xxx",
  "title": "星际穿越",
  "original_title": "Interstellar",
  "type": "movie",
  "year": 2014,
  "season": null,
  "episodes": null,
  "quality": "1080p",
  "language": "zh-CN",
  "subtitle": "中字",
  "description": null,
  "poster": null,
  "source": "example_source",
  "source_type": "website",
  "source_url": "https://example.invalid/detail/123",
  "links": [],
  "score": 0.0,
  "created_at": "2026-05-04T10:00:00Z",
  "updated_at": "2026-05-04T10:00:00Z"
}
```

规则：

1. MUST 保留原始标题和来源 URL。
2. SHOULD 尽量解析标题、年份、清晰度、季集信息。
3. MUST 对无法识别字段填 `null`，不要编造元数据。

### 4.6 Deduper

Deduper 负责合并同一媒体资源的多个来源或版本。

去重依据：

```text
normalized_title
year
media_type
season
episodes
provider url
quality
size_bytes
```

标题归一化 SHOULD 处理：

```text
空格
标点
中英文括号
繁简体
年份
清晰度标签
常见别名
```

MVP 可以使用启发式规则；不得引入复杂推荐算法阻塞主链路。

### 4.7 Ranker

Ranker 负责排序候选项，不负责过滤合法性。

初始评分：

```text
final_score =
  title_score      * 0.40 +
  source_weight    * 0.20 +
  freshness_score  * 0.15 +
  link_valid_score * 0.15 +
  quality_score    * 0.10
```

MVP 可先返回基础分数，但字段必须存在，便于后续优化。

### 4.8 Cloud Provider Driver

Cloud Provider Driver 负责操作用户个人网盘。它只处理 staging 目录，不接触 NAS。

接口：

```python
class CloudProvider:
    name: str

    async def save_share(self, url: str, code: str | None, target_dir: str) -> str:
        raise NotImplementedError

    async def list_files(self, path: str) -> list[CloudFile]:
        raise NotImplementedError

    async def open_file_stream(self, file_id: str, offset: int = 0):
        raise NotImplementedError

    async def delete(self, path: str) -> None:
        raise NotImplementedError
```

规则：

1. MUST 只允许删除 `cloud.staging_root` 下的路径。
2. MUST 记录 provider 操作失败原因。
3. SHOULD 支持 HTTP Range 或等价能力；不支持时必须从头重试。
4. MUST 不在日志输出 token、cookie、授权 header。

### 4.9 Transfer Service

Transfer Service 负责任务状态机、队列调度、下载、校验、清理。

能力：

```text
create task
enqueue task
execute state machine
download cloud files
write temp files
track progress
verify files
rename files
cleanup cloud staging
retry recoverable failures
cancel running task
```

### 4.10 Storage Writer

MVP 正式 NAS 写入方式是应用内 SmbWriter，不依赖系统 SMB mount。LocalWriter 仅用于开发和测试。

SMB 配置示例：

```yaml
storage:
  type: smb
  smb:
    host: fnos.local
    port: 445
    share: media
    username: your_user
    password: your_password
    domain: ""
    base_path: /
    libraries:
      movies: Movies
      tv: TV
      anime: Anime
```

Web Console 可以修改 SMB 配置。SMB 配置应保存到数据库 settings 表或等价运行时配置存储中，修改后无需重启 API 或 Worker。

SMB 配置热加载规则：

```text
保存新 SMB 配置
关闭旧 SMB 连接
运行中且使用旧 SMB 配置的任务进入 failed
错误码 STORAGE_CONFIG_CHANGED
retryable = true
保留 .downloading 文件
保留 cloud staging
新任务和重试任务使用最新 SMB 配置
```

规则：

1. MUST 写入 `.downloading` 临时文件。
2. MUST 校验成功后原子 rename 到最终文件名。
3. MUST 防止路径穿越。
4. SHOULD 在任务开始前检查目标磁盘可用空间。

### 4.11 Web Console

MVP 包含 React + Vite 轻量 Web Console。Web Console 是核心操作控制台，不是完整媒体库 UI。

MVP Web Console 必须覆盖：

```text
搜索资源
展示候选结果
媒体源配置管理
SMB 配置查看和修改
SMB 连接测试
SMB 目录浏览
创建归档任务
任务进度查看
取消 / 重试任务
```

MVP Web Console 不做：

```text
登录注册
多用户权限
完整媒体库 UI
海报墙
播放器
完整文件管理器
拖拽式管理
任意 NAS 文件删除
```

媒体源配置规则：

```text
Web Console 支持管理配置型源和文档/表格型源。
Web Console 不支持在线编辑代码型 Source Adapter。
代码型 Source Adapter 通过代码实现和部署。
```

---

## 5. 任务状态机

### 5.1 状态定义

```text
pending            task created, not started
staging_to_cloud   saving share to user cloud staging
cloud_ready        cloud staging files listed
downloading        downloading files to temp paths
verifying          checking local files
renaming           renaming temp files to final paths
cleaning_cloud     deleting cloud staging path
completed          task finished successfully
failed             task failed and stopped
cancelled          task cancelled by user/system
```

`searching` 不属于 Transfer Task 状态。搜索是独立 API 行为，不应混入搬运任务状态机。

### 5.2 正常流转

```text
pending
  -> staging_to_cloud
  -> cloud_ready
  -> downloading
  -> verifying
  -> renaming
  -> cleaning_cloud
  -> completed
```

### 5.3 失败和重试

失败时：

```text
any running state -> failed
```

重试规则：

```text
failed at staging_to_cloud -> pending
failed at downloading      -> downloading if temp file can resume, otherwise cloud_ready
failed at verifying        -> downloading or failed based on verification error
failed at cleaning_cloud   -> cleaning_cloud
```

规则：

1. MUST 记录 `error_code`、`error_message`、`retryable`。
2. MUST 保留 cloud staging，除非校验和 rename 已完成。
3. MUST 不因 cleanup 失败删除本地已完成文件。
4. SHOULD 对可恢复错误做有限次数重试。

SMB 配置变更时：

```text
running task using old SMB config -> failed
error_code = STORAGE_CONFIG_CHANGED
retryable = true
```

规则：

1. MUST 保留 `.downloading` 文件。
2. MUST 保留 cloud staging。
3. MUST 关闭旧 SMB 连接。
4. MUST 让新任务和重试任务使用最新 SMB 配置。
5. SHOULD 在 Web Console 中提示用户运行中任务已因存储配置变化中断。

### 5.4 取消

取消规则：

1. `pending` 可以直接变为 `cancelled`。
2. `downloading` 取消时应停止读取流，保留 `.downloading` 文件供用户或重试处理。
3. `cleaning_cloud` 期间取消可能不生效；必须返回当前状态。
4. `completed` 不允许取消。

### 5.5 文件状态

`transfer_files.status` 必须与任务状态分开维护。

```text
pending       file record created
downloading   temp file is being written
verified      temp file passed verification but has not been renamed
completed     final file exists and temp file has been renamed
failed        file failed and task should stop or retry
cancelled     file download was cancelled
```

删除 cloud staging 前，所有文件必须处于 `completed`，不能只处于 `verified`。

---

## 6. 下载与校验

### 6.1 单文件流程

```text
read cloud metadata
  -> determine total_bytes
  -> validate target path
  -> create/open target.downloading
  -> open cloud stream from offset
  -> write chunks
  -> update file and task progress
  -> verify size/readability
  -> rename target.downloading to target
```

### 6.2 多文件流程

```text
list cloud staging files
  -> create local directories
  -> download files sequentially or limited concurrency
  -> verify each file
  -> verify task aggregate
  -> rename all verified files
  -> delete cloud staging root
```

MVP 默认 `max_concurrent_files_per_task = 1`，避免复杂恢复问题。

### 6.3 校验策略

MVP：

```text
local file exists
local file is readable
local size == cloud size
```

LATER：

```text
hash if provider supports reliable hash
ffprobe for video probing
subtitle encoding detection
```

注意：很多网盘不提供可靠 hash，MVP 不应依赖 hash。

### 6.4 断点续传

如果存在：

```text
Movie.mkv.downloading
```

且大小小于云端文件大小，则尝试从该 offset 继续下载。要求 provider 支持 Range 或等价能力。不支持时必须删除或覆盖临时文件并从头下载，不能静默拼接错误内容。

---

## 7. 进度模型

### 7.1 任务级进度

```json
{
  "task_id": "task_123",
  "status": "downloading",
  "progress": 42.6,
  "done_bytes": 5368709120,
  "total_bytes": 12582912000,
  "speed_bytes_per_sec": 8388608,
  "eta_seconds": 856,
  "current_file": "Interstellar.2014.1080p.mkv"
}
```

### 7.2 文件级进度

```json
{
  "file_id": "file_001",
  "filename": "Interstellar.2014.1080p.mkv",
  "status": "downloading",
  "done_bytes": 5368709120,
  "total_bytes": 12582912000,
  "progress": 42.6
}
```

速度 MUST 使用滑动窗口计算，例如最近 5 秒 done_bytes 增量。不要只使用任务启动以来的平均速度。

---

## 8. 数据模型

MVP 使用 PostgreSQL。以下 DDL 是语义规范，实际迁移可按 SQLAlchemy/Alembic 生成。

### 8.1 sources

```sql
CREATE TABLE sources (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  type TEXT NOT NULL,
  base_url TEXT,
  enabled BOOLEAN NOT NULL DEFAULT TRUE,
  legal_note TEXT,
  trust_level INTEGER NOT NULL DEFAULT 1,
  created_by_user BOOLEAN NOT NULL DEFAULT TRUE,
  config_json JSONB,
  created_at TIMESTAMP NOT NULL,
  updated_at TIMESTAMP NOT NULL
);
```

### 8.2 resources

```sql
CREATE TABLE resources (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  normalized_title TEXT,
  original_title TEXT,
  type TEXT,
  year INTEGER,
  season INTEGER,
  episodes TEXT,
  quality TEXT,
  language TEXT,
  subtitle TEXT,
  description TEXT,
  poster TEXT,
  score REAL NOT NULL DEFAULT 0,
  created_at TIMESTAMP NOT NULL,
  updated_at TIMESTAMP NOT NULL
);
```

### 8.3 resource_links

```sql
CREATE TABLE resource_links (
  id TEXT PRIMARY KEY,
  resource_id TEXT NOT NULL,
  provider TEXT NOT NULL,
  url TEXT NOT NULL,
  code TEXT,
  source_id TEXT,
  source_url TEXT,
  valid BOOLEAN,
  risk_level TEXT NOT NULL DEFAULT 'unknown',
  visibility TEXT NOT NULL DEFAULT 'unknown',
  last_checked_at TIMESTAMP,
  created_at TIMESTAMP NOT NULL,
  updated_at TIMESTAMP NOT NULL
);
```

### 8.4 transfer_tasks

```sql
CREATE TABLE transfer_tasks (
  id TEXT PRIMARY KEY,
  resource_id TEXT,
  link_id TEXT NOT NULL,
  status TEXT NOT NULL,
  mode TEXT NOT NULL,
  cloud_staging_path TEXT,
  target_root TEXT NOT NULL,
  target_path TEXT NOT NULL,
  total_bytes BIGINT NOT NULL DEFAULT 0,
  done_bytes BIGINT NOT NULL DEFAULT 0,
  speed_bytes_per_sec BIGINT NOT NULL DEFAULT 0,
  error_code TEXT,
  error_message TEXT,
  retryable BOOLEAN,
  retry_count INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMP NOT NULL,
  updated_at TIMESTAMP NOT NULL,
  started_at TIMESTAMP,
  completed_at TIMESTAMP
);
```

### 8.5 transfer_files

```sql
CREATE TABLE transfer_files (
  id TEXT PRIMARY KEY,
  task_id TEXT NOT NULL,
  cloud_file_id TEXT,
  cloud_path TEXT NOT NULL,
  target_path TEXT NOT NULL,
  temp_path TEXT NOT NULL,
  filename TEXT NOT NULL,
  size_bytes BIGINT NOT NULL,
  done_bytes BIGINT NOT NULL DEFAULT 0,
  status TEXT NOT NULL,
  error_code TEXT,
  error_message TEXT,
  created_at TIMESTAMP NOT NULL,
  updated_at TIMESTAMP NOT NULL
);
```

### 8.6 transfer_logs

```sql
CREATE TABLE transfer_logs (
  id TEXT PRIMARY KEY,
  task_id TEXT NOT NULL,
  level TEXT NOT NULL,
  event TEXT NOT NULL,
  message TEXT,
  data_json JSONB,
  created_at TIMESTAMP NOT NULL
);
```

### 8.7 settings

运行时可变配置保存到 settings 表，例如 SMB 配置、媒体库路径和部分 transfer 参数。

```sql
CREATE TABLE settings (
  key TEXT PRIMARY KEY,
  value_json JSONB NOT NULL,
  is_sensitive BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMP NOT NULL,
  updated_at TIMESTAMP NOT NULL
);
```

规则：

1. API 返回 settings 时必须隐藏敏感字段明文。
2. SMB password 不应回显给 Web Console。
3. 更新 SMB password 时，空值表示保留原值。

---

## 9. API 契约

### 9.1 错误响应

所有错误使用统一结构：

```json
{
  "error": {
    "code": "NAS_NO_SPACE",
    "message": "Not enough space on target NAS path",
    "retryable": false
  }
}
```

### 9.2 Search

```http
GET /search?q=interstellar&type=movie&year=2014
```

响应：

```json
{
  "query": "interstellar",
  "count": 1,
  "results": [
    {
      "id": "res_001",
      "title": "星际穿越",
      "original_title": "Interstellar",
      "type": "movie",
      "year": 2014,
      "quality": "1080p",
      "score": 0.94,
      "links": [
        {
          "id": "link_001",
          "provider": "quark",
          "code": null,
          "valid": true,
          "risk_level": "unknown"
        }
      ]
    }
  ]
}
```

### 9.3 Resource Detail

```http
GET /resources/{resource_id}
```

### 9.4 Create Transfer

```http
POST /transfers
```

请求：

```json
{
  "resource_id": "res_001",
  "link_id": "link_001",
  "target": {
    "type": "smb",
    "library": "movies",
    "path": "Interstellar (2014)"
  },
  "mode": "move_after_verified_download"
}
```

响应：

```json
{
  "task_id": "task_001",
  "status": "pending"
}
```

### 9.5 Transfer Detail

```http
GET /transfers/{task_id}
```

响应：

```json
{
  "task_id": "task_001",
  "status": "downloading",
  "progress": 42.6,
  "done_bytes": 5368709120,
  "total_bytes": 12582912000,
  "speed_bytes_per_sec": 8388608,
  "eta_seconds": 856,
  "current_file": "Interstellar.2014.1080p.mkv",
  "error": null
}
```

### 9.6 Cancel Transfer

```http
POST /transfers/{task_id}/cancel
```

### 9.7 Retry Transfer

```http
POST /transfers/{task_id}/retry
```

### 9.8 Storage Settings

```http
GET /settings/storage
PUT /settings/storage
POST /settings/storage/test
GET /storage/browse?path=Movies
```

规则：

1. `GET /settings/storage` 不返回 password 明文，只返回 `password_set`。
2. `PUT /settings/storage` 保存后必须热加载 SMB 配置。
3. 修改 SMB 配置必须中断使用旧配置的运行中任务，错误码为 `STORAGE_CONFIG_CHANGED`。
4. `POST /settings/storage/test` 使用最新提交的配置测试 SMB 连接。
5. `GET /storage/browse` 只允许浏览 SMB base path 或 library 目录下的路径。

### 9.9 Source Settings

```http
GET  /sources
POST /sources
GET  /sources/{source_id}
PUT  /sources/{source_id}
POST /sources/{source_id}/enable
POST /sources/{source_id}/disable
POST /sources/{source_id}/test
```

规则：

1. Web Console 只支持管理配置型源和文档/表格型源。
2. 代码型 Source Adapter 不支持前端在线编辑。

---

## 10. 配置规范

示例配置：

```yaml
app:
  name: Sundarr
  host: 0.0.0.0
  port: 8080

database:
  url: postgresql+psycopg://sundarr:sundarr@postgres:5432/sundarr

redis:
  url: redis://redis:6379/0

storage:
  type: smb
  temp_suffix: .downloading
  smb:
    host: fnos.local
    port: 445
    share: media
    username: your_user
    password: your_password
    domain: ""
    base_path: /
    libraries:
      movies: Movies
      tv: TV
      anime: Anime

transfer:
  max_concurrent_tasks: 2
  max_concurrent_files_per_task: 1
  chunk_size: 8388608
  retry_count: 3
  retry_delay_seconds: 10
  verify_mode: size
  speed_window_seconds: 5

cloud:
  staging_root: /Sundarr/_staging

search:
  cache_ttl_seconds: 600
  timeout_seconds: 10
  source_failure_breaker_seconds: 300
```

规则：

1. MUST 支持环境变量覆盖配置。
2. MUST 不把 cookie、token、密码写入普通配置样例。
3. MVP 可使用 `.env` 和数据库 settings 保存个人配置；复杂 secret backend 放到 LATER。

运行时可变配置 SHOULD 保存到数据库 settings 表或等价存储中，包括：

```text
storage.smb
storage.libraries
source configuration
部分 transfer 参数
```

SMB 配置必须支持热加载。修改 SMB 配置后不需要重启 API 或 Worker。

---

## 11. 安全规则

### 11.1 凭据安全

敏感信息包括：

```text
cloud cookie/token
SMB username/password
source auth token
API token
```

规则：

1. MUST 不输出到日志。
2. MUST 不返回给前端或 AI 工具。
3. MUST 不提交到仓库。
4. MVP 不实现复杂 secret backend。

### 11.2 路径安全

用户传入 target path 时必须：

1. 解析为规范 SMB 相对路径。
2. 校验路径位于 `storage.smb.base_path` 或配置的 library 子目录下。
3. 拒绝 `..` 路径穿越。
4. 拒绝写入 SMB share 允许范围之外的路径。
5. 拒绝覆盖已存在正式文件，除非未来显式支持 overwrite 策略。

### 11.3 删除安全

删除 cloud staging 前必须同时满足：

```text
task.status == cleaning_cloud
all transfer_files.status == completed
all target files exist
all target sizes match source sizes
cloud_staging_path == cloud.staging_root + "/" + task_id or is a child path of it
```

MUST 永远不允许删除 staging_root 之外的路径。

### 11.4 日志安全

日志可记录：

```text
task_id
source_id
provider
status
error_code
duration
bytes
```

日志不得记录：

```text
cookie
token
password
authorization header
完整私密分享链接中的敏感参数
```

---

## 12. 错误码

MVP 错误码：

```text
SEARCH_SOURCE_TIMEOUT
SEARCH_SOURCE_FAILED
LINK_PARSE_FAILED
CLOUD_SAVE_FAILED
CLOUD_FILE_LIST_FAILED
CLOUD_RANGE_NOT_SUPPORTED
CLOUD_STREAM_FAILED
TARGET_PATH_INVALID
TARGET_PATH_OUTSIDE_ROOT
NAS_NO_SPACE
NAS_WRITE_FAILED
VERIFY_FAILED
RENAME_FAILED
CLOUD_CLEANUP_FAILED
TASK_CANCELLED
STORAGE_CONFIG_CHANGED
```

错误必须标记是否可重试：

```text
retryable = true   timeout, temporary network error, cloud stream interrupted
retryable = true   storage config changed while task is running
retryable = false  invalid target path, no permission, verification mismatch after retry limit
```

---

## 13. 推荐代码结构

```text
sundarr/
  app/
    main.py
    config.py
    api/
      health.py
      sources.py
      search.py
      resources.py
      transfers.py
      settings.py
      storage.py
    core/
      database.py
      redis.py
      errors.py
      logging.py
      security.py
      paths.py
    models/
      source.py
      resource.py
      transfer.py
      setting.py
    schemas/
      source.py
      resource.py
      transfer.py
      error.py
      setting.py
    sources/
      base.py
      website.py
      document.py
      sheet.py
    parsers/
      html.py
      text.py
      link_extractor.py
      title.py
    services/
      search_service.py
      resource_service.py
      dedupe_service.py
      rank_service.py
      transfer_service.py
      settings_service.py
    cloud/
      base.py
      quark.py
      aliyun.py
    storage/
      base.py
      local_writer.py
      smb_writer.py
    workers/
      transfer_worker.py
      cleanup_worker.py
  web/
    package.json
    vite.config.ts
    src/
  migrations/
  tests/
  docker-compose.yml
  Dockerfile
  README.md
```

---

## 14. 核心伪代码

### 14.1 搜索聚合

```python
async def aggregate_search(keyword: str, filters: SearchFilters) -> list[ResourceCandidate]:
    raw_items = []

    for source in enabled_sources:
        try:
            items = await source.search(keyword)
            raw_items.extend(items)
        except Exception as exc:
            log_source_error(source.id, exc)

    candidates = []
    for item in raw_items:
        links = extract_cloud_links(item["raw_content"])
        resource = normalize_raw_item(item, links)
        candidates.append(resource)

    deduped = deduplicate(candidates)
    ranked = rank(keyword, deduped)
    save_to_resource_library(ranked)
    return ranked
```

### 14.2 搬运任务

```python
async def run_transfer_task(task_id: str) -> None:
    task = get_task_for_update(task_id)
    set_status(task, "staging_to_cloud")

    staging_path = await cloud.save_share(
        url=task.link.url,
        code=task.link.code,
        target_dir=f"/Sundarr/_staging/{task.id}",
    )
    set_cloud_staging_path(task, staging_path)

    files = await cloud.list_files(staging_path)
    create_transfer_files(task, files)
    update_total_bytes(task, sum(file.size for file in files))
    set_status(task, "cloud_ready")

    set_status(task, "downloading")
    for file in files:
        assert_not_cancelled(task.id)
        await download_file_to_temp_path(task, file)

    set_status(task, "verifying")
    verify_task_files(task.id)

    set_status(task, "renaming")
    rename_verified_temp_files(task.id)
    mark_task_files_completed(task.id)

    set_status(task, "cleaning_cloud")
    assert_safe_cloud_delete_path(staging_path, task.id)
    await cloud.delete(staging_path)

    set_status(task, "completed")
```

### 14.3 下载单文件

```python
async def download_file_to_temp_path(task: TransferTask, cloud_file: CloudFile) -> None:
    target_path = build_safe_target_path(task, cloud_file)
    temp_path = target_path + settings.storage.temp_suffix
    offset = get_existing_size(temp_path)

    if offset > cloud_file.size:
        remove_invalid_temp_file(temp_path)
        offset = 0

    stream = await cloud.open_file_stream(cloud_file.id, offset=offset)

    async with writer.open_append(temp_path) as file:
        async for chunk in stream:
            assert_not_cancelled(task.id)
            await file.write(chunk)
            offset += len(chunk)
            update_progress(task.id, cloud_file.id, offset)

    verify_size(temp_path, cloud_file.size)
    mark_file_verified(task.id, cloud_file.id)
```

---

## 15. MVP 开发顺序

Agent 必须按以下顺序推进，除非用户明确改变优先级。

### Phase 0: Project Skeleton

交付：

```text
FastAPI app
Dockerfile
docker-compose.yml
PostgreSQL
Redis
GET /health
settings loader
pytest baseline
```

### Phase 1: Persistence Models

交付：

```text
Alembic migrations
Source model
Resource model
ResourceLink model
TransferTask model
TransferFile model
TransferLog model
```

### Phase 2: Search And Resource Library

交付：

```text
BaseSource
one example source
parser pipeline
link extractor
normalizer
deduper
ranker
GET /search
GET /resources/{id}
```

### Phase 3: Cloud Staging

交付：

```text
CloudProvider interface
one provider implementation or mock provider for local testing
save_share
list_files
open_file_stream
delete with safe path guard
```

### Phase 4: Storage Writer

交付：

```text
SmbWriter
LocalWriter for tests
SMB connection test
SMB directory browse
storage settings hot reload
STORAGE_CONFIG_CHANGED interruption
.downloading temp files
```

### Phase 5: Transfer Worker

交付：

```text
POST /transfers
GET /transfers/{id}
worker state machine
progress update
size verification
rename
```

### Phase 6: Cleanup And Recovery

交付：

```text
safe cloud cleanup
retry failed task
cancel task
worker startup recovery
transfer logs
```

### Phase 7: Web Console

交付：

```text
React + Vite app
search page
transfer task page
SMB settings page
SMB connection test
SMB directory browser
source settings page
running task interruption notice for STORAGE_CONFIG_CHANGED
```

### Phase 8: AI Friendly API

交付：

```text
stable tool-like endpoints
candidate explanation fields
default target library mapping
```

---

## 16. Agent 任务拆分

如果需要按 issue 开发，使用以下任务列表。每个 issue 应包含测试或最小验证方式。

### Issue 1: Initialize Project

```text
Create FastAPI project
Add Dockerfile and docker-compose.yml
Add PostgreSQL and Redis services
Add /health
Add config loader
Add pytest smoke test
```

### Issue 2: Define Persistence Layer

```text
Create SQLAlchemy models
Create Alembic migrations
Add database session management
Add repository helpers only where needed
```

### Issue 3: Implement Source And Parsing Pipeline

```text
Define BaseSource
Add one example source
Implement HTML/text parser
Implement source timeout and error isolation
```

### Issue 4: Implement Cloud Link Extractor

```text
Detect provider url
Detect extraction code
Return provider/url/code/confidence
Add tests for multiline and multiple-link text
```

### Issue 5: Implement Search Service

```text
Aggregate sources
Normalize raw items
Deduplicate candidates
Rank results
Persist resources and links
Expose /search and /resources/{id}
```

### Issue 6: Implement Cloud Provider Interface

```text
Define CloudProvider
Implement provider or mock provider
Implement safe staging path rules
Implement stream opening with optional offset
```

### Issue 7: Implement Storage Writer

```text
Define StorageWriter
Implement SmbWriter
Implement LocalWriter for tests
Implement SMB settings hot reload
Interrupt running tasks with STORAGE_CONFIG_CHANGED
Add SMB connection test
Add SMB directory browse
```

### Issue 8: Implement Transfer Worker

```text
Create transfer task
Execute state machine
Download to .downloading
Persist progress
Expose task detail
```

### Issue 9: Implement Verification And Rename

```text
Verify file exists
Verify file size
Rename temp file to final file
Reject overwrite by default
```

### Issue 10: Implement Cleanup, Retry And Cancel

```text
Delete only safe cloud staging path
Retry based on failure state
Cancel pending/downloading tasks
Add transfer logs
```

### Issue 11: Implement Web Console

```text
Create React + Vite app
Implement search page
Implement transfer task page
Implement SMB settings page
Implement source settings page
Show STORAGE_CONFIG_CHANGED interruption notice
```

### Issue 12: Implement AI-Friendly API

```text
Define stable AI tool responses
Add default target library mapping
Return candidate explanations
```

---

## 17. 测试要求

MVP 至少覆盖：

```text
config loading
target path validation
cloud staging delete guard
link extraction
normalization basics
dedupe basics
SMB writer mock
SMB config hot reload
STORAGE_CONFIG_CHANGED interrupts running task
transfer state transition
download resume offset logic
verification failure keeps cloud staging
cleanup only after verification success
API error response format
```

不得只依赖真实网盘做测试。MUST 提供 mock cloud provider 或本地文件 provider 供自动化测试使用。

---

## 18. 与外部工具关系

### 18.1 OpenList

OpenList MAY 作为后续可选文件列表或访问后端，不是 MVP 核心依赖。

原因：OpenList 更适合挂载和浏览，不适合作为 Sundarr 的任务状态机、进度统计和安全删除核心。

### 18.2 FNOS

FNOS 在 MVP 中只作为 NAS 和 SMB 共享提供者。Sundarr 不依赖 FNOS 私有 API。

### 18.3 rclone

rclone MAY 在后续作为 Transfer Driver：

```text
TransferDriver:
  - native
  - rclone
  - webdav
```

MVP 使用 native stream download，确保进度和状态可控。

---

## 19. 未来扩展

LATER 功能必须建立在 MVP 主链路稳定之后。

```text
Web UI
AI Agent integration
TMDb metadata enrichment
NFO generation
media library refresh
subscription search
multi NAS target
multi cloud provider
native SMB driver
rclone driver
Prometheus metrics
OpenTelemetry tracing
```

---

## 20. 最终目标

Sundarr 最终应成为一个网盘媒体资源自动化归档系统：

```text
发现资源 -> 暂存资源 -> 搬运资源 -> 校验资源 -> 清理云端 -> 沉淀到本地 NAS 媒体库
```

目标用户体验：

```text
用户：帮我找《星际穿越》1080p 并保存到电影库。
Sundarr：
  1. 搜索用户配置的合法来源。
  2. 返回候选资源和来源说明。
  3. 用户确认后转存到个人网盘 staging 目录。
  4. 下载到 NAS 电影目录的 .downloading 文件。
  5. 校验成功后 rename 为正式文件。
  6. 删除云端 staging 目录。
  7. 返回任务完成状态。
```

项目口号：

```text
Sundarr — Search cloud media. Stage it. Bring it home.
```

中文：

```text
Sundarr：搜索云端媒体，临时中转，归档回家。
```
