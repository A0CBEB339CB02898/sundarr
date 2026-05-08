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
link_id TEXT
status TEXT NOT NULL
mode TEXT NOT NULL
cloud_staging_path TEXT
target_type TEXT NOT NULL
target_library TEXT
target_path TEXT NOT NULL
source_type TEXT
source_path TEXT
source_config_snapshot JSONB
ingest_seen_file_id TEXT
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

`link_id` 对搜索资源搬运任务必填；对挂载网盘导入任务可为空。

`source_type`、`source_path`、`source_config_snapshot` 和 `ingest_seen_file_id` 用于记录挂载网盘导入来源。`storage_config_snapshot` 用于判断任务是否使用旧 SMB 配置。

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
ingest 全局配置
```

规则：

```text
API 不返回敏感字段明文。
SMB password 不回显给 Web Console。
password 空值更新表示保留旧值。
数据库初始化完成后写入默认 settings，不覆盖已存在用户配置。
```

---

## 9. ingest_bindings

用途：保存挂载网盘来源目录和本地媒体库目标目录的绑定关系。

字段建议：

```text
id TEXT PRIMARY KEY
name TEXT NOT NULL
enabled BOOLEAN NOT NULL DEFAULT TRUE
media_type TEXT NOT NULL
source_smb_json JSONB NOT NULL
target_smb_json JSONB NOT NULL
delete_source_after_success BOOLEAN
delete_empty_source_dirs BOOLEAN
created_at TIMESTAMP NOT NULL
updated_at TIMESTAMP NOT NULL
```

规则：

```text
media_type 允许 movie / series / unclassified。
source_smb_json 保存来源 SMB host/share/base_path 等配置。
target_smb_json 保存目标 SMB host/share/base_path 等配置。
source 和 target 通常是同一 SMB server，但允许跨 share 或跨 server。
delete_source_after_success 为空时使用全局默认。
delete_empty_source_dirs 为空时使用全局默认。
```

---

## 10. ingest_seen_files

用途：记录已扫描或已处理的来源文件，避免重复导入。

字段建议：

```text
id TEXT PRIMARY KEY
binding_id TEXT
source_fingerprint TEXT NOT NULL
source_path TEXT NOT NULL
source_size BIGINT
source_mtime TEXT
status TEXT NOT NULL
task_id TEXT
created_at TIMESTAMP NOT NULL
updated_at TIMESTAMP NOT NULL
```

规则：

```text
source_fingerprint 由来源 SMB 标识和来源路径组成，用于避免重复发现同一路径。
status 至少包含 discovered / stable / queued / importing / completed / failed / ignored。
目录型资源可用目录路径和聚合 size/mtime 生成 fingerprint。
```

## 11. 验收标准

数据模型完成时必须满足：

```text
迁移可创建所有核心表。
Source / Resource / ResourceLink 可读写。
TransferTask / TransferFile 状态可持久化。
Setting 可保存 SMB 配置。
Ingest binding 可保存来源和目标 SMB 目录绑定。
transfer_logs 可记录状态变化。
敏感字段不会通过 API 明文返回。
```
