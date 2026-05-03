# 配置规范

本文档定义 Sundarr 的配置来源、运行时配置和热加载规则。

---

## 1. 配置分层

配置分为两类：

```text
启动配置
运行时配置
```

启动配置来自：

```text
.env
config.yaml
environment variables
```

运行时配置来自：

```text
settings table
sources table
```

---

## 2. 启动配置

启动配置用于启动 API、Worker 和基础依赖。

示例：

```yaml
app:
  name: Sundarr
  host: 0.0.0.0
  port: 8080

database:
  url: postgresql://sundarr:sundarr@postgres:5432/sundarr

redis:
  url: redis://redis:6379/0

cloud:
  staging_root: /Sundarr/_staging
```

规则：

```text
database.url 和 redis.url 属于启动配置。
修改启动配置通常需要重启。
```

---

## 3. 运行时配置

运行时配置保存到数据库。

包括：

```text
storage.smb
storage.libraries
部分 transfer 参数
source configuration
```

运行时配置可以由 Web Console 修改。

---

## 4. SMB 配置

SMB 配置结构：

```json
{
  "host": "fnos.local",
  "port": 445,
  "share": "media",
  "username": "user",
  "password": "password",
  "domain": "",
  "base_path": "/",
  "libraries": {
    "movies": "Movies",
    "tv": "TV",
    "anime": "Anime"
  }
}
```

规则：

```text
password 不回显明文。
password 留空表示保留旧值。
保存 SMB 配置后必须热加载。
保存 SMB 配置会中断使用旧配置的运行中任务。
```

---

## 5. Transfer 配置

MVP 默认：

```yaml
transfer:
  max_concurrent_tasks: 2
  max_concurrent_files_per_task: 1
  chunk_size: 8388608
  retry_count: 3
  retry_delay_seconds: 10
  verify_mode: size
  speed_window_seconds: 5
```

部分参数可后续放入 settings 表热加载。

---

## 6. Source 配置

Source 配置保存到 sources 表。

Web Console 可管理：

```text
配置型源
文档/表格型源
```

代码型源通过代码实现，不通过前端在线编辑。

---

## 7. 敏感信息规则

MVP 不实现复杂 secret backend。

必须做到：

```text
不提交 .env。
不在日志输出 password/token/cookie。
API 不返回 password 明文。
Web Console 不展示 password 明文。
```

---

## 8. 验收标准

配置系统完成时必须满足：

```text
API 和 Worker 可读取启动配置。
settings 表可保存 SMB 配置。
Web Console 可修改 SMB 配置。
SMB 配置修改无需重启。
SMB 配置修改中断旧配置运行中任务。
Source 配置可持久化。
敏感字段不会明文返回。
```
