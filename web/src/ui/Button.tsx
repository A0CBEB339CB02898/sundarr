import React from 'react'

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger'
type Size = 'sm' | 'md' | 'lg'

type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant
  size?: Size
}

/**
 * Button · docs/16-design-system.md §6.5
 * variant: primary / secondary / ghost / danger
 * size:    sm / md (默认) / lg
 */
export function Button({
  variant = 'secondary',
  size = 'md',
  className,
  type,
  children,
  ...rest
}: ButtonProps) {
  const cls = className ? `ui-button ${className}` : 'ui-button'
  return (
    <button
      className={cls}
      data-variant={variant}
      data-size={size === 'md' ? undefined : size}
      type={type ?? 'button'}
      {...rest}
    >
      {children}
    </button>
  )
}
