# 网盘直链下载规范

本文档定义 Sundarr 网盘直链下载功能的历史预研架构、边界和验收标准。该能力不包含在 MVP 中，没有近期排期；Alist、真实网盘 Provider 和 Cordis 决策均不改变这一边界。

---

## 1. 功能概述

在现有"搜索 → 保存到网盘 → SMB 挂载 → 远程媒体库同步到本地媒体库"链路之外，后续可新增一条**快速通道**：

```text
搜索资源
-> 提取网盘分享链接
-> 用户登录网盘账号（Cookie/扫码）
-> 脚本调用网盘 API 获取直链（CDN 地址）
-> aria2 多线程下载到本地
-> 写入媒体库目录
-> 校验
-> rename
```

核心价值：**跳过"保存到自己网盘"和"SMB 挂载"两个步骤**，直接从网盘 CDN 下载。

---

## 2. 功能分块

### Block 1: 网盘认证管理

**职责**：管理用户对各网盘的登录态（Cookie/Token）。

```text
支持网盘：夸克、百度、阿里云盘、123云盘（高级功能首个实现可优先验证夸克）
认证方式：
  - Cookie 手动输入
  - 扫码登录（获取 Cookie）
  - Token 刷新（如百度 AccessToken）
存储：加密存储 Cookie/Token 到 settings 表
过期检测：定时验证 Cookie 有效性
```

**不负责**：不负责文件下载、不负责链接解析。

### Block 2: 直链提取器

**职责**：将网盘分享链接转换为可下载的 CDN 直链。

```text
输入：分享链接 + 可选提取码 + 认证 Cookie
处理：
  - 识别网盘类型（从 URL 域名判断）
  - 调用对应网盘 API 获取文件元数据
  - 调用对应网盘 API 获取下载直链（dlink/download_url）
输出：直链 URL + 文件名 + 文件大小 + 请求头（UA/Referer）
```

**不负责**：不负责实际下载、不负责认证管理。

### Block 3: Aria2 下载服务

**职责**：通过 aria2 RPC 多线程下载文件到本地。

```text
部署：docker-compose 服务
接口：JSON-RPC 2.0 over HTTP
能力：
  - 多线程分片下载
  - 断点续传
  - 并发任务管理
  - 进度回调
集成：Sundarr Worker 通过 RPC 提交下载任务
```

**不负责**：不负责直链获取、不负责文件归档。

### Block 4: 下载任务编排

**职责**：串联认证 → 直链获取 → aria2 下载 → 文件归档的完整流程。

```text
输入：资源链接 + 目标媒体库
流程：
  1. 检查目标网盘 Cookie 有效性
  2. 调用直链提取器获取 CDN 链接
  3. 提交 aria2 RPC 下载任务
  4. 等待下载完成（轮询或回调）
  5. 校验文件大小
  6. rename 到目标媒体库目录
输出：下载完成的本地文件路径
```

**不负责**：不负责 Cookie 管理细节、不负责 aria2 部署。

---

## 3. 功能边界

### 做

```text
夸克网盘扫码登录
夸克网盘直链提取
百度网盘 Cookie 认证 + 直链提取（后续）
阿里云盘 Cookie 认证 + 直链提取（后续）
123云盘 Cookie 认证 + 直链提取（后续）
aria2 Docker 部署
aria2 RPC 下载
多线程下载
断点续传
下载进度跟踪
文件大小校验
下载完成后写入媒体库目录
Web Console 网盘账号管理页面
Web Console 直链下载任务页面
```

### 不做

```text
网盘限速破解
绕过网盘会员限制
绕过网盘验证码
网盘文件管理（删除、移动、重命名）
网盘文件预览
完整网盘 UI
多用户权限
BT/磁力下载
```

---

## 4. 支持网盘优先级

| 优先级 | 网盘 | 认证方式 | 直链 API | 状态 |
|--------|------|----------|----------|------|
| P0 | 夸克网盘 | 扫码登录 | `drive-pc.quark.cn/1/clouddrive/file/download` | 首批实现 |
| P1 | 百度网盘 | Cookie + AccessToken | `pan.baidu.com/rest/2.0/xpan/multimedia` | 后续 |
| P1 | 阿里云盘 | Cookie | `api.aliyundrive.com/v2/file/get_download_url` | 后续 |
| P2 | 123云盘 | Cookie | `123pan.com/api/file/download_info` | 后续 |
| P2 | UC网盘 | Cookie | `pc-api.uc.cn/1/clouddrive/file/download` | 后续 |
| P3 | 天翼云盘 | OAuth | `api.cloud.189.cn/open/file/getFileDownloadUrl.action` | 后续 |
| P3 | 迅雷云盘 | Cookie | 镜像域名列表 | 后续 |
| P3 | 移动云盘 | Cookie | `personal-kd-njs.yun.139.com/hcy/file/getDownloadUrl` | 后续 |

---

## 5. 技术方案

### 5.1 网盘认证模块

```python
# 抽象接口
class CloudAuth(ABC):
    @abstractmethod
    async def get_qrcode(self) -> QRCodeResult: ...

    @abstractmethod
    async def check_qrcode_status(self, token: str) -> AuthResult: ...

    @abstractmethod
    async def validate_cookie(self, cookie: str) -> bool: ...

    @abstractmethod
    def get_headers(self) -> dict: ...

# 夸克实现
class QuarkAuth(CloudAuth):
    # 扫码登录流程：
    # 1. GET /1/clouddrive/passport/qrcode/create → 获取二维码 URL
    # 2. 轮询 GET /1/clouddrive/passport/qrcode/status?token=xxx
    # 3. 用户手机扫码确认
    # 4. 获取 cookie（__puus、__pus 等）
```

### 5.2 直链提取模块

```python
# 抽象接口
class DirectLinkExtractor(ABC):
    @abstractmethod
    async def extract(self, share_url: str, password: str = None) -> FileInfo: ...

# 夸克实现
class QuarkExtractor(DirectLinkExtractor):
    # 流程：
    # 1. 解析分享链接，提取 share_id
    # 2. POST /1/clouddrive/share/sharepage/token → 获取 share_token
    # 3. POST /1/clouddrive/share/sharepage/detail → 获取文件列表
    # 4. POST /1/clouddrive/file/download → 获取 download_url（直链）
    # 返回：FileInfo(url, filename, size, headers)
```

### 5.3 Aria2 集成

```yaml
# docker-compose.yml 新增
services:
  aria2:
    image: p3terx/aria2-pro
    container_name: sundarr-aria2
    ports:
      - "6800:6800"    # RPC
      - "6888:6888"    # BT
      - "6888:6888/udp"
    volumes:
      - ./downloads:/downloads
      - ./aria2-config:/config
    environment:
      - RPC_SECRET=${ARIA2_RPC_SECRET}
      - RPC_PORT=6800
      - DOWNLOAD_ROOT=/downloads
      - MAX_CONCURRENT_DOWNLOADS=5
      - MAX_CONNECTION_PER_SERVER=16
      - SPLIT=16
      - MIN_SPLIT_SIZE=5M
    restart: unless-stopped
```

```python
# Aria2 RPC 客户端
class Aria2Client:
    def __init__(self, rpc_url: str, secret: str): ...

    async def add_uri(self, url: str, filename: str, 
                      headers: dict = None,
                      out_dir: str = None) -> str:
        """提交下载任务，返回 GID"""

    async def get_status(self, gid: str) -> DownloadStatus:
        """查询下载状态"""

    async def pause(self, gid: str) -> bool: ...
    async def unpause(self, gid: str) -> bool: ...
    async def remove(self, gid: str) -> bool: ...

    async def get_global_stat(self) -> GlobalStat:
        """获取全局下载统计"""
```

### 5.4 数据模型

```sql
-- 网盘账号表
CREATE TABLE cloud_accounts (
    id SERIAL PRIMARY KEY,
    provider VARCHAR(32) NOT NULL,        -- quark/baidu/aliyun/123pan
    account_name VARCHAR(128),             -- 用户自定义名称
    cookie_encrypted TEXT,                 -- 加密存储的 Cookie
    token_encrypted TEXT,                  -- 加密存储的 Token
    expires_at TIMESTAMP,                 -- 过期时间
    status VARCHAR(16) DEFAULT 'active',  -- active/expired/invalid
    last_validated_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 直链下载任务表
CREATE TABLE direct_download_tasks (
    id SERIAL PRIMARY KEY,
    share_url TEXT NOT NULL,               -- 原始分享链接
    extract_code VARCHAR(16),              -- 提取码
    provider VARCHAR(32) NOT NULL,         -- 网盘类型
    account_id INT REFERENCES cloud_accounts(id),
    -- 提取结果
    direct_link_url TEXT,                  -- CDN 直链
    filename VARCHAR(512),
    file_size BIGINT,
    request_headers JSONB,                 -- 下载所需的 headers
    -- aria2 信息
    aria2_gid VARCHAR(32),                -- aria2 任务 GID
    aria2_status VARCHAR(16),             -- active/completed/error/removed
    -- 本地文件
    local_path TEXT,                       -- 最终文件路径
    local_size BIGINT,
    -- 状态
    status VARCHAR(16) DEFAULT 'pending',
    -- pending -> extracting -> downloading -> verifying -> completed
    -- pending -> extracting -> failed
    -- downloading -> failed
    error_code VARCHAR(64),
    error_message TEXT,
    retryable BOOLEAN DEFAULT FALSE,
    retry_count INT DEFAULT 0,
    -- 时间
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);
```

### 5.5 API 设计

```text
认证管理：
  GET  /api/v1/cloud-accounts              # 列出网盘账号
  POST /api/v1/cloud-accounts              # 添加网盘账号（手动 Cookie）
  POST /api/v1/cloud-accounts/qr-login     # 扫码登录（获取二维码）
  GET  /api/v1/cloud-accounts/qr-status    # 轮询扫码状态
  POST /api/v1/cloud-accounts/{id}/validate # 验证 Cookie 有效性
  DELETE /api/v1/cloud-accounts/{id}        # 删除账号

直链下载：
  POST /api/v1/direct-downloads/extract     # 提取直链（不下载）
  POST /api/v1/direct-downloads             # 提取直链 + 提交 aria2 下载
  GET  /api/v1/direct-downloads             # 列出直链下载任务
  GET  /api/v1/direct-downloads/{id}        # 查询任务状态
  POST /api/v1/direct-downloads/{id}/retry  # 重试失败任务
  POST /api/v1/direct-downloads/{id}/cancel # 取消任务

Aria2 状态：
  GET  /api/v1/aria2/status                # aria2 服务状态
  POST /api/v1/aria2/test                  # 测试 aria2 连接
```

---

## 6. 实现阶段

### Phase 12.1: Aria2 服务集成

**目标**：aria2 作为 Docker 服务接入 Sundarr，可通过 RPC 下载文件。

**交付物**：

```text
docker-compose.yml 增加 aria2 服务
Aria2Client RPC 客户端
aria2 连接测试 API
aria2 状态查询 API
aria2 配置（RPC 地址、密钥）存入 settings
```

**验收标准**：

```text
docker compose up -d aria2 可启动 aria2 服务。
POST /api/v1/aria2/test 返回连接成功。
可通过 RPC 提交一个 HTTP 下载任务。
下载文件存入 /downloads 目录。
GET /api/v1/aria2/status 返回 aria2 全局状态。
```

**停止条件**：

```text
aria2 Docker 服务可独立启动。
Aria2Client 可完成 add_uri + get_status 基础流程。
pytest 通过。
docker-compose.yml 变更不影响现有服务。
```

### Phase 12.2: 夸克网盘认证

**目标**：实现夸克网盘扫码登录和 Cookie 管理。

**交付物**：

```text
CloudAuth 抽象接口
QuarkAuth 实现
扫码登录 API（获取二维码）
扫码状态轮询 API
Cookie 加密存储
Cookie 有效性验证
cloud_accounts 数据模型和迁移
Web Console 网盘账号管理页面
```

**验收标准**：

```text
POST /api/v1/cloud-accounts/qr-login 返回二维码图片 URL 或 base64。
用户手机扫码后，轮询 GET /api/v1/cloud-accounts/qr-status 返回成功。
Cookie 自动加密存储到 cloud_accounts 表。
POST /api/v1/cloud-accounts/{id}/validate 可验证 Cookie 有效性。
过期 Cookie 标记为 expired。
Web Console 可查看已添加账号列表。
Web Console 可删除账号。
Cookie 不以明文存储或返回。
```

**停止条件**：

```text
扫码登录完整流程可跑通。
Cookie 加密存储有测试覆盖。
pytest 通过。
Web Console 构建通过。
```

### Phase 12.3: 夸克直链提取

**目标**：通过分享链接 + Cookie 获取夸克网盘文件直链。

**交付物**：

```text
DirectLinkExtractor 抽象接口
QuarkExtractor 实现
分享链接解析
share_token 获取
文件元数据获取
直链（download_url）提取
请求头构造（UA、Referer）
直链提取 API
```

**验收标准**：

```text
给定有效分享链接 + 有效 Cookie，可返回直链 URL。
返回信息包含：直链 URL、文件名、文件大小、请求头。
提取失败时返回明确错误码。
单文件和多文件分享链接均能处理。
提取码分享链接能正确传入提取码。
```

**停止条件**：

```text
单文件分享链接可成功提取直链。
多文件分享链接可列出文件并逐个提取。
pytest 覆盖成功和失败路径。
不依赖 aria2（纯提取，不含下载）。
```

### Phase 12.4: 直链下载完整流程

**目标**：串联认证 → 直链提取 → aria2 下载 → 文件归档。

**交付物**：

```text
direct_download_tasks 数据模型和迁移
下载任务编排逻辑
aria2 下载进度轮询
下载完成回调或轮询
文件大小校验
rename 到目标路径
任务状态机：pending -> extracting -> downloading -> verifying -> completed
失败处理和错误码
重试机制
Web Console 直链下载任务页面
```

**验收标准**：

```text
POST /api/v1/direct-downloads 可创建下载任务。
任务自动完成：提取直链 → aria2 下载 → 校验 → rename。
GET /api/v1/direct-downloads/{id} 可查询进度和状态。
下载完成后文件存在于目标路径。
文件大小校验失败时任务标记为 failed。
失败任务可重试。
Web Console 可查看任务列表和详情。
```

**停止条件**：

```text
端到端流程：分享链接 → 直链 → 下载 → 本地文件，可跑通。
进度可追踪。
pytest 通过。
Web Console 构建通过。
```

### Phase 12.5: 百度/阿里云盘扩展（后续）

**目标**：扩展支持百度网盘和阿里云盘。

**交付物**：

```text
BaiduAuth + BaiduExtractor
AliyunAuth + AliyunExtractor
各网盘特有的认证流程
各网盘特有的直链提取逻辑
```

**验收标准**：

```text
各网盘扫码或 Cookie 登录可用。
各网盘直链提取可用。
统一接口，上层无需感知网盘差异。
```

---

## 7. 与现有模块的关系

```text
搜索模块（Phase 2/9）
  ↓ 输出：资源链接（含网盘分享链接）
直链下载模块（Phase 12）
  ↓ 输入：网盘分享链接
  ↓ 输出：本地文件
媒体库目录（Phase 8）
  ↓ 直接写入媒体库目录
  ↓ 不经过 SMB
```

与 Phase 8 的区别：

```text
Phase 8（下载到本地）：
  来源：已挂载的网盘 SMB 目录
  方式：SMB 协议读取
  前置：用户需先保存到网盘 + 配置 SMB 挂载

Phase 12（直链下载）：
  来源：网盘分享链接
  方式：HTTP 直链 + aria2 多线程下载
  前置：用户只需登录网盘账号
  优势：跳过保存到网盘和 SMB 挂载
```

---

## 8. 安全要求

```text
Cookie/Token 加密存储，不写入日志
Cookie/Token 不通过 API 明文返回
aria2 RPC 密钥随机生成，不硬编码
下载文件先写入临时目录，校验后 rename
不存储用户密码明文
不绕过网盘安全机制
不请求网盘 API 之外的接口
```

---

## 9. 测试策略

```text
单元测试：
  CloudAuth 接口 mock 测试
  DirectLinkExtractor mock 测试
  Aria2Client mock 测试
  任务状态机测试

集成测试：
  aria2 Docker 启动 + RPC 连接测试
  夸克扫码登录流程测试（需真实 Cookie）
  直链提取测试（需真实分享链接 + Cookie）

不依赖：
  不依赖真实网盘账号运行单元测试
  不依赖真实下载运行状态机测试
  Mock Cookie 和直链用于 CI
```

---

## 10. 配置项

```yaml
# aria2 配置
aria2:
  rpc_url: "http://aria2:6800/jsonrpc"
  rpc_secret: ""  # 自动生成
  max_concurrent: 5
  max_connections_per_server: 16
  split: 16
  min_split_size: "5M"
  download_root: "/downloads"

# 网盘认证配置
cloud_auth:
  cookie_storage: "encrypted"  # encrypted/plain
  cookie_ttl_check: 3600       # 秒，Cookie 有效期检查间隔
  qr_login_timeout: 120        # 秒，扫码登录超时
```
