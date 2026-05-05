# 数据模型

本文档定义 Sundarr MVP 的数据库模型语义。实际实现可使用 SQLAlchemy/Alembic 生成迁移。

---

## 1. 数据库

MVP 使用：

```text
PostgreSQL
```

规则：

```text
任务状态以 PostgreSQL 为事实来源。
Redis 只做缓存和实时进度辅助。
半结构化配置使用 JSONB。
```

---

## 2. sources

用途：保存媒体源配置。

字段：

```text
id TEXT PRIMARY KEY
name TEXT NOT NULL
type TEXT NOT NULL
enabled BOOLEAN NOT NULL DEFAULT TRUE
legal_note TEXT
trust_level INTEGER NOT NULL DEFAULT 1
created_by_user BOOLEAN NOT NULL DEFAULT TRUE
config_json JSONB
last_error_code TEXT
last_error_message TEXT
last_checked_at TIMESTAMP
created_at TIMESTAMP NOT NULL
updated_at TIMESTAMP NOT NULL
```

约束：

```text
type 允许 configurable / code / document。
Web Console 只能管理 configurable / document。
```

---

## 3. resources

用途：保存标准化媒体资源。

字段：

```text
id TEXT PRIMARY KEY
title TEXT NOT NULL
normalized_title TEXT
original_title TEXT
type TEXT
year INTEGER
season INTEGER
episodes TEXT
quality TEXT
language TEXT
subtitle TEXT
description TEXT
poster TEXT
score REAL NOT NULL DEFAULT 0
metadata_json JSONB
created_at TIMESTAMP NOT NULL
updated_at TIMESTAMP NOT NULL
```

---

## 4. resource_links

用途：保存资源对应的网盘链接。

字段：

```text
id TEXT PRIMARY KEY
resource_id TEXT NOT NULL
provider TEXT NOT NULL
url TEXT NOT NULL
code TEXT
source_id TEXT
source_url TEXT
valid BOOLEAN
risk_level TEXT NOT NULL DEFAULT 'unknown'
visibility TEXT NOT NULL DEFAULT 'unknown'
last_checked_at TIMESTAMP
created_at TIMESTAMP NOT NULL
updated_at TIMESTAMP NOT NULL
```

建议索引：

```text
resource_id
provider
hash(url)
```

---

## 5. transfer_tasks

用途：保存搬运任务。

字段：

```text
id TEXT PRIMARY KEY
resource_id TEXT
link_id TEXT NOT NULL
status TEXT NOT NULL
mode TEXT NOT NULL
cloud_staging_path TEXT
target_type TEXT NOT NULL
target_library TEXT
target_path TEXT NOT NULL
storage_config_snapshot JSONB
total_bytes BIGINT NOT NULL DEFAULT 0
done_bytes BIGINT NOT NULL DEFAULT 0
speed_bytes_per_sec BIGINT NOT NULL DEFAULT 0
error_code TEXT
error_message TEXT
retryable BOOLEAN
retry_count INTEGER NOT NULL DEFAULT 0
created_at TIMESTAMP NOT NULL
updated_at TIMESTAMP NOT NULL
started_at TIMESTAMP
completed_at TIMESTAMP
```

状态见 `docs/07-transfer-state-machine.md`。

`storage_config_snapshot` 用于判断任务是否使用旧 SMB 配置。

---

## 6. transfer_files

用途：保存任务内文件状态。

字段：

```text
id TEXT PRIMARY KEY
task_id TEXT NOT NULL
cloud_file_id TEXT
cloud_path TEXT NOT NULL
target_path TEXT NOT NULL
temp_path TEXT NOT NULL
filename TEXT NOT NULL
size_bytes BIGINT NOT NULL
done_bytes BIGINT NOT NULL DEFAULT 0
status TEXT NOT NULL
error_code TEXT
error_message TEXT
created_at TIMESTAMP NOT NULL
updated_at TIMESTAMP NOT NULL
```

状态见 `docs/07-transfer-state-machine.md`。

---

## 7. transfer_logs

用途：保存任务事件日志。

字段：

```text
id TEXT PRIMARY KEY
task_id TEXT NOT NULL
level TEXT NOT NULL
event TEXT NOT NULL
message TEXT
data_json JSONB
created_at TIMESTAMP NOT NULL
```

日志不得保存 cookie、token、password。

---

## 8. settings

用途：保存运行时可变配置。

字段：

```text
key TEXT PRIMARY KEY
value_json JSONB NOT NULL
is_sensitive BOOLEAN NOT NULL DEFAULT FALSE
created_at TIMESTAMP NOT NULL
updated_at TIMESTAMP NOT NULL
```

保存内容：

```text
storage.smb
cloud.local
worker.enabled
worker.concurrency
source configuration
library 映射
transfer 参数
```

规则：

```text
API 不返回敏感字段明文。
SMB password 不回显给 Web Console。
password 空值更新表示保留旧值。
数据库初始化完成后写入默认 settings，不覆盖已存在用户配置。
```

---

## 9. 验收标准

数据模型完成时必须满足：

```text
迁移可创建所有核心表。
Source / Resource / ResourceLink 可读写。
TransferTask / TransferFile 状态可持久化。
Setting 可保存 SMB 配置。
transfer_logs 可记录状态变化。
敏感字段不会通过 API 明文返回。
```
