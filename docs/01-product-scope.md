# 产品范围

本文档定义 Sundarr 的产品目标、MVP 范围和明确不做事项。

---

## 1. 项目定位

Sundarr 是一个个人自用的网盘媒体资源自动化归档系统。

核心目标：

```text
搜索合法资源
-> 提取网盘链接
-> 转存到个人网盘临时目录
-> 下载到 NAS
-> 校验文件
-> 清理云端临时目录
```

Sundarr 不是：

```text
BT 下载器
盗版资源分发系统
网盘破解工具
OpenList 替代品
完整 NAS 文件管理器
完整媒体库管理系统
```

---

## 2. 目标用户场景

目标用户是个人 NAS 用户。

典型流程：

```text
用户在 Web Console 搜索媒体资源。
Sundarr 从多个已配置来源聚合搜索结果。
用户选择候选资源和目标媒体库目录。
Sundarr 将分享链接转存到个人网盘 staging 目录。
Sundarr 从 staging 目录下载文件到 NAS SMB share。
下载期间写入 .downloading 临时文件。
校验成功后 rename 为正式文件。
最后删除 cloud staging 目录。
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
至少 1 个真实或可替换 Cloud Provider 接口
应用内 SmbWriter
LocalWriter 测试实现
Transfer Worker
.downloading 临时文件
大小校验
成功后 rename
校验成功后清理 cloud staging
任务取消和重试
SMB 配置查看、修改、测试连接、目录浏览
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
管理配置型源和文档/表格型源
查看和修改 SMB 配置
测试 SMB 连接
浏览 SMB 目标目录
创建归档任务
查看任务状态和进度
取消 / 重试任务
显示 STORAGE_CONFIG_CHANGED 中断提示
```

不做：

```text
完整媒体库 UI
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
不能写入 SMB 配置允许范围之外的路径
cookie/token/password 不写入日志
校验失败不清理 cloud staging
默认不覆盖已有正式文件
```

---

## 6. 媒体源范围

多源搜索是核心能力。

MVP 支持三类源：

```text
配置型源
代码型源
文档/表格型源
```

Web Console 只支持管理：

```text
配置型源
文档/表格型源
```

代码型 Source Adapter 必须通过代码实现和部署，不允许在 Web Console 中在线编辑代码。

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

SMB 配置支持在 Web Console 修改并热加载。

修改 SMB 配置时：

```text
关闭旧 SMB 连接
中断使用旧配置的运行中任务
任务进入 failed
错误码 STORAGE_CONFIG_CHANGED
retryable = true
保留 .downloading 文件
保留 cloud staging
新任务和重试任务使用最新 SMB 配置
```

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
rclone driver
OpenList 可选后端
Prometheus metrics
OpenTelemetry tracing
```
