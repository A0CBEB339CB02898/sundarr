import { StatusBadge } from '../ui'

export function StatusStack({
  enabled,
  bindingStatus,
  lastTestOk,
  errorCode,
  errorMessage,
  onDetail,
}: {
  enabled: boolean
  bindingStatus?: string | null
  lastTestOk: boolean | null
  errorCode?: string | null
  errorMessage?: string | null
  onDetail: (message: string) => void
}) {
  const detail = `${errorCode || 'TEST_FAILED'}：${errorMessage || '测试失败。'}`
  return (
    <span className="status-stack">
      <StatusBadge tone={enabled ? 'success' : 'paused'}>{enabled ? '已启用' : '已禁用'}</StatusBadge>
      {bindingStatus ? <StatusBadge tone="paused">{bindingStatus}</StatusBadge> : null}
      {lastTestOk === true ? <StatusBadge tone="success">测试通过</StatusBadge> : null}
      {lastTestOk === false ? (
        <button className="status-detail-button" onClick={() => onDetail(detail)} title={detail} type="button">
          测试不通过
        </button>
      ) : null}
    </span>
  )
}
