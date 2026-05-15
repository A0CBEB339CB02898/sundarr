import { Card } from '../ui'
import { noticeForTransfer } from '../utils/labels'
import type { TransferResponse } from '../types'

export function TransferNotice({ transfer }: { transfer: TransferResponse }) {
  const message = noticeForTransfer(transfer)
  if (!message) return null
  return (
    <Card className="tx-notice">
      <strong>{message.title}</strong>
      <p>{message.body}</p>
    </Card>
  )
}
