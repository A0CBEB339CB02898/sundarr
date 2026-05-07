# Transfer 状态机

本文档定义 Sundarr 搬运任务和文件状态机。

---

## 1. 任务状态

`transfer_tasks.status` 允许值：

```text
pending
staging_to_cloud
cloud_ready
downloading
verifying
renaming
cleaning_cloud
completed
failed
cancelled
```

`searching` 不属于 Transfer Task 状态。搜索是独立 API 行为。

---

## 2. 正常流转

```text
pending
  -> staging_to_cloud
  -> cloud_ready
  -> downloading
  -> verifying
  -> renaming
  -> cleaning_cloud
  -> completed
```

每次状态变化必须更新：

```text
status
updated_at
transfer_logs
```

---

## 3. 文件状态

`transfer_files.status` 允许值：

```text
pending
downloading
verified
completed
failed
cancelled
```

含义：

```text
pending       file record created
downloading   temp file is being written
verified      temp file passed verification but has not been renamed
completed     final file exists and temp file has been renamed
failed        file failed and task should stop or retry
cancelled     file download was cancelled
```

注意：

```text
verified 不等于 completed。
只有 completed 文件才允许参与 cloud cleanup 前置判断。
```

---

## 4. 失败规则

任意运行中状态失败时：

```text
any running state -> failed
```

必须记录：

```text
error_code
error_message
retryable
retry_count
transfer_logs
```

失败时默认保留：

```text
.downloading 文件
cloud staging
transfer logs
```

除非任务已经完成校验、rename 和 cleanup。

---

## 5. 重试规则

重试入口：

```text
POST /transfers/{task_id}/retry
```

重试目标状态：

```text
failed + retryable=true -> pending
```

规则：

```text
retryable=false 的任务不能自动重试。
retry 必须增加 retry_count。
retry 使用最新 SMB 配置。
retry 不应删除现有 .downloading，除非确认 temp invalid。
MVP 6.2 不实现复杂 resume，重试统一回到 pending 由 Worker 重新领取。
retry 必须写入 transfer_logs.event = task_retried。
```

---

## 6. 取消规则

取消入口：

```text
POST /transfers/{task_id}/cancel
```

规则：

```text
pending -> cancelled
staging_to_cloud -> cancelled
cloud_ready -> cancelled
downloading -> stop stream and keep .downloading
verifying -> best effort cancel
renaming -> normally not cancellable
cleaning_cloud -> normally not cancellable
completed -> cannot cancel
failed -> cannot cancel
cancelled -> cannot cancel again
```

取消下载时：

```text
task.status = cancelled
current transfer_file.status = cancelled
error_code = TASK_CANCELLED
retryable = false
transfer_logs.event = task_cancelled
保留 .downloading
保留 cloud staging
```

---

## 7. SMB 配置变更中断

当 SMB 配置修改时，系统必须中断所有使用旧 SMB 配置且未完成的运行中任务。

中断结果：

```text
task.status = failed
error_code = STORAGE_CONFIG_CHANGED
retryable = true
```

必须保留：

```text
.downloading 文件
cloud staging
transfer logs
```

必须执行：

```text
关闭旧 SMB 连接
阻止旧配置继续写入
Web Console 显示中断提示
```

新任务和重试任务必须使用最新 SMB 配置。

---

## 8. Cleanup 前置条件

只有满足以下条件，才能删除 cloud staging：

```text
task.status == cleaning_cloud
all transfer_files.status == completed
all target files exist
all target sizes match source sizes
cloud_staging_path is under /Sundarr/_staging/{task_id}/
```

禁止：

```text
校验失败后 cleanup
只有 verified 就 cleanup
cleanup staging_root 之外路径
cleanup 失败后删除本地文件
```

MVP cleanup 行为：

```text
completed -> cleaning_cloud -> completed
cleanup_completed 写入 transfer_logs
cleanup_failed 写入 transfer_logs
cleanup 失败时保持 task.status = completed，设置 error_code = CLOUD_CLEANUP_FAILED，retryable = true
```

---

## 9. Worker 启动恢复

本节属于 Phase 6 Cleanup And Recovery 范围，不属于 Phase 5 第一轮 Worker 主链路验收。

Worker 启动时必须扫描未完成任务。

处理建议：

```text
pending -> 可重新入队
staging_to_cloud -> failed, retryable=true
cloud_ready -> 可重新入队 downloading
downloading -> 可尝试 resume
verifying -> 可重新 verifying
renaming -> 可重新检查 temp/final 状态
cleaning_cloud -> 可重新 cleanup
```

恢复必须保守，不能误删 cloud staging。

Phase 6 拆分顺序：

```text
Phase 6.1 cancel task
Phase 6.2 retry failed task
Phase 6.3 safe cloud cleanup
Phase 6.4 worker startup recovery
Phase 6.5 transfer logs API
```

---

## 10. 进度规则

任务级进度：

```text
done_bytes = sum(transfer_files.done_bytes)
total_bytes = sum(transfer_files.size_bytes)
progress = done_bytes / total_bytes
```

Phase 5 先实现任务级 `done_bytes` / `total_bytes` / `progress` 的最小可查询能力；速度、ETA 和更细粒度 current_file 展示可以在 Phase 5.5 或 Web Console 阶段继续完善。

速度计算：

```text
最近 speed_window_seconds 内 done_bytes 增量 / 时间
```

不要只使用任务开始以来的平均速度。

---

## 11. 验收标准

状态机完成时必须满足：

```text
正常任务可从 pending 到 completed。
失败任务记录 error_code、error_message、retryable。
取消 downloading 保留 .downloading 和 cloud staging。
校验失败不 cleanup。
只有 transfer_files.status == completed 才 cleanup。
SMB 配置变更会导致运行中任务 STORAGE_CONFIG_CHANGED。
Worker 重启后不会误删 staging。
```
