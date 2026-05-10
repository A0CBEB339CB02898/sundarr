import React from 'react'

type CardProps = React.HTMLAttributes<HTMLDivElement> & {
  emphasis?: 'default' | 'featured' | 'sunken'
}

/**
 * Card · docs/16-design-system.md §6.4
 * 新版容器：surface-1/2/sunken + hairline border + radius-lg。
 * 用 className 合并以兼容调用方自定义样式。
 */
export function Card({ emphasis = 'default', className, children, ...rest }: CardProps) {
  const cls = className ? `ui-card ${className}` : 'ui-card'
  const dataEmphasis = emphasis === 'default' ? undefined : emphasis
  return (
    <div className={cls} data-emphasis={dataEmphasis} {...rest}>
      {children}
    </div>
  )
}
