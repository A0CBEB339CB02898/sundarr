import React, { useEffect, useState } from 'react'
import ReactDOM from 'react-dom/client'
import './styles.css'

type PageKey = 'search' | 'transfers' | 'storage' | 'sources' | 'status'

type NavItem = {
  key: PageKey
  path: string
  label: string
  description: string
}

type HealthResponse = {
  status: string
  database: string
  redis: string
  worker: string
}

const navItems: NavItem[] = [
  { key: 'search', path: '/search', label: '搜索', description: '搜索资源并创建搬运任务' },
  { key: 'transfers', path: '/transfers', label: '任务', description: '查看进度、日志、取消和重试' },
  { key: 'storage', path: '/storage', label: '存储', description: '管理 SMB 配置和目录浏览' },
  { key: 'sources', path: '/sources', label: '媒体源', description: '管理配置型和文档型来源' },
  { key: 'status', path: '/status', label: '状态', description: '查看 API、Worker、数据库和 Redis' },
]

const pageCopy: Record<PageKey, { title: string; eyebrow: string; body: string; next: string }> = {
  search: {
    eyebrow: 'Search',
    title: '搜索资源并创建搬运任务',
    body: '这里将接入 GET /search 和 POST /transfers，形成从候选资源到任务创建的最小流程。',
    next: 'Phase 7.5 实现搜索表单、候选列表和创建任务。',
  },
  transfers: {
    eyebrow: 'Transfers',
    title: '任务控制台',
    body: '这里将接入任务状态、任务日志、取消和重试 API，让 Phase 6 的恢复能力可以被前端操作。',
    next: 'Phase 7.3 实现任务查询、日志、取消和重试。',
  },
  storage: {
    eyebrow: 'Storage',
    title: 'SMB 存储设置',
    body: '这里将管理 SMB 配置摘要、连接测试和目录浏览，并明确提示 STORAGE_CONFIG_CHANGED 的影响。',
    next: 'Phase 7.4 实现配置表单、连接测试和目录浏览。',
  },
  sources: {
    eyebrow: 'Sources',
    title: '媒体源管理',
    body: '这里将管理配置型源和文档/表格型源；代码型 Source Adapter 只读展示，不在线编辑。',
    next: 'Phase 7.6 实现 source 列表、编辑、启用、禁用和测试。',
  },
  status: {
    eyebrow: 'Status',
    title: '系统状态摘要',
    body: '这里将作为第一个真实前后端闭环，展示 API、Worker、PostgreSQL 和 Redis 状态。',
    next: 'Phase 7.2 接入 GET /health 和刷新按钮。',
  },
}

const api = createApiClient()

function App() {
  const [activePage, setActivePage] = useState<PageKey>(() => pageFromPath(window.location.pathname))

  useEffect(() => {
    const onPopState = () => setActivePage(pageFromPath(window.location.pathname))
    window.addEventListener('popstate', onPopState)
    return () => window.removeEventListener('popstate', onPopState)
  }, [])

  function navigate(item: NavItem) {
    window.history.pushState({}, '', item.path)
    setActivePage(item.key)
  }

  return (
    <div className="app-shell">
      <aside className="sidebar" aria-label="主导航">
        <div className="brand">
          <span className="brand-mark">S</span>
          <div>
            <p>Sundarr</p>
            <small>Web Console</small>
          </div>
        </div>
        <nav className="nav-list">
          {navItems.map((item) => (
            <button
              aria-current={activePage === item.key ? 'page' : undefined}
              className="nav-item"
              key={item.key}
              onClick={() => navigate(item)}
              type="button"
            >
              <span>{item.label}</span>
              <small>{item.description}</small>
            </button>
          ))}
        </nav>
      </aside>

      <main className="content-shell">
        <PageHeader activePage={activePage} />
        <PagePanel activePage={activePage} />
      </main>
    </div>
  )
}

function PageHeader({ activePage }: { activePage: PageKey }) {
  const copy = pageCopy[activePage]
  return (
    <header className="page-header">
      <p className="eyebrow">{copy.eyebrow}</p>
      <h1>{copy.title}</h1>
      <p>{copy.body}</p>
    </header>
  )
}

function PagePanel({ activePage }: { activePage: PageKey }) {
  const copy = pageCopy[activePage]
  if (activePage === 'status') {
    return <StatusPanel />
  }

  return (
    <section className="panel" aria-labelledby={`${activePage}-title`}>
      <div>
        <p className="panel-kicker">当前停止点</p>
        <h2 id={`${activePage}-title`}>Phase 7.1 页面壳已就绪</h2>
        <p>{copy.next}</p>
      </div>
      <div className="state-grid">
        <LoadingState message="后续页面加载数据时使用此状态。" />
        <ErrorState message="API 错误会统一显示在这里。" />
        <EmptyState message="没有数据时展示明确的空状态。" />
      </div>
      <ApiClientPreview />
    </section>
  )
}

function StatusPanel() {
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  useEffect(() => {
    void loadHealth()
  }, [])

  async function loadHealth() {
    setIsLoading(true)
    setError(null)
    try {
      setHealth(await api.get<HealthResponse>('/health'))
    } catch (exc) {
      setHealth(null)
      setError(exc instanceof Error ? exc.message : '无法读取系统状态。')
    } finally {
      setIsLoading(false)
    }
  }

  const items = health
    ? [
        { label: 'API', value: health.status },
        { label: 'PostgreSQL', value: health.database },
        { label: 'Redis', value: health.redis },
        { label: 'Worker', value: health.worker },
      ]
    : []

  return (
    <section className="panel" aria-labelledby="status-title">
      <div className="panel-header-row">
        <div>
          <p className="panel-kicker">当前停止点</p>
          <h2 id="status-title">系统状态</h2>
          <p>调用 GET /health，展示 API、PostgreSQL、Redis 和 Worker 的当前状态。</p>
        </div>
        <button className="primary-button" disabled={isLoading} onClick={loadHealth} type="button">
          {isLoading ? '刷新中' : '刷新状态'}
        </button>
      </div>

      {isLoading && !health ? <LoadingState message="正在读取系统状态。" /> : null}
      {error ? <ErrorState message={error} /> : null}
      {!isLoading && !error && !health ? <EmptyState message="尚未读取到系统状态。" /> : null}

      {health ? (
        <div className="status-grid">
          {items.map((item) => (
            <StatusCard key={item.label} label={item.label} value={item.value} />
          ))}
        </div>
      ) : null}

      <ApiClientPreview />
    </section>
  )
}

function StatusCard({ label, value }: { label: string; value: string }) {
  const tone = value === 'ok' ? 'ok' : value === 'unknown' ? 'unknown' : 'error'
  return (
    <article className={`status-card ${tone}`}>
      <span>{label}</span>
      <strong>{statusLabel(value)}</strong>
      <p>{statusDescription(label, value)}</p>
    </article>
  )
}

function LoadingState({ message }: { message: string }) {
  return (
    <div className="state-card">
      <span className="spinner" aria-hidden="true" />
      <strong>加载中</strong>
      <p>{message}</p>
    </div>
  )
}

function ErrorState({ message }: { message: string }) {
  return (
    <div className="state-card error-card">
      <strong>请求失败</strong>
      <p>{message}</p>
    </div>
  )
}

function EmptyState({ message }: { message: string }) {
  return (
    <div className="state-card empty-card">
      <strong>暂无数据</strong>
      <p>{message}</p>
    </div>
  )
}

function ApiClientPreview() {
  return (
    <div className="api-preview">
      <span>API Client</span>
      <code>{api.example('health')}</code>
    </div>
  )
}

function statusLabel(value: string) {
  if (value === 'ok') return '正常'
  if (value === 'unknown') return '未知'
  return '异常'
}

function statusDescription(label: string, value: string) {
  if (value === 'ok') return `${label} 当前可用。`
  if (value === 'unknown') return `${label} 状态未知，通常表示尚未由本地 CLI 管理。`
  return `${label} 当前不可用，请检查后端日志或本地启动状态。`
}

function pageFromPath(pathname: string): PageKey {
  const matched = navItems.find((item) => item.path === pathname)
  return matched?.key ?? 'search'
}

function createApiClient() {
  const baseUrl = import.meta.env.VITE_API_BASE_URL || ''
  return {
    async get<T>(path: string): Promise<T> {
      const response = await fetch(`${baseUrl}${path}`)
      if (!response.ok) {
        throw new Error(`请求失败：${response.status}`)
      }
      return response.json() as Promise<T>
    },
    example(path: string) {
      return `GET ${baseUrl || '<same-origin>'}/${path.replace(/^\//, '')}`
    },
  }
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
