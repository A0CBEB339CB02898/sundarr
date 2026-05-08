# 挂载网盘导入规范

本文档定义 Sundarr 下一阶段的挂载网盘导入能力。该能力取代“真实网盘 Provider 直接下载”作为近期主链路。

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

新的近期主链路是：

```text
用户手动保存资源到网盘
-> fnOS 将网盘远程挂载为目录
-> fnOS 通过 SMB 暴露挂载目录
-> Sundarr 独立服务器通过 SMB 扫描来源目录
-> Sundarr 通过 SMB 写入 NAS 本地媒体库
-> 校验、rename、删除源文件和空目录
```

---

## 2. 目标

挂载网盘导入需要覆盖：

```text
独立服务器部署 Sundarr。
通过 SMB 访问 fnOS 暴露的网盘挂载目录。
通过 SMB 写入 NAS 本地媒体库目录。
支持 movie / series / unclassified 三类目标库。
支持来源目录和目标目录绑定。
绑定不明确时导入 unclassified。
成功后按配置删除源文件，并清理空目录。
保留后续 AI 自动分类扩展空间。
```

---

## 3. 不做事项

当前阶段不做：

```text
Sundarr 内置挂载网盘。
Sundarr 自动把分享链接保存到网盘。
直接调用封闭网盘下载接口搬运大文件。
绕过网盘客户端、验证码、会员或风控限制。
AI 自动分类。
媒体刮削。
```

后续大阶段可再实现：

```text
在 Sundarr 中配置挂载网盘。
在 Sundarr 中将分享链接保存到网盘。
结合 AI 模型或外部数据辅助判断 movie / series / unclassified。
```

---

## 4. 目录绑定

Sundarr 需要维护“网盘挂载目录 -> 本地媒体库目录”的绑定。

示例：

```json
{
  "name": "电影导入",
  "media_type": "movie",
  "source_path": "/CloudMovie",
  "target_library": "movie",
  "target_path": "/movie",
  "enabled": true
}
```

剧集示例：

```json
{
  "name": "剧集导入",
  "media_type": "series",
  "source_path": "/CloudSeries",
  "target_library": "series",
  "target_path": "/series",
  "enabled": true
}
```

未分类目标：

```json
{
  "target_library": "unclassified",
  "target_path": "/unclassified"
}
```

规则：

```text
source_path 是网盘挂载 SMB 共享内路径。
target_path 是 NAS 本地媒体库 SMB 共享内路径。
来源和目标通常在同一个 SMB server，但不能强制要求。
来源和目标可以跨不同 share。
媒体库默认包含 movie 和 series，可增加 unclassified。
```

---

## 5. 未分类规则

以下情况进入未分类目录：

```text
来源路径没有匹配任何 binding。
来源路径同时匹配多个 binding。
绑定被禁用。
media_type 无法确定。
目标路径生成失败。
```

未分类导入策略：

```text
保留原始文件名。
目录型资源保留原始目录结构。
后续可由 AI 或外部数据辅助重新分类。
```

---

## 6. 扫描和稳定性判断

Sundarr Worker 需要周期扫描启用的来源目录。

默认建议：

```text
scan_interval_seconds = 60
stable_seconds = 120
```

文件或目录必须满足稳定条件才可导入：

```text
连续扫描 size 不变。
mtime 超过 stable_seconds。
不匹配临时文件后缀。
不处于已处理记录中。
```

扫描结果写入 `ingest_seen_files`。稳定文件进入 `stable` 状态，创建导入任务后进入 `queued` 状态，并记录对应 `task_id`。

目录型资源：

```text
剧集通常在网盘端已经是目录，包含分集内容。
导入时应保留目录结构，不额外拆分季集。
目录稳定性以目录内所有文件稳定为准。
```

---

## 7. 导入任务状态

建议新增 ingest 模式任务状态，避免继续借用 cloud staging 语义。

状态：

```text
pending
waiting_source
importing
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
-> waiting_source
-> importing
-> verifying
-> renaming
-> cleaning_source
-> completed
```

失败时必须保留：

```text
.downloading 文件
源文件
任务日志
```

成功后清理源文件：

```text
目标文件存在。
目标 size == 源 size。
rename 已完成。
source_path 位于允许的 source_root 内。
delete_source_after_success = true。
```

---

## 8. 删除源文件和空目录

全局配置：

```text
ingest.delete_source_after_success = true
ingest.delete_empty_source_dirs = true
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
不能删除 source_root。
不能删除 source_root 之外路径。
不能删除未被当前任务确认完成的源文件。
只能删除导入后变为空的目录。
```

---

## 9. Web Console

建议新增页面：

```text
/app/ingest
```

页面能力：

```text
查看导入绑定列表。
新增、编辑、启用、禁用 binding。
配置全局 delete_source_after_success。
配置 unclassified 目录。
测试来源 SMB 目录可读。
测试目标 SMB 目录可写。
手动扫描一次。
查看最近发现文件和导入任务。
```

---

## 10. API 方向

建议 API：

```text
GET  /ingest/config
POST /ingest/config/save
GET  /ingest/bindings
POST /ingest/bindings/create
GET  /ingest/bindings/{binding_id}
POST /ingest/bindings/{binding_id}/update
POST /ingest/bindings/{binding_id}/enable
POST /ingest/bindings/{binding_id}/disable
POST /ingest/bindings/{binding_id}/test
POST /ingest/scan
GET  /ingest/discovered
POST /ingest/tasks/create
```

MVP 仍不使用 PUT / PATCH / DELETE。

`POST /ingest/tasks/create` 只为 `stable` 且尚未绑定任务的发现文件创建 `mode=ingest` 的 transfer task。任务创建后，实际 SMB 来源到 SMB 目标复制由 Worker 执行。

---

## 11. 验收标准

挂载网盘导入完成时必须满足：

```text
可以配置 movie / series / unclassified 目标库。
可以配置来源目录到目标目录的绑定。
绑定不明确时进入 unclassified。
可以扫描 SMB 来源目录。
可以判断文件或目录稳定后再导入。
可以通过 SMB 将文件写入 NAS 本地媒体库。
成功后按配置删除源文件和空目录。
失败时保留源文件和 .downloading。
默认自动化测试不依赖真实 SMB 或真实网盘。
真实 fnOS 挂载目录导入通过手动集成验收验证。
```
