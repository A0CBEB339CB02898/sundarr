import { Button, StatusBadge, ProgressBar } from '../ui'
import { ErrorState as UIErrorState, EmptyState as UIEmptyState } from '../ui'
import { formatBytes } from '../utils/format'
import { transferStatusLabel, transferStatusToneUI, isTransferRunning } from '../utils/labels'
import type { TransferResponse } from '../types'

export function GlobalTransferPanel({
  error,
  isOpen,
  onClose,
  onOpen,
  onRefresh,
  onClear,
  onSelect,
  transfers,
}: {
  error: string | null
  isOpen: boolean
  onClose: () => void
  onOpen: () => void
  onRefresh: () => void
  onClear: () => void
  onSelect: (taskId?: string) => void
  transfers: TransferResponse[]
}) {
  const activeTransfers = transfers.filter(
    (transfer) => !['completed', 'failed', 'cancelled'].includes(transfer.status),
  )
  const visibleTransfers = (activeTransfers.length > 0 ? activeTransfers : transfers).slice(0, 5)

  return (
    <aside className="tx-dock" data-open={isOpen || undefined} aria-label="全局任务面板">
      <button
        className="tx-dock-tab"
        onClick={isOpen ? onClose : onOpen}
        type="button"
        aria-expanded={isOpen}
      >
        <span>任务</span>
        <strong>{activeTransfers.length || transfers.length}</strong>
      </button>
      <div className="tx-dock-card" role="region" aria-label="当前任务">
        <div className="tx-dock-head">
          <p className="ui-eyebrow">当前任务</p>
          <div className="tx-dock-head-actions">
            <Button variant="ghost" size="sm" onClick={onRefresh}>
              刷新
            </Button>
            <Button variant="ghost" size="sm" onClick={onClear}>
              清空
            </Button>
          </div>
        </div>
        {error ? <UIErrorState message="无法读取任务列表" sub={error} /> : null}
        {!error && visibleTransfers.length === 0 ? (
          <UIEmptyState message="暂无任务" sub="创建任务后会出现在这里。" />
        ) : null}
        <div className="tx-dock-list">
          {visibleTransfers.map((transfer) => {
            const running = isTransferRunning(transfer.status)
            const progress = Math.max(0, Math.min(100, transfer.progress))
            return (
              <button
                className="tx-dock-row"
                key={transfer.id}
                onClick={() => onSelect(transfer.id)}
                type="button"
              >
                <div className="tx-dock-row-head">
                  <StatusBadge tone={transferStatusToneUI(transfer.status)} pulse={running}>
                    {transferStatusLabel(transfer.status)}
                  </StatusBadge>
                  <strong title={transfer.target_path}>{transfer.target_path}</strong>
                </div>
                <ProgressBar
                  value={progress / 100}
                  valueLabel={
                    <>
                      {progress.toFixed(0)}%
                      {transfer.status === 'downloading' && transfer.speed_bytes_per_sec > 0
                        ? ` · ${formatBytes(transfer.speed_bytes_per_sec)}/s`
                        : ''}
                    </>
                  }
                />
                <small title={transfer.current_file || transfer.id}>
                  {transfer.current_file || transfer.id}
                </small>
              </button>
            )
          })}
        </div>
        <Button
          variant="primary"
          className="tx-dock-cta"
          onClick={() => onSelect()}
        >
          打开任务页
        </Button>
      </div>
    </aside>
  )
}
