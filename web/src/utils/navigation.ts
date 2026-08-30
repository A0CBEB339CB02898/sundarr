import { navItems } from '../types'
import type { PageKey } from '../types'

export function pageFromPath(pathname: string): PageKey {
  if (pathname === '/app/favorite-resources' || pathname === '/app/favorite-links') return 'favorites'
  if (pathname === '/app/discover' || pathname.startsWith('/app/discover/')) return 'discover'
  const matched = navItems.find((item) => item.path === pathname)
  if (!matched && pathname === '/') return 'discover'
  return matched?.key ?? 'discover'
}
