import React from 'react'

type ProgressBarProps = {
  /** 0..1。indeterminate=true 时此值被忽略 */
  value?: number
  indeterminate?: boolean
  label?: React.ReactNode
  valueLabel?: React.ReactNode
  className?: string
}

/**
 * ProgressBar · docs/16-design-system.md §6.12
 * 轨道 6px，填充 --accent。indeterminate 时横向扫动。
 */
export function ProgressBar({
  value = 0,
  indeterminate,
  label,
  valueLabel,
  className,
}: ProgressBarProps) {
  const cls = className ? `ui-progress ${className}` : 'ui-progress'
  const width = indeterminate ? undefined : `${Math.max(0, Math.min(1, value)) * 100}%`
  const ariaValue = indeterminate ? undefined : Math.round(Math.max(0, Math.min(1, value)) * 100)
  return (
    <div className={cls} data-indeterminate={indeterminate ? 'true' : undefined}>
      {label || valueLabel ? (
        <div className="label">
          <span>{label}</span>
          <span>{valueLabel}</span>
        </div>
      ) : null}
      <div
        className="track"
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={ariaValue}
      >
        <div className="fill" style={{ width }} />
      </div>
    </div>
  )
}
