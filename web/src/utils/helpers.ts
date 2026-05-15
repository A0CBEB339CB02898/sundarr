export function newUuid() {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return crypto.randomUUID()
  }
  return `${Date.now().toString(16)}-${Math.random().toString(16).slice(2)}`
}

export function normalizeBrowsePath(path: string) {
  const normalized = path.trim().replace(/\\/g, '/').replace(/^\/+|\/+$/g, '')
  return normalized ? `/${normalized}` : '/'
}

export function normalizeLibraryPath(path: string) {
  const normalized = path.trim().replace(/\\/g, '/').replace(/^\/+|\/+$/g, '')
  return normalized ? `/${normalized}` : '/'
}

export function remoteBindingPreview(names: string[]) {
  if (names.length <= 2) return names.join('、')
  return `${names.slice(0, 2).join('、')}…`
}

export function triStateFromBoolean(value: boolean | null): '' | 'true' | 'false' {
  if (value === true) return 'true'
  if (value === false) return 'false'
  return ''
}

export function triStateToBoolean(value: '' | 'true' | 'false') {
  if (value === 'true') return true
  if (value === 'false') return false
  return null
}

export function detailToMessage(detail: unknown) {
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => {
        if (typeof item === 'string') return item
        if (item && typeof item === 'object' && 'msg' in item) return String(item.msg)
        return ''
      })
      .filter(Boolean)
    return messages.join('；')
  }
  return ''
}

import type { ResourceCandidate } from '../types'

export function suggestedTargetPath(resource: ResourceCandidate) {
  const year = resource.year ? ` (${resource.year})` : ''
  return `Movies/${resource.normalized_title || resource.title}${year}`
}
