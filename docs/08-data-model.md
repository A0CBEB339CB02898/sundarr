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

用途：保存已安装搜索源的目录信息，与代码中的 Source Adapter 对应。搜索执行逻辑仍以代码 Adapter 为事实来源，`sources` 表只用于列表展示和外键关联。

字段：

```text
id TEXT PRIMARY KEY
name TEXT NOT NULL
description TEXT NOT NULL DEFAULT ''
homepage_url TEXT NOT NULL DEFAULT ''
registered_at TIMESTAMP NOT NULL
created_at TIMESTAMP NOT NULL
updated_at TIMESTAMP NOT NULL
```

约束：

```text
搜索源不支持启用、禁用、合规说明、信任等级、最后错误等旧字段。
项目初始化和 `/sources` / `/search` API 会把代码中的 Source Adapter 同步到该表。
Web Console 不允许创建、编辑、删除搜索源，也不在数据库中保存可执行 Python 代码。
```

---

## 3. resources

用途：保存用户主动收藏过的标准化媒体资源，或作为用户收藏资源链接时的最小父级资源记录。

Resource 与 ResourceLink 同属收藏模块。产品层面只暴露一个收藏入口，资源收藏和资源链接收藏只是收藏模块下的两类对象。

边界：

```text
搜索结果默认不写入 resources。
只有用户主动收藏资源，或用户收藏资源链接时需要创建父级 Resource，才写入 resources。
创建传输任务当前不依赖 Resource / ResourceLink；任务事实来源仍是远程媒体库扫描结果。
Resource 表示“这是什么资源”，不表示某个具体网盘链接或版本。
质量、版本、网盘类型、提取码和链接有效性属于 ResourceLink。
```

字段：

```text
id TEXT PRIMARY KEY
title TEXT NOT NULL
normalized_title TEXT NOT NULL
original_title TEXT
year INTEGER
favorited_at TIMESTAMP
created_at TIMESTAMP NOT NULL
updated_at TIMESTAMP NOT NULL
```

字段说明：

```text
favorited_at 为空表示该 Resource 只是为了某个已收藏 ResourceLink 存在，本身未被收藏。
favorited_at 非空表示用户已收藏该 Resource。
normalized_title 用于搜索结果与已收藏资源匹配，给实时搜索结果打“已收藏”标记。
year 只作为弱辅助字段；获取不到时可为空，不作为必填条件。
```

---

## 4. resource_links

用途：保存用户主动收藏过的具体资源链接。

边界：

```text
搜索结果默认不写入 resource_links。
只有用户主动收藏某条链接，才写入 resource_links。
ResourceLink 表示“这个资源的一个具体可用链接/版本”。
ResourceLink 可以单独收藏；单独收藏链接时必须同时写入一个最小 Resource 父记录。
```

字段：

```text
id TEXT PRIMARY KEY
resource_id TEXT NOT NULL
provider TEXT NOT NULL
name TEXT
url TEXT NOT NULL
code TEXT
quality TEXT
valid BOOLEAN
last_checked_at TIMESTAMP
source_id TEXT
source_url TEXT
favorited_at TIMESTAMP NOT NULL
created_at TIMESTAMP NOT NULL
updated_at TIMESTAMP NOT NULL
```

字段说明：

```text
quality 是该具体链接的版本/画质标签，例如 1080p、4K、WEB-DL、BluRay，不属于 Resource。
name 是该具体链接的展示名称，可来自搜索源链接标题，也可由资源标题和 quality 兜底生成。
valid / last_checked_at 来自链接检测结果，可通过手动刷新更新。
source_id / source_url 用于追踪该链接来自哪个搜索源和源页面。
risk_level / visibility 不纳入 MVP 最小模型。
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

`resource_id` / `link_id` 不作为当前传输任务创建的必需字段；当前任务创建事实来源是远程媒体库扫描结果。

后续如增加“从收藏链接创建任务”，可在创建任务时把收藏链接信息快照进任务，并选择性关联 `resource_id` / `link_id`。

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
last_test_ok BOOLEAN
last_test_error_code TEXT
last_test_error_message TEXT
created_at TIMESTAMP NOT NULL
updated_at TIMESTAMP NOT NULL
```

规则：

```text
API 不返回 password 明文，只返回 password_set。
password 空值更新表示保留旧 password。
修改某个 SMB connection 会中断使用该 connection 旧配置快照的运行中任务。
last_test_ok / last_test_error_code / last_test_error_message 记录最近一次连接测试结果；最近一次测试明确失败时，不能作为已启用连接使用。
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
last_test_ok BOOLEAN
last_test_error_code TEXT
last_test_error_message TEXT
created_at TIMESTAMP NOT NULL
updated_at TIMESTAMP NOT NULL
```

规则：

```text
media_type 允许 movie / series / unclassified，后续可扩展。
connection_id 必须引用已配置 SMB connection。
base_path 是 connection base_path 内的目录路径，指向本地 NAS 媒体库目录；API 统一保存为带前导斜杠的写法。
API 不在媒体库中保存 SMB host/share/username/password。
至少需要一个 unclassified 媒体库作为绑定不明确时的 fallback。
last_test_ok / last_test_error_code / last_test_error_message 记录最近一次目录测试结果；最近一次测试明确失败时，不能作为已启用媒体库使用。
```

---

## 11. remote_media_libraries

状态：已实现。

用途：保存远程媒体库目录定义。远程媒体库绑定 SMB connection 下的远程目录，并可指向一个本地媒体库作为同步目标。

字段建议：

```text
id TEXT PRIMARY KEY
name TEXT NOT NULL
media_type TEXT NOT NULL
enabled BOOLEAN NOT NULL DEFAULT TRUE
connection_id TEXT NOT NULL
base_path TEXT NOT NULL
target_library_id TEXT
scan_interval_seconds INTEGER NOT NULL DEFAULT 60
stable_seconds INTEGER NOT NULL DEFAULT 120
delete_source_after_success BOOLEAN
delete_empty_source_dirs BOOLEAN
last_test_ok BOOLEAN
last_test_error_code TEXT
last_test_error_message TEXT
created_at TIMESTAMP NOT NULL
updated_at TIMESTAMP NOT NULL
```

规则：

```text
connection_id 必须引用已配置 SMB connection。
target_library_id 为空时表示尚未绑定本地媒体库，列表页必须展示未绑定。
target_library_id 不为空时，系统会维护同 id 的同步绑定用于扫描。
最近一次测试明确失败时，不能作为已启用远程媒体库使用。
```

---

## 12. sync_bindings

状态：已实现（由历史 download_to_local 结构重构而来，当前模型命名已统一）。

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

## 13. sync_seen_files

状态：已实现（由历史 download_to_local_seen_files 重构而来，当前模型命名已统一）。

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

## 14. plugin_repositories

用途：存储外部可信 Git 插件仓库配置。当前实际用途是加载 SOURCE Adapter。

字段：

```text
id TEXT PRIMARY KEY
name TEXT NOT NULL
repo_url TEXT NOT NULL UNIQUE
branch TEXT NOT NULL DEFAULT 'main'
current_commit TEXT
previous_commit TEXT
auto_update BOOLEAN NOT NULL DEFAULT FALSE
enabled BOOLEAN NOT NULL DEFAULT TRUE
status TEXT NOT NULL DEFAULT 'pending'
last_error TEXT
last_checked_at TIMESTAMP
last_loaded_at TIMESTAMP
created_at TIMESTAMP NOT NULL
updated_at TIMESTAMP NOT NULL
```

规则：

```text
status 至少包含 pending / loaded / error。
current_commit 锁定当前使用的 commit，系统从本地缓存中的已锁定 commit 加载。
previous_commit 保留上一个 commit 用于回滚。
auto_update 为 false 时不自动拉取远程更新。
```

## 15. plugin_configs

用途：存储已加载插件的运行时配置。

字段：

```text
id TEXT PRIMARY KEY
plugin_id TEXT NOT NULL UNIQUE
plugin_type TEXT NOT NULL
config_data TEXT NOT NULL DEFAULT '{}'
enabled BOOLEAN NOT NULL DEFAULT TRUE
status TEXT NOT NULL DEFAULT 'active'
repository_id TEXT REFERENCES plugin_repositories(id)
created_at TIMESTAMP NOT NULL
updated_at TIMESTAMP NOT NULL
```

规则：

```text
plugin_id 为插件唯一标识，来自搜索源 Adapter 注册。
plugin_type 标识插件类型（当前使用 source）。
config_data 存储 JSON 格式的插件配置。
repository_id 关联来源仓库；当前真实 Source 全部来自外部仓库。
```

`PluginActivation` 是进程内运行时对象，不新增为任务事实表。Repository/Config 保存声明和期望状态，Activation 诊断通过运行时 API 暴露，不能把内存状态误写成跨进程事实来源。

## 16. plugin_logs

用途：记录插件运行时日志，供诊断和错误排查。

字段：

```text
id TEXT PRIMARY KEY
plugin_id TEXT NOT NULL
level TEXT NOT NULL
message TEXT NOT NULL
details TEXT
timestamp TIMESTAMP NOT NULL
```

规则：

```text
level 至少包含 info / warn / error / debug。
details 存储 JSON 格式的附加上下文。
日志不包含敏感凭据。
```

## 17. 验收标准

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
