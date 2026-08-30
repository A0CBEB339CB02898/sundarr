import React from 'react'

export type StatusTone = 'info' | 'running' | 'paused' | 'success' | 'danger'

type StatusBadgeProps = {
  tone: StatusTone
  pulse?: boolean
  children: React.ReactNode
  className?: string
}

/**
 * StatusBadge · docs/11-前端设计系统.md §6.6
 * 映射 Transfer 状态到 5 种 tone；pulse 用于 downloading 等进行中状态。
 */
export function StatusBadge({ tone, pulse, children, className }: StatusBadgeProps) {
  const cls = className ? `ui-badge ${className}` : 'ui-badge'
  return (
    <span className={cls} data-tone={tone} data-pulse={pulse ? 'true' : undefined}>
      {children}
    </span>
  )
}
