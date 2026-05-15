# 前端 main.tsx 拆分重构

## 原因

`web/src/main.tsx` 为单文件 SPA，5005 行，包含 8 个页面模块、60+ 类型定义、30+ 工具函数全部混在一个文件中，无标准 React 项目目录结构（无 pages/、components/、api/、types/、utils/），严重偏离 React 最佳实践，已不可维护。

## 目标

| 指标 | 重构前 | 重构后 |
|------|--------|--------|
| `main.tsx` 行数 | 5005 | ~10（仅入口渲染） |
| 最大文件行数 | 5005 | < 800（各页面独立） |
| 类型复用 | 无法独立 import | `import type { ... } from '@/types'` |
| 页面隔离 | 全部共享闭包作用域 | 各自独立文件，按需 import |
| 新人上手成本 | 需通读 5000 行 | 按页面模块逐文件阅读 |

## 目标目录结构

```
web/src/
├── main.tsx                    (入口：ReactDOM.render + <App />，~10 行)
├── App.tsx                     (根组件：状态管理、导航、布局壳、Toast，~200 行)
├── styles.css                  (不变)
│
├── types/
│   ├── index.ts                (统一 re-export)
│   ├── page.ts                 (PageKey, NavItem, ThemeMode)
│   ├── health.ts               (HealthResponse 等)
│   ├── transfer.ts             (TransferResponse, TransferStatus, TransferLog...)
│   ├── storage.ts              (SmbConnection, StorageConfig, StorageBrowse...)
│   ├── search.ts               (SearchResponse, ResourceCandidate, ResourceLink...)
│   ├── favorites.ts            (ResourceFavorite 等)
│   ├── source.ts               (SourceResponse, SourceTestResponse...)
│   ├── library.ts              (MediaLibrary, DTL 类型)
│   ├── sync.ts                 (SyncBinding, SyncConfig...)
│   └── remote-library.ts       (RemoteMediaLibrary...)
│
├── api/
│   └── client.ts               (createApiClient, responseJson, responseErrorMessage, api 实例)
│
├── components/
│   ├── ThemeSwitcher.tsx       (主题切换 + 图标)
│   ├── ViewToggle.tsx
│   ├── PaginationControls.tsx
│   ├── TextField.tsx
│   ├── StatusStack.tsx
│   ├── StorageBrowser.tsx
│   ├── TransferTable.tsx
│   ├── TransferSummary.tsx
│   ├── TransferDetail.tsx
│   ├── DetailItem.tsx
│   ├── TransferNotice.tsx
│   ├── TransferLogs.tsx
│   ├── GlobalTransferPanel.tsx
│   └── ResourceCard.tsx
│
├── pages/
│   ├── PagePanel.tsx           (页面路由分发器)
│   ├── SearchPage.tsx
│   ├── FavoritesPage.tsx
│   ├── TransfersPage.tsx
│   ├── StoragePage.tsx
│   ├── SourcesPage.tsx
│   ├── LibrariesPage.tsx
│   ├── RemoteLibrariesPage.tsx
│   └── StatusPage.tsx
│
├── utils/
│   ├── format.ts               (formatBytes, formatDate, formatDateTime, formatClockFromISO, formatRelative)
│   ├── labels.ts               (所有中文 label/tone 函数)
│   ├── forms.ts                (所有 emptyForm / formFromConfig / formToRequest)
│   ├── theme.ts                (storedThemeMode, applyThemeMode, themeModeLabel)
│   ├── navigation.ts           (pageFromPath)
│   └── helpers.ts              (suggestedTargetPath, detailToMessage, triState 转换, newUuid, normalizePath...)
│
└── ui/                         (不变)
```

## 实现方式

**纯拆分，不改逻辑。** 每个函数/组件原样搬到对应文件，只加必要的 import/export，不重构任何业务逻辑。

依赖关系决定了提取顺序：

```
types/        ← 零依赖
utils/        ← 依赖 types
api/          ← 依赖 types
components/   ← 依赖 types、utils、ui
pages/        ← 依赖 types、api、components、utils、ui
App.tsx       ← 依赖 types、api、components、pages、utils、ui
main.tsx      ← 依赖 App.tsx
```

## 执行流程

每个步骤：
1. 创建新文件，原样搬移代码，添加 import/export
2. 更新 main.tsx，从新文件引入
3. `npm run build` 确认编译通过
4. 手动冒烟测试验证功能正常
5. `git commit` 该步骤

## 回归验证

- **构建验证**：每次拆分后 `npm run build`（tsc + vite build），编译失败即回退
- **Git diff 审查**：提交前确认 diff 只有 import/export 行变化，无业务逻辑改动
- **手动冒烟测试**：启动 dev server，逐页面确认功能正常
- CSS 不动、JSX 结构一字不改 → 视觉差异理论为 0

## 进度

| 步骤 | 状态 | 提交 |
|------|------|------|
| 创建目录结构 + 文档 | ✅ 完成 | b41f39d |
| 提取 types/ | ✅ 完成 | b471f42 |
| 提取 utils/ + api/client.ts | ✅ 完成 | bbb0c17 |
| 提取 components/ | ✅ 完成 | bf6bc48 |
| 提取所有 pages/ + App.tsx + 精简 main.tsx | ✅ 完成 | 见最终提交 |
| 构建验证 | ✅ 通过 | JS 301.72 kB 不变 |

## 最终结果

| 指标 | 重构前 | 重构后 |
|------|--------|--------|
| `main.tsx` 行数 | 5005 | 9 |
| 文件总数 | 13 | 57 |
| 最大文件行数 | 5005 | < 800 |
| 目录数 | 1 (ui/) | 6 (types/ api/ components/ pages/ utils/ ui/) |
| JS bundle | 301.72 kB | 301.72 kB（不变） |
| CSS bundle | 75.10 kB | 75.10 kB（不变） |
