import React from 'react'

type StateProps = {
  message: React.ReactNode
  sub?: React.ReactNode
  icon?: React.ReactNode
  action?: React.ReactNode
  className?: string
}

/**
 * Loading / Empty / Error 三件套 · docs/16-design-system.md §6.13
 * 三者共用同一布局，只在 tone 与默认 icon 上有差异。
 */
function StateBlock({
  tone,
  message,
  sub,
  icon,
  action,
  className,
}: StateProps & { tone?: 'error' }) {
  const cls = className ? `ui-state ${className}` : 'ui-state'
  return (
    <div className={cls} data-tone={tone} role={tone === 'error' ? 'alert' : undefined}>
      {icon ? <div className="ui-state-icon">{icon}</div> : null}
      <div className="ui-state-msg">{message}</div>
      {sub ? <div className="ui-state-sub">{sub}</div> : null}
      {action ? <div>{action}</div> : null}
    </div>
  )
}

export function LoadingState(props: Omit<StateProps, 'icon'> & { icon?: React.ReactNode }) {
  const icon = props.icon ?? <span className="ui-spinner" aria-hidden="true" />
  return <StateBlock {...props} icon={icon} />
}

export function EmptyState(props: StateProps) {
  return <StateBlock {...props} />
}

export function ErrorState(props: StateProps) {
  return <StateBlock {...props} tone="error" />
}
