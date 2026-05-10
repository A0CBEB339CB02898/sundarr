import React from 'react'

type FieldProps = {
  label?: React.ReactNode
  helper?: React.ReactNode
  error?: boolean
  htmlFor?: string
  children: React.ReactNode
  className?: string
}

/**
 * Field · docs/16-design-system.md §6.8
 * 包一层 label + input/select/textarea + helper/error。
 * 不强制 input 类型，调用方放 <input /> 或 <select /> 等即可。
 */
export function Field({ label, helper, error, htmlFor, children, className }: FieldProps) {
  const cls = className ? `ui-field ${className}` : 'ui-field'
  return (
    <div className={cls} data-error={error ? 'true' : undefined}>
      {label != null ? <label htmlFor={htmlFor}>{label}</label> : null}
      {children}
      {helper != null ? <small className="helper">{helper}</small> : null}
    </div>
  )
}
