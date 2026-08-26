# 两阶段搜索架构改造规范

状态：Core `fetch_detail` 协议、API 和 Web Console 交互已实现；SeedHub 实现已移至外部插件仓库，等待 Phase 10.2 端到端验收。

## 1. 目标

将搜索从"一次拉取全部详情"改为"两阶段按需加载"，减少对搜索源（尤其是 SeedHub）的无意义请求压力。

- 搜索阶段只返回资源元数据（不拉详情页、不解析链接）
- 链接获取由用户在前端显式触发
- 同时兼容"一步搜索源"（Phase 1 直接带链接）
- 搜索和收藏模块新增网格/列表双布局切换

## 2. 两阶段协议

### 2.1 SourceModel 扩展

```python
FetchDetailFunction = Callable[[str], Awaitable[RawSearchItem]]

@dataclass(frozen=True)
class SourceModel:
    id: str
    name: str
    description: str
    homepage_url: str
    search_function: SearchFunction
    test_function: SourceTestFunction | None = None
    fetch_detail_function: FetchDetailFunction | None = None  # 新增
```

- `fetch_detail_function is None`：一步源，search 已返回完整结果
- `fetch_detail_function is not None`：两步源，search 只返回资源元数据

### 2.2 Phase 1：搜索（轻量）

| 源类型 | 行为 | HTTP 请求量 |
|---|---|---|
| 两步源（SeedHub） | 只搜索列表页，返回资源元数据，detail_url 指向详情页 | 1 次 |
| 一步源（未来） | 搜索并返回完整结果（含 links） | 自身控制 |

SearchResponse 中的 ResourceCandidate：
- `links: []`
- `source_url` 承载 detail_url，用于 Phase 2
- 前端根据 `source_id` 在注册表中查找 `has_fetch_detail`
- 或者：返回中增加 `has_more_links: bool` 字段

### 2.3 Phase 2：获取详情（按需）

```
POST /search/detail
{
  "source_id": "seedhub",
  "detail_url": "https://www.seedhub.cc/movies/114243/"
}

Response: ResourceCandidate（含 links）
```

后端调用对应源的 `fetch_detail_function(detail_url)`。

## 3. 交互流程

```
用户输入"怪奇物语" → 回车
  ┌─────────────────────────────────────────────────────┐
  │ Phase 1（~1 秒，各源并行搜索）                       │
  │ → 显示资源卡片列表                                  │
  │   每张卡片：标题、年份、来源标签、链接数量徽标        │
  │   两步源：徽标显示"加载链接"                         │
  │   一步源：徽标显示"3 个链接"，可直接展开             │
  └─────────────────────────────────────────────────────┘
  ↓ 用户点击"加载链接"
  ┌─────────────────────────────────────────────────────┐
  │ Phase 2（~2-3 秒，仅请求该资源的详情页）             │
  │ → 卡片展开，显示链接列表（名称、网盘、质量、更新时间）│
  │   "收藏资源"按钮在链接加载后可用                     │
  └─────────────────────────────────────────────────────┘
```

**跨源合并**：同名资源（normalized_title + year 相同）合并为一个卡片，显示多来源标签。

**合并资源加载链接**：用户点击"加载链接"时，只请求没有链接的源（两步源），一步源的链接直接展示。

## 4. 前端布局设计

### 4.1 布局切换

搜索模块和收藏模块的顶部工具栏右侧，提供网格/列表切换按钮组：

```
[搜索结果]            [网格 ⊞ | 列表 ≡]
```

切换到网格视图后，资源以卡片网格排列，每行 2-4 列（响应式）。列表视图为现有的纵向列表布局。

切换状态保存在 localStorage，下次打开恢复。

### 4.2 网格视图（资源卡片）

```
┌─────────────────────┐ ┌─────────────────────┐
│                     │ │                     │
│    [占位图/海报]     │ │    [占位图/海报]     │
│                     │ │                     │
│ 怪奇物语 第五季      │ │ 好东西              │
│ 2025 · 剧集         │ │ 2024 · 电影         │
│ [seedhub]           │ │ [seedhub]           │
│ [加载链接]          │ │ [加载链接]          │
└─────────────────────┘ └─────────────────────┘
```

**设计规范**：
- 卡片背景：`var(--surface-2)`
- 卡片圆角：`var(--radius-md)`
- 占位图区域：`aspect-ratio: 2/3`，灰色背景 + 居中资源名首字
- 标题：`font-size: 14px; font-weight: 600;`，单行截断
- 元信息行：`font-size: 12px; color: var(--text-muted)`
- 来源标签：等宽字体 pill badge，暖色系
- 卡片 hover：边框变为 accent 色，轻微上浮 (transform: translateY(-1px))

### 4.3 列表视图（不变）

保持现有纵向列表布局。资源卡片展开后显示链接行（现有的分列布局）。

### 4.4 加载链接状态

两步源资源卡片在网格/列表视图中统一显示"加载链接"按钮：

- 未加载：按钮显示 `加载链接`，次要样式
- 加载中：按钮变灰显示 `加载中…`，右侧跳动圆点
- 已加载：按钮变为 provider 统计文字（如 `3 夸克 · 2 百度`），点击可收起/展开链接
- 加载失败：按钮变红显示 `加载失败`，点击重试

### 4.5 集合页面布局

收藏页面的"收藏资源"标签页复用与搜索相同的结果展示方式（两阶段交互 + 网格/列表切换）。已有的分页、源分组、provider 过滤保持。

## 5. 后端改动清单

### 5.1 SourceModel（`sundarr/app/sources/base.py`）
- 新增 `fetch_detail_function: FetchDetailFunction | None = None`

### 5.2 SeedHub（外部 `sundarr-sources` 插件）
- Core 已支持两阶段 `SourceModel.fetch_detail_function`。
- SeedHub 的 `search()` 和 `fetch_detail()` 实现属于外部搜索源仓库，不再位于 Sundarr Core。
- 外部 SeedHub 必须用离线 fixture 覆盖列表页、详情页和跳转链接解析。

### 5.3 SearchService（`sundarr/app/services/search_service.py`）
- `search()` 只做轻量搜索
- 新增 `fetch_detail(source_id: str, detail_url: str) -> ResourceCandidate`

### 5.4 API（`sundarr/app/api/search.py`）
- `GET /search` 返回的 ResourceCandidate 不含 links
- 新增 `POST /search/detail`：按 source_id + detail_url 获取链接

### 5.5 schemas（`sundarr/app/schemas/search.py`）
- ResourceCandidate 新增 `has_more_links: bool = False`
- SearchResponse 新增 `detail_url: str | None = None`

## 6. 前端改动清单

### 6.1 搜索模块
- 搜索结果卡片由"资源名 + 年份 + 来源"组成，不显示链接
- 点击"加载链接"展开 Phase 2，显示链接列表
- 新 LoadMoreButton / ExpandableCard 组件

### 6.2 收藏模块
- 收藏资源标签页统一两阶段交互
- 新增网格/列表切换

### 6.3 布局切换组件
- 通用 `ViewToggle` 组件：网格 ⊞ / 列表 ≡
- 搜索和收藏共享此组件
- 状态存储在 localStorage

### 6.4 网格卡片样式
- 新增 `.sx-grid-view`、`.sx-grid-card`、`.sx-grid-card-placeholder` CSS

## 7. 验收标准
- 搜索"好东西"只向 SeedHub 发起 1 次 HTTP 请求（搜索列表页）
- 点击"加载链接"发起 2-3 次 HTTP 请求（详情页 + 跳转页）
- 网格/列表切换正常，状态持久化
- 搜索和收藏模块均支持两种布局
- 一步源（测试用）仍可正常返回完整结果
- pytest 全部通过
