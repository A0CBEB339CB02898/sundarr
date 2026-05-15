import type { StatusTone } from '../ui'
import type { TransferStatus, DtlMediaType, MediaType, ResourceLinkResult, TransferResponse } from '../types'

export function syncSeenStatusLabel(status: string) {
  const labels: Record<string, string> = { discovered: '已发现', stable: '已稳定', queued: '已排队', downloading: '下载中', completed: '已完成', failed: '失败', ignored: '已忽略' }
  return labels[status] || status
}

export function syncSeenTone(status: string) {
  if (status === 'completed') return 'ok'
  if (status === 'failed') return 'error'
  if (status === 'discovered' || status === 'ignored') return 'unknown'
  return 'running'
}

export function dtlSeenStatusLabel(status: string) {
  const labels: Record<string, string> = { discovered: '已发现', stable: '已稳定', queued: '已排队', downloading: '下载中', completed: '已完成', failed: '失败', ignored: '已忽略' }
  return labels[status] || status
}

export function dtlSeenTone(status: string) {
  if (status === 'completed') return 'ok'
  if (status === 'failed') return 'error'
  if (status === 'discovered' || status === 'ignored') return 'unknown'
  return 'running'
}

export function mediaTypeLabel(type: MediaType) {
  const labels: Record<MediaType, string> = {
    movie: '电影',
    tv: '剧集',
    anime: '动画',
    unknown: '未知',
  }
  return labels[type]
}

export function providerLabel(provider: string) {
  const labels: Record<string, string> = {
    magnet: '磁力',
    quark: '夸克网盘',
    aliyun: '阿里网盘',
    baidu: '百度网盘',
    xunlei: '迅雷网盘',
    uc: 'UC网盘',
    unknown: '未知链接',
  }
  return labels[provider] || provider
}

export function validationLabel(link: ResourceLinkResult) {
  if (link.validation_status === 'valid') return '有效'
  if (link.validation_status === 'invalid') return '失效'
  if (link.validation_status === 'error') return '检测失败'
  if (link.validation_status === 'unknown') return '未知'
  return link.valid === true ? '有效' : link.valid === false ? '失效' : '未检测'
}

export function linkValidationTone(status: ResourceLinkResult['validation_status']): StatusTone {
  if (status === 'valid') return 'success'
  if (status === 'invalid' || status === 'error') return 'danger'
  if (status === 'unknown') return 'paused'
  if (status === 'checking') return 'running'
  return 'info'
}

export function dtlMediaTypeLabel(type: DtlMediaType) {
  const labels: Record<DtlMediaType, string> = {
    movie: '电影',
    series: '剧集',
    unclassified: '未分类',
  }
  return labels[type]
}

export function canCancelTransfer(status: TransferStatus) {
  return ['pending', 'staging_to_cloud', 'cloud_ready', 'downloading', 'verifying', 'paused'].includes(status)
}

export function canPauseTransfer(status: TransferStatus) {
  return ['pending', 'staging_to_cloud', 'cloud_ready', 'downloading', 'verifying'].includes(status)
}

export function canResumeTransfer(status: TransferStatus) {
  return status === 'paused'
}

export function transferStatusLabel(status: TransferStatus) {
  const labels: Record<TransferStatus, string> = {
    pending: '等待中',
    staging_to_cloud: '转存中',
    cloud_ready: '云端就绪',
    downloading: '下载中',
    verifying: '校验中',
    renaming: '重命名中',
    cleaning_cloud: '清理中',
    cleaning_source: '清理来源',
    completed: '已完成',
    failed: '失败',
    cancelled: '已取消',
    paused: '已暂停',
  }
  return labels[status]
}

export function transferStatusTone(status: TransferStatus) {
  if (status === 'completed') return 'ok'
  if (status === 'failed') return 'error'
  if (status === 'cancelled') return 'unknown'
  if (status === 'paused') return 'unknown'
  return 'running'
}

export function transferStatusToneUI(status: TransferStatus): StatusTone {
  if (status === 'completed') return 'success'
  if (status === 'failed' || status === 'cancelled') return 'danger'
  if (status === 'paused') return 'paused'
  if (status === 'pending') return 'info'
  return 'running'
}

export function isTransferRunning(status: TransferStatus) {
  return [
    'staging_to_cloud',
    'cloud_ready',
    'downloading',
    'verifying',
    'renaming',
    'cleaning_cloud',
    'cleaning_source',
  ].includes(status)
}

export function noticeForTransfer(transfer: TransferResponse) {
  if (transfer.error_code === 'STORAGE_CONFIG_CHANGED') {
    return {
      title: 'SMB 配置已变更，任务已中断。',
      body: '.downloading 文件和 cloud staging 已保留。确认新配置后可以重试任务。',
    }
  }
  if (transfer.error_code === 'CLOUD_CLEANUP_FAILED') {
    return {
      title: '任务已完成，但 cloud staging 清理失败。',
      body: '目标文件已保留，后续需要再次执行安全清理或检查 cloud staging。',
    }
  }
  if (transfer.error_code === 'WORKER_RECOVERY_REQUIRED') {
    return {
      title: 'Worker 启动恢复已介入。',
      body: '任务曾停留在运行态，已保守标记为可重试失败，未删除 .downloading 或 cloud staging。',
    }
  }
  return null
}

export function statusLabel(value: string) {
  if (value === 'ok') return '正常'
  if (value === 'unknown') return '未知'
  return '异常'
}

export function statusDescription(label: string, value: string) {
  if (value === 'ok') return `${label} 当前可用。`
  if (value === 'unknown') return `${label} 状态未知，通常表示尚未由本地 CLI 管理。`
  return `${label} 当前不可用，请检查后端日志或本地启动状态。`
}
