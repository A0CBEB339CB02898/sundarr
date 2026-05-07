# 测试计划

本文档定义 Sundarr MVP 必须覆盖的测试范围。

---

## 1. 测试原则

MVP 自动化测试不得依赖：

```text
真实网盘
真实 NAS
真实 SMB 服务器
真实外部资源站
```

必须提供：

```text
Mock/Local Provider
LocalWriter
可替换 StorageWriter
可控 Source fixture
```

每完成一项非文档型开发任务后，必须运行对应回归测试。

最低回归规则：

```text
后端代码变更必须运行 pytest。
前端代码变更必须运行 npm run build，必要时运行前端测试。
配置或 Docker 变更必须运行相关启动或配置校验。
失败测试必须优先修复，不能继续积累新功能。
```

如果某项测试因环境限制无法运行，必须在交付说明中明确说明原因和风险。

默认 pytest 使用 SQLite 内存数据库验证模型、服务和 API 行为，不要求本机 PostgreSQL 已启动。真实 PostgreSQL 连通性属于本地集成环境检查，必须通过 `/health` 或独立启动校验确认。

真实 SMB 可用于手动开发测试，以减少过度 mock 带来的偏差。但这类测试必须满足：

```text
不纳入默认 pytest。
不得要求 CI 或其他开发者具备真实 NAS。
不得提交真实 SMB 密码、host 私密信息或可访问路径。
测试目标目录应使用专用目录，例如 /SundarrManualTest。
真实写入测试必须只操作测试目录，避免误删媒体库正式文件。
```

---

## 2. 配置测试

必须覆盖：

```text
启动配置加载
环境变量覆盖
settings 表读写
GET /health 返回真实 database 状态
SMB password 不回显
SMB 配置热加载
```

---

## 3. Source Adapter 测试

必须覆盖：

```text
SearchQuery 输入
RawSearchItem 输出
source timeout
source failure isolation
配置型源解析
文档/表格型源解析
代码型源不能前端编辑
```

---

## 4. Search Pipeline 测试

必须覆盖：

```text
link extraction
multiline extraction code
multiple links in one text
normalization basics
dedupe basics
rank score exists
resource persistence
```

---

## 5. Storage Writer 测试

必须覆盖：

```text
LocalWriter exists / size / mkdirs / open_append / rename
SmbWriter mock connection test
path normalization
reject .. traversal
reject outside base_path
.downloading write
rename after verification
default reject overwrite
SMB config hot reload
STORAGE_CONFIG_CHANGED interrupts running task
```

当前覆盖状态：

```text
LocalWriter exists / size / open_append / rename / remove guard 已覆盖。
SmbWriter 目前覆盖安全路径、UNC 构造、session 注册、连接测试和缺少客户端依赖错误。
Storage config 已覆盖 password 不回显、空 password 保留、路径校验、配置变更中断运行中任务。
真实 SMB 连接、真实目录浏览、真实写入、真实 size、真实 rename 不纳入默认 pytest，需通过手动集成验收覆盖。
```

允许补充单独的手动真实 SMB 测试脚本或命令，用于开发者本机验证：

```text
POST /storage/config/save 保存真实 SMB 配置。
POST /storage/config/test 验证连接。
GET /storage/browse 浏览测试目录。
后续 Worker 完成后，用 /SundarrManualTest 验证 .downloading、size、rename。
```

---

## 6. Transfer 状态机测试

Phase 5 必须覆盖：

```text
pending -> completed normal flow
failed stores error_code / retryable
verification failure keeps cloud staging
worker reads worker.concurrency from settings
worker disabled does not claim tasks
sundarr start / restart / stop / status manages Worker
worker respects concurrency limit
LocalCloudProvider + LocalWriter happy path
unsupported target is not claimed before its executor exists
size verification and rename
cloud stream failure marks task failed
write failure marks task failed
size mismatch marks task failed
target exists marks task failed without overwrite
GET /transfers/{id} returns progress and current_file
GET /health returns worker status when managed by local CLI
```

Phase 6 再覆盖：

```text
cancel downloading keeps .downloading
completed / failed task rejects cancel
cancelled task is not processed by Worker
cleanup only after all files completed
cleanup requires target exists and size matches
retry failed task
retry refreshes storage config snapshot
worker startup recovery
worker startup recovery keeps .downloading and cloud staging
GET /transfers/{id}/logs returns ordered logs
GET /transfers/{id}/logs filters sensitive data
cleanup refuses staging root and outside path
cancel / retry / cleanup / recovery writes transfer_logs
```

---

## 7. API 测试

必须覆盖：

```text
GET /health
GET /search
GET /resources/{id}
POST /transfers
GET /transfers/{id}
GET /storage/config
POST /storage/config/save
POST /storage/config/test
GET /storage/browse
统一错误响应
```

`POST /transfers/{id}/cancel`、`POST /transfers/{id}/retry` 和 `GET /transfers/{id}/logs` 属于 Phase 6 API 测试范围。

---

## 8. Web Console 测试

MVP 可先做轻量测试。

必须覆盖：

```text
页面可启动
搜索表单可提交
任务列表可显示
SMB 配置表单不显示 password 明文
STORAGE_CONFIG_CHANGED 提示可显示
```

---

## 9. 验收标准

测试体系完成时必须满足：

```text
pytest 可运行。
前端测试或 smoke check 可运行。
不需要真实网盘即可验证主链路。
不需要真实 NAS 即可验证写入流程。
真实供应商开发和真实集成测试等 Web Console 具备任务操作界面后再做。
关键误删保护有测试。
```
