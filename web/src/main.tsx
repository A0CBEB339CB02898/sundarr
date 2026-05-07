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

type SourceType = 'configurable' | 'document' | 'code'
type EditableSourceType = 'configurable' | 'document'

type SourceResponse = {
  id: string
  name: string
  type: SourceType
  enabled: boolean
  legal_note: string | null
  trust_level: number
  created_by_user: boolean
  config_json: Record<string, unknown>
  last_error_code: string | null
  last_error_message: string | null
}

type SourceListResponse = {
  count: number
  results: SourceResponse[]
}

type SourceTestResponse = {
  ok: boolean
  source_id: string
  items: Record<string, unknown>[]
  error_code: string | null
  error_message: string | null
  tested_at: string
}

type SourceFormState = {
  id: string
  name: string
  type: SourceType
  enabled: boolean
  legal_note: string
  trust_level: string
  config_json: string
}

const navItems: NavItem[] = [
  { key: 'search', path: '/app/search', label: '搜索', description: '搜索资源并创建搬运任务' },
  { key: 'transfers', path: '/app/transfers', label: '任务', description: '查看进度、日志、取消和重试' },
  { key: 'storage', path: '/app/storage', label: '存储', description: '管理 SMB 配置和目录浏览' },
  { key: 'sources', path: '/app/sources', label: '媒体源', description: '管理配置型和文档型来源' },
  { key: 'status', path: '/app/status', label: '状态', description: '查看 API、Worker、数据库和 Redis' },
]

const pageCopy: Record<PageKey, { title: string; eyebrow: string; body: string; next: string }> = {
  search: {
    eyebrow: 'Search',
    title: '搜索资源并创建搬运任务',
    body: '搜索候选资源，选择可用链接，并创建后续搬运任务。',
    next: '当前页面暂不可用，请从左侧导航重新进入。',
  },
  transfers: {
    eyebrow: 'Transfers',
    title: '任务控制台',
    body: '查询任务状态、查看日志，并按任务状态取消或重试。',
    next: '当前页面暂不可用，请从左侧导航重新进入。',
  },
  storage: {
    eyebrow: 'Storage',
    title: 'SMB 存储设置',
    body: '管理 SMB 配置、测试连接，并只读浏览目标目录。',
    next: '当前页面暂不可用，请从左侧导航重新进入。',
  },
  sources: {
    eyebrow: 'Sources',
    title: '媒体源管理',
    body: '管理配置型源和文档/表格型源；代码型 Source Adapter 只读展示。',
    next: '当前页面暂不可用，请从左侧导航重新进入。',
  },
  status: {
    eyebrow: 'Status',
    title: '系统状态摘要',
    body: '查看 API、Worker、PostgreSQL 和 Redis 的当前状态。',
    next: '当前页面暂不可用，请从左侧导航重新进入。',
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
  if (activePage === 'sources') {
    return <SourcesPanel />
  }

  return (
    <section className="panel" aria-labelledby={`${activePage}-title`}>
      <div>
        <p className="panel-kicker">控制台</p>
        <h2 id={`${activePage}-title`}>页面暂不可用</h2>
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

function SourcesPanel() {
  const [sources, setSources] = useState<SourceResponse[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [form, setForm] = useState<SourceFormState>(emptySourceForm())
  const [mode, setMode] = useState<'create' | 'edit'>('create')
  const [testResult, setTestResult] = useState<SourceTestResponse | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [isTesting, setIsTesting] = useState(false)
  const [isToggling, setIsToggling] = useState(false)

  useEffect(() => {
    void loadSources()
  }, [])

  const selectedSource = sources.find((source) => source.id === selectedId) || null
  const isCodeSource = selectedSource?.type === 'code'
  const isEditable = mode === 'create' || !isCodeSource

  async function loadSources(nextSelectedId = selectedId) {
    setIsLoading(true)
    setError(null)
    try {
      const response = await api.get<SourceListResponse>('/sources')
      setSources(response.results)
      const nextSource = response.results.find((source) => source.id === nextSelectedId) || response.results[0] || null
      if (nextSource) {
        selectSource(nextSource, false)
      } else {
        startCreate()
      }
    } catch (exc) {
      setSources([])
      setError(exc instanceof Error ? exc.message : '无法读取媒体源。')
    } finally {
      setIsLoading(false)
    }
  }

  function selectSource(source: SourceResponse, clearFeedback = true) {
    setMode('edit')
    setSelectedId(source.id)
    setForm(sourceFormFromResponse(source))
    setTestResult(null)
    if (clearFeedback) {
      setMessage(null)
      setError(null)
    }
  }

  function startCreate() {
    setMode('create')
    setSelectedId(null)
    setForm(emptySourceForm())
    setTestResult(null)
    setMessage(null)
    setError(null)
  }

  async function saveSource() {
    if (!isEditable) {
      setError('代码型 Source Adapter 只能只读展示，不能在线编辑。')
      return
    }
    const actionText = mode === 'create' ? '创建媒体源' : '保存媒体源配置'
    if (!window.confirm(`确认${actionText}？`)) {
      return
    }
    setIsSaving(true)
    setError(null)
    setMessage(null)
    try {
      const config = parseSourceConfig(form.config_json)
      const payload = {
        name: form.name.trim(),
        enabled: form.enabled,
        legal_note: form.legal_note.trim() || null,
        trust_level: Number(form.trust_level) || 1,
        config_json: config,
      }
      const saved = mode === 'create'
        ? await api.post<SourceResponse>('/sources/create', { ...payload, id: form.id.trim(), type: form.type })
        : await api.post<SourceResponse>(`/sources/${encodeURIComponent(form.id)}/update`, payload)
      setMessage(mode === 'create' ? '媒体源已创建。' : '媒体源已保存。')
      await loadSources(saved.id)
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : '保存媒体源失败。')
    } finally {
      setIsSaving(false)
    }
  }

  async function toggleSource(enabled: boolean) {
    if (!selectedSource || isCodeSource) {
      setError('代码型 Source Adapter 只能只读展示，不能在线启用或禁用。')
      return
    }
    if (!window.confirm(`确认${enabled ? '启用' : '禁用'}媒体源 ${selectedSource.name}？`)) {
      return
    }
    setIsToggling(true)
    setError(null)
    setMessage(null)
    try {
      const action = enabled ? 'enable' : 'disable'
      const updated = await api.post<SourceResponse>(`/sources/${encodeURIComponent(selectedSource.id)}/${action}`)
      setMessage(enabled ? '媒体源已启用。' : '媒体源已禁用。')
      await loadSources(updated.id)
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : '切换媒体源状态失败。')
    } finally {
      setIsToggling(false)
    }
  }

  async function testSource() {
    if (!selectedSource) {
      setError('请先选择一个已保存的媒体源。')
      return
    }
    setIsTesting(true)
    setError(null)
    setMessage(null)
    setTestResult(null)
    try {
      const result = await api.post<SourceTestResponse>(`/sources/${encodeURIComponent(selectedSource.id)}/test`)
      setTestResult(result)
      if (result.ok) {
        setMessage('媒体源测试通过。')
      } else {
        setError(`${result.error_code || 'SOURCE_TEST_FAILED'}：${result.error_message || '媒体源测试失败。'}`)
      }
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : '测试媒体源失败。')
    } finally {
      setIsTesting(false)
    }
  }

  function updateField(key: keyof SourceFormState, value: string | boolean) {
    setForm((current) => ({ ...current, [key]: value }))
  }

  return (
    <section className="panel" aria-labelledby="sources-title">
      <div className="panel-header-row">
        <div>
          <p className="panel-kicker">媒体源</p>
          <h2 id="sources-title">媒体源管理</h2>
          <p>管理配置型和文档/表格型 source；代码型 Source Adapter 只读展示。</p>
        </div>
        <button className="ghost-button" disabled={isLoading} onClick={() => void loadSources()} type="button">
          {isLoading ? '读取中' : '重新读取'}
        </button>
      </div>

      {message ? <div className="notice-card"><strong>操作完成</strong><p>{message}</p></div> : null}
      {error ? <ErrorState message={error} /> : null}
      {isLoading && sources.length === 0 ? <LoadingState message="正在读取媒体源列表。" /> : null}

      <div className="sources-layout">
        <aside className="source-list" aria-label="媒体源列表">
          <div className="section-heading"><h3>Source 列表</h3><span>{sources.length} 个</span></div>
          <button className="source-row create-row" data-selected={mode === 'create'} onClick={startCreate} type="button">
            <span>新建</span>
            <strong>创建配置型或文档型 Source</strong>
            <small>Web Console 可编辑</small>
          </button>
          {sources.length === 0 ? <EmptyState message="暂无媒体源，可先创建配置型或文档型 source。" /> : null}
          {sources.map((source) => (
            <button className="source-row" data-selected={selectedId === source.id} key={source.id} onClick={() => selectSource(source)} type="button">
              <span>{sourceTypeLabel(source.type)}</span>
              <strong>{source.name}</strong>
              <small>{source.enabled ? '已启用' : '已禁用'} · trust {source.trust_level}</small>
            </button>
          ))}
        </aside>

        <div className="source-editor">
          <form
            className="source-form"
            onSubmit={(event) => {
              event.preventDefault()
              void saveSource()
            }}
          >
            <TextField disabled={mode === 'edit'} helper="创建后不可修改。仅允许字母、数字、下划线和短横线。" label="Source ID" onChange={(value) => updateField('id', value)} required value={form.id} />
            <TextField disabled={!isEditable} helper="在搜索结果和来源列表中展示的人类可读名称。" label="名称" onChange={(value) => updateField('name', value)} required value={form.name} />
            <label className="field">
              <span>类型</span>
              <select disabled={mode === 'edit'} onChange={(event) => updateField('type', event.target.value as EditableSourceType)} value={form.type}>
                <option value="configurable">配置型</option>
                <option value="document">文档/表格型</option>
                {form.type === 'code' ? <option value="code">代码型</option> : null}
              </select>
              <small>配置型用于规则化网页源；文档/表格型用于维护静态条目；代码型只能只读展示。</small>
            </label>
            <TextField disabled={!isEditable} helper="1 到 5，数字越大表示该 source 可信度越高。" label="Trust Level" onChange={(value) => updateField('trust_level', value)} required type="number" value={form.trust_level} />
            <label className="field checkbox-field">
              <span>启用状态</span>
              <label><input checked={form.enabled} disabled={!isEditable} onChange={(event) => updateField('enabled', event.target.checked)} type="checkbox" /> 启用</label>
              <small>禁用后不会参与搜索，但配置会保留。</small>
            </label>
            <label className="field source-note-field">
              <span>合规说明</span>
              <textarea disabled={!isEditable} onChange={(event) => updateField('legal_note', event.target.value)} value={form.legal_note} />
              <small>记录该 source 的来源范围、使用限制或合法性说明。</small>
            </label>
            <label className="field source-config-field">
              <span>Config JSON</span>
              <textarea disabled={!isEditable} onChange={(event) => updateField('config_json', event.target.value)} spellCheck="false" value={form.config_json} />
              <small>{sourceConfigHint(form.type)}</small>
            </label>

            {isCodeSource ? <div className="notice-card source-form-wide"><strong>只读 Source Adapter</strong><p>代码型 source 不允许通过 Web Console 在线编辑、启用或禁用。</p></div> : null}

            <div className="form-actions">
              <button className="primary-button" disabled={!isEditable || isSaving} type="submit">{isSaving ? '保存中' : mode === 'create' ? '创建 Source' : '保存 Source'}</button>
              <button className="secondary-button" disabled={!selectedSource || isTesting} onClick={() => void testSource()} type="button">{isTesting ? '测试中' : '测试 Source'}</button>
              <button className="ghost-button" disabled={!selectedSource || isCodeSource || isToggling || selectedSource.enabled} onClick={() => void toggleSource(true)} type="button">启用</button>
              <button className="ghost-button" disabled={!selectedSource || isCodeSource || isToggling || !selectedSource.enabled} onClick={() => void toggleSource(false)} type="button">禁用</button>
            </div>
          </form>

          {selectedSource ? <SourceSummary source={selectedSource} /> : <EmptyState message="填写表单后创建新的媒体源。" />}
          {testResult ? <SourceTestResult result={testResult} /> : null}
        </div>
      </div>

      <ApiClientPreview />
    </section>
  )
}

function SourceSummary({ source }: { source: SourceResponse }) {
  return (
    <div className="source-summary">
      <div className="section-heading"><h3>{source.name}</h3><span>{source.enabled ? '已启用' : '已禁用'}</span></div>
      <div className="detail-grid">
        <DetailItem label="ID" value={source.id} />
        <DetailItem label="类型" value={sourceTypeLabel(source.type)} />
        <DetailItem label="用户创建" value={source.created_by_user ? '是' : '否'} />
        <DetailItem label="Trust Level" value={String(source.trust_level)} />
        <DetailItem label="最后错误" value={source.last_error_code || '无'} />
        <DetailItem label="错误说明" value={source.last_error_message || '无'} />
      </div>
      {source.legal_note ? <p>{source.legal_note}</p> : null}
    </div>
  )
}

function SourceTestResult({ result }: { result: SourceTestResponse }) {
  return (
    <div className="source-summary">
      <div className="section-heading"><h3>测试结果</h3><span>{result.ok ? '通过' : '失败'}</span></div>
      <DetailItem label="测试时间" value={formatDateTime(result.tested_at)} />
      {result.error_code ? <div className="error-detail"><strong>{result.error_code}</strong><p>{result.error_message || '无错误详情。'}</p></div> : null}
      {result.items.length === 0 ? <EmptyState message="测试未返回预览条目。" /> : null}
      {result.items.map((item, index) => <code className="json-preview" key={index}>{JSON.stringify(item, null, 2)}</code>)}
    </div>
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
    if (!window.confirm(`确认创建搬运任务到 ${targetPath}？`)) {
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
          <p className="panel-kicker">搜索</p>
          <h2 id="search-title">搜索与创建任务</h2>
          <p>搜索候选资源，选择网盘链接，填写目标路径后创建 transfer task。</p>
        </div>
      </div>

      <form className="search-form" onSubmit={(event) => { event.preventDefault(); void runSearch() }}>
        <TextField helper="要搜索的片名、剧名或关键词。" label="关键词" onChange={(value) => updateField('q', value)} required value={form.q} />
        <label className="field">
          <span>类型</span>
          <select onChange={(event) => updateField('type', event.target.value)} value={form.type}>
            <option value="unknown">未知</option>
            <option value="movie">电影</option>
            <option value="tv">剧集</option>
            <option value="anime">动画</option>
          </select>
          <small>用于缩小搜索范围；不确定时选“未知”。</small>
        </label>
        <TextField helper="可选，用于区分同名作品。" label="年份" onChange={(value) => updateField('year', value)} type="number" value={form.year} />
        <TextField helper="最多返回多少个候选结果。" label="数量限制" onChange={(value) => updateField('limit', value)} type="number" value={form.limit} />
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
          <TextField helper="逻辑媒体库名称，例如 movies、tv、anime。" label="目标 Library" onChange={(value) => updateField('target_library', value)} value={form.target_library} />
          <TextField helper="相对目标路径，不要填写 SMB host/share；例如 Movies/Movie Name (2024)。" label="目标路径" onChange={(value) => updateField('target_path', value)} required value={form.target_path} />
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
    if (!window.confirm('确认保存 SMB 配置？使用旧配置的运行中任务会按 STORAGE_CONFIG_CHANGED 中断。')) {
      return
    }
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
          <p className="panel-kicker">存储</p>
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
        <TextField helper="SMB 服务器地址，只填主机名或 IP，不要带 \\\\ 或共享名。" label="Host" onChange={(value) => updateField('host', value)} required value={form.host} />
        <TextField helper="SMB 端口，通常是 445。" label="Port" onChange={(value) => updateField('port', value)} required type="number" value={form.port} />
        <TextField helper="SMB 共享名，即 \\\\host\\share 中的 share，不要填写子目录。" label="Share" onChange={(value) => updateField('share', value)} required value={form.share} />
        <TextField helper="用于登录 SMB 的账号名。" label="Username" onChange={(value) => updateField('username', value)} required value={form.username} />
        <TextField helper="SMB 域或工作组；个人 NAS 通常留空。" label="Domain" onChange={(value) => updateField('domain', value)} value={form.domain} />
        <TextField helper="共享内的工作根目录，例如 /Sundarr；使用共享根目录时填 /。" label="Base Path" onChange={(value) => updateField('base_path', value)} value={form.base_path} />
        <TextField
          helper={passwordSet ? '已保存密码且不会回显。留空保存表示保留旧密码。' : 'SMB 登录密码；保存后不会在页面回显。'}
          label="Password"
          onChange={(value) => updateField('password', value)}
          type="password"
          value={form.password}
        />
        <TextField helper="电影默认目录，相对于 Base Path。" label="Movies Library" onChange={(value) => updateField('library_movies', value)} value={form.library_movies} />
        <TextField helper="剧集默认目录，相对于 Base Path。" label="TV Library" onChange={(value) => updateField('library_tv', value)} value={form.library_tv} />
        <TextField helper="动画默认目录，相对于 Base Path。" label="Anime Library" onChange={(value) => updateField('library_anime', value)} value={form.library_anime} />

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
            <small>相对于 Base Path 的目录；留空表示浏览 Base Path。</small>
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
  disabled = false,
  helper,
  label,
  onChange,
  required = false,
  type = 'text',
  value,
}: {
  disabled?: boolean
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
      <input disabled={disabled} onChange={(event) => onChange(event.target.value)} required={required} type={type} value={value} />
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
    const actionText = action === 'cancel' ? '取消' : '重试'
    if (!window.confirm(`确认${actionText}任务 ${transfer.id}？`)) {
      return
    }
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
          <p className="panel-kicker">任务</p>
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
          <small>创建任务后返回的 ID，用于查询状态和日志。</small>
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
          <p className="panel-kicker">状态</p>
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
  if (!matched && pathname === '/') return 'search'
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

function emptySourceForm(): SourceFormState {
  return {
    id: '',
    name: '',
    type: 'configurable',
    enabled: true,
    legal_note: '',
    trust_level: '1',
    config_json: '{\n  "search_url": "https://example.invalid/search?q={query}",\n  "selectors": {}\n}',
  }
}

function sourceFormFromResponse(source: SourceResponse): SourceFormState {
  return {
    id: source.id,
    name: source.name,
    type: source.type,
    enabled: source.enabled,
    legal_note: source.legal_note || '',
    trust_level: String(source.trust_level),
    config_json: JSON.stringify(source.config_json || {}, null, 2),
  }
}

function parseSourceConfig(value: string): Record<string, unknown> {
  try {
    const parsed = JSON.parse(value || '{}') as unknown
    if (!parsed || Array.isArray(parsed) || typeof parsed !== 'object') {
      throw new Error('Config JSON 必须是对象。')
    }
    return parsed as Record<string, unknown>
  } catch (exc) {
    if (exc instanceof SyntaxError) throw new Error('Config JSON 格式无效。')
    throw exc
  }
}

function sourceTypeLabel(type: SourceType) {
  const labels: Record<SourceType, string> = {
    configurable: '配置型',
    document: '文档/表格型',
    code: '代码型',
  }
  return labels[type]
}

function sourceConfigHint(type: SourceType) {
  if (type === 'document') {
    return '文档/表格型 source 需要 items 数组，至少包含 title 和 url/link/content。'
  }
  if (type === 'code') {
    return '代码型 Source Adapter 由后端代码提供，Web Console 只读展示配置。'
  }
  return '配置型 source 需要 search_url 字符串和 selectors 对象。'
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
    const body = (await response.json()) as { detail?: unknown }
    return detailToMessage(body.detail) || `请求失败：${response.status}`
  } catch {
    return `请求失败：${response.status}`
  }
}

function detailToMessage(detail: unknown) {
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
