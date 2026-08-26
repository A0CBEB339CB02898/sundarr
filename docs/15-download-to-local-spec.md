# 远程媒体库同步到本地媒体库规范

本文档定义 Sundarr Phase 8 历史“下载到本地”能力的当前规范命名：远程媒体库同步到本地媒体库。该能力从已挂载的网盘 SMB 目录读取内容，并同步到本地 SMB 媒体库目录。

状态：模型、API、Web Console、扫描、任务创建和 Worker 自动化路径已实现；真实 source SMB -> target SMB 完整流程是发布前手动验收门。

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

MVP 主链路是：

```text
用户手动保存资源到网盘
-> NAS 或挂载服务将网盘远程挂载为目录
-> SMB 服务暴露挂载目录
-> Sundarr 将挂载目录配置为远程媒体库
-> Sundarr 通过同步绑定连接远程媒体库（来源）和本地媒体库（目标）
-> Worker 同步到 .downloading、校验、rename
-> 成功后按配置删除来源文件和空目录
```

后续“分享链接保存到网盘”模块命名为“保存到网盘”，不属于本模块。

---

## 2. 目标

远程媒体库同步到本地媒体库需要覆盖：

```text
支持多个 SMB connection。
远程媒体库只能选择已配置 SMB connection 下的远程目录。
本地媒体库管理模块负责创建 movie / series / unclassified 等本地媒体库。
本地媒体库必须绑定到某个 SMB connection 下的本地 NAS 目录。
同步绑定负责连接远程媒体库（来源）和本地媒体库（目标）。
绑定不明确时进入 unclassified 本地媒体库。
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

SMB connection 由 Storage 模块统一管理。远程媒体库和本地媒体库不得重复填写 SMB host、share、username、password。

媒体库保存：

```text
connection_id
base_path
media_type
```

远程媒体库保存：

```text
connection_id
base_path
media_type
target_library_id
```

同步绑定连接远程媒体库和本地媒体库；远程媒体库 SMB connection 和本地媒体库 SMB connection 可以相同，也可以不同。

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

远程媒体库示例：

```json
{
  "name": "电影远程库",
  "media_type": "movie",
  "connection_id": "cloud_mount",
  "base_path": "CloudMovie",
  "target_library_id": "library_movie",
  "enabled": true
}
```

剧集示例：

```json
{
  "name": "剧集远程库",
  "media_type": "series",
  "connection_id": "cloud_mount",
  "base_path": "CloudSeries",
  "target_library_id": "library_series",
  "enabled": true
}
```

规则：

```text
base_path 是 connection_id 对应 SMB base_path 内的相对路径。
base_path 通常是 NAS 已挂载的网盘目录。
target_library_id 指向本地媒体库，目标目录来自媒体库的 connection_id 和 base_path。
媒体类型允许 movie / series / unclassified。
同步绑定的 media_type、远程媒体库 media_type 和本地媒体库 media_type 必须一致。
```

---

## 6. 扫描和稳定性判断

Worker 或手动操作扫描启用的来源目录。
Worker 应按 scan_interval_seconds 定时扫描启用的同步绑定，也允许 Web Console 手动触发单次扫描。

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

扫描必须忽略 `*.sundarr.downloading` 临时文件，避免把未完成或中断遗留文件当作正式媒体文件创建任务。

扫描结果写入 `sync_seen_files`。稳定文件进入 `stable`，创建同步任务后进入 `queued`，并记录对应 `task_id`。

目标路径规则：

```text
目标路径 = 本地媒体库 base_path + 去掉远程媒体库 base_path 后的来源相对路径。
例如远程媒体库 base_path=CloudMovie，来源 CloudMovie/Movie.mkv，同步到本地 Movies/Movie.mkv。
如果媒体本身带目录结构，例如 CloudMovie/MovieFolder/Movie.mkv，则同步到 Movies/MovieFolder/Movie.mkv。
```

创建任务前，如果目标路径已存在同名文件，且 size 和 MD5 均与来源文件一致，应直接将该发现记录视为已完成，不再创建重复任务。

---

## 7. 任务状态

同步任务复用 `transfer_tasks`，但不进入 cloud staging。

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
sync.delete_source_after_success = true
sync.delete_empty_source_dirs = true
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
/app/remote-libraries
```

页面能力：

```text
查看远程媒体库列表。
查看同步绑定列表。
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
目标目录由本地媒体库管理模块维护，远程媒体库和同步页面不重复配置目标目录。
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
GET  /remote-media-libraries
POST /remote-media-libraries/create
GET  /remote-media-libraries/{library_id}
POST /remote-media-libraries/{library_id}/update
POST /remote-media-libraries/{library_id}/enable
POST /remote-media-libraries/{library_id}/disable
POST /remote-media-libraries/{library_id}/test
GET  /sync/config
POST /sync/config/save
GET  /sync/bindings
POST /sync/bindings/create
GET  /sync/bindings/{binding_id}
POST /sync/bindings/{binding_id}/update
POST /sync/bindings/{binding_id}/enable
POST /sync/bindings/{binding_id}/disable
POST /sync/bindings/{binding_id}/test
POST /sync/scan
GET  /sync/discovered
POST /sync/tasks/create
```

MVP 仍不使用 PUT / PATCH / DELETE。

---

## 11. 验收标准

远程媒体库同步到本地媒体库完成时必须满足：

```text
可以配置多个 SMB connection。
可以创建 movie / series / unclassified 媒体库，并绑定到本地 SMB 目录。
可以配置远程媒体库到本地媒体库的同步绑定。
绑定只引用远程媒体库和本地媒体库，不保存 SMB 凭据。
绑定不明确时进入 unclassified 本地媒体库。
可以扫描 SMB 来源目录。
可以判断文件或目录稳定后再同步。
可以通过 SMB 将远程媒体库文件写入本地媒体库。
成功后按配置删除源文件和空目录。
失败时保留源文件和 .downloading。
默认自动化测试不依赖真实 SMB 或真实网盘。
真实挂载目录同步到本地媒体库通过手动集成验收验证。
```
