import { navItems } from '../types'
import type { PageKey } from '../types'

export function pageFromPath(pathname: string): PageKey {
  if (pathname === '/app/favorite-resources' || pathname === '/app/favorite-links') return 'favorites'
  if (pathname === '/app/discover' || pathname.startsWith('/app/discover/')) return 'discover'
  if (['/app/settings', '/app/sources', '/app/plugins', '/app/storage', '/app/libraries', '/app/remote-libraries', '/app/status'].includes(pathname)) return 'settings'
  const matched = navItems.find((item) => item.path === pathname)
  if (!matched && pathname === '/') return 'discover'
  return matched?.key ?? 'discover'
}
