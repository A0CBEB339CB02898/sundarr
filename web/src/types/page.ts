export type PageKey = 'discover' | 'search' | 'favorites' | 'transfers' | 'settings'
export type ThemeMode = 'light' | 'dark' | 'system'

export type NavItem = {
  key: PageKey
  path: string
  label: string
  description: string
}

export const navItems: NavItem[] = [
  { key: 'discover', path: '/app/discover', label: '发现', description: '浏览目录、热门与关注更新' },
  { key: 'search', path: '/app/search', label: '资源搜索', description: '查找具体资源链接' },
  { key: 'favorites', path: '/app/favorites', label: '收藏', description: '查看收藏资源和收藏链接' },
  { key: 'transfers', path: '/app/transfers', label: '任务', description: '查看进度、日志、取消和重试' },
  { key: 'settings', path: '/app/settings', label: '设置', description: '管理插件、存储与媒体库' },
]
