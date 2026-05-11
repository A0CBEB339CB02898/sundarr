# 产品范围

本文档定义 Sundarr 的产品目标、MVP 范围和明确不做事项。

---

## 1. 项目定位

Sundarr 是一个个人自用的远程媒体库同步到本地媒体库自动化系统。

核心目标：

```text
搜索合法资源
-> 提取网盘链接
-> 用户手动保存到网盘
-> 网盘通过 SMB 暴露为远程媒体库
-> 将远程媒体库同步到本地媒体库
-> 校验文件
-> 删除来源文件和空目录
```

Sundarr 不是：

```text
BT 下载器
盗版资源分发系统
网盘破解工具
OpenList 替代品
完整 NAS 文件管理器
完整媒体库 UI / 播放器
```

---

## 2. 目标用户场景

目标用户是个人 NAS 用户。

典型流程：

```text
用户在 Web Console 搜索媒体资源。
Sundarr 从多个已配置来源聚合搜索结果。
用户选择候选资源和目标媒体库。
用户手动将资源保存到网盘。
NAS 或挂载服务将网盘远程挂载为目录，并通过 SMB 暴露给 Sundarr。
Sundarr 根据同步绑定，将远程媒体库中的文件同步到对应本地媒体库目录。
下载期间写入 .downloading 临时文件。
校验成功后 rename 为正式文件。
最后按配置删除来源文件和空目录。
```

---

## 3. MVP 必须做

MVP 必须完成最小可用闭环。

功能范围：

```text
FastAPI API 后端
React + Vite 轻量 Web Console
PostgreSQL 持久化
Redis 缓存和实时进度辅助
多源 Source Adapter 框架
Cloud Link Extractor
Resource Library
Mock/Local Cloud Provider
远程媒体库同步到本地媒体库规范
本地媒体库管理，支持创建 movie / series / unclassified 等本地媒体库
本地媒体库绑定到某个 SMB 连接下的本地 NAS 目录
远程媒体库绑定到某个 SMB 连接下的远程目录（如网盘挂载目录）
同步绑定连接远程媒体库（来源）和本地媒体库（目标）
应用内 SmbWriter
LocalWriter 测试实现
Transfer Worker
.downloading 临时文件
大小校验
成功后 rename
Cloud Provider / cloud staging 保留为可选扩展和测试抽象
成功后删除挂载来源文件和空目录
任务取消和重试
多个 SMB 连接查看、修改、测试连接、目录浏览
媒体源配置管理
```

---

## 4. Web Console 范围

MVP 包含轻量 Web Console。

必须覆盖：

```text
搜索资源
展示候选结果
查看资源详情
管理已安装代码型 Source Adapter
查看和修改多个 SMB 连接
测试 SMB 连接
浏览 SMB 目录
创建和管理媒体库
创建归档任务
查看任务状态和进度
取消 / 重试任务
显示 STORAGE_CONFIG_CHANGED 中断提示
配置远程媒体库到本地媒体库的同步绑定
配置未分类目录
```

不做：

```text
完整媒体库 UI / 海报墙 / 播放器
海报墙
播放器
完整文件管理器
拖拽式管理
任意 NAS 文件删除
登录注册
多用户权限
```

---

## 5. 权限范围

MVP 按个人自用项目处理。

不做：

```text
用户注册
用户登录
多用户权限
角色管理
OAuth
API token 管理
审计系统
```

仍保留最低误操作保护：

```text
不能删除 cloud staging 根目录之外的路径
不能删除挂载来源根目录之外的路径
不能写入 SMB 配置允许范围之外的路径
cookie/token/password 不写入日志
校验失败不清理 cloud staging
校验失败不删除挂载来源文件
默认不覆盖已有正式文件
```

---

## 6. 媒体源范围

多源即时搜索是核心能力。Sundarr 要做的是从真实媒体网站即时搜索资源，而不是要求用户维护本地资源表。

媒体源近期主线：

```text
真实网站代码型 Source Adapter 框架
每个真实网站通过一个代码型 Adapter 接入
多个 Adapter 并发搜索
结果统一进入 Search Pipeline
```

代码型 Source Adapter 必须通过代码实现和部署，不允许在 Web Console 中在线编辑 Python 代码。

当前 MVP 的媒体源范围是框架能力，不等于真实网站 Adapter 已经完成。

Phase 0-7 已覆盖：

```text
Source Adapter 抽象
ExampleSource 示例源
Search Pipeline
sources 管理 API
Web Console Sources 页面
```

Phase 0-7 未覆盖：

```text
真实站点爬虫
真实网站代码型 Adapter SDK 完整开发体验
多个真实网站 Adapter 并发搜索验收
站点分页和反爬策略
通过 Web Console 配置复杂爬虫
真实媒体源手动验收
```

真实媒体源开发属于后续独立大阶段，不作为 Phase 0-7 或 Phase 8 Download To Local 的阻塞项。

后续可单独实验：

```text
文档型网站是否存在可通用读取模式
文档型网站是否值得抽象为专用 Adapter 模板
```

该实验不等于承诺实现通用在线文档读取，也不要求用户维护本地文档。

---

## 7. SMB 范围

MVP 不依赖系统 SMB mount。

正式 NAS 写入方式：

```text
应用内 SmbWriter
```

测试和开发方式：

```text
LocalWriter
```

SMB 配置支持多个连接，并可在 Web Console 修改和热加载。

修改某个 SMB 连接配置时：

```text
关闭旧 SMB 连接
中断使用旧配置的运行中任务
任务进入 failed
错误码 STORAGE_CONFIG_CHANGED
retryable = true
保留 .downloading 文件
保留 cloud staging
使用该连接的新任务和重试任务使用最新 SMB 配置
```

媒体库管理模块只能引用已配置的 SMB 连接和目录，不重复填写 SMB host、share、username、password。

媒体库在 Sundarr 中指本地 NAS 上的逻辑媒体目录，例如 movie、series、unclassified。MVP 需要提供媒体库管理模块，用于创建媒体库并绑定到某个 SMB 连接下的本地目录。

同步模块不直接重复配置目标 SMB 目录，而是通过同步绑定连接远程媒体库（来源）和本地媒体库（目标）。Worker 定时扫描这些绑定，并将稳定文件同步到绑定的本地媒体库目录。

媒体库管理是目录绑定管理能力，不等于完整媒体库 UI、海报墙、播放器或媒体刮削。

---

## 8. MVP 不做事项

MVP 不做：

```text
BT / 磁力 / 种子下载
盗版资源分发或资源托管
绕过网盘限制、破解会员、绕过验证码
复杂 Web UI
完整媒体库 UI
多用户权限系统
媒体刮削
海报墙
NFO 生成
Playwright 重型抓取
OpenList 核心搬运层
rclone 核心传输层
多 provider 一次性全量接入
国内封闭网盘直接下载作为 MVP 核心搬运层
将网盘直链下载（Cloud Direct Download）纳入 MVP 或近期主线
绕过网盘 App、验证码、会员或风控限制
真实媒体源通用爬虫框架
通过 Web Console 配置复杂网站爬虫
要求用户维护本地文档/表格作为主要媒体源
```

---

## 9. 后续扩展

MVP 稳定后可考虑：

```text
完整 Web UI
AI Agent 深度集成
TMDb 元数据补全
NFO 生成
订阅搜索
多 NAS 目标
多云盘 provider
Sundarr 内配置挂载网盘
保存到网盘
网盘直链下载（Cloud Direct Download，高级功能）
AI / 外部数据辅助自动分类
rclone driver
OpenList 可选后端
Prometheus metrics
OpenTelemetry tracing
```
