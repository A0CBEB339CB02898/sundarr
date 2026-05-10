import React from 'react'

/**
 * Kbd · docs/16-design-system.md §6.15
 * 小 keycap 样式。使用 HTML 语义 <kbd>。
 */
export function Kbd({ children, className }: { children: React.ReactNode; className?: string }) {
  const cls = className ? `ui-kbd ${className}` : 'ui-kbd'
  return <kbd className={cls}>{children}</kbd>
}
