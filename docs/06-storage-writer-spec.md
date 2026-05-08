# Storage Writer 规范

本文档定义 Sundarr 写入 NAS 的抽象层和应用内 SmbWriter 行为。

---

## 1. 设计目标

MVP 不依赖系统 SMB mount。

正式写入方式：

```text
SmbWriter
```

测试写入方式：

```text
LocalWriter
```

目标：

```text
统一写入接口
支持 .downloading 临时文件
支持断点续传
支持 rename
支持远端大小检查
支持 SMB 配置热加载
支持配置变化中断运行中任务
```

---

## 1.1 当前实现边界

截至 2026-05-06，Phase 4 当前实现边界如下：

```text
StorageWriter 接口已落地。
LocalWriter 已支持 exists / size / mkdirs / open_append / open_read / rename / remove / remove_empty_dir，并有自动化测试。
SmbWriter 使用 smbprotocol 包提供的 smbclient 高层接口。
SmbWriter 已实现 UNC 路径构造、安全路径防护、连接测试、目录浏览、写入、size、rename 的调用边界。
自动化测试不连接真实 SMB 服务器。
POST /storage/config/test 会尝试真实 SMB 连接和根路径访问。
GET /storage/browse 已接入 SmbWriter.list_dir，真实 SMB 不可达时返回 SMB_CONNECT_FAILED。
STORAGE_CONFIG_CHANGED 中断运行中 SMB 任务的数据库状态规则已有测试覆盖。
真实 SMB 环境已完成连接、目录浏览、创建目录、写入 .downloading、size、rename 和清理测试文件的手动验收。
```

因此 Phase 4 Storage Writer 已满足当前停止条件。后续 Phase 5 可以在该写入抽象上实现 Transfer Worker 主链路。

---

## 2. StorageWriter 接口

```python
class StorageWriter:
    async def exists(self, path: str) -> bool:
        raise NotImplementedError

    async def size(self, path: str) -> int:
        raise NotImplementedError

    async def mkdirs(self, path: str) -> None:
        raise NotImplementedError

    async def open_append(self, path: str):
        raise NotImplementedError

    async def open_read(self, path: str):
        raise NotImplementedError

    async def rename(self, src: str, dst: str) -> None:
        raise NotImplementedError

    async def remove(self, path: str) -> None:
        raise NotImplementedError

    async def remove_empty_dir(self, path: str) -> None:
        raise NotImplementedError
```

Transfer Worker 只能依赖 StorageWriter 接口，不应直接调用 SMB 库。

`open_read` 供挂载网盘导入读取 SMB 来源文件使用。`remove_empty_dir` 只能删除空目录，不能递归删除目录树。

---

## 3. SmbWriter 配置

SMB 配置保存到数据库 settings 表或等价运行时配置存储。

配置结构：

```json
{
  "type": "smb",
  "host": "nas.example.invalid",
  "port": 445,
  "share": "media",
  "username": "your_user",
  "password": "your_password",
  "domain": "",
  "base_path": "/",
  "libraries": {
    "movies": "Movies",
    "tv": "TV",
    "anime": "Anime"
  }
}
```

API 返回时不得回显 password 明文。

返回示例：

```json
{
  "type": "smb",
  "host": "nas.example.invalid",
  "port": 445,
  "share": "media",
  "username": "your_user",
  "password_set": true,
  "domain": "",
  "base_path": "/",
  "libraries": {
    "movies": "Movies",
    "tv": "TV",
    "anime": "Anime"
  }
}
```

---

## 4. 路径规则

前端和 API 传入的 target path 必须是 SMB share 内的相对路径。

示例：

```json
{
  "type": "smb",
  "library": "movies",
  "path": "Interstellar (2014)"
}
```

最终路径：

```text
smb://host/share/Movies/Interstellar (2014)/filename.mkv
```

规则：

```text
拒绝绝对系统路径。
拒绝 .. 路径穿越。
拒绝写入 base_path 或 library 之外。
默认不覆盖已有正式文件。
允许继续写入已存在的 .downloading 文件。
```

---

## 5. 写入流程

单文件写入：

```text
build safe target path
build temp path = target + .downloading
mkdirs parent directory
check existing temp size
open cloud stream from offset
append/write to temp file
verify temp file size
rename temp file to final target
mark transfer file completed
```

`.downloading` 文件是防止媒体库误扫的保护机制。

---

## 6. 断点续传

如果远端存在：

```text
Movie.mkv.downloading
```

且大小小于 cloud source size，则尝试从该 offset 继续下载。

规则：

```text
如果 cloud provider 支持 offset stream，则续传。
如果不支持 offset stream，则从头重下。
如果 temp size > source size，必须标记 temp invalid，并从头重下。
不得静默拼接不可信内容。
```

---

## 7. Rename 规则

rename 前必须满足：

```text
temp file exists
temp size == cloud source size
final target does not exist
transfer_file.status == verified
```

rename 后：

```text
final target exists
temp file no longer exists
transfer_file.status = completed
```

如果 final target 已存在，MVP 默认失败，不覆盖。

---

## 8. SMB 配置热加载

SMB 配置可从 Web Console 修改。

保存新配置时必须：

```text
写入 settings
清除旧 SMB 连接缓存
中断使用旧配置的运行中任务
新任务使用最新配置
重试任务使用最新配置
```

运行中任务中断规则：

```text
task.status = failed
error_code = STORAGE_CONFIG_CHANGED
retryable = true
保留 .downloading 文件
保留 cloud staging
```

---

## 9. Web Console API

Storage 相关 API：

```text
GET  /storage/config
POST /storage/config/save
POST /storage/config/test
GET  /storage/browse?path=Movies
```

规则：

```text
GET 不返回 password 明文。
POST /storage/config/save 中 password 为空表示保留旧值。
POST /storage/config/test 会验证配置结构、路径合法性，并尝试真实 SMB 连接和根路径访问。
GET /storage/browse 只能浏览允许范围内路径。
```

---

## 10. 错误码

Storage Writer 相关错误码：

```text
STORAGE_CONFIG_INVALID
STORAGE_CONFIG_CHANGED
SMB_CONNECT_FAILED
SMB_AUTH_FAILED
SMB_PATH_INVALID
SMB_PATH_OUTSIDE_ROOT
SMB_CLIENT_NOT_INSTALLED
SMB_NO_SPACE
SMB_WRITE_FAILED
SMB_RENAME_FAILED
TARGET_EXISTS
```

---

## 11. 验收标准

Storage Writer 完成时必须满足：

```text
LocalWriter 可用于测试。
SmbWriter 可测试连接。
SmbWriter 可浏览目录。
SmbWriter 可写入 .downloading。
SmbWriter 可获取远端大小。
SmbWriter 可 rename。
SMB 配置修改无需重启。
SMB 配置修改会中断使用旧配置的运行中任务。
被中断任务保留 .downloading 和 cloud staging。
```
