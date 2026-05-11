type BrandLockupProps = {
  compact?: boolean
  subtitle?: string
}

export function BrandLockup({ compact = false, subtitle = 'Web Console' }: BrandLockupProps) {
  return (
    <div className="brand" data-compact={compact ? 'true' : undefined}>
      <BrandMark />
      <div className="brand-copy">
        <Wordmark />
        {subtitle ? <small>{subtitle}</small> : null}
      </div>
    </div>
  )
}

function BrandMark() {
  return (
    <svg className="brand-mark" viewBox="0 0 100 100" role="img" aria-label="Sundarr">
      <title>Sundarr</title>
      <rect width="100" height="100" rx="22" ry="22" fill="var(--mark-bg, var(--accent))" />
      <circle cx="50" cy="50" r="28" fill="var(--mark-fg, var(--bg))" />
      <circle cx="40" cy="38" r="7" fill="var(--mark-bg, var(--accent))" />
      <circle cx="54" cy="42" r="4.5" fill="var(--mark-bg, var(--accent))" />
      <circle cx="38" cy="56" r="4.5" fill="var(--mark-bg, var(--accent))" />
      <circle cx="58" cy="60" r="5.5" fill="var(--mark-bg, var(--accent))" />
    </svg>
  )
}

function Wordmark() {
  return (
    <svg className="brand-wordmark" viewBox="0 0 350 100" role="img" aria-label="Sundarr" preserveAspectRatio="xMidYMid meet">
      <title>Sundarr</title>
      <text className="brand-wordmark-text" x="8" y="72" textLength="213" lengthAdjust="spacing">Sundar</text>
      <circle className="brand-wordmark-dot" cx="238" cy="54" r="7" />
      <text className="brand-wordmark-text" x="252" y="72">r</text>
    </svg>
  )
}
