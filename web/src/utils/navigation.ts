import { navItems } from '../types'
import type { PageKey } from '../types'

export function pageFromPath(pathname: string): PageKey {
  if (pathname === '/app/favorite-resources' || pathname === '/app/favorite-links') return 'favorites'
  const matched = navItems.find((item) => item.path === pathname)
  if (!matched && pathname === '/') return 'search'
  return matched?.key ?? 'search'
}
