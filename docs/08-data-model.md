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
sync_seen_file_id TEXT
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

`link_id` 对搜索资源搬运任务必填；对同步任务可为空。

`source_type`、`source_path`、`source_config_snapshot` 和 `sync_seen_file_id` 用于记录同步来源。`storage_config_snapshot` 用于判断任务是否使用旧 SMB 配置。历史 `ingest_seen_file_id` 字段已由 Phase 9 迁移为 `sync_seen_file_id`。

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
media_libraries
transfer 参数
sync 全局配置
```

规则：

```text
API 不返回敏感字段明文。
SMB password 不回显给 Web Console。
password 空值更新表示保留旧值。
数据库初始化完成后写入默认 settings，不覆盖已存在用户配置。
```

---

## 9. smb_connections

状态：已实现。

用途：保存可复用的 SMB 连接。远程媒体库、本地媒体库和其他 SMB 相关模块只能引用 SMB connection，不重复保存 SMB 凭据。

字段建议：

```text
id TEXT PRIMARY KEY
name TEXT NOT NULL
enabled BOOLEAN NOT NULL DEFAULT TRUE
host TEXT NOT NULL
port INTEGER NOT NULL DEFAULT 445
share TEXT NOT NULL
username TEXT NOT NULL
password TEXT
domain TEXT
base_path TEXT NOT NULL DEFAULT '/'
created_at TIMESTAMP NOT NULL
updated_at TIMESTAMP NOT NULL
```

规则：

```text
API 不返回 password 明文，只返回 password_set。
password 空值更新表示保留旧 password。
修改某个 SMB connection 会中断使用该 connection 旧配置快照的运行中任务。
```

---

## 10. media_libraries

状态：已实现。

用途：保存本地 NAS 媒体库定义。媒体库是 movie、series、unclassified 等逻辑库，并绑定到某个 SMB connection 下的本地目录。

字段建议：

```text
id TEXT PRIMARY KEY
name TEXT NOT NULL
media_type TEXT NOT NULL
enabled BOOLEAN NOT NULL DEFAULT TRUE
connection_id TEXT NOT NULL
base_path TEXT NOT NULL
created_at TIMESTAMP NOT NULL
updated_at TIMESTAMP NOT NULL
```

规则：

```text
media_type 允许 movie / series / unclassified，后续可扩展。
connection_id 必须引用已配置 SMB connection。
base_path 是 connection base_path 内的相对路径，指向本地 NAS 媒体库目录。
API 不在媒体库中保存 SMB host/share/username/password。
至少需要一个 unclassified 媒体库作为绑定不明确时的 fallback。
```

---

## 11. sync_bindings

状态：已实现（由历史 download_to_local 结构重构而来，Phase 9 继续清理旧命名残留）。

用途：保存远程媒体库到本地媒体库的同步规则。

字段建议：

```text
id TEXT PRIMARY KEY
name TEXT NOT NULL
enabled BOOLEAN NOT NULL DEFAULT TRUE
media_type TEXT NOT NULL
remote_library_id TEXT NOT NULL
target_library_id TEXT NOT NULL
delete_source_after_success BOOLEAN
delete_empty_source_dirs BOOLEAN
created_at TIMESTAMP NOT NULL
updated_at TIMESTAMP NOT NULL
```

规则：

```text
media_type 允许 movie / series / unclassified，并应与目标媒体库类型一致。
remote_library_id 必须引用已配置 remote_media_libraries。
target_library_id 必须引用已配置 media_libraries。
来源目录来自 remote_library_id 对应远程媒体库的 connection_id 和 base_path，通常是已挂载的网盘目录。
目标写入目录来自 target_library_id 对应媒体库的 connection_id 和 base_path。
delete_source_after_success 为空时使用全局默认。
delete_empty_source_dirs 为空时使用全局默认。
```

---

## 12. sync_seen_files

状态：已实现（由历史 download_to_local_seen_files 重构而来，Phase 9 继续清理旧命名残留）。

用途：记录已扫描或已处理的远程媒体库来源文件，避免重复同步到本地媒体库。

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
source_fingerprint 由远程媒体库、来源目录和来源文件路径组成，用于避免重复发现同一路径。
status 至少包含 discovered / stable / queued / downloading / completed / failed / ignored。
目录型资源可用目录路径和聚合 size/mtime 生成 fingerprint。
```

## 13. 验收标准

数据模型完成时必须满足：

```text
迁移可创建所有核心表。
Source / Resource / ResourceLink 可读写。
TransferTask / TransferFile 状态可持久化。
SMB connection 可保存多个 SMB 连接配置。
Media library 可引用 SMB connection 和本地目录。
Sync binding 可引用远程媒体库和本地媒体库。
transfer_logs 可记录状态变化。
敏感字段不会通过 API 明文返回。
```
