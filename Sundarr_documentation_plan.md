# Sundarr 文档维护计划

本文件是文档索引，不复制各规格全文。编号文档是事实来源，避免汇总文档与实现再次漂移。

更新时间：2026-08-27。

## 事实来源

| 主题 | 文档 |
|---|---|
| 文档导航 | `docs/00-文档索引.md` |
| 产品范围和 MVP 边界 | `docs/01-产品范围.md` |
| 技术和架构决策 | `docs/02-架构决策.md` |
| 阶段状态和验收门 | `docs/03-开发路线图.md` |
| SOURCE 与搜索管线 | `docs/04-资源搜索.md` |
| SMB、同步与传输状态机 | `docs/05-媒体库同步与传输.md` |
| 数据模型 | `docs/06-数据模型.md` |
| HTTP API 和插件诊断 | `docs/07-接口契约.md` |
| 配置和本地开发 | `docs/08-配置与本地开发.md` |
| 测试与验收 | `docs/09-测试与验收.md` |
| Web Console | `docs/10-网页控制台.md` |
| 前端设计系统 | `docs/11-前端设计系统.md` |
| AI Tool API | `docs/12-人工智能工具接口.md` |
| 系统模块边界 | `docs/13-系统模块.md` |
| 插件 Activation Runtime | `docs/14-插件系统.md` |
| 插件清单 | `docs/15-插件清单.md` |
| 官方仓库和插件开发 | `docs/16-插件仓库与开发.md` |
| 非 MVP 远期方向 | `docs/17-远期功能.md` |

## 当前阶段

```text
Phase 0-9.5 已完成。
Phase 10.0 质量基线收口已完成。
Phase 10.1 通用插件框架第一次技术验收已完成。
Phase 10.2 媒体发现 Core 与 Web Console 结构性收口已完成，没有建设面向用户的 Mock 数据链。
Phase 10.3 当前优先：`sundarr-plugin` 已完成仓库初始化，`sundarr-sources` 保持独立 SOURCE 边界；下一步实现 TMDb，再迁移回归 SeedHub，并依次开发豆瓣目录和豆瓣想看。首个 TMDb 端到端通过后冻结 Plugin API v2。
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
阶段状态只以 docs/03-开发路线图.md 为准。
插件生命周期只以 docs/14-插件系统.md 为准。
```
