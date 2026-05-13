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

每完成一项非文档型开发任务后，必须运行对应回归测试和冒烟测试。

最低回归规则：

```text
后端代码变更必须运行 pytest。
前端代码变更必须运行 npm run build，必要时运行前端测试。
配置或 Docker 变更必须运行相关启动或配置校验。
失败测试必须优先修复，不能继续积累新功能。
```

最低冒烟规则：

```text
后端 API 变更必须对本次改动的 endpoint 做最小调用，确认状态码和关键响应字段可用。
后端 CLI 或 Worker 变更必须运行对应命令或等价入口，确认进程、状态或任务流转可触发。
前端页面变更必须确认受影响路由可打开，关键交互可触发，且不会出现空白页或运行时错误。
配置、启动或 Docker 变更必须确认应用可启动，并通过 /health、配置读取或连接测试完成最小验证。
```

冒烟测试用于验证本次交付入口真实可用，不替代回归测试。冒烟测试可以通过自动化测试、TestClient/API 调用、CLI 命令、启动后访问 `/health`、前端页面本地打开检查，或与本次交付等价的最小端到端验证完成。

如果某项回归测试或冒烟测试因环境限制无法运行，必须在交付说明中明确说明原因和风险。

默认 pytest 使用 SQLite 内存数据库验证模型、服务和 API 行为，不要求本机 PostgreSQL 已启动。真实 PostgreSQL 连通性属于本地集成环境检查，必须通过 `/health` 或独立启动校验确认。

Windows 本地运行 pytest 时，默认使用项目内 `.sundarr` 目录作为 pytest 临时目录和 cache 目录，避免系统 Temp、pytest 内置 basetemp 或默认 `.pytest_cache` 权限、占用问题影响测试结果。推荐命令：

```bash
.venv\Scripts\python -m pytest
```

不要在 Windows / Codex 沙盒环境下手动传入 `--basetemp`。项目测试通过 `tests/conftest.py` 接管 `tmp_path` 到 `.sundarr\pytest-tmp`，并通过 `pyproject.toml` 固定 cache 到 `.sundarr\pytest-cache`，避免 pytest 内置临时目录在混合权限运行后生成仅管理员或系统可访问的私有 ACL。

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
代码型 Adapter 插件加载
代码型 Adapter 参数配置
真实站点 Adapter fixture
网盘链接和提取码提取复用
代码型源不能前端编辑
```

真实媒体源测试原则：

```text
每个真实网站 Adapter 必须有 fixture 测试。
默认自动化测试不依赖实时外部网站。
实时网站访问作为手动集成验收或显式集成测试，不纳入默认 pytest。
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

Phase 8 远程媒体库同步到本地媒体库必须覆盖：

```text
多 SMB connection 配置校验                                          已覆盖 (test_smb_connections.py)
SMB connection password 不回显                                     已覆盖 (test_smb_connections.py)
媒体库只能引用 SMB connection 和本地目录                              已覆盖 (test_media_libraries.py)
媒体库至少覆盖 movie / series / unclassified                        已覆盖 (test_media_libraries.py)
同步 binding 只能引用远程媒体库和本地媒体库                          已覆盖 (test_sync.py)
来源路径 traversal 防护                                              已覆盖 (test_download_to_local.py)
媒体库目标路径 traversal 防护                                        已覆盖 (test_media_libraries.py)
文件稳定性判断                                                       已覆盖 (test_sync.py)
目录型资源稳定性判断                                                  待覆盖
binding 匹配 movie / series                                         已覆盖 (test_download_to_local.py)
binding 不明确时进入 unclassified 本地媒体库                          待覆盖
SMB source -> SMB target 的 Worker 任务领取规则                    已覆盖 (test_worker.py)
LocalWriter 替身覆盖 source -> target 的下载成功路径                 已覆盖 (test_worker.py)
.downloading 写入、size 校验、rename                                已覆盖 (test_worker.py)
成功后删除源文件                                                     已覆盖 (test_worker.py)
成功后删除空目录                                                     已覆盖 (test_worker.py)
失败时保留源文件和 .downloading                                     已覆盖 (test_worker.py)
重复扫描不重复创建任务                                                已覆盖 (test_sync.py)
```

真实挂载目录同步到本地媒体库属于手动集成验收，不纳入默认 pytest。手动验收必须使用测试目录和测试文件，避免误删正式媒体库。

---

## 7. API 测试

必须覆盖：

```text
GET /health
GET /search
GET /resources/{id}
POST /transfers
GET /transfers
GET /transfers/{id}
GET /storage/config
POST /storage/config/save
POST /storage/config/test
GET /storage/browse
GET /storage/smb-connections
POST /storage/smb-connections/create
GET /media-libraries
POST /media-libraries/create
GET /remote-media-libraries
POST /remote-media-libraries/create
GET /sync/bindings
POST /sync/bindings/create
POST /sync/scan
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
全局任务面板可显示当前任务摘要
SMB 配置表单不显示 password 明文
STORAGE_CONFIG_CHANGED 提示可显示
配置类页面先展示列表，通过新增按钮弹出表单，不默认展开空新增表单
媒体库页面可创建本地媒体库目录绑定
远程媒体库页面不显示 SMB password 明文
同步页面绑定目标为本地媒体库，不重复配置目标 SMB 凭据
远程媒体库页面可手动触发扫描
亮色 / 暗色 / 跟随系统主题可切换
移动端布局可读可操作
```

Phase 0-7 手动验收结论：

```text
SMB 连接和目录读取通过。
health 状态查询通过。
真实媒体源搜索未通过，因为当前未实现真实网站代码型 Adapter。
真实任务进度未验收，因为当前没有真实下载到本地任务。
任务展示需要从单任务查询补充为任务列表和全局浮动任务面板。
页面布局、移动端响应式和主题模式纳入 Phase 7.8。
```

真实媒体源测试说明：

```text
当前 Source Adapter 测试只覆盖抽象接口、示例源和配置管理。
真实媒体源需要通过代码型 Adapter 逐站点开发，不作为 Phase 0-7 或 Phase 8 默认测试范围。
文档型网站是否可通用读取作为后续实验阶段验证，不作为当前默认测试范围。
```

---

## 9. 验收标准

测试体系完成时必须满足：

```text
pytest 可运行。
前端测试或 smoke check 可运行。
每个非文档型交付都有对应回归测试记录和冒烟测试记录。
不需要真实网盘直接下载即可验证主链路。
不需要真实 NAS 即可验证写入流程。
真实挂载目录下载到本地通过手动集成验收验证。
关键误删保护有测试。
```
