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

type TransferResponse = {
  id: string
  resource_id: string | null
  link_id: string
  status: TransferStatus
  mode: string
  cloud_staging_path: string | null
  target_type: string
  target_library: string | null
  target_path: string
  total_bytes: number
  done_bytes: number
  progress: number
  current_file: string | null
  error_code: string | null
  error_message: string | null
  retryable: boolean | null
  retry_count: number
}

type TransferLogResponse = {
  id: string
  task_id: string
  level: string
  event: string
  message: string | null
  data: Record<string, unknown> | null
  created_at: string
}

type TransferStatus =
  | 'pending'
  | 'staging_to_cloud'
  | 'cloud_ready'
  | 'downloading'
  | 'verifying'
  | 'renaming'
  | 'cleaning_cloud'
  | 'completed'
  | 'failed'
  | 'cancelled'

type StorageConfigResponse = {
  type: 'smb'
  host: string
  port: number
  share: string
  username: string
  password_set: boolean
  domain: string
  base_path: string
  libraries: Record<string, string>
}

type StorageConfigRequest = Omit<StorageConfigResponse, 'password_set'> & {
  password: string | null
}

type StorageConfigTestResponse = {
  ok: boolean
  error_code: string | null
  error_message: string | null
}

type StorageBrowseResponse = {
  path: string
  entries: StorageBrowseEntry[]
}

type StorageBrowseEntry = {
  name: string
  path: string
  is_dir: boolean
  size: number | null
}

type StorageFormState = {
  host: string
  port: string
  share: string
  username: string
  password: string
  domain: string
  base_path: string
  library_movies: string
  library_tv: string
  library_anime: string
}

type MediaType = 'movie' | 'tv' | 'anime' | 'unknown'

type SearchResponse = {
  query: string
  count: number
  results: ResourceCandidate[]
}

type ResourceCandidate = {
  id: string
  title: string
  normalized_title: string
  original_title: string | null
  type: MediaType
  year: number | null
  quality: string | null
  score: number
  explanation: string
  source_id: string
  source_url: string | null
  links: ResourceLinkResult[]
}

type ResourceLinkResult = {
  id: string
  provider: string
  url: string
  code: string | null
  valid: boolean | null
  risk_level: string
}

type SearchFormState = {
  q: string
  type: MediaType
  year: string
  limit: string
  target_library: string
  target_path: string
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
  if (activePage === 'transfers') {
    return <TransfersPanel />
  }
  if (activePage === 'storage') {
    return <StoragePanel />
  }
  if (activePage === 'search') {
    return <SearchPanel />
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

function SearchPanel() {
  const [form, setForm] = useState<SearchFormState>({
    q: '',
    type: 'unknown',
    year: '',
    limit: '20',
    target_library: 'movies',
    target_path: '',
  })
  const [response, setResponse] = useState<SearchResponse | null>(null)
  const [selectedLink, setSelectedLink] = useState<{ resource: ResourceCandidate; link: ResourceLinkResult } | null>(null)
  const [createdTask, setCreatedTask] = useState<TransferResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isSearching, setIsSearching] = useState(false)
  const [isCreating, setIsCreating] = useState(false)

  async function runSearch() {
    const keyword = form.q.trim()
    if (!keyword) {
      setError('请输入搜索关键词。')
      return
    }

    setIsSearching(true)
    setError(null)
    setCreatedTask(null)
    try {
      const params = new URLSearchParams({ q: keyword, type: form.type, limit: form.limit || '20' })
      if (form.year.trim()) params.set('year', form.year.trim())
      const result = await api.get<SearchResponse>(`/search?${params.toString()}`)
      setResponse(result)
      setSelectedLink(null)
    } catch (exc) {
      setResponse(null)
      setSelectedLink(null)
      setError(exc instanceof Error ? exc.message : '搜索失败。')
    } finally {
      setIsSearching(false)
    }
  }

  async function createTransfer() {
    if (!selectedLink) {
      setError('请先选择一个资源链接。')
      return
    }
    const targetPath = form.target_path.trim()
    if (!targetPath) {
      setError('请输入目标路径。目标路径不明确时需要先确认。')
      return
    }

    setIsCreating(true)
    setError(null)
    try {
      const task = await api.post<TransferResponse>('/transfers', {
        link_id: selectedLink.link.id,
        target_library: form.target_library.trim() || null,
        target_path: targetPath,
      })
      setCreatedTask(task)
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : '创建任务失败。')
    } finally {
      setIsCreating(false)
    }
  }

  function updateField(key: keyof SearchFormState, value: string) {
    setForm((current) => ({ ...current, [key]: value }))
  }

  return (
    <section className="panel" aria-labelledby="search-title">
      <div className="panel-header-row">
        <div>
          <p className="panel-kicker">当前停止点</p>
          <h2 id="search-title">搜索与创建任务</h2>
          <p>搜索候选资源，选择网盘链接，填写目标路径后创建 transfer task。</p>
        </div>
      </div>

      <form className="search-form" onSubmit={(event) => { event.preventDefault(); void runSearch() }}>
        <TextField label="关键词" onChange={(value) => updateField('q', value)} required value={form.q} />
        <label className="field">
          <span>类型</span>
          <select onChange={(event) => updateField('type', event.target.value)} value={form.type}>
            <option value="unknown">未知</option>
            <option value="movie">电影</option>
            <option value="tv">剧集</option>
            <option value="anime">动画</option>
          </select>
        </label>
        <TextField label="年份" onChange={(value) => updateField('year', value)} type="number" value={form.year} />
        <TextField label="数量限制" onChange={(value) => updateField('limit', value)} type="number" value={form.limit} />
        <div className="form-actions">
          <button className="primary-button" disabled={isSearching} type="submit">{isSearching ? '搜索中' : '搜索资源'}</button>
        </div>
      </form>

      {isSearching ? <LoadingState message="正在聚合搜索候选资源。" /> : null}
      {error ? <ErrorState message={error} /> : null}

      {response ? (
        <div className="search-results">
          <div className="section-heading"><h3>候选资源</h3><span>{response.count} 个结果</span></div>
          {response.results.length === 0 ? <EmptyState message="没有搜索到候选资源。" /> : null}
          {response.results.map((resource) => (
            <ResourceCard
              key={resource.id}
              onSelect={(link) => {
                setSelectedLink({ resource, link })
                if (!form.target_path.trim()) updateField('target_path', suggestedTargetPath(resource))
              }}
              resource={resource}
              selectedLinkId={selectedLink?.link.id || null}
            />
          ))}
        </div>
      ) : null}

      <section className="create-transfer-panel" aria-labelledby="create-transfer-title">
        <div className="section-heading"><h3 id="create-transfer-title">创建任务</h3><span>{selectedLink ? selectedLink.link.provider : '未选择链接'}</span></div>
        {selectedLink ? <div className="selected-link-card"><strong>{selectedLink.resource.title}</strong><p>{selectedLink.link.url}</p></div> : <EmptyState message="请先在候选资源中选择一个链接。" />}
        <form className="search-form" onSubmit={(event) => { event.preventDefault(); void createTransfer() }}>
          <TextField label="目标 Library" onChange={(value) => updateField('target_library', value)} value={form.target_library} />
          <TextField label="目标路径" onChange={(value) => updateField('target_path', value)} required value={form.target_path} />
          <div className="form-actions">
            <button className="secondary-button" disabled={!selectedLink || isCreating} type="submit">{isCreating ? '创建中' : '创建 Transfer'}</button>
          </div>
        </form>
        {!form.target_path.trim() ? <div className="notice-card"><strong>需要确认目标路径</strong><p>目标路径为空时不会创建任务，请先确认 library 和最终文件路径。</p></div> : null}
        {createdTask ? <div className="notice-card"><strong>任务已创建</strong><p>任务 ID：{createdTask.id}。可前往任务页查询进度。</p></div> : null}
      </section>

      <ApiClientPreview />
    </section>
  )
}

function ResourceCard({ onSelect, resource, selectedLinkId }: { onSelect: (link: ResourceLinkResult) => void; resource: ResourceCandidate; selectedLinkId: string | null }) {
  return (
    <article className="resource-card">
      <div className="resource-header">
        <div>
          <span className="status-pill running">{mediaTypeLabel(resource.type)}</span>
          <h3>{resource.title}</h3>
          <p>{resource.explanation}</p>
        </div>
        <strong>{resource.score.toFixed(2)}</strong>
      </div>
      <div className="detail-grid">
        <DetailItem label="年份" value={resource.year ? String(resource.year) : '未知'} />
        <DetailItem label="质量" value={resource.quality || '未知'} />
        <DetailItem label="来源" value={resource.source_id} />
      </div>
      <div className="link-list">
        {resource.links.length === 0 ? <EmptyState message="该候选资源没有可用链接。" /> : null}
        {resource.links.map((link) => (
          <button className="link-row" data-selected={selectedLinkId === link.id} key={link.id} onClick={() => onSelect(link)} type="button">
            <span>{link.provider}</span>
            <strong>{link.url}</strong>
            <small>风险：{link.risk_level}</small>
          </button>
        ))}
      </div>
    </article>
  )
}

function StoragePanel() {
  const [form, setForm] = useState<StorageFormState>(emptyStorageForm())
  const [passwordSet, setPasswordSet] = useState(false)
  const [browsePath, setBrowsePath] = useState('')
  const [browseResult, setBrowseResult] = useState<StorageBrowseResponse | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [isTesting, setIsTesting] = useState(false)
  const [isBrowsing, setIsBrowsing] = useState(false)

  useEffect(() => {
    void loadStorageConfig()
  }, [])

  async function loadStorageConfig() {
    setIsLoading(true)
    setError(null)
    try {
      const config = await api.get<StorageConfigResponse>('/storage/config')
      setForm(storageFormFromConfig(config))
      setPasswordSet(config.password_set)
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : '无法读取存储配置。')
    } finally {
      setIsLoading(false)
    }
  }

  async function saveStorageConfig() {
    setIsSaving(true)
    setError(null)
    setMessage(null)
    try {
      const saved = await api.post<StorageConfigResponse>('/storage/config/save', storageRequestFromForm(form))
      setForm(storageFormFromConfig(saved))
      setPasswordSet(saved.password_set)
      setMessage('SMB 配置已保存。使用旧配置的运行中任务会按 STORAGE_CONFIG_CHANGED 中断。')
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : '保存存储配置失败。')
    } finally {
      setIsSaving(false)
    }
  }

  async function testStorageConfig() {
    setIsTesting(true)
    setError(null)
    setMessage(null)
    try {
      const result = await api.post<StorageConfigTestResponse>('/storage/config/test', storageRequestFromForm(form))
      if (result.ok) {
        setMessage('SMB 连接测试通过。')
      } else {
        setError(`${result.error_code || 'STORAGE_TEST_FAILED'}：${result.error_message || 'SMB 连接测试失败。'}`)
      }
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : '测试存储配置失败。')
    } finally {
      setIsTesting(false)
    }
  }

  async function browseStorage(nextPath = browsePath) {
    setIsBrowsing(true)
    setError(null)
    try {
      const result = await api.get<StorageBrowseResponse>(`/storage/browse?path=${encodeURIComponent(nextPath.trim())}`)
      setBrowseResult(result)
      setBrowsePath(result.path)
    } catch (exc) {
      setBrowseResult(null)
      setError(exc instanceof Error ? exc.message : '浏览存储目录失败。')
    } finally {
      setIsBrowsing(false)
    }
  }

  function updateField(key: keyof StorageFormState, value: string) {
    setForm((current) => ({ ...current, [key]: value }))
  }

  return (
    <section className="panel" aria-labelledby="storage-title">
      <div className="panel-header-row">
        <div>
          <p className="panel-kicker">当前停止点</p>
          <h2 id="storage-title">SMB 存储设置</h2>
          <p>管理 SMB 连接配置、测试连接，并在允许范围内浏览目标目录。</p>
        </div>
        <button className="ghost-button" disabled={isLoading} onClick={() => void loadStorageConfig()} type="button">
          {isLoading ? '读取中' : '重新读取'}
        </button>
      </div>

      {message ? <div className="notice-card"><strong>操作完成</strong><p>{message}</p></div> : null}
      {error ? <ErrorState message={error} /> : null}
      {isLoading ? <LoadingState message="正在读取 SMB 配置。" /> : null}

      <form
        className="storage-form"
        onSubmit={(event) => {
          event.preventDefault()
          void saveStorageConfig()
        }}
      >
        <TextField label="Host" onChange={(value) => updateField('host', value)} required value={form.host} />
        <TextField label="Port" onChange={(value) => updateField('port', value)} required type="number" value={form.port} />
        <TextField label="Share" onChange={(value) => updateField('share', value)} required value={form.share} />
        <TextField label="Username" onChange={(value) => updateField('username', value)} required value={form.username} />
        <TextField label="Domain" onChange={(value) => updateField('domain', value)} value={form.domain} />
        <TextField label="Base Path" onChange={(value) => updateField('base_path', value)} value={form.base_path} />
        <TextField
          helper={passwordSet ? '已保存密码。留空表示保留旧密码。' : '尚未保存密码。'}
          label="Password"
          onChange={(value) => updateField('password', value)}
          type="password"
          value={form.password}
        />
        <TextField label="Movies Library" onChange={(value) => updateField('library_movies', value)} value={form.library_movies} />
        <TextField label="TV Library" onChange={(value) => updateField('library_tv', value)} value={form.library_tv} />
        <TextField label="Anime Library" onChange={(value) => updateField('library_anime', value)} value={form.library_anime} />

        <div className="form-actions">
          <button className="primary-button" disabled={isSaving} type="submit">
            {isSaving ? '保存中' : '保存配置'}
          </button>
          <button className="secondary-button" disabled={isTesting} onClick={() => void testStorageConfig()} type="button">
            {isTesting ? '测试中' : '测试连接'}
          </button>
        </div>
      </form>

      <section className="browser-panel" aria-labelledby="storage-browser-title">
        <div className="section-heading">
          <h3 id="storage-browser-title">目录浏览</h3>
          <span>只读浏览</span>
        </div>
        <form
          className="lookup-form"
          onSubmit={(event) => {
            event.preventDefault()
            void browseStorage()
          }}
        >
          <label>
            <span>路径</span>
            <input onChange={(event) => setBrowsePath(event.target.value)} placeholder="例如 Movies" type="text" value={browsePath} />
          </label>
          <button className="primary-button" disabled={isBrowsing} type="submit">
            {isBrowsing ? '浏览中' : '浏览目录'}
          </button>
        </form>

        {isBrowsing && !browseResult ? <LoadingState message="正在读取目录。" /> : null}
        {browseResult ? <StorageBrowser result={browseResult} onOpen={(path) => void browseStorage(path)} /> : <EmptyState message="输入路径后浏览 SMB 目录。" />}
      </section>

      <ApiClientPreview />
    </section>
  )
}

function TextField({
  helper,
  label,
  onChange,
  required = false,
  type = 'text',
  value,
}: {
  helper?: string
  label: string
  onChange: (value: string) => void
  required?: boolean
  type?: string
  value: string
}) {
  return (
    <label className="field">
      <span>{label}</span>
      <input onChange={(event) => onChange(event.target.value)} required={required} type={type} value={value} />
      {helper ? <small>{helper}</small> : null}
    </label>
  )
}

function StorageBrowser({ result, onOpen }: { result: StorageBrowseResponse; onOpen: (path: string) => void }) {
  if (result.entries.length === 0) {
    return <EmptyState message="该目录为空。" />
  }

  return (
    <div className="storage-browser">
      <p>当前路径：<strong>{result.path || '/'}</strong></p>
      <div className="browser-list">
        {result.entries.map((entry) => (
          <button className="browser-row" disabled={!entry.is_dir} key={entry.path} onClick={() => onOpen(entry.path)} type="button">
            <span>{entry.is_dir ? '目录' : '文件'}</span>
            <strong>{entry.name}</strong>
            <small>{entry.is_dir ? entry.path : formatBytes(entry.size || 0)}</small>
          </button>
        ))}
      </div>
    </div>
  )
}

function TransfersPanel() {
  const [taskId, setTaskId] = useState('')
  const [transfer, setTransfer] = useState<TransferResponse | null>(null)
  const [logs, setLogs] = useState<TransferLogResponse[]>([])
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [isMutating, setIsMutating] = useState(false)

  async function loadTransfer(nextTaskId = taskId) {
    const trimmedTaskId = nextTaskId.trim()
    if (!trimmedTaskId) {
      setError('请输入任务 ID。')
      return
    }

    setIsLoading(true)
    setError(null)
    try {
      const [task, taskLogs] = await Promise.all([
        api.get<TransferResponse>(`/transfers/${encodeURIComponent(trimmedTaskId)}`),
        api.get<TransferLogResponse[]>(`/transfers/${encodeURIComponent(trimmedTaskId)}/logs`),
      ])
      setTransfer(task)
      setLogs(taskLogs)
      setTaskId(trimmedTaskId)
    } catch (exc) {
      setTransfer(null)
      setLogs([])
      setError(exc instanceof Error ? exc.message : '无法读取任务。')
    } finally {
      setIsLoading(false)
    }
  }

  async function runTaskAction(action: 'cancel' | 'retry') {
    if (!transfer) return
    setIsMutating(true)
    setError(null)
    try {
      const updated = await api.post<TransferResponse>(`/transfers/${encodeURIComponent(transfer.id)}/${action}`)
      const taskLogs = await api.get<TransferLogResponse[]>(`/transfers/${encodeURIComponent(transfer.id)}/logs`)
      setTransfer(updated)
      setLogs(taskLogs)
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : '任务操作失败。')
    } finally {
      setIsMutating(false)
    }
  }

  const canCancel = transfer ? canCancelTransfer(transfer.status) : false
  const canRetry = transfer?.status === 'failed' && transfer.retryable === true

  return (
    <section className="panel" aria-labelledby="transfers-title">
      <div className="panel-header-row">
        <div>
          <p className="panel-kicker">当前停止点</p>
          <h2 id="transfers-title">任务查询与控制</h2>
          <p>输入任务 ID 后读取任务详情、关键日志，并按当前状态执行取消或重试。</p>
        </div>
      </div>

      <form
        className="lookup-form"
        onSubmit={(event) => {
          event.preventDefault()
          void loadTransfer()
        }}
      >
        <label>
          <span>任务 ID</span>
          <input onChange={(event) => setTaskId(event.target.value)} placeholder="例如 task_001" type="text" value={taskId} />
        </label>
        <button className="primary-button" disabled={isLoading} type="submit">
          {isLoading ? '查询中' : '查询任务'}
        </button>
      </form>

      {isLoading && !transfer ? <LoadingState message="正在读取任务详情和日志。" /> : null}
      {error ? <ErrorState message={error} /> : null}
      {!isLoading && !error && !transfer ? <EmptyState message="输入任务 ID 后查看任务详情。" /> : null}

      {transfer ? (
        <>
          <TransferSummary transfer={transfer} />
          <div className="action-row">
            <button className="primary-button" disabled={!canCancel || isMutating} onClick={() => void runTaskAction('cancel')} type="button">
              {isMutating ? '处理中' : '取消任务'}
            </button>
            <button className="secondary-button" disabled={!canRetry || isMutating} onClick={() => void runTaskAction('retry')} type="button">
              {isMutating ? '处理中' : '重试任务'}
            </button>
            <button className="ghost-button" disabled={isLoading || isMutating} onClick={() => void loadTransfer(transfer.id)} type="button">
              刷新详情
            </button>
          </div>
          <TransferNotice transfer={transfer} />
          <TransferLogs logs={logs} />
        </>
      ) : null}

      <ApiClientPreview />
    </section>
  )
}

function TransferSummary({ transfer }: { transfer: TransferResponse }) {
  return (
    <div className="transfer-summary">
      <div className="summary-main">
        <span className={`status-pill ${transferStatusTone(transfer.status)}`}>{transferStatusLabel(transfer.status)}</span>
        <h3>{transfer.id}</h3>
        <p>{transfer.target_path}</p>
      </div>
      <div className="progress-block">
        <div className="progress-meta">
          <span>进度</span>
          <strong>{transfer.progress.toFixed(2)}%</strong>
        </div>
        <div className="progress-track" aria-label={`任务进度 ${transfer.progress.toFixed(2)}%`}>
          <span style={{ width: `${Math.min(100, Math.max(0, transfer.progress))}%` }} />
        </div>
      </div>
      <div className="detail-grid">
        <DetailItem label="当前文件" value={transfer.current_file || '无'} />
        <DetailItem label="目标类型" value={transfer.target_type} />
        <DetailItem label="已完成" value={formatBytes(transfer.done_bytes)} />
        <DetailItem label="总大小" value={formatBytes(transfer.total_bytes)} />
        <DetailItem label="重试次数" value={String(transfer.retry_count)} />
        <DetailItem label="可重试" value={transfer.retryable === true ? '是' : '否'} />
      </div>
      {transfer.error_code || transfer.error_message ? (
        <div className="error-detail">
          <strong>{transfer.error_code || '任务错误'}</strong>
          <p>{transfer.error_message || '无错误详情。'}</p>
        </div>
      ) : null}
    </div>
  )
}

function DetailItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="detail-item">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  )
}

function TransferNotice({ transfer }: { transfer: TransferResponse }) {
  const message = noticeForTransfer(transfer)
  if (!message) return null
  return (
    <div className="notice-card">
      <strong>{message.title}</strong>
      <p>{message.body}</p>
    </div>
  )
}

function TransferLogs({ logs }: { logs: TransferLogResponse[] }) {
  if (logs.length === 0) {
    return <EmptyState message="该任务暂无日志。" />
  }

  return (
    <div className="log-list">
      <div className="section-heading">
        <h3>任务日志</h3>
        <span>{logs.length} 条</span>
      </div>
      {logs.map((log) => (
        <article className="log-item" key={log.id}>
          <div>
            <span className={`log-level ${log.level}`}>{log.level}</span>
            <strong>{log.event}</strong>
          </div>
          <time>{formatDateTime(log.created_at)}</time>
          <p>{log.message || '无日志说明。'}</p>
          {log.data ? <code>{JSON.stringify(log.data)}</code> : null}
        </article>
      ))}
    </div>
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
        throw new Error(await responseErrorMessage(response))
      }
      return response.json() as Promise<T>
    },
    async post<T>(path: string, body?: unknown): Promise<T> {
      const response = await fetch(`${baseUrl}${path}`, {
        body: body === undefined ? undefined : JSON.stringify(body),
        headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
        method: 'POST',
      })
      if (!response.ok) {
        throw new Error(await responseErrorMessage(response))
      }
      return response.json() as Promise<T>
    },
    example(path: string) {
      return `GET ${baseUrl || '<same-origin>'}/${path.replace(/^\//, '')}`
    },
  }
}

function emptyStorageForm(): StorageFormState {
  return {
    host: '',
    port: '445',
    share: '',
    username: '',
    password: '',
    domain: '',
    base_path: '/',
    library_movies: '',
    library_tv: '',
    library_anime: '',
  }
}

function storageFormFromConfig(config: StorageConfigResponse): StorageFormState {
  return {
    host: config.host,
    port: String(config.port || 445),
    share: config.share,
    username: config.username,
    password: '',
    domain: config.domain || '',
    base_path: config.base_path || '/',
    library_movies: config.libraries.movies || '',
    library_tv: config.libraries.tv || '',
    library_anime: config.libraries.anime || '',
  }
}

function storageRequestFromForm(form: StorageFormState): StorageConfigRequest {
  const libraries: Record<string, string> = {}
  if (form.library_movies.trim()) libraries.movies = form.library_movies.trim()
  if (form.library_tv.trim()) libraries.tv = form.library_tv.trim()
  if (form.library_anime.trim()) libraries.anime = form.library_anime.trim()

  return {
    type: 'smb',
    host: form.host.trim(),
    port: Number(form.port) || 445,
    share: form.share.trim(),
    username: form.username.trim(),
    password: form.password ? form.password : null,
    domain: form.domain.trim(),
    base_path: form.base_path.trim() || '/',
    libraries,
  }
}

function mediaTypeLabel(type: MediaType) {
  const labels: Record<MediaType, string> = {
    movie: '电影',
    tv: '剧集',
    anime: '动画',
    unknown: '未知',
  }
  return labels[type]
}

function suggestedTargetPath(resource: ResourceCandidate) {
  const library = resource.type === 'tv' ? 'TV' : resource.type === 'anime' ? 'Anime' : 'Movies'
  const year = resource.year ? ` (${resource.year})` : ''
  return `${library}/${resource.normalized_title || resource.title}${year}`
}

async function responseErrorMessage(response: Response) {
  try {
    const body = (await response.json()) as { detail?: string }
    if (body.detail) return body.detail
  } catch {
    return `请求失败：${response.status}`
  }
  return `请求失败：${response.status}`
}

function canCancelTransfer(status: TransferStatus) {
  return ['pending', 'staging_to_cloud', 'cloud_ready', 'downloading', 'verifying'].includes(status)
}

function transferStatusLabel(status: TransferStatus) {
  const labels: Record<TransferStatus, string> = {
    pending: '等待中',
    staging_to_cloud: '转存中',
    cloud_ready: '云端就绪',
    downloading: '下载中',
    verifying: '校验中',
    renaming: '重命名中',
    cleaning_cloud: '清理中',
    completed: '已完成',
    failed: '失败',
    cancelled: '已取消',
  }
  return labels[status]
}

function transferStatusTone(status: TransferStatus) {
  if (status === 'completed') return 'ok'
  if (status === 'failed') return 'error'
  if (status === 'cancelled') return 'unknown'
  return 'running'
}

function noticeForTransfer(transfer: TransferResponse) {
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

function formatBytes(value: number) {
  if (value <= 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  const index = Math.min(Math.floor(Math.log(value) / Math.log(1024)), units.length - 1)
  return `${(value / 1024 ** index).toFixed(index === 0 ? 0 : 2)} ${units[index]}`
}

function formatDateTime(value: string) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('zh-CN')
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
