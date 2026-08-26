# Sundarr Design Context

## Design Register

product

## Visual Positioning

Sundarr Web Console 是一个暖色 Homelab 操作台。它服务于长时间运行的媒体同步任务：密度要足够高，状态要清楚，视觉要温暖可信，而不是冷冰冰的企业后台。

核心场景：个人 NAS 用户在桌面浏览器里检查 SMB 连接、远程媒体库、同步任务和 Worker 状态。界面应让用户放心地把 12 小时任务交给系统执行。

## Theme Strategy

三种主题：

- `Light (Parchment)`：暖米色画布，适合日间配置和阅读。
- `Dark (Ember)`：带棕色底色的近黑操作台，适合夜间和长期监控。
- `System`：跟随 `prefers-color-scheme`。

Dark 是旗舰体验，Light 是完整镜像，不是简单反相。

## Color Strategy

策略：Restrained product UI。暖色中性阶梯 + 单一 terracotta 强调色。

关键规则：

- 不使用纯 `#000000` 或 `#ffffff` 作为界面文本。
- Terracotta 只作为信号色，不做大面积背景。
- 状态色必须与 `success / warning / danger / info` 语义绑定，不滥用 accent。

主要 tokens：

```css
--accent: #d97642;          /* dark theme terracotta */
--accent-light: #b05623;    /* light theme terracotta */
--mark-bg: var(--accent);
--mark-fg: #f2ead8;
```

Dark Ember：

```css
--bg: #11100e;
--surface-1: #1a1814;
--surface-2: #221f1a;
--surface-3: #2a2621;
--surface-sunken: #0b0a08;
--text: #f2ead8;
--text-muted: #b9ad96;
--text-subtle: #847a68;
```

Light Parchment：

```css
--bg: #f6f1e7;
--surface-1: #fdfaf2;
--surface-2: #ece4d3;
--surface-3: #fdfaf2;
--surface-sunken: #eae2cf;
--text: #201910;
--text-muted: #5c4f3d;
--text-subtle: #8b7d67;
```

## Typography

- Sans：Inter，回退到 `PingFang SC`、`Hiragino Sans GB`、`Microsoft YaHei`。
- Mono：JetBrains Mono，用于任务 ID、路径、时间戳、日志、代码和数字列。
- 默认 body 为 14px，保留操作台密度。
- Page title 约 32px，移动端降到 24px。
- 表格数字和状态数据使用 tabular numerics。

## Layout Principles

- 信息密度是功能，不是缺陷。
- 静态卡片不靠阴影，使用 surface ladder + 1px hairline。
- 侧栏是主导航；任务面板和状态摘要保持高可见性。
- 配置页面默认先展示列表，通过新增按钮打开表单，不默认展开空新增表单。
- 移动端需要可读可操作，任务面板降级为底部抽屉或折叠入口。

## Brand System

品牌名：Sundarr = Sunday + `arr`。

品牌应读作 Servarr 家族旁支：圆角正方形徽章 + 单一主色底，但使用 Sundarr 自己的 Punched Disc 标记。

### Primary Mark

- 100×100 viewBox。
- 圆角方形 badge，`rx=22`。
- Terracotta 背景。
- Cream disc，`cx=50 cy=50 r=28`。
- 四个不对称穿孔，Web Console 小尺寸使用同色圆点覆盖而不是 SVG mask。

UI 几何：

```text
(40, 38) r=7
(54, 42) r=4.5
(38, 56) r=4.5
(58, 60) r=5.5
```

### Wordmark

Wordmark 写作 `Sundar·r`。中点用 terracotta，表达 Sunday 日轮和 Servarr 后缀。禁止全大写、斜体或移除中点。

### Assets

- `docs/assets/brand/logo.svg`
- `docs/assets/brand/logo-mono.svg`
- `web/public/brand/logo.svg`
- `web/public/brand/logo-mono.svg`
- `web/src/ui/Brand.tsx`

## Component Direction

- `BrandLockup` 用于 sidebar / top bar。
- `ThemeSwitcher` 是三段 icon control，保留 `aria-label` 和 `title`。
- `StatusBadge` 使用语义色和 6px 状态点。
- `ProgressBar` 使用 terracotta 填充，运行态可轻微动画。
- `Card` 只在需要边界和分组时使用，不嵌套滥用。
- Error / Empty / Loading states 使用清楚标题、短说明和可执行动作。

## Motion

- Hover / icon reveal：120ms。
- Toast / dropdown / tab：180ms。
- Drawer / modal / progress value：240ms。
- 默认 ease-out：`cubic-bezier(0.22, 0.61, 0.36, 1)`。
- 尊重 `prefers-reduced-motion: reduce`。

## Accessibility

- 所有交互元素必须可通过键盘访问。
- 当前导航使用 `aria-current="page"`。
- 主题按钮使用 `aria-pressed`、`aria-label` 和 `title`。
- Toast 使用 live region。
- 表单字段必须有 label；错误和 helper 文本应可被读屏关联。
- 色彩对比应满足 WCAG AA：正文 4.5:1，大字号 3:1。

## Copy Rules

- 简体中文优先。
- 技术名词和协议字段保留英文，例如 `SMB`、`Worker`、`Adapter`、`Transfer`。
- 错误文案结构：发生了什么 + 影响 + 下一步。
- 不使用夸张营销词，不暗示绕过网盘限制。

## Absolute Avoids

- 冷蓝灰默认后台。
- 渐变文字。
- 玻璃拟态作为默认容器。
- 大数字 hero metric 模板。
- 统一尺寸图标卡片网格。
- 把 terracotta 用作大面积背景。
- 在 Web Console 中引入完整本地媒体库 UI、本地媒体库海报墙或播放器视觉；媒体发现中心的海报展示不在此限制内。

## Source Documents

- `docs/13-web-console-spec.md`
- `docs/16-design-system.md`
- `docs/assets/brand/README.md`
- `web/src/styles.css`
- `web/src/ui/Brand.tsx`
