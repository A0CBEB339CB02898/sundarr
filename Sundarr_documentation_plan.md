# Sundarr 文档维护计划

本文件是文档索引，不复制各规格全文。编号文档是事实来源，避免汇总文档与实现再次漂移。

更新时间：2026-08-27。

## 事实来源

| 主题 | 文档 |
|---|---|
| 产品范围和 MVP 边界 | `docs/01-product-scope.md` |
| 技术和架构决策 | `docs/02-architecture-decisions.md` |
| 阶段状态和验收门 | `docs/03-mvp-roadmap.md` |
| Source Adapter | `docs/04-source-adapter-spec.md` |
| 搜索处理管线 | `docs/05-search-pipeline-spec.md` |
| SMB Storage Writer | `docs/06-storage-writer-spec.md` |
| Transfer 状态机 | `docs/07-transfer-state-machine.md` |
| 数据模型 | `docs/08-data-model.md` |
| API 契约 | `docs/09-api-contract.md` |
| 配置 | `docs/10-configuration.md` |
| 测试 | `docs/11-test-plan.md` |
| 本地开发 | `docs/12-local-development.md` |
| Web Console | `docs/13-web-console-spec.md` |
| AI Tool API | `docs/14-ai-tool-api-spec.md` |
| 远程媒体库同步 | `docs/15-download-to-local-spec.md` |
| 前端设计系统 | `docs/16-design-system.md` |
| 系统模块边界 | `docs/17-system-module-review.md` |
| Cloud Direct Download（非 MVP） | `docs/18-cloud-direct-download-spec.md` |
| 官方外部插件仓库（文件名历史保留） | `docs/19-source-repository-plugin-spec.md` |
| 插件 Activation Runtime | `docs/20-plugin-system.md` |
| 插件清单 | `docs/20-plugin-manifest-spec.md` |
| 两阶段搜索 | `docs/20-two-phase-search-spec.md` |
| 插件 API | `docs/21-plugin-api-spec.md` |
| 插件开发 | `docs/22-plugin-development-guide.md` |
| 当前实现摘要 | `docs/23-implementation-summary.md` |
| 当前实施路线 | `docs/24-implementation-roadmap.md` |
| 下一步执行清单 | `docs/25-next-steps.md` |

## 当前阶段

```text
Phase 0-9.5 已完成。
Phase 10.0 质量基线收口已完成。
Phase 10.1 通用插件框架第一次技术验收已完成。
Phase 10.2 媒体发现 Core 与 Web Console 结构性收口已完成，没有建设面向用户的 Mock 数据链。
Phase 10.3 当前优先：初始化 `sundarr-plugin` 通用 Manifest v2 官方仓库，保留 `sundarr-sources` 独立 SOURCE 仓库，逐个实现真实插件并使用真实数据持续回归 Core；首个 TMDb 端到端通过后冻结 Plugin API v2。
Phase 11 AI Friendly API 未开始。
Phase 12 Cloud Direct Download 非 MVP、非近期主线。
```

## 当前新增决策

```text
Sundarr Core 保持 Python + FastAPI。
插件系统借鉴 Cordis 的显式依赖、Activation、可逆清理和原子切换语义，但不依赖 Cordis 包。
Phase 11 后可提供可选 Cordis / DeepSeek Harness HTTP 桥接插件。
插件类型按稳定业务合同划分；MVP 为 SOURCE、CATALOG_PROVIDER、WATCHLIST_PROVIDER，未来保留 TRANSFER_DRIVER、NOTIFICATION。
通用 Manifest v2 支持同仓库多插件声明，迁移期兼容 flat v1 SOURCE 清单。
发现、资源搜索和搬运不是一条所有任务都必须流过的插件流水线；当前 SMB 同步保持 Core 内置。
```

## 维护规则

```text
先更新对应编号事实文档，再更新 README、PRODUCT 和 docs/23-25。
历史测试报告保留当时事实，不改写历史结果。
不在汇总文档复制完整 API、数据模型和状态机。
阶段状态只以 docs/03-mvp-roadmap.md 为准。
插件生命周期只以 docs/20-plugin-system.md 为准。
```
