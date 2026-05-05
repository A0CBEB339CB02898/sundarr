# Agent 工作规则

本文件定义 Agent 在 Sundarr 项目中的默认工作方式。除非用户明确覆盖，本文件规则优先于普通建议。

---

## 1. 开始任务前必须汇报

Agent 在开始每个非 trivial 任务前，必须先向用户汇报：

```text
当前目标
当前进度
本轮交付物
验收标准
停止条件
```

要求：

1. 汇报必须简洁、具体。
2. 不写空泛计划。
3. 当目标、范围、阻塞或交付物发生变化时，必须及时更新汇报。

---

## 2. 文档同步规则

Agent 必须持续从对话中提取已经确认的长期决策，并及时更新项目文档。

长期决策包括：

```text
产品范围变化
MVP 边界变化
技术选型变化
架构决策
模块职责变化
API、数据模型、状态机变化
开发优先级变化
用户明确偏好
功能进入或移出 MVP
```

不得直接写入文档的内容：

```text
临时头脑风暴
尚未确认的方案
一次性解释
已放弃的想法
闲聊内容
```

规则：

1. 用户明确确认长期决策后，Agent 应在同一轮尽量更新相关文档。
2. 如果一个决策影响多个文档，必须先更新事实来源文档，再更新派生文档。
3. 如果用户只是在比较方案或讨论可能性，必须先总结待确认决策并询问是否写入文档。

---

## 3. 文档归属

文档更新应优先写入对应事实来源：

```text
产品范围和 MVP 边界 -> docs/01-product-scope.md
技术选型和架构理由 -> docs/02-architecture-decisions.md
开发顺序和阶段验收 -> docs/03-mvp-roadmap.md
多源搜索接入规则 -> docs/04-source-adapter-spec.md
搜索处理管线 -> docs/05-search-pipeline-spec.md
SMB / Storage Writer -> docs/06-storage-writer-spec.md
任务状态机 -> docs/07-transfer-state-machine.md
数据模型 -> docs/08-data-model.md
API 契约 -> docs/09-api-contract.md
配置规则 -> docs/10-configuration.md
测试要求 -> docs/11-test-plan.md
本地开发 -> docs/12-local-development.md
Web Console -> docs/13-web-console-spec.md
AI Tool API -> docs/14-ai-tool-api-spec.md
Agent 工作规则 -> AGENTS.md
```

当前汇总参考文档：

```text
Sundarr_mvp_architecture_and_agent_spec.md
Sundarr_documentation_plan.md
```

---

## 4. 当前固定决策

以下决策已确认，后续实现不得随意改变：

```text
MVP 使用 Python + FastAPI 作为 API 后端。
MVP 使用 React + Vite 作为轻量 Web Console。
FastAPI 只作为 API 后端，不做 Jinja2 页面渲染。
FastAPI 后续可封装为 media search tool 供 AI 调用。
MVP 使用 PostgreSQL + Redis。
MVP 不做登录、注册、多用户、权限系统。
MVP 不依赖系统 SMB mount，使用应用内 SmbWriter。
SMB 配置可在 Web Console 修改并热加载。
SMB 配置修改会中断使用旧 SMB 配置的运行中任务。
被中断任务进入 failed，错误码 STORAGE_CONFIG_CHANGED，retryable=true。
被中断任务保留 .downloading 文件和 cloud staging。
MVP 先使用 Mock/Local Provider 跑通流程，再接真实网盘 provider。
多源搜索支持配置型源、代码型源、文档/表格型源。
Web Console 只管理配置型源和文档/表格型源，不在线编辑代码型 Source Adapter。
Web Console 是核心控制台，不做完整媒体库 UI。
项目文档、Git commit message、代码注释、报错提示、界面文案和其他项目相关文本原则上使用简体中文。
```

---

## 4.1 项目文本语言规则

项目内面向人类阅读的文本原则上使用简体中文。

适用范围：

```text
项目文档
Git commit message
代码注释
错误提示
日志事件说明
前端界面文案
README
配置示例说明
测试用例描述
```

例外：

```text
代码标识符
第三方库 API 名称
协议字段
HTTP 标准术语
数据库字段名
枚举值
必须与外部系统保持一致的英文字符串
```

如果英文能显著降低歧义，例如标准错误码 `STORAGE_CONFIG_CHANGED`，可以保留英文枚举值，但对应说明文字应使用简体中文。

---

## 5. MVP 不做事项

除非用户重新确认，MVP 不做：

```text
BT / 磁力 / 种子下载
盗版资源分发或资源托管
绕过网盘限制、破解会员、绕过验证码
登录注册
多用户权限
角色管理
OAuth
复杂审计日志
完整媒体库 UI
海报墙
播放器
完整 NAS 文件管理器
在线编辑代码型 Source Adapter
TMDb / NFO / 媒体刮削
Playwright 重型抓取
OpenList 作为核心搬运层
rclone 作为 MVP 核心传输层
```

---

## 6. 开发顺序

Agent 应按 `docs/03-mvp-roadmap.md` 的 Phase 顺序推进。

默认顺序：

```text
Phase 0: Project Skeleton
Phase 1: Persistence Models
Phase 2: Search And Resource Library
Phase 3: Cloud Staging
Phase 4: Storage Writer
Phase 5: Transfer Worker
Phase 6: Cleanup And Recovery
Phase 7: Web Console
Phase 8: AI Friendly API
```

不得提前实现后续阶段的大型功能，除非当前阶段验收需要或用户明确要求。

---

## 7. Git 规则

1. Agent 可以在完成一个清晰、可验证的交付单元后，自主判断是否需要创建 commit。
2. 创建 commit 前必须检查 `git status`、`git diff` 和近期提交信息。
3. 不要提交 `.env`、凭据、token、cookie、SMB 密码等敏感信息。
4. 不要修改或回滚用户未授权的变更。
5. 不要使用破坏性 Git 命令，除非用户明确要求。
6. commit 应保持小而聚焦，信息准确说明本次交付。
7. 如果存在测试失败、范围不清或疑似敏感文件，必须先暂停并向用户说明，不得自动提交。

---

## 8. 测试与验收

实现代码时，Agent 必须优先保证：

```text
可启动
可测试
状态可追踪
失败可恢复
误删有保护
```

MVP 自动化测试不得依赖真实网盘或真实 NAS。必须提供 Mock/Local Provider 和可测试的 Storage Writer 抽象。

每完成一项非文档型开发任务后，Agent 必须执行对应回归测试，避免技术债积累。

最低要求：

```text
后端变更 -> 运行 pytest
前端变更 -> 运行 npm run build，必要时运行前端测试
配置 / Docker 变更 -> 运行相关启动或配置校验
文档规则变更 -> 检查相关文档是否一致
```

如果回归测试失败，Agent 必须优先修复失败，再继续下一项任务。不得在已知测试失败的情况下继续堆叠新功能，除非用户明确要求暂停修复。
