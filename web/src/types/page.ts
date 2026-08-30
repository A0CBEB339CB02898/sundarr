export type PageKey = 'discover' | 'search' | 'favorites' | 'transfers' | 'storage' | 'sources' | 'libraries' | 'remote-libraries' | 'plugins' | 'status'
export type ThemeMode = 'light' | 'dark' | 'system'

export type NavItem = {
  key: PageKey
  path: string
  label: string
  description: string
}

export const navItems: NavItem[] = [
  { key: 'discover', path: '/app/discover', label: '发现', description: '浏览目录、热门与关注更新' },
  { key: 'sources', path: '/app/sources', label: '媒体源', description: '管理已安装 Adapter' },
  { key: 'plugins', path: '/app/plugins', label: '插件', description: '管理仓库、配置与运行状态' },
  { key: 'search', path: '/app/search', label: '搜索', description: '搜索资源并创建搬运任务' },
  { key: 'favorites', path: '/app/favorites', label: '收藏', description: '查看收藏资源和收藏链接' },
  { key: 'storage', path: '/app/storage', label: '存储', description: '管理 SMB 配置和目录浏览' },
  { key: 'libraries', path: '/app/libraries', label: '本地媒体库', description: '管理本地媒体库目录绑定' },
  { key: 'remote-libraries', path: '/app/remote-libraries', label: '远程媒体库', description: '管理远程媒体库目录绑定' },
  { key: 'transfers', path: '/app/transfers', label: '任务', description: '查看进度、日志、取消和重试' },
  { key: 'status', path: '/app/status', label: '状态', description: '查看 API、Worker、数据库和 Redis' },
]
