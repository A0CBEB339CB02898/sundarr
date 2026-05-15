import { Card } from '../ui'
import { StatusBadge, ProgressBar } from '../ui'
import { TransferDetail } from './TransferDetail'
import { formatBytes, formatClockFromISO, formatRelative } from '../utils/format'
import { transferStatusLabel, transferStatusToneUI, isTransferRunning } from '../utils/labels'
import type { TransferResponse } from '../types'

export function TransferSummary({ transfer }: { transfer: TransferResponse }) {
  const running = isTransferRunning(transfer.status)
  const progress = Math.max(0, Math.min(100, transfer.progress))
  return (
    <Card emphasis="featured" className="tx-summary">
      <div className="tx-summary-head">
        <StatusBadge tone={transferStatusToneUI(transfer.status)} pulse={running}>
          {transferStatusLabel(transfer.status)}
        </StatusBadge>
        <div>
          <p className="tx-summary-id">{transfer.id}</p>
          <p className="tx-summary-path">{transfer.target_path}</p>
        </div>
      </div>
      <ProgressBar
        value={progress / 100}
        label="进度"
        valueLabel={`${progress.toFixed(2)}%`}
      />
      <dl className="tx-detail-grid">
        <TransferDetail label="当前文件" value={transfer.current_file || '无'} />
        <TransferDetail label="目标类型" value={transfer.target_type} />
        <TransferDetail label="已完成" value={formatBytes(transfer.done_bytes)} mono />
        <TransferDetail label="总大小" value={formatBytes(transfer.total_bytes)} mono />
        <TransferDetail
          label="速度"
          value={
            transfer.speed_bytes_per_sec > 0 ? `${formatBytes(transfer.speed_bytes_per_sec)}/s` : '--'
          }
          mono
        />
        <TransferDetail label="重试次数" value={String(transfer.retry_count)} mono />
        <TransferDetail label="可重试" value={transfer.retryable === true ? '是' : '否'} />
      </dl>
      {transfer.error_code || transfer.error_message ? (
        <div className="tx-error-card" role="alert">
          <strong>{transfer.error_code || '任务错误'}</strong>
          <p>{transfer.error_message || '无错误详情。'}</p>
        </div>
      ) : null}
    </Card>
  )
}
