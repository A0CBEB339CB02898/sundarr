# 下载到本地规范

本文档定义 Sundarr Phase 8 “下载到本地”能力：从已挂载的网盘 SMB 目录下载到本地 SMB 媒体库目录。

---

## 1. 背景

国内主流网盘通常不适合由后端绕过官方 App 或客户端直接稳定下载大文件。

Sundarr 不应把以下能力作为近期主链路：

```text
绕过网盘 App 直接下载
破解会员或限速
绕过验证码或风控
依赖非稳定下载直链
```

近期主链路是：

```text
用户手动保存资源到网盘
-> NAS 或挂载服务将网盘远程挂载为目录
-> SMB 服务暴露挂载目录
-> Sundarr 从已配置 SMB 连接中选择来源目录
-> Sundarr 将来源目录正向绑定到某个本地媒体库
-> Worker 下载到 .downloading、校验、rename
-> 成功后按配置删除来源文件和空目录
```

后续“分享链接保存到网盘”模块命名为“保存到网盘”，不属于本模块。

---

## 2. 目标

下载到本地需要覆盖：

```text
支持多个 SMB connection。
来源目录只能选择已配置 SMB connection 下的目录。
媒体库管理模块负责创建 movie / series / unclassified 等本地媒体库。
媒体库必须绑定到某个 SMB connection 下的本地 NAS 目录。
下载到本地 binding 负责将来源目录正向绑定到某个媒体库。
绑定不明确时进入 unclassified 媒体库。
成功后按配置删除来源文件，并清理空目录。
保留后续完整媒体库 UI 和 AI 自动分类扩展空间。
```

---

## 3. 不做事项

当前阶段不做：

```text
Sundarr 内置挂载网盘。
保存到网盘。
直接调用封闭网盘下载接口搬运大文件。
绕过网盘客户端、验证码、会员或风控限制。
AI 自动分类。
完整媒体库 UI、海报墙或播放器。
媒体刮削。
```

当前阶段的媒体库管理只负责本地 NAS 目录绑定，不等于完整媒体库 UI。

---

## 4. SMB 连接关系

SMB connection 由 Storage 模块统一管理。下载到本地模块不得重复填写 SMB host、share、username、password。

媒体库保存：

```text
connection_id
base_path
media_type
```

下载绑定只保存：

```text
source_connection_id
source_path
target_library_id
```

来源 SMB connection 和媒体库 SMB connection 可以相同，也可以不同。

---

## 5. 媒体库和目录绑定

媒体库示例：

```json
{
  "name": "电影",
  "media_type": "movie",
  "connection_id": "media_library",
  "base_path": "Movies",
  "enabled": true
}
```

下载绑定示例：

```json
{
  "name": "电影下载",
  "media_type": "movie",
  "source_connection_id": "cloud_mount",
  "source_path": "CloudMovie",
  "target_library_id": "library_movie",
  "enabled": true
}
```

剧集示例：

```json
{
  "name": "剧集下载",
  "media_type": "series",
  "source_connection_id": "cloud_mount",
  "source_path": "CloudSeries",
  "target_library_id": "library_series",
  "enabled": true
}
```

规则：

```text
source_path 是 source_connection_id 对应 SMB base_path 内的相对路径。
source_path 通常是 NAS 已挂载的网盘目录。
target_library_id 指向本地媒体库，目标目录来自媒体库的 connection_id 和 base_path。
媒体类型允许 movie / series / unclassified。
```

---

## 6. 扫描和稳定性判断

Worker 或手动操作扫描启用的来源目录。
Worker 应按 scan_interval_seconds 定时扫描启用的下载绑定，也允许 Web Console 手动触发单次扫描。

默认建议：

```text
scan_interval_seconds = 60
stable_seconds = 120
```

文件或目录必须满足稳定条件才可下载：

```text
连续扫描 size 不变。
mtime 超过 stable_seconds。
不匹配临时文件后缀。
不处于已处理记录中。
```

扫描结果写入 `download_to_local_seen_files`。稳定文件进入 `stable`，创建下载任务后进入 `queued`，并记录对应 `task_id`。

---

## 7. 任务状态

下载到本地任务复用 `transfer_tasks`，但不进入 cloud staging。

状态：

```text
pending
downloading
verifying
renaming
cleaning_source
completed
failed
cancelled
```

正常流转：

```text
pending
-> downloading
-> verifying
-> renaming
-> cleaning_source
-> completed
```

实现规则：

```text
pending 任务由 Worker 领取后进入 downloading。
Worker 使用 source_connection 快照读取 SMB 来源文件。
Worker 使用目标媒体库 connection 快照写入 SMB 目标 .downloading 文件。
校验 .downloading size 后 rename 为正式文件。
成功后按全局配置和 binding 覆盖配置清理来源文件和空目录。
```

失败时必须保留：

```text
.downloading 文件
源文件
任务日志
```

---

## 8. 删除源文件和空目录

全局配置：

```text
download_to_local.delete_source_after_success = true
download_to_local.delete_empty_source_dirs = true
```

binding 可以覆盖全局配置：

```text
binding.delete_source_after_success = null | true | false
binding.delete_empty_source_dirs = null | true | false
```

优先级：

```text
binding 覆盖 > 全局默认
```

删除保护：

```text
不能删除 source connection 的 base_path。
不能删除 source connection base_path 之外路径。
不能删除未被当前任务确认完成的源文件。
只能删除下载后变为空的目录。
```

---

## 9. Web Console

页面：

```text
/app/download-to-local
```

页面能力：

```text
查看下载绑定列表。
通过新增按钮弹出表单创建 binding。
编辑、启用、禁用 binding。
选择来源 SMB connection 和来源目录。
选择目标媒体库。
配置全局 delete_source_after_success。
配置 unclassified 媒体库。
测试来源目录可读和目标目录可写。
手动扫描一次。
查看最近发现文件和下载任务。
```

页面规则：

```text
默认先展示列表，不默认展开空新增表单。
新增和编辑使用弹出表单。
表单只选择已配置 SMB connection，不重复填写 SMB 凭据。
目标目录由媒体库管理模块维护，下载到本地页面不重复配置目标目录。
```

---

## 10. API 方向

状态：已实现。

建议 API：

```text
GET  /media-libraries
POST /media-libraries/create
GET  /media-libraries/{library_id}
POST /media-libraries/{library_id}/update
POST /media-libraries/{library_id}/enable
POST /media-libraries/{library_id}/disable
POST /media-libraries/{library_id}/test
GET  /download-to-local/config
POST /download-to-local/config/save
GET  /download-to-local/bindings
POST /download-to-local/bindings/create
GET  /download-to-local/bindings/{binding_id}
POST /download-to-local/bindings/{binding_id}/update
POST /download-to-local/bindings/{binding_id}/enable
POST /download-to-local/bindings/{binding_id}/disable
POST /download-to-local/bindings/{binding_id}/test
POST /download-to-local/scan
GET  /download-to-local/discovered
POST /download-to-local/tasks/create
```

MVP 仍不使用 PUT / PATCH / DELETE。

---

## 11. 验收标准

下载到本地完成时必须满足：

```text
可以配置多个 SMB connection。
可以创建 movie / series / unclassified 媒体库，并绑定到本地 SMB 目录。
可以配置来源目录到媒体库的绑定。
绑定只引用来源 SMB connection、来源目录和目标媒体库，不保存 SMB 凭据。
绑定不明确时进入 unclassified 媒体库。
可以扫描 SMB 来源目录。
可以判断文件或目录稳定后再下载。
可以通过 SMB 将文件写入本地媒体库。
成功后按配置删除源文件和空目录。
失败时保留源文件和 .downloading。
默认自动化测试不依赖真实 SMB 或真实网盘。
真实挂载目录下载到本地通过手动集成验收验证。
```
