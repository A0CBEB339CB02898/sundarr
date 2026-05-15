import { Card, StatusBadge, ProgressBar, Button, EmptyState as UIEmptyState } from '../ui'
import { formatBytes, formatRelative } from '../utils/format'
import { isTransferRunning, transferStatusLabel, transferStatusToneUI, canPauseTransfer, canResumeTransfer } from '../utils/labels'
import type { TransferResponse } from '../types'

export function TransferTable({
  onSelect,
  selectedId,
  transfers,
  onDelete,
  onPause,
  onResume,
}: {
  onSelect: (id: string) => void
  selectedId: string | null
  transfers: TransferResponse[]
  onDelete: (id: string) => void
  onPause: (id: string) => void
  onResume: (id: string) => void
}) {
  if (transfers.length === 0) {
    return (
      <Card emphasis="sunken">
        <UIEmptyState
          message="还没有任务"
          sub="创建搜索任务或下载到本地任务后，会显示在这里。"
        />
      </Card>
    )
  }

  return (
    <Card emphasis="sunken" className="tx-table-card">
      <div className="tx-table-head">
        <p className="ui-eyebrow">最近任务</p>
        <span className="tx-table-count">{transfers.length}</span>
      </div>
      <div className="tx-table" role="table" aria-label="任务列表">
        <div className="tx-table-header" role="row">
          <span role="columnheader">状态</span>
          <span role="columnheader">目标 / 文件</span>
          <span role="columnheader">进度</span>
          <span role="columnheader">速度</span>
          <span role="columnheader">更新</span>
          <span role="columnheader" aria-label="操作" />
        </div>
        {transfers.map((item) => {
          const running = isTransferRunning(item.status)
          const progress = Math.max(0, Math.min(100, item.progress))
          return (
            <div
              className="tx-row"
              key={item.id}
              role="row"
              data-selected={selectedId === item.id || undefined}
            >
              <button
                className="tx-row-main"
                onClick={() => onSelect(item.id)}
                type="button"
                aria-label={`查看任务 ${item.target_path}`}
              >
                <span className="tx-col-status" role="cell">
                  <StatusBadge tone={transferStatusToneUI(item.status)} pulse={running}>
                    {transferStatusLabel(item.status)}
                  </StatusBadge>
                </span>
                <span className="tx-col-title" role="cell">
                  <strong title={item.target_path}>{item.target_path}</strong>
                  <small title={item.current_file || item.id}>
                    {item.current_file || item.id}
                  </small>
                </span>
                <span className="tx-col-progress" role="cell">
                  <ProgressBar value={progress / 100} />
                  <em>{progress.toFixed(0)}%</em>
                </span>
                <span className="tx-col-num" role="cell">
                  {item.status === 'downloading' && item.speed_bytes_per_sec > 0
                    ? `${formatBytes(item.speed_bytes_per_sec)}/s`
                    : '--'}
                </span>
                <span className="tx-col-num" role="cell">
                  {formatRelative(item.updated_at)}
                </span>
              </button>
              <div className="tx-row-actions" role="cell">
                {canPauseTransfer(item.status) && (
                  <Button variant="ghost" size="sm" onClick={() => onPause(item.id)}>
                    暂停
                  </Button>
                )}
                {canResumeTransfer(item.status) && (
                  <Button variant="ghost" size="sm" onClick={() => onResume(item.id)}>
                    继续
                  </Button>
                )}
                {(item.status === 'completed' ||
                  item.status === 'failed' ||
                  item.status === 'cancelled') && (
                  <Button variant="danger" size="sm" onClick={() => onDelete(item.id)}>
                    删除
                  </Button>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </Card>
  )
}
