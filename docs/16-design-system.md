# 16 · Sundarr Design System

> Status: v0.1 (spec frozen, visual rework happens in a follow-up PR).
> Scope: the entire web console (`/web`) — every page, every state, three theme modes.
> Inspired by [Linear](https://github.com/VoltAgent/awesome-design-md/blob/main/design-md/linear.app/DESIGN.md) (surface ladder, single-accent discipline), [Warp](https://github.com/VoltAgent/awesome-design-md/blob/main/design-md/warp/DESIGN.md) (warm-not-cold dark, cream text, editorial micro-labels), and [VoltAgent](https://github.com/VoltAgent/awesome-design-md/blob/main/design-md/voltagent/DESIGN.md) (border-weight-as-elevation, mono-as-credibility). Tokens, hierarchy, and component recipes below are Sundarr-original; nothing is copied verbatim. Content rephrased for compliance with licensing restrictions.

---

## 1. Voice & Atmosphere

Sundarr is a self-hosted media mover for homelabbers. The console is a **warm operator terminal**: dense enough to see 30 running tasks on a 1440p display, quiet enough to read for an hour, honest enough to trust with a 12-hour download job. The name is "Sunday" plus the *arr family suffix — the interface should feel like a calm Sunday afternoon in a tool that belongs to the Radarr / Sonarr / Prowlarr lineage without copying their Bootstrap-era look.

Three theme modes ship: **Light (Parchment)**, **Dark (Ember)**, **System** (follows `prefers-color-scheme`). Dark is the flagship. Light is a full first-class mirror, not a hastily inverted dump.

**Principles**
1. **Warm, not sterile.** Canvas is near-black with a brown undertone; text is cream, not pure white. No cold blue-grays.
2. **One accent, used with restraint.** Terracotta — inherited from the existing `--accent-strong`. Brand mark, active nav, primary CTA, focus ring, progress bars. Nothing else.
3. **Elevation by surface-ladder + hairline border.** No drop shadows except for lifted dialogs and the global transfer panel.
4. **Information density is a feature.** Task table is the hero. Typography and spacing must support a 32-row viewport at 1440p without cramping.
5. **Motion is functional.** 150–220ms, ease-out. Toasts slide, progress bars animate, nothing bounces.

---

## 2. Color Tokens

Token names extend (not replace) the existing CSS variables in `web/src/styles.css` so the rewrite is additive. Names marked `(new)` don't exist yet.

### 2.1 Dark — "Ember"

| Token | Value | Role |
|---|---|---|
| `--bg` | `#11100e` | Page canvas. Near-black with brown undertone. |
| `--surface-1` *(new, replaces `--panel-solid`)* | `#1a1814` | Default card, sidebar-content, panel. |
| `--surface-2` *(new, replaces `--panel-alt`)* | `#221f1a` | Featured / hovered / active cards, sub-nav. |
| `--surface-3` *(new)* | `#2a2621` | Popovers, dropdowns, modal body. |
| `--surface-sunken` *(new)* | `#0b0a08` | Code blocks, input fields, log viewer. |
| `--hairline` *(new, replaces `--border`)* | `rgba(240, 225, 200, 0.10)` | 1px containment on cards, table rows. |
| `--hairline-strong` *(new)* | `rgba(240, 225, 200, 0.20)` | Active card border, focused input rim. |
| `--text` | `#f2ead8` | Primary text (cream parchment, **not** `#ffffff`). |
| `--text-muted` *(rename `--muted`)* | `#b9ad96` | Secondary, descriptions, metadata. |
| `--text-subtle` *(new)* | `#847a68` | Tertiary, timestamps, eyebrow labels. |
| `--text-disabled` *(new)* | `#585143` | Disabled text, placeholder. |
| `--accent` | `#d97642` | Terracotta signal. Brand, primary CTA, progress fill, link emphasis. |
| `--accent-hover` *(new)* | `#e68a58` | Primary button hover. |
| `--accent-pressed` *(new)* | `#b85d2d` | Primary button pressed / focus ring. |
| `--accent-tint` *(new)* | `rgba(217, 118, 66, 0.14)` | Active nav background, selected row. |
| `--success` *(new)* | `#4ea77a` | `done`, `verified` statuses. |
| `--success-tint` *(new)* | `rgba(78, 167, 122, 0.14)` | Success row, badge bg. |
| `--warning` *(new)* | `#d9a441` | `paused`, `retrying` statuses. |
| `--warning-tint` *(new)* | `rgba(217, 164, 65, 0.14)` | Warning row, badge bg. |
| `--danger-text` | `#e77b6b` | `failed`, `cancelled`, destructive confirm. |
| `--danger-bg` | `rgba(231, 123, 107, 0.12)` | Danger row, destructive button hover. |
| `--info` *(new)* | `#6aa3c4` | `pending`, `queued`, informational toasts. |
| `--info-tint` *(new)* | `rgba(106, 163, 196, 0.14)` | Info row. |
| `--shadow-sm` *(new)* | `0 2px 6px rgba(0, 0, 0, 0.35)` | Popovers, dropdowns. |
| `--shadow-lg` *(new, replaces `--shadow`)* | `0 24px 60px rgba(0, 0, 0, 0.55)` | Global transfer panel, modals. |
| `--shadow-glow` *(new)* | `0 0 0 1px rgba(217, 118, 66, 0.45), 0 0 12px rgba(217, 118, 66, 0.18)` | Focus ring on brand mark, keyboard focus. |

### 2.2 Light — "Parchment"

A genuine mirror, not an inversion. Keeps the existing `#f4f0e8` parchment canvas.

| Token | Value | Role |
|---|---|---|
| `--bg` | `#f6f1e7` | Page canvas. Warm cream. |
| `--surface-1` | `#fdfaf2` | Default card. |
| `--surface-2` | `#ece4d3` | Featured / hovered / active. |
| `--surface-3` | `#ffffff` | Popovers, modal body. |
| `--surface-sunken` | `#eae2cf` | Code, input, log viewer. |
| `--hairline` | `rgba(31, 22, 10, 0.10)` | Card border. |
| `--hairline-strong` | `rgba(31, 22, 10, 0.20)` | Active/focused border. |
| `--text` | `#201910` | Primary (rich espresso, not `#000000`). |
| `--text-muted` | `#5c4f3d` | Secondary. |
| `--text-subtle` | `#8b7d67` | Tertiary. |
| `--text-disabled` | `#b8ad97` | Disabled. |
| `--accent` | `#b05623` | Terracotta — slightly deeper to retain contrast on cream. |
| `--accent-hover` | `#c6663a` | |
| `--accent-pressed` | `#8f4219` | |
| `--accent-tint` | `rgba(176, 86, 35, 0.10)` | |
| `--success` | `#2f8255` | |
| `--success-tint` | `rgba(47, 130, 85, 0.12)` | |
| `--warning` | `#b8832a` | |
| `--warning-tint` | `rgba(184, 131, 42, 0.14)` | |
| `--danger-text` | `#a93623` | |
| `--danger-bg` | `rgba(169, 54, 35, 0.10)` | |
| `--info` | `#3e6f8a` | |
| `--info-tint` | `rgba(62, 111, 138, 0.10)` | |
| `--shadow-sm` | `0 2px 6px rgba(43, 31, 18, 0.08)` | |
| `--shadow-lg` | `0 24px 60px rgba(43, 31, 18, 0.12)` | |
| `--shadow-glow` | `0 0 0 1px rgba(176, 86, 35, 0.45), 0 0 8px rgba(176, 86, 35, 0.20)` | |

### 2.3 Theme Binding

```
:root                  → Light (Parchment) tokens
:root[data-theme=dark] → Dark (Ember) tokens
@media (prefers-color-scheme: dark)
  :root:not([data-theme]) → Dark (Ember) tokens
```

`ThemeSwitcher` writes `data-theme="light|dark"` to `<html>`, or removes the attribute for `system`. This matches the existing logic — no rewrite needed.

### 2.4 Accent Discipline

The terracotta accent appears **only** in these places:

1. Brand mark & wordmark
2. Primary CTA (`button[data-variant=primary]`)
3. Active sidebar nav item (`aria-current=page`)
4. Keyboard focus ring
5. Progress bar fill (running transfers)
6. Link emphasis and inline `<code class="kbd">` keycaps

Never as a section background, decorative flourish, or icon-colour dump. If a badge needs colour, it uses `--info / --success / --warning / --danger`, not accent.

---

## 3. Typography

### 3.1 Families

```css
--font-sans: "Inter", ui-sans-serif, system-ui, -apple-system, "Segoe UI",
             "Helvetica Neue", Arial, "PingFang SC", "Hiragino Sans GB",
             "Microsoft YaHei", sans-serif;
--font-mono: "JetBrains Mono", ui-monospace, "SF Mono", Menlo, Consolas,
             "Liberation Mono", monospace;
```

Inter 承担绝大多数文本。JetBrains Mono 出现在：任务 ID、时间戳、路径、日志、代码、wordmark 中间的 sun-ray（小太阳）备用字符、以及通过 `font-variant-numeric: tabular-nums` 打开的表格数字（进度 / 大小 / 速度列）。

CJK 回退必须显式声明 —— 界面有大量中文，不能让 Inter 回退到系统衬线字体。`PingFang SC` / `Hiragino Sans GB` / `Microsoft YaHei` 只作为系统字体被引用，不随产品分发。

**License 合规**：两款字体均采用 [SIL Open Font License 1.1](https://scripts.sil.org/ofl)，允许免费商用、嵌入、重分发。唯一限制是"不得单独售卖字体本身"。当我们在 Docker 镜像或 `web/public/fonts/` 随产品分发字体文件时，需要在 `LICENSES/` 目录保留各自的 OFL 文本：

| 字体 | 来源 | License |
|---|---|---|
| Inter | [github.com/rsms/inter](https://github.com/rsms/inter) | SIL OFL 1.1 |
| JetBrains Mono | [github.com/JetBrains/JetBrainsMono](https://github.com/JetBrains/JetBrainsMono) | SIL OFL 1.1 |

CJK 回退字体不涉及分发，零风险。

### 3.2 Scale

| Token | Size / Line / Track | Weight | Use |
|---|---|---|---|
| `display` | 32 / 1.15 / -0.6px | 600 | Page title (`PageHeader h1`) |
| `title` | 22 / 1.25 / -0.3px | 600 | Card titles, section headers |
| `subtitle` | 18 / 1.40 / -0.1px | 500 | Sub-sections, summary cards |
| `body-lg` | 16 / 1.50 / -0.05px | 400 | Long-form paragraphs, page lead |
| `body` | 14 / 1.50 / 0 | 400 | **Default.** Tables, nav, forms. |
| `body-sm` | 13 / 1.45 / 0 | 400 | Descriptions, helper text |
| `caption` | 12 / 1.40 / 0 | 400 | Timestamps, metadata |
| `button` | 14 / 1.20 / 0 | 500 | All button labels |
| `eyebrow` | 11 / 1.30 / +0.8px | 600 | Uppercase section labels (`PageHeader .eyebrow`, card headers) |
| `mono` | 13 / 1.50 / 0 | 400 | IDs, paths, log output, timestamps |
| `mono-sm` | 12 / 1.45 / 0 | 400 | Inline IDs in tables |

Default body is 14px (not 16px) — this is deliberate for density. The page lead paragraph stays at 16px (`body-lg`). Headings scale down on mobile: `display` → 24px below 640px.

### 3.3 Rules

- Never use pure `#ffffff` or `#000000` for text. Always through the `--text*` tokens.
- Uppercase only paired with `eyebrow` tracking. Never uppercase body or button labels.
- Tabular numerics (`font-variant-numeric: tabular-nums`) on every number in the task table, size/speed columns, and status badges.
- Chinese UI copy uses the same tokens; no separate Chinese typographic scale.

---

## 4. Space & Shape

### 4.1 Spacing

4px base. Tokens: `--space-1: 4 · --space-2: 8 · --space-3: 12 · --space-4: 16 · --space-5: 24 · --space-6: 32 · --space-7: 48 · --space-8: 64 · --space-section: 96`.

Conventions:
- **Sidebar width**: 272px desktop, 240px collapsed-but-visible, 100% on mobile drawer.
- **Content max-width**: 1440px, centred, with 32px gutter.
- **Card padding**: 20px default (`--space-5 - 4`), 24px (`--space-5`) for feature cards, 32px (`--space-6`) for the CTA / empty-state hero.
- **Table row padding**: 10px vertical · 16px horizontal (density target: 40px row height at `body` size).
- **Form field padding**: 8px vertical · 12px horizontal (matches button padding so inline input+button align).
- **Button padding**: `sm` 6/12 · `md` 8/14 · `lg` 10/18.
- **Section gap** in page: 32px between cards, 48px between major sections.

### 4.2 Radius

| Token | Value | Use |
|---|---|---|
| `--radius-xs` | 4px | Keycaps, small tags, pagination digits |
| `--radius-sm` | 6px | Inline chips, toast icon bubble |
| `--radius-md` | 8px | **Default.** Buttons, inputs, nav items, table row hover pill |
| `--radius-lg` | 12px | Cards, feature tiles |
| `--radius-xl` | 16px | Brand mark block, hero / screenshot frame |
| `--radius-pill` | 9999px | Status badges, pricing/interval toggles, progress bar |

No radius larger than 16px on containers. Pill only on small categorical shapes.

### 4.3 Elevation

| Level | Recipe | Use |
|---|---|---|
| 0 flat | canvas only | Body text, rows inside tables |
| 1 surface | `--surface-1` + 1px `--hairline` | Default cards, sidebar body, nav items |
| 2 surface | `--surface-2` + 1px `--hairline` | Active card, hovered row, selected task |
| 3 surface + glow | `--surface-1` + 1px `--accent` @ 45% + `--shadow-sm` | Focused input, selected nav, active tab |
| 4 floating | `--surface-3` + 1px `--hairline` + `--shadow-sm` | Popovers, dropdowns, browse modal |
| 5 drawer | `--surface-3` + `--shadow-lg` | Global transfer panel, modal dialog |

No `box-shadow` on static cards. Depth is carried by surface steps + hairline — Linear's rule.

---

## 5. Brand & Logo

"Sundarr" = Sunday + ·arr suffix. 视觉上 Sundarr 隶属于 Servarr 家族（Radarr / Sonarr / Lidarr 等），沿用**圆角正方形徽章 + 粗体单字母 + 单一主色底**的家族语言；差异化在于 **"S" 与播放三角形的整合方式**，以及暖色 terracotta 底色（其他 *arr 多用冷色）。

### 5.1 Primary Mark

- **载体**：64×64 圆角正方形（桌面 logo），`border-radius: 14px`（@64px，等比缩放）。
- **底色**：`--mark-bg` = `--accent`（terracotta）。
- **前景**：`--mark-fg` = 奶油白（dark 模式）/ 奶油米（light 模式），约对应 `--text` / `--surface-1`。
- **主字形**：Inter 900 / 46pt "S"，字距 -2.5px，垂直光学居中。
- **整合元素**：播放三角形（▶），具体整合强度与位置由最终选定的 logo 概念决定。
  候选概念见 `docs/assets/brand/logo-preview.html`，四档强度（纯 S / 指示灯点 /
  内嵌三角 / 播放尾整合）供挑选，默认推荐"内嵌三角"（中度整合）。
- **Clear space**：徽章外留白 ≥ cap-height / 2（@64px 即 ≥ 12px）。
- **最小尺寸**：16px favicon 仍保留圆角 + 单字 S；< 14px 允许降级为纯色方块。

> 以下字段在选定最终概念后由 Agent 回填：路径 SVG、PNG 导出清单、象素级
> 对齐表。实施计划见 §11 第 4 步 Brand。

### 5.2 Wordmark

`sundarr` 全小写，Inter 600，字距 -0.3px。尾部 `r·r` 上色 `--accent`（80% 不透明度），
呼应 Servarr 家族 *arr 后缀。不允许全大写、不允许斜体。组合使用："徽章 + 横向间距 10px + wordmark"。

### 5.3 Favicon

16 / 32 / 48 / 180px PNG + ICO + SVG。所有尺寸均使用圆角 + 实色底（非透明），
便于深色浏览器 tab 与 iOS 主屏图标显示。≤ 16px 时内部三角细节可省略。

### 5.4 Brand Voice（用于界面文案、错误提示、空状态）

- 直接、第二人称（"你的任务已暂停"而非"任务已被暂停"）。
- 不为错误道歉；陈述发生了什么 + 下一步该怎么做。
- 面向用户文案用简中，技术术语（`Worker` `Adapter` `SMB` `Transfer`）保留英文，
  与代码库一致。

---

## 6. Component Recipes

Each recipe maps 1:1 to an existing React component or JSX block in `web/src/main.tsx`.

### 6.1 Sidebar (`aside.sidebar`)

- **Desktop (≥1024px)**: Fixed 272px, always visible. Background `--surface-1`, border-right `--hairline`. Three zones: brand (top, 64px), nav-list (middle, scrollable), theme-switcher + version (bottom).
- **Tablet (768–1023px)**: Collapsed to 64px icon rail. Only icons + brand mark. Expand on hover (220ms) to 272px as an overlay.
- **Mobile (<768px)**: Hidden by default. Replaced by a top bar (`header.top-bar`) with brand-mark + hamburger + theme-switcher. Hamburger opens a full-height left drawer (the same sidebar content) with a scrim.

### 6.2 Nav Item (`button.nav-item`)

- Layout: 12px vertical, 16px horizontal padding; 2-line stack (`label` at `body`/500, `description` at `body-sm`/400 `--text-subtle`).
- States: default (`--surface-1`, no border) · hover (`--surface-2`) · active (`aria-current=page`: `--accent-tint` background, 3px terracotta left indicator bar, `label` → `--accent`, `description` → `--text-muted`).
- Radius: `--radius-md`. Indicator bar is outside the radius — a full-height 3px strip at left edge, `--accent`, `border-radius: 0 2px 2px 0`.
- Icons (new): 16px lucide icons left of label. One per nav item: `satellite-dish` (sources), `search` (search), `hard-drive` (storage), `library` (libraries), `globe` (remote-libraries), `arrow-right-left` (transfers), `activity` (status).

### 6.3 Page Header (`header.page-header`)

- Eyebrow (`p.eyebrow`): `eyebrow` token, `--text-subtle`, no margin-bottom beyond 4px.
- Title (`h1`): `display` token, `--text`, 0 margin.
- Body (`p`): `body-lg` token, `--text-muted`, max-width 720px, 8px top margin.
- Optional right-aligned action cluster: primary CTA + secondary, aligned to title baseline.

### 6.4 Card (new container)

```
.card {
  background: var(--surface-1);
  border: 1px solid var(--hairline);
  border-radius: var(--radius-lg);
  padding: var(--space-5);
}
.card[data-emphasis="featured"] { background: var(--surface-2); }
.card[data-emphasis="sunken"]   { background: var(--surface-sunken); }
```

Card header uses the `eyebrow` token (uppercase small label), followed by `title`. Card footer has a `--hairline` top border, `--space-4` padding, aligned-right action cluster.

### 6.5 Button

Variants: `primary` · `secondary` · `ghost` · `danger` · `icon`.

| Variant | Background | Text | Border | Hover | Pressed |
|---|---|---|---|---|---|
| primary | `--accent` | `--bg` (high contrast) | none | `--accent-hover` | `--accent-pressed` |
| secondary | `--surface-1` | `--text` | 1px `--hairline` | `--surface-2` | `--surface-2`, border `--hairline-strong` |
| ghost | transparent | `--text-muted` | none | `--surface-2`, text `--text` | — |
| danger | `--danger-bg` | `--danger-text` | 1px `--danger-text` @ 30% | `--danger-text`, text `--bg` | darker |
| icon | transparent | `--text-muted` | none | `--surface-2`, text `--text` | — |

All: `--radius-md`, `button` typography, 8px/14px padding (md). Disabled = 0.5 opacity. Focus = 2px offset outline `--accent-pressed`.

### 6.6 Status Badge (pill)

`--radius-pill`, 2/10 padding, 12px font, 500 weight. Status → colour:

| Status | Fg / Bg |
|---|---|
| `pending`, `queued` | `--info` / `--info-tint` |
| `downloading`, `verifying`, `renaming`, `cleaning_*` | `--accent` / `--accent-tint` |
| `paused` | `--warning` / `--warning-tint` |
| `done` | `--success` / `--success-tint` |
| `failed`, `cancelled` | `--danger-text` / `--danger-bg` |

A 6px dot before the label in the fg colour. For `downloading` variants, the dot pulses (1.4s ease-in-out, opacity 0.5↔1.0).

### 6.7 Table (Transfer list, Library list, etc.)

- Container: `.card[data-emphasis="sunken"]` — no padding; table fills.
- Header row: `--surface-2` background, `caption` typography, `--text-subtle`, `eyebrow` letter-spacing. 32px height. Border-bottom `--hairline`.
- Body row: 40px default (density), 48px comfortable. Border-bottom `--hairline`. Hover: `--surface-2`. Selected: `--accent-tint` + 2px left bar in `--accent`.
- Columns in transfers: Status badge · Title (label + source-subtitle) · Progress (bar + %) · Speed (mono tabular) · ETA (mono tabular) · Updated (mono, relative) · Actions (icon row on hover).
- Empty state: centred `EmptyState` component inside table body area.

### 6.8 Form Field (`.field`)

- Label: `body-sm`, `--text-muted`, 4px bottom margin.
- Input / Select / Textarea: `--surface-sunken`, 1px `--hairline`, `--radius-md`, 8/12 padding, `body` size.
- Focus: border `--accent`, outer 2px ring `--accent` @ 35% opacity.
- Helper text (`small.helper`): `caption`, `--text-subtle`, 6px top margin.
- Error state: border `--danger-text`, helper becomes `--danger-text`.
- TriState & endpoint fields inherit these recipes.

### 6.9 Toast (`.toast`)

Existing component; refine:

- Container bottom-right, stacked, 12px gap.
- Each toast: 320–420px width, 12/16 padding, `--radius-md`, `--surface-3`, 1px `--hairline-strong`, `--shadow-sm`.
- Left 4px indicator stripe in `--success | --danger-text | --info`.
- Icon bubble: 20×20, `--radius-sm`, tinted bg (success/info/danger -tint), fg icon in corresponding semantic colour.
- Progress bar: bottom 2px strip, `--accent` at 55% opacity, width animates from 100% to 0% over `duration` ms. Existing CSS is close; keep.
- Motion: slide-in from +16px right + fade 180ms ease-out; slide-out 150ms ease-in.

### 6.10 Global Transfer Panel (`GlobalTransferPanel`)

- Floating dock: bottom-right, 420px wide desktop, full-width bottom sheet on mobile.
- Collapsed: 48px pill showing running count + latest progress bar, `--surface-3`, `--shadow-lg`.
- Expanded: 420×max(420, 60vh), rounded `--radius-lg` top corners only when bottom-docked, full `--radius-lg` when floating.
- Header: title "任务" + running count + refresh + clear + close icons.
- List: same row recipe as 6.7, capped at 10 items with "View all" link to `/app/transfers`.

### 6.11 Browse Modal (SMB / Storage)

- Overlay `rgba(0, 0, 0, 0.55)` with 8px backdrop-filter blur (dark) / 4px (light).
- Dialog: 720px max-width, 70vh max-height, `--surface-3`, `--radius-lg`, `--shadow-lg`.
- Header: breadcrumb (mono 13) + close icon. Body: table of folders/files with icon, name, size, modified. Footer: cancel + select.

### 6.12 Progress Bar

- Track: 6px height, `--surface-2`, `--radius-pill`.
- Fill: `--accent`, `--radius-pill`, width transitions 300ms ease-out on value change.
- Indeterminate (no bytes-total): a 30%-width fill sweeps left-to-right 1.6s linear infinite.
- Label (optional): `caption` mono tabular, right-aligned above track.

### 6.13 Loading / Empty / Error States

Already exist as `LoadingState`, `EmptyState`, `ErrorState`. Keep the API, restyle:

- Each is a centred stack: 40×40 icon/spinner on top, `subtitle` message, optional `body-sm` secondary line, optional CTA button.
- Padding 48px vertical. `--text-muted` for message text. `--danger-text` border-left 3px for errors.
- Spinner: 20px, 2px `--hairline` track + `--accent` arc, 0.9s linear rotate.
- Skeleton variant (new): `--surface-2` blocks with a left-to-right shimmer gradient, 1.2s ease-in-out infinite.

### 6.14 Theme Switcher

- Segmented control, 3 pills: 亮色 / 暗色 / 跟随系统.
- Container: `--surface-sunken`, `--radius-pill`, 2px padding, 1px `--hairline`.
- Selected pill: `--surface-1`, `--shadow-sm`, text `--text`. Unselected: text `--text-muted`.
- 12px font, 6/12 padding per pill. Lives at sidebar bottom (desktop) / in top bar (mobile).

### 6.15 Keyboard Shortcuts (new affordance)

Display keyboard hints on hover for major actions. Keycap (`kbd.kbd`):
- 2/6 padding, `--radius-xs`, `--surface-sunken`, 1px `--hairline`, `--text-muted`, `mono-sm`, tabular.
- Common pairs: `⌘/Ctrl` + `K` (global search), `/` (focus search), `P` (pause selected), `R` (resume), `Esc` (close modal).

---

## 7. Page-by-Page Blueprint

### 7.1 `/app/sources` — 媒体源

- Page header + "新增媒体源" primary button at right.
- Grid of source cards (3-col desktop, 2-col tablet, 1-col mobile), each showing: adapter icon · name (`title`) · status badge · description (`body-sm`) · last tested timestamp (mono) · actions (Test, Edit, Disable).
- Adding / editing opens a side drawer (right, 480px), not a full modal.

### 7.2 `/app/search` — 搜索

- Single search input at top, full-width, 48px tall, with a keycap `/` hint inside.
- Filter chips row below (source filter, category, date).
- Results as a vertical list of `ResourceCard` — each card shows title, source, metadata row (size / date / seeders), and expands on click to show available links as a nested mini-table.

### 7.3 `/app/storage` — 存储

- Two-column layout on desktop: left 40% SMB connections list, right 60% browse preview. Stacks on mobile.
- List uses the sidebar-nav-item pattern (not a card grid) — allows fast switching between 10+ connections.

### 7.4 `/app/libraries` — 本地媒体库

- Table layout: name · type (movie/series/unclassified) · path · scan settings · stats (count, last scan) · actions. Inline-editable path via click-to-edit.

### 7.5 `/app/remote-libraries` — 远程媒体库

- Same table recipe as 7.4 plus a remote endpoint column (mono). Add a sync-status badge.

### 7.6 `/app/transfers` — 任务 *(hero page)*

- Split layout: 60% left task table, 40% right task detail pane. On mobile, table full-width; tapping a row pushes to a detail route.
- Filters row at top: status multiselect · source filter · search · date range · density toggle (compact / comfortable).
- Bulk-action bar appears when ≥1 row selected: Pause / Resume / Cancel / Retry / Delete.
- Detail pane: `TransferSummary` (progress bar, status, size, speed, ETA, source, destination) + `TransferLogs` (mono log viewer with auto-scroll toggle) + actions.

### 7.7 `/app/status` — 状态

- 2×2 card grid of `StatusCard`s (API · DB · Redis · Worker), each showing: label (eyebrow) · value (title) · status dot + coloured description line · last checked (mono caption).
- Below: a "Diagnostics" collapsible with raw JSON from `/health`, rendered in mono in `--surface-sunken`.

---

## 8. Motion

Durations & easings:
- `--motion-fast: 120ms` — hover state colour shift, icon reveal.
- `--motion-base: 180ms` — toast slide, dropdown open, tab change.
- `--motion-slow: 240ms` — drawer / modal open, sidebar collapse, progress bar value change.
- Easing: `--ease-out: cubic-bezier(0.22, 0.61, 0.36, 1)` default; `--ease-in: cubic-bezier(0.55, 0.06, 0.68, 0.19)` for exits.
- Respect `prefers-reduced-motion: reduce` — kill all slide/fade transforms, keep instantaneous opacity only.

Brand mark pulse: the terracotta `·` in the `S·` mark pulses `drop-shadow(0 0 2px)` → `drop-shadow(0 0 6px)` at 3s ease-in-out infinite — the "power on" signal, inspired by VoltAgent's bolt glow (rephrased recipe, our colours).

---

## 9. Responsive

| Name | Width | Sidebar | Header | Table | Global Transfer Panel |
|---|---|---|---|---|---|
| Mobile | <640 | Drawer from hamburger | Top bar, sticky | Single-column card list | Full-width bottom sheet |
| Tablet | 640–1023 | 64px icon rail, hover-expand | Normal | Reduced columns, no detail pane | Floating 360px |
| Desktop | 1024–1439 | 272px fixed | Normal | Full | Floating 420px |
| Wide | ≥1440 | 272px fixed | Normal, content max-1440 centred | Detail pane visible | Floating 420px |

Touch targets: 44×44 minimum on mobile for buttons, row-action icons, and nav items.

---

## 10. Accessibility Checklist

- All interactive elements reachable by Tab, ordered logically (sidebar nav → page actions → content).
- Visible 2px focus ring (`--accent-pressed` outer, 2px offset) on every interactive element. Never remove outlines without replacing.
- Colour contrast: all token pairs must pass WCAG AA 4.5:1 for body / 3:1 for large text. Status badges must pass AA against their `-tint` bg.
- `aria-current="page"` on active nav item (already wired).
- `aria-live="polite"` on toast container (already wired), `aria-live="assertive"` on error toasts.
- Modals trap focus, close on `Esc`, restore focus to trigger on close.
- Form fields have `<label>` association; helper and error text linked via `aria-describedby`.
- Table rows get `role="row"` and action buttons announce the task title.

---

## 11. Implementation Plan (for the follow-up PR)

1. **Tokens**: rewrite `styles.css` top block to include every token in §2, keeping the theme-switching logic.
2. **Global primitives**: extract `Card`, `Button`, `StatusBadge`, `ProgressBar`, `Field`, `Table`, `EmptyState`, `LoadingState`, `ErrorState`, `Toast`, `Skeleton`, `Kbd` into `web/src/ui/` as tiny React components with className + variant props.
3. **Shell**: rebuild `App` / `Sidebar` / `TopBar` to the §6 recipes, add the hamburger + drawer + mobile top bar.
4. **Brand**: add `S·` SVG component, wire it into `brand-mark` + favicon + meta.
5. **Pages**: redo in this order — (a) Transfers (hero), (b) Status, (c) Storage, (d) Sources, (e) Libraries, (f) Remote Libraries, (g) Search. Each page PR-reviewable independently once the shell is in.
6. **Polish**: skeletons for initial load states, keyboard shortcuts, reduced-motion audit.

Do not start step 1 until the current 10-fix PR is merged. This doc is the contract; PRs against it cite the section number they implement.

---

## 12. Attribution

This document synthesizes patterns from three public design references listed at the top and applies them to Sundarr's warm-terracotta palette and dense operator context. All token values, typography hierarchy, component recipes, page blueprints, and brand specifications are Sundarr-original and were not copied verbatim from any source.
