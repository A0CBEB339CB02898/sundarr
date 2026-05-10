# Sundarr Brand Assets

本目录存放 Sundarr 品牌系统的最终资产。对应的规范文档在
[`docs/16-design-system.md`](../../16-design-system.md) §5。

## 文件

| 文件 | 用途 |
|---|---|
| `logo.svg` | 主徽章。Punched Disc 原型。terracotta 圆角 + 奶油 disc + 4 个不对称圆孔。 |
| `logo-mono.svg` | 单色变体。`currentColor` 驱动，用于印刷、浮雕、反白场景。 |
| `cover.html` | 通用封面模板。4 个变体：`doc` / `about` / `pr` / `hero`。通过 URL query 注入标题。 |
| `showcase.html` | **品牌综合示例页**。logo / wordmark / 尺度 / 色票 / 封面预览 / 应用模式，一站式。 |
| `README.md` | 本文件。 |

## 快速引用

### 产品内（React）

```tsx
import logo from '@/assets/brand/logo.svg?url';

<img src={logo} alt="Sundarr" width={32} height={32} />
```

或作为组件（可跟随 CSS 变量着色）：

```tsx
import Logo from '@/assets/brand/logo.svg?react';

<Logo style={{ color: 'currentColor' }} />  {/* logo-mono.svg */}
```

### 文档内（Markdown）

```markdown
![Sundarr](./assets/brand/logo.svg)
```

### HTML 内嵌（SVG symbol）

若一页需要渲染多个实例，用 `<symbol>` 复用（见 `showcase.html`）。

### 封面模板

任何 Markdown 文档 / PR / README 都可以用 iframe 或截图嵌入 `cover.html`：

```
cover.html?variant=doc&eyebrow=DOCS%20/%2007&title=任务状态机
cover.html?variant=about
cover.html?variant=pr&title=Brand%20identity%20final
cover.html?variant=hero&subtitle=Sunday%20morning.%20Your%20cloud.%20Your%20NAS.
```

## Wordmark 规则（r · r rule）

wordmark 的核心规则：`Sundarr` 渲染为 `Sunda r · r`，**中间的点用 `--accent`
上色**，小号、上移、略细。这是 Servarr 家族 `*arr` 后缀的视觉签名。

```html
<span class="wordmark">
  Sunda<span>r</span><span class="dot">·</span><span>r</span>
</span>
```

```css
.wordmark { font-weight: 500; letter-spacing: -0.025em; }
.wordmark .dot {
  color: var(--accent);
  margin: 0 0.02em;
  font-size: 0.62em;
  position: relative; top: -0.14em;
  font-weight: 400;
}
```

三档尺寸：

- **hero** 64 px — 文档封面 / splash / 关于页
- **brand** 16 px — 顶栏 / 侧栏副标 / 导航品牌区
- **inline** 14 px — 正文引用；&lt; 13 px 退化为 `Sundarr`

## 颜色锚点

- `--mark-bg` 徽章底色 terracotta `#d97642`（dark）/ `#b05623`（light）
- `--mark-fg` 前景 disc 奶油 `#f2ead8`（dark）/ `#fdfaf2`（light）

完整的 token 表在 `docs/16-design-system.md` §2。

## 不要做的事

- ✗ 不要在 logo 内部添加任何新元素。扩展遵循 "subtract rather than add"。
- ✗ 不要用纯白 `#ffffff` 或纯黑 `#000000`。
- ✗ 不要把 wordmark 写成全大写、斜体、或去掉中间的 `·`。
- ✗ 不要把 terracotta 用作大面积背景色，它只是信号色。见 §2.4。
