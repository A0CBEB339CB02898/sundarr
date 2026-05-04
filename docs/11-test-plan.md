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

---

## 2. 配置测试

必须覆盖：

```text
启动配置加载
环境变量覆盖
settings 表读写
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

---

## 6. Transfer 状态机测试

必须覆盖：

```text
pending -> completed normal flow
failed stores error_code / retryable
cancel downloading keeps .downloading
verification failure keeps cloud staging
cleanup only after all files completed
retry failed task
worker startup recovery
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
POST /transfers/{id}/cancel
POST /transfers/{id}/retry
GET /settings/storage
PUT /settings/storage
POST /settings/storage/test
GET /storage/browse
统一错误响应
```

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
关键误删保护有测试。
```
