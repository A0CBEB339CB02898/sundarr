import { Card, EmptyState as UIEmptyState } from '../ui'
import { formatDateTime } from '../utils/format'
import type { TransferLogResponse } from '../types'

export function TransferLogs({ logs }: { logs: TransferLogResponse[] }) {
  if (logs.length === 0) {
    return (
      <Card>
        <UIEmptyState message="该任务暂无日志" />
      </Card>
    )
  }

  return (
    <Card emphasis="sunken" className="tx-logs">
      <div className="tx-logs-head">
        <p className="ui-eyebrow">任务日志</p>
        <span className="tx-logs-count">{logs.length} 条</span>
      </div>
      <ol className="tx-log-list">
        {logs.map((log) => (
          <li className="tx-log-item" key={log.id}>
            <div className="tx-log-head">
              <span className="tx-log-level" data-level={log.level}>
                {log.level}
              </span>
              <strong>{log.event}</strong>
              <time>{formatDateTime(log.created_at)}</time>
            </div>
            <p>{log.message || '无日志说明。'}</p>
            {log.data ? <code>{JSON.stringify(log.data)}</code> : null}
          </li>
        ))}
      </ol>
    </Card>
  )
}
