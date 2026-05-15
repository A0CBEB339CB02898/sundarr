export function TransferDetail({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="tx-detail-item">
      <dt>{label}</dt>
      <dd data-mono={mono ? 'true' : undefined}>{value}</dd>
    </div>
  )
}
