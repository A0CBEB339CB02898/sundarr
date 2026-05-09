import React, { useEffect, useState } from 'react'
import ReactDOM from 'react-dom/client'
import './styles.css'

type PageKey = 'search' | 'transfers' | 'storage' | 'sources' | 'libraries' | 'remote-libraries' | 'sync' | 'status'
type ThemeMode = 'light' | 'dark' | 'system'

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
  link_id: string | null
  status: TransferStatus
  mode: string
  cloud_staging_path: string | null
  target_type: string
  target_library: string | null
  target_path: string
  source_type: string | null
  source_path: string | null
  ingest_seen_file_id: string | null
  total_bytes: number
  done_bytes: number
  progress: number
  current_file: string | null
  error_code: string | null
  error_message: string | null
  retryable: boolean | null
  retry_count: number
  created_at: string | null
  updated_at: string | null
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
  | 'cleaning_source'
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
  modified_at: string | null
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

type IngestMediaType = 'movie' | 'series' | 'unclassified'

type IngestConfigResponse = {
  delete_source_after_success: boolean
  delete_empty_source_dirs: boolean
  scan_interval_seconds: number
  stable_seconds: number
  unclassified_target_path: string
}

type IngestSmbEndpointResponse = {
  host: string
  port: number
  share: string
  username: string
  password_set: boolean
  domain: string
  base_path: string
}

type IngestBindingResponse = {
  id: string
  name: string
  enabled: boolean
  media_type: IngestMediaType
  source_smb: IngestSmbEndpointResponse
  target_smb: IngestSmbEndpointResponse
  delete_source_after_success: boolean | null
  delete_empty_source_dirs: boolean | null
  created_at: string | null
  updated_at: string | null
}

type IngestBindingListResponse = {
  count: number
  results: IngestBindingResponse[]
}

type IngestDiscoveredFileResponse = {
  id: string
  binding_id: string | null
  source_fingerprint: string
  source_path: string
  source_size: number | null
  source_mtime: string | null
  status: string
  task_id: string | null
  created_at: string | null
  updated_at: string | null
}

type IngestDiscoveredListResponse = {
  count: number
  results: IngestDiscoveredFileResponse[]
}

type IngestScanResponse = {
  scanned_bindings: number
  discovered_count: number
  stable_count: number
  results: IngestDiscoveredFileResponse[]
}

type IngestTaskCreateResponse = {
  created_count: number
  skipped_count: number
  tasks: TransferResponse[]
}

type IngestBindingTestResponse = {
  ok: boolean
  source_ok: boolean
  target_ok: boolean
  error_code: string | null
  error_message: string | null
}

type SmbConnectionResponse = {
  id: string
  name: string
  enabled: boolean
  host: string
  port: number
  share: string
  username: string
  password_set: boolean
  domain: string
  base_path: string
  created_at: string | null
  updated_at: string | null
}

type SmbConnectionListResponse = {
  count: number
  results: SmbConnectionResponse[]
}

type MediaLibraryResponse = {
  id: string
  name: string
  media_type: DtlMediaType
  enabled: boolean
  connection_id: string
  base_path: string
  created_at: string | null
  updated_at: string | null
}

type MediaLibraryListResponse = {
  count: number
  results: MediaLibraryResponse[]
}

type DtlMediaType = 'movie' | 'series' | 'unclassified'

type DtlConfigResponse = {
  delete_source_after_success: boolean
  delete_empty_source_dirs: boolean
  scan_interval_seconds: number
  stable_seconds: number
  unclassified_library_id: string
}

type DtlBindingResponse = {
  id: string
  name: string
  enabled: boolean
  media_type: DtlMediaType
  source_connection_id: string
  source_path: string
  target_library_id: string
  delete_source_after_success: boolean | null
  delete_empty_source_dirs: boolean | null
  created_at: string | null
  updated_at: string | null
}

type DtlBindingListResponse = {
  count: number
  results: DtlBindingResponse[]
}

type DtlDiscoveredFileResponse = {
  id: string
  binding_id: string | null
  source_fingerprint: string
  source_path: string
  source_size: number | null
  source_mtime: string | null
  status: string
  task_id: string | null
  created_at: string | null
  updated_at: string | null
}

type DtlDiscoveredListResponse = {
  count: number
  results: DtlDiscoveredFileResponse[]
}

type DtlScanResponse = {
  scanned_bindings: number
  discovered_count: number
  stable_count: number
  results: DtlDiscoveredFileResponse[]
}

type DtlTaskCreateResponse = {
  created_count: number
  skipped_count: number
  tasks: TransferResponse[]
}

type DtlBindingTestResponse = {
  ok: boolean
  source_ok: boolean
  target_ok: boolean
  error_code: string | null
  error_message: string | null
}

type DtlBindingFormState = {
  id: string
  name: string
  enabled: boolean
  media_type: DtlMediaType
  source_connection_id: string
  source_path: string
  target_library_id: string
  delete_source_after_success: '' | 'true' | 'false'
  delete_empty_source_dirs: '' | 'true' | 'false'
}

type DtlConfigFormState = {
  delete_source_after_success: boolean
  delete_empty_source_dirs: boolean
  scan_interval_seconds: string
  stable_seconds: string
  unclassified_library_id: string
}

type LibraryFormState = {
  id: string
  name: string
  media_type: DtlMediaType
  enabled: boolean
  connection_id: string
  base_path: string
}

type IngestFormState = {
  id: string
  name: string
  enabled: boolean
  media_type: IngestMediaType
  source_host: string
  source_port: string
  source_share: string
  source_username: string
  source_password: string
  source_domain: string
  source_base_path: string
  target_host: string
  target_port: string
  target_share: string
  target_username: string
  target_password: string
  target_domain: string
  target_base_path: string
  delete_source_after_success: '' | 'true' | 'false'
  delete_empty_source_dirs: '' | 'true' | 'false'
}

type IngestConfigFormState = {
  delete_source_after_success: boolean
  delete_empty_source_dirs: boolean
  scan_interval_seconds: string
  stable_seconds: string
  unclassified_target_path: string
}

const navItems: NavItem[] = [
  { key: 'search', path: '/app/search', label: '搜索', description: '搜索资源并创建搬运任务' },
  { key: 'transfers', path: '/app/transfers', label: '任务', description: '查看进度、日志、取消和重试' },
  { key: 'storage', path: '/app/storage', label: '存储', description: '管理 SMB 配置和目录浏览' },
  { key: 'sources', path: '/app/sources', label: '媒体源', description: '管理已安装 Adapter' },
  { key: 'libraries', path: '/app/libraries', label: '媒体库', description: '管理本地媒体库目录绑定' },
  { key: 'remote-libraries', path: '/app/remote-libraries', label: '远程媒体库', description: '管理远程媒体库目录绑定' },
  { key: 'sync', path: '/app/sync', label: '同步', description: '管理远程到本地的同步绑定' },
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
    body: '管理已安装代码型 Source Adapter 的启用、参数、测试和错误状态。',
    next: '当前页面暂不可用，请从左侧导航重新进入。',
  },
  libraries: {
    eyebrow: 'Libraries',
    title: '媒体库管理',
    body: '管理 movie / series / unclassified 等本地媒体库目录绑定。',
    next: '当前页面暂不可用，请从左侧导航重新进入。',
  },
  'remote-libraries': {
    eyebrow: 'Remote Libraries',
    title: '远程媒体库管理',
    body: '管理 movie / series / unclassified 等远程媒体库目录绑定。',
    next: '当前页面暂不可用，请从左侧导航重新进入。',
  },
  sync: {
    eyebrow: 'Sync',
    title: '同步管理',
    body: '管理远程媒体库到本地媒体库的同步绑定。',
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
  const [themeMode, setThemeMode] = useState<ThemeMode>(() => storedThemeMode())
  const [transfers, setTransfers] = useState<TransferResponse[]>([])
  const [transferError, setTransferError] = useState<string | null>(null)
  const [isTransferPanelOpen, setIsTransferPanelOpen] = useState(false)

  useEffect(() => {
    const onPopState = () => setActivePage(pageFromPath(window.location.pathname))
    window.addEventListener('popstate', onPopState)
    return () => window.removeEventListener('popstate', onPopState)
  }, [])

  useEffect(() => {
    applyThemeMode(themeMode)
    window.localStorage.setItem('sundarr.theme', themeMode)
  }, [themeMode])

  useEffect(() => {
    void loadTransfers()
    const timer = window.setInterval(() => void loadTransfers(), 15000)
    const onTransfersChanged = () => void loadTransfers()
    window.addEventListener('sundarr:transfers-changed', onTransfersChanged)
    return () => {
      window.clearInterval(timer)
      window.removeEventListener('sundarr:transfers-changed', onTransfersChanged)
    }
  }, [])

  async function loadTransfers() {
    try {
      const result = await api.get<TransferResponse[]>('/transfers?limit=20')
      setTransfers(result)
      setTransferError(null)
    } catch (exc) {
      setTransferError(exc instanceof Error ? exc.message : '无法读取任务列表。')
    }
  }

  function navigate(item: NavItem) {
    window.history.pushState({}, '', item.path)
    setActivePage(item.key)
    if (item.key === 'transfers') {
      setIsTransferPanelOpen(false)
    }
  }

  function navigateToTransfers(taskId?: string) {
    window.history.pushState({}, '', '/app/transfers')
    setActivePage('transfers')
    setIsTransferPanelOpen(false)
    window.dispatchEvent(new CustomEvent('sundarr:select-transfer', { detail: { taskId } }))
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
        <ThemeSwitcher mode={themeMode} onChange={setThemeMode} />
      </aside>

      <main className="content-shell">
        <PageHeader activePage={activePage} />
        <PagePanel activePage={activePage} onTransfersChanged={loadTransfers} transfers={transfers} />
      </main>
      <GlobalTransferPanel
        error={transferError}
        isOpen={isTransferPanelOpen}
        onClose={() => setIsTransferPanelOpen(false)}
        onOpen={() => setIsTransferPanelOpen(true)}
        onRefresh={() => void loadTransfers()}
        onSelect={navigateToTransfers}
        transfers={transfers}
      />
    </div>
  )
}

function ThemeSwitcher({ mode, onChange }: { mode: ThemeMode; onChange: (mode: ThemeMode) => void }) {
  return (
    <div className="theme-switcher" aria-label="主题模式">
      <span>主题</span>
      <div>
        {(['light', 'dark', 'system'] as ThemeMode[]).map((item) => (
          <button className="theme-button" data-active={mode === item} key={item} onClick={() => onChange(item)} type="button">
            {themeModeLabel(item)}
          </button>
        ))}
      </div>
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

function PagePanel({
  activePage,
  onTransfersChanged,
  transfers,
}: {
  activePage: PageKey
  onTransfersChanged: () => Promise<void>
  transfers: TransferResponse[]
}) {
  const copy = pageCopy[activePage]
  if (activePage === 'status') {
    return <StatusPanel />
  }
  if (activePage === 'transfers') {
    return <TransfersPanel onTransfersChanged={onTransfersChanged} transfers={transfers} />
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
  if (activePage === 'libraries') {
    return <LibrariesPanel />
  }
  if (activePage === 'remote-libraries') {
    return <RemoteLibrariesPanel />
  }
  if (activePage === 'sync') {
    return <SyncPanel onTransfersChanged={onTransfersChanged} />
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

function IngestPanel({ onTransfersChanged }: { onTransfersChanged: () => Promise<void> }) {
  const [configForm, setConfigForm] = useState<IngestConfigFormState>(emptyIngestConfigForm())
  const [bindings, setBindings] = useState<IngestBindingResponse[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [form, setForm] = useState<IngestFormState>(emptyIngestForm())
  const [mode, setMode] = useState<'create' | 'edit'>('create')
  const [discovered, setDiscovered] = useState<IngestDiscoveredFileResponse[]>([])
  const [scanResult, setScanResult] = useState<IngestScanResponse | null>(null)
  const [createdTasks, setCreatedTasks] = useState<IngestTaskCreateResponse | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [isScanning, setIsScanning] = useState(false)
  const [isCreatingTasks, setIsCreatingTasks] = useState(false)

  useEffect(() => {
    void loadIngest()
  }, [])

  const selectedBinding = bindings.find((binding) => binding.id === selectedId) || null

  async function loadIngest(nextSelectedId = selectedId) {
    setIsLoading(true)
    setError(null)
    try {
      const [config, bindingList, discoveredList] = await Promise.all([
        api.get<IngestConfigResponse>('/ingest/config'),
        api.get<IngestBindingListResponse>('/ingest/bindings'),
        api.get<IngestDiscoveredListResponse>('/ingest/discovered'),
      ])
      setConfigForm(ingestConfigFormFromResponse(config))
      setBindings(bindingList.results)
      setDiscovered(discoveredList.results)
      const nextBinding = bindingList.results.find((binding) => binding.id === nextSelectedId) || bindingList.results[0] || null
      if (nextBinding) {
        selectBinding(nextBinding, false)
      } else {
        startCreate()
      }
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : '无法读取挂载网盘导入配置。')
    } finally {
      setIsLoading(false)
    }
  }

  function selectBinding(binding: IngestBindingResponse, clearFeedback = true) {
    setMode('edit')
    setSelectedId(binding.id)
    setForm(ingestFormFromResponse(binding))
    if (clearFeedback) {
      setMessage(null)
      setError(null)
      setScanResult(null)
      setCreatedTasks(null)
    }
  }

  function startCreate() {
    setMode('create')
    setSelectedId(null)
    setForm(emptyIngestForm())
    setMessage(null)
    setError(null)
    setScanResult(null)
    setCreatedTasks(null)
  }

  async function saveConfig() {
    setIsSaving(true)
    setError(null)
    setMessage(null)
    try {
      const saved = await api.post<IngestConfigResponse>('/ingest/config/save', ingestConfigRequestFromForm(configForm))
      setConfigForm(ingestConfigFormFromResponse(saved))
      setMessage('导入全局配置已保存。')
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : '保存导入全局配置失败。')
    } finally {
      setIsSaving(false)
    }
  }

  async function saveBinding() {
    const actionText = mode === 'create' ? '创建导入绑定' : '保存导入绑定'
    if (!window.confirm(`确认${actionText}？`)) return
    setIsSaving(true)
    setError(null)
    setMessage(null)
    try {
      const payload = ingestBindingRequestFromForm(form)
      const saved = mode === 'create'
        ? await api.post<IngestBindingResponse>('/ingest/bindings/create', payload)
        : await api.post<IngestBindingResponse>(`/ingest/bindings/${encodeURIComponent(form.id)}/update`, omitId(payload))
      setMessage(mode === 'create' ? '导入绑定已创建。' : '导入绑定已保存。')
      await loadIngest(saved.id)
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : '保存导入绑定失败。')
    } finally {
      setIsSaving(false)
    }
  }

  async function toggleBinding(enabled: boolean) {
    if (!selectedBinding) return
    if (!window.confirm(`确认${enabled ? '启用' : '禁用'}导入绑定 ${selectedBinding.name}？`)) return
    setIsSaving(true)
    setError(null)
    setMessage(null)
    try {
      const action = enabled ? 'enable' : 'disable'
      const updated = await api.post<IngestBindingResponse>(`/ingest/bindings/${encodeURIComponent(selectedBinding.id)}/${action}`)
      setMessage(enabled ? '导入绑定已启用。' : '导入绑定已禁用。')
      await loadIngest(updated.id)
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : '切换导入绑定状态失败。')
    } finally {
      setIsSaving(false)
    }
  }

  async function testBinding() {
    if (!selectedBinding) {
      setError('请先选择已保存的导入绑定。')
      return
    }
    setIsSaving(true)
    setError(null)
    setMessage(null)
    try {
      const result = await api.post<IngestBindingTestResponse>(`/ingest/bindings/${encodeURIComponent(selectedBinding.id)}/test`)
      setMessage(result.ok ? '导入绑定配置结构测试通过。' : `${result.error_code || 'INGEST_TEST_FAILED'}：${result.error_message || '导入绑定测试失败。'}`)
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : '测试导入绑定失败。')
    } finally {
      setIsSaving(false)
    }
  }

  async function scanSources(bindingId?: string) {
    setIsScanning(true)
    setError(null)
    setMessage(null)
    setScanResult(null)
    try {
      const result = await api.post<IngestScanResponse>('/ingest/scan', bindingId ? { binding_id: bindingId } : {})
      setScanResult(result)
      setMessage(`扫描完成：发现 ${result.discovered_count} 个新文件，稳定 ${result.stable_count} 个文件。`)
      const discoveredList = await api.get<IngestDiscoveredListResponse>('/ingest/discovered')
      setDiscovered(discoveredList.results)
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : '扫描来源目录失败。')
    } finally {
      setIsScanning(false)
    }
  }

  async function createTasks(bindingId?: string) {
    setIsCreatingTasks(true)
    setError(null)
    setMessage(null)
    setCreatedTasks(null)
    try {
      const result = await api.post<IngestTaskCreateResponse>('/ingest/tasks/create', bindingId ? { binding_id: bindingId } : {})
      setCreatedTasks(result)
      setMessage(`已创建 ${result.created_count} 个导入任务，跳过 ${result.skipped_count} 个文件。`)
      const discoveredList = await api.get<IngestDiscoveredListResponse>('/ingest/discovered')
      setDiscovered(discoveredList.results)
      window.dispatchEvent(new Event('sundarr:transfers-changed'))
      await onTransfersChanged()
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : '创建导入任务失败。')
    } finally {
      setIsCreatingTasks(false)
    }
  }

  function updateField(key: keyof IngestFormState, value: string | boolean) {
    setForm((current) => ({ ...current, [key]: value }))
  }

  function updateConfigField(key: keyof IngestConfigFormState, value: string | boolean) {
    setConfigForm((current) => ({ ...current, [key]: value }))
  }

  return (
    <section className="panel" aria-labelledby="ingest-title">
      <div className="panel-header-row">
        <div>
          <p className="panel-kicker">导入</p>
          <h2 id="ingest-title">挂载网盘导入</h2>
          <p>从 SMB 来源目录扫描稳定文件，创建 ingest 任务后由 Worker 写入目标 SMB 媒体库。</p>
        </div>
        <button className="ghost-button" disabled={isLoading} onClick={() => void loadIngest()} type="button">
          {isLoading ? '读取中' : '重新读取'}
        </button>
      </div>

      {message ? <div className="notice-card"><strong>操作完成</strong><p>{message}</p></div> : null}
      {error ? <ErrorState message={error} /> : null}
      {isLoading ? <LoadingState message="正在读取导入配置、绑定和发现文件。" /> : null}

      <section className="ingest-section" aria-labelledby="ingest-config-title">
        <div className="section-heading"><h3 id="ingest-config-title">全局配置</h3><span>影响默认清理和稳定性判断</span></div>
        <form className="storage-form" onSubmit={(event) => { event.preventDefault(); void saveConfig() }}>
          <div className="checkbox-field source-form-wide">
            <label><input checked={configForm.delete_source_after_success} onChange={(event) => updateConfigField('delete_source_after_success', event.target.checked)} type="checkbox" />导入成功后删除源文件</label>
          </div>
          <div className="checkbox-field source-form-wide">
            <label><input checked={configForm.delete_empty_source_dirs} onChange={(event) => updateConfigField('delete_empty_source_dirs', event.target.checked)} type="checkbox" />删除变为空的来源目录</label>
          </div>
          <TextField helper="两次扫描之间文件 size/mtime 不变超过该秒数后才创建任务。" label="Stable Seconds" onChange={(value) => updateConfigField('stable_seconds', value)} type="number" value={configForm.stable_seconds} />
          <TextField helper="后续自动扫描使用；当前页面可手动触发扫描。" label="Scan Interval Seconds" onChange={(value) => updateConfigField('scan_interval_seconds', value)} type="number" value={configForm.scan_interval_seconds} />
          <TextField helper="绑定不明确时进入的目标目录，相对目标 SMB base path。" label="Unclassified Target Path" onChange={(value) => updateConfigField('unclassified_target_path', value)} value={configForm.unclassified_target_path} />
          <div className="form-actions"><button className="primary-button" disabled={isSaving} type="submit">{isSaving ? '保存中' : '保存全局配置'}</button></div>
        </form>
      </section>

      <div className="sources-layout">
        <section className="source-list" aria-labelledby="ingest-binding-list-title">
          <div className="section-heading"><h3 id="ingest-binding-list-title">导入绑定</h3><span>{bindings.length} 个</span></div>
          <button className="source-row create-row" onClick={startCreate} type="button"><strong>新建导入绑定</strong><small>配置 SMB 来源和 SMB 目标目录</small></button>
          {bindings.length === 0 ? <EmptyState message="暂无导入绑定。" /> : null}
          {bindings.map((binding) => (
            <button className="source-row" data-selected={selectedId === binding.id} key={binding.id} onClick={() => selectBinding(binding)} type="button">
              <span>{ingestMediaTypeLabel(binding.media_type)} · {binding.enabled ? '已启用' : '已禁用'}</span>
              <strong>{binding.name}</strong>
              <small>{binding.source_smb.share}:{binding.source_smb.base_path} → {binding.target_smb.share}:{binding.target_smb.base_path}</small>
            </button>
          ))}
        </section>

        <section className="source-editor" aria-labelledby="ingest-binding-editor-title">
          <div className="section-heading"><h3 id="ingest-binding-editor-title">{mode === 'create' ? '创建绑定' : '编辑绑定'}</h3><span>{selectedBinding ? selectedBinding.id : 'new'}</span></div>
          <form className="source-form" onSubmit={(event) => { event.preventDefault(); void saveBinding() }}>
            <TextField disabled={mode === 'edit'} helper="唯一 ID，保存后不可改。" label="Binding ID" onChange={(value) => updateField('id', value)} required value={form.id} />
            <TextField helper="页面展示名称。" label="名称" onChange={(value) => updateField('name', value)} required value={form.name} />
            <label className="field">
              <span>媒体类型</span>
              <select onChange={(event) => updateField('media_type', event.target.value as IngestMediaType)} value={form.media_type}>
                <option value="movie">电影</option>
                <option value="series">剧集</option>
                <option value="unclassified">未分类</option>
              </select>
              <small>用于写入目标 library 和后续分类。</small>
            </label>
            <div className="checkbox-field"><label><input checked={form.enabled} onChange={(event) => updateField('enabled', event.target.checked)} type="checkbox" />启用绑定</label></div>
            <EndpointFields form={form} kind="source" onChange={updateField} passwordSet={selectedBinding?.source_smb.password_set || false} title="来源 SMB" />
            <EndpointFields form={form} kind="target" onChange={updateField} passwordSet={selectedBinding?.target_smb.password_set || false} title="目标 SMB" />
            <TriStateField helper="为空时使用全局配置。" label="成功后删除源文件" onChange={(value) => updateField('delete_source_after_success', value)} value={form.delete_source_after_success} />
            <TriStateField helper="为空时使用全局配置。" label="删除空来源目录" onChange={(value) => updateField('delete_empty_source_dirs', value)} value={form.delete_empty_source_dirs} />
            <div className="form-actions">
              <button className="primary-button" disabled={isSaving} type="submit">{isSaving ? '保存中' : mode === 'create' ? '创建绑定' : '保存绑定'}</button>
              <button className="ghost-button" disabled={!selectedBinding || isSaving} onClick={() => void testBinding()} type="button">测试绑定</button>
              <button className="secondary-button" disabled={!selectedBinding || isSaving || selectedBinding?.enabled === false} onClick={() => void toggleBinding(false)} type="button">禁用</button>
              <button className="secondary-button" disabled={!selectedBinding || isSaving || selectedBinding?.enabled === true} onClick={() => void toggleBinding(true)} type="button">启用</button>
            </div>
          </form>
        </section>
      </div>

      <section className="ingest-section" aria-labelledby="ingest-actions-title">
        <div className="section-heading"><h3 id="ingest-actions-title">扫描与任务</h3><span>{discovered.length} 个发现文件</span></div>
        <div className="action-row">
          <button className="primary-button" disabled={isScanning} onClick={() => void scanSources()} type="button">{isScanning ? '扫描中' : '扫描全部启用绑定'}</button>
          <button className="ghost-button" disabled={!selectedBinding || isScanning} onClick={() => void scanSources(selectedBinding?.id)} type="button">扫描当前绑定</button>
          <button className="secondary-button" disabled={isCreatingTasks} onClick={() => void createTasks()} type="button">{isCreatingTasks ? '创建中' : '为稳定文件创建任务'}</button>
          <button className="ghost-button" disabled={!selectedBinding || isCreatingTasks} onClick={() => void createTasks(selectedBinding?.id)} type="button">仅当前绑定创建任务</button>
        </div>
        {scanResult ? <IngestScanSummary result={scanResult} /> : null}
        {createdTasks ? <IngestTaskSummary result={createdTasks} /> : null}
        <DiscoveredFiles files={discovered} />
      </section>

      <ApiClientPreview />
    </section>
  )
}

function EndpointFields({
  form,
  kind,
  onChange,
  passwordSet,
  title,
}: {
  form: IngestFormState
  kind: 'source' | 'target'
  onChange: (key: keyof IngestFormState, value: string | boolean) => void
  passwordSet: boolean
  title: string
}) {
  const prefix = kind === 'source' ? 'source' : 'target'
  return (
    <fieldset className="endpoint-fieldset">
      <legend>{title}</legend>
      <TextField helper="SMB 主机名或 IP，不要带共享名。" label="Host" onChange={(value) => onChange(`${prefix}_host` as keyof IngestFormState, value)} required value={String(form[`${prefix}_host` as keyof IngestFormState])} />
      <TextField helper="SMB 端口，通常为 445。" label="Port" onChange={(value) => onChange(`${prefix}_port` as keyof IngestFormState, value)} required type="number" value={String(form[`${prefix}_port` as keyof IngestFormState])} />
      <TextField helper="共享名，即 \\host\share 中的 share。" label="Share" onChange={(value) => onChange(`${prefix}_share` as keyof IngestFormState, value)} required value={String(form[`${prefix}_share` as keyof IngestFormState])} />
      <TextField helper="SMB 登录账号。" label="Username" onChange={(value) => onChange(`${prefix}_username` as keyof IngestFormState, value)} required value={String(form[`${prefix}_username` as keyof IngestFormState])} />
      <TextField helper="域或工作组；个人 NAS 通常留空。" label="Domain" onChange={(value) => onChange(`${prefix}_domain` as keyof IngestFormState, value)} value={String(form[`${prefix}_domain` as keyof IngestFormState])} />
      <TextField helper="共享内根目录；来源填挂载网盘目录，目标填媒体库目录。" label="Base Path" onChange={(value) => onChange(`${prefix}_base_path` as keyof IngestFormState, value)} value={String(form[`${prefix}_base_path` as keyof IngestFormState])} />
      <TextField
        helper={passwordSet ? '已保存密码且不会回显。留空保存表示保留旧密码。' : 'SMB 密码；保存后不会回显。'}
        label="Password"
        onChange={(value) => onChange(`${prefix}_password` as keyof IngestFormState, value)}
        type="password"
        value={String(form[`${prefix}_password` as keyof IngestFormState])}
      />
    </fieldset>
  )
}

function TriStateField({ helper, label, onChange, value }: { helper: string; label: string; onChange: (value: '' | 'true' | 'false') => void; value: '' | 'true' | 'false' }) {
  return (
    <label className="field">
      <span>{label}</span>
      <select onChange={(event) => onChange(event.target.value as '' | 'true' | 'false')} value={value}>
        <option value="">使用全局配置</option>
        <option value="true">是</option>
        <option value="false">否</option>
      </select>
      <small>{helper}</small>
    </label>
  )
}

function IngestScanSummary({ result }: { result: IngestScanResponse }) {
  return (
    <div className="detail-grid">
      <DetailItem label="扫描绑定" value={String(result.scanned_bindings)} />
      <DetailItem label="新发现" value={String(result.discovered_count)} />
      <DetailItem label="已稳定" value={String(result.stable_count)} />
    </div>
  )
}

function IngestTaskSummary({ result }: { result: IngestTaskCreateResponse }) {
  return (
    <div className="notice-card">
      <strong>导入任务创建结果</strong>
      <p>创建 {result.created_count} 个任务，跳过 {result.skipped_count} 个文件。</p>
      {result.tasks.length > 0 ? <p>最新任务：{result.tasks.map((task) => task.id).join('、')}</p> : null}
    </div>
  )
}

function DiscoveredFiles({ files }: { files: IngestDiscoveredFileResponse[] }) {
  if (files.length === 0) {
    return <EmptyState message="暂无发现文件。先扫描启用的导入绑定。" />
  }
  return (
    <div className="transfer-list">
      {files.map((file) => (
        <article className="discovered-row" key={file.id}>
          <span className={`status-pill ${ingestSeenTone(file.status)}`}>{ingestSeenStatusLabel(file.status)}</span>
          <strong>{file.source_path}</strong>
          <small>{file.binding_id || '无绑定'} · {formatBytes(file.source_size || 0)}</small>
          <small>{file.task_id ? `任务 ${file.task_id}` : '未创建任务'}</small>
        </article>
      ))}
    </div>
  )
}

function LibrariesPanel() {
  const [libraries, setLibraries] = useState<MediaLibraryResponse[]>([])
  const [connections, setConnections] = useState<SmbConnectionResponse[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [form, setForm] = useState<LibraryFormState>(emptyLibraryForm())
  const [mode, setMode] = useState<'create' | 'edit'>('create')
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [isSaving, setIsSaving] = useState(false)

  useEffect(() => { void loadLibraries() }, [])

  const selectedLibrary = libraries.find((l) => l.id === selectedId) || null

  async function loadLibraries(nextSelectedId = selectedId) {
    setIsLoading(true)
    setError(null)
    try {
      const [libList, connList] = await Promise.all([
        api.get<MediaLibraryListResponse>('/media-libraries'),
        api.get<SmbConnectionListResponse>('/storage/smb-connections'),
      ])
      setLibraries(libList.results)
      setConnections(connList.results)
      const next = libList.results.find((l) => l.id === nextSelectedId) || libList.results[0] || null
      if (next) { selectLibrary(next, false) } else { startCreate() }
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : '无法读取媒体库配置。')
    } finally { setIsLoading(false) }
  }

  function selectLibrary(lib: MediaLibraryResponse, clearFeedback = true) {
    setMode('edit'); setSelectedId(lib.id)
    setForm({ id: lib.id, name: lib.name, media_type: lib.media_type, enabled: lib.enabled, connection_id: lib.connection_id, base_path: lib.base_path })
    if (clearFeedback) { setMessage(null); setError(null) }
  }

  function startCreate() {
    setMode('create'); setSelectedId(null)
    setForm(emptyLibraryForm()); setMessage(null); setError(null)
  }

  async function saveLibrary() {
    if (!window.confirm(`确认${mode === 'create' ? '创建' : '保存'}媒体库？`)) return
    setIsSaving(true); setError(null); setMessage(null)
    try {
      const payload = { name: form.name.trim(), media_type: form.media_type, enabled: form.enabled, connection_id: form.connection_id.trim(), base_path: form.base_path.trim() || '/' }
      const saved = mode === 'create'
        ? await api.post<MediaLibraryResponse>('/media-libraries/create', { id: form.id.trim(), ...payload })
        : await api.post<MediaLibraryResponse>(`/media-libraries/${encodeURIComponent(form.id)}/update`, payload)
      setMessage(mode === 'create' ? '媒体库已创建。' : '媒体库已保存。')
      await loadLibraries(saved.id)
    } catch (exc) { setError(exc instanceof Error ? exc.message : '保存媒体库失败。') }
    finally { setIsSaving(false) }
  }

  async function toggleLibrary(enabled: boolean) {
    if (!selectedLibrary) return
    if (!window.confirm(`确认${enabled ? '启用' : '禁用'}媒体库 ${selectedLibrary.name}？`)) return
    setIsSaving(true); setError(null); setMessage(null)
    try {
      await api.post<MediaLibraryResponse>(`/media-libraries/${encodeURIComponent(selectedLibrary.id)}/${enabled ? 'enable' : 'disable'}`)
      setMessage(enabled ? '媒体库已启用。' : '媒体库已禁用。')
      await loadLibraries(selectedLibrary.id)
    } catch (exc) { setError(exc instanceof Error ? exc.message : '切换媒体库状态失败。') }
    finally { setIsSaving(false) }
  }

  async function testLibrary() {
    if (!selectedLibrary) { setError('请先选择已保存的媒体库。'); return }
    setIsSaving(true); setError(null); setMessage(null)
    try {
      const result = await api.post<{ ok: boolean; error_code: string | null; error_message: string | null }>(`/media-libraries/${encodeURIComponent(selectedLibrary.id)}/test`)
      setMessage(result.ok ? '媒体库目录测试通过。' : `${result.error_code || 'TEST_FAILED'}：${result.error_message || '测试失败。'}`)
    } catch (exc) { setError(exc instanceof Error ? exc.message : '测试媒体库失败。') }
    finally { setIsSaving(false) }
  }

  function updateField(key: keyof LibraryFormState, value: string | boolean) { setForm((c) => ({ ...c, [key]: value })) }

  return (
    <section className="panel" aria-labelledby="libraries-title">
      <div className="panel-header-row">
        <div>
          <p className="panel-kicker">媒体库</p>
          <h2 id="libraries-title">媒体库管理</h2>
          <p>管理 movie / series / unclassified 等本地媒体库目录绑定。</p>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button className="ghost-button" disabled={isLoading} onClick={() => void loadLibraries()} type="button">{isLoading ? '读取中' : '重新读取'}</button>
          <button className="primary-button" onClick={startCreate} type="button">新增</button>
        </div>
      </div>
      {message && <div className="inline-message">{message}</div>}
      {error && <div className="inline-message error">{error}</div>}
      <div className="ingest-layout">
        <section className="source-list" aria-labelledby="lib-list-title">
          <div className="section-heading"><h3 id="lib-list-title">媒体库列表</h3><span>{libraries.length} 个</span></div>
          <div className="transfer-list">
            {libraries.map((lib) => (
              <button key={lib.id} type="button" className={`source-row ${lib.id === selectedId ? 'selected' : ''}`} onClick={() => selectLibrary(lib)}>
                <strong>{lib.name}</strong>
                <span>{lib.media_type} · {lib.connection_id} · {lib.base_path} · {lib.enabled ? '已启用' : '已禁用'}</span>
              </button>
            ))}
            {libraries.length === 0 && <EmptyState message="暂无媒体库。点击新增创建。" />}
          </div>
        </section>
        <section className="source-editor" aria-labelledby="lib-editor-title">
          <div className="section-heading"><h3 id="lib-editor-title">{mode === 'create' ? '创建媒体库' : '编辑媒体库'}</h3><span>{selectedLibrary ? selectedLibrary.id : 'new'}</span></div>
          <div className="form-grid">
            <label><span>唯一标识</span><input disabled={mode === 'edit'} value={form.id} onChange={(e) => updateField('id', e.target.value)} /></label>
            <label><span>名称</span><input value={form.name} onChange={(e) => updateField('name', e.target.value)} /></label>
            <label><span>媒体类型</span><select value={form.media_type} onChange={(e) => updateField('media_type', e.target.value)}>
              <option value="movie">电影</option><option value="series">剧集</option><option value="unclassified">未分类</option>
            </select></label>
            <label><span>SMB 连接</span><select value={form.connection_id} onChange={(e) => updateField('connection_id', e.target.value)}>
              <option value="">选择连接</option>{connections.map((c) => <option key={c.id} value={c.id}>{c.name} ({c.host}/{c.share})</option>)}
            </select></label>
            <label><span>目录路径</span><input value={form.base_path} onChange={(e) => updateField('base_path', e.target.value)} /></label>
          </div>
          <div className="form-actions">
            <button className="primary-button" disabled={isSaving} onClick={() => void saveLibrary()} type="button">{isSaving ? '保存中' : mode === 'create' ? '创建' : '保存'}</button>
            {selectedLibrary && <>
              <button className="ghost-button" disabled={isSaving} onClick={() => void toggleLibrary(!selectedLibrary.enabled)} type="button">{selectedLibrary.enabled ? '禁用' : '启用'}</button>
              <button className="ghost-button" disabled={isSaving} onClick={() => void testLibrary()} type="button">测试</button>
            </>}
          </div>
        </section>
      </div>
    </section>
  )
}

function RemoteLibrariesPanel() {
  const [libraries, setLibraries] = useState<MediaLibraryResponse[]>([])
  const [connections, setConnections] = useState<SmbConnectionResponse[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [form, setForm] = useState<LibraryFormState>(emptyLibraryForm())
  const [mode, setMode] = useState<'create' | 'edit'>('create')
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [isSaving, setIsSaving] = useState(false)

  useEffect(() => { void loadLibraries() }, [])

  const selectedLibrary = libraries.find((l) => l.id === selectedId) || null

  async function loadLibraries(nextSelectedId = selectedId) {
    setIsLoading(true)
    setError(null)
    try {
      const [libList, connList] = await Promise.all([
        api.get<MediaLibraryListResponse>('/remote-media-libraries'),
        api.get<SmbConnectionListResponse>('/storage/smb-connections'),
      ])
      setLibraries(libList.results)
      setConnections(connList.results)
      const next = libList.results.find((l) => l.id === nextSelectedId) || libList.results[0] || null
      if (next) { selectLibrary(next, false) } else { startCreate() }
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : '无法读取远程媒体库配置。')
    } finally { setIsLoading(false) }
  }

  function selectLibrary(lib: MediaLibraryResponse, clearFeedback = true) {
    setMode('edit'); setSelectedId(lib.id)
    setForm({ id: lib.id, name: lib.name, media_type: lib.media_type, enabled: lib.enabled, connection_id: lib.connection_id, base_path: lib.base_path })
    if (clearFeedback) { setMessage(null); setError(null) }
  }

  function startCreate() {
    setMode('create'); setSelectedId(null)
    setForm(emptyLibraryForm()); setMessage(null); setError(null)
  }

  async function saveLibrary() {
    if (!window.confirm(`确认${mode === 'create' ? '创建' : '保存'}远程媒体库？`)) return
    setIsSaving(true); setError(null); setMessage(null)
    try {
      const payload = { name: form.name.trim(), media_type: form.media_type, enabled: form.enabled, connection_id: form.connection_id.trim(), base_path: form.base_path.trim() || '/' }
      const saved = mode === 'create'
        ? await api.post<MediaLibraryResponse>('/remote-media-libraries/create', { id: form.id.trim(), ...payload })
        : await api.post<MediaLibraryResponse>(`/remote-media-libraries/${encodeURIComponent(form.id)}/update`, payload)
      setMessage(mode === 'create' ? '远程媒体库已创建。' : '远程媒体库已保存。')
      await loadLibraries(saved.id)
    } catch (exc) { setError(exc instanceof Error ? exc.message : '保存远程媒体库失败。') }
    finally { setIsSaving(false) }
  }

  async function toggleLibrary(enabled: boolean) {
    if (!selectedLibrary) return
    if (!window.confirm(`确认${enabled ? '启用' : '禁用'}远程媒体库 ${selectedLibrary.name}？`)) return
    setIsSaving(true); setError(null); setMessage(null)
    try {
      await api.post<MediaLibraryResponse>(`/remote-media-libraries/${encodeURIComponent(selectedLibrary.id)}/${enabled ? 'enable' : 'disable'}`)
      setMessage(enabled ? '远程媒体库已启用。' : '远程媒体库已禁用。')
      await loadLibraries(selectedLibrary.id)
    } catch (exc) { setError(exc instanceof Error ? exc.message : '切换远程媒体库状态失败。') }
    finally { setIsSaving(false) }
  }

  async function testLibrary() {
    if (!selectedLibrary) { setError('请先选择已保存的远程媒体库。'); return }
    setIsSaving(true); setError(null); setMessage(null)
    try {
      const result = await api.post<{ ok: boolean; error_code: string | null; error_message: string | null }>(`/remote-media-libraries/${encodeURIComponent(selectedLibrary.id)}/test`)
      setMessage(result.ok ? '远程媒体库目录测试通过。' : `${result.error_code || 'TEST_FAILED'}：${result.error_message || '测试失败。'}`)
    } catch (exc) { setError(exc instanceof Error ? exc.message : '测试远程媒体库失败。') }
    finally { setIsSaving(false) }
  }

  function updateField(key: keyof LibraryFormState, value: string | boolean) { setForm((c) => ({ ...c, [key]: value })) }

  return (
    <section className="panel" aria-labelledby="remote-libraries-title">
      <div className="panel-header-row">
        <div>
          <p className="panel-kicker">远程媒体库</p>
          <h2 id="remote-libraries-title">远程媒体库管理</h2>
          <p>管理远程媒体库目录绑定，用于同步到本地媒体库。</p>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button className="ghost-button" disabled={isLoading} onClick={() => void loadLibraries()} type="button">{isLoading ? '读取中' : '重新读取'}</button>
          <button className="primary-button" onClick={startCreate} type="button">新增</button>
        </div>
      </div>
      {message && <div className="inline-message">{message}</div>}
      {error && <div className="inline-message error">{error}</div>}
      <div className="ingest-layout">
        <section className="source-list" aria-labelledby="remote-lib-list-title">
          <div className="section-heading"><h3 id="remote-lib-list-title">远程媒体库列表</h3><span>{libraries.length} 个</span></div>
          <div className="transfer-list">
            {libraries.map((lib) => (
              <button key={lib.id} type="button" className={`source-row ${lib.id === selectedId ? 'selected' : ''}`} onClick={() => selectLibrary(lib)}>
                <strong>{lib.name}</strong>
                <span>{lib.media_type} · {lib.connection_id} · {lib.base_path} · {lib.enabled ? '已启用' : '已禁用'}</span>
              </button>
            ))}
            {libraries.length === 0 && <EmptyState message="暂无远程媒体库。点击新增创建。" />}
          </div>
        </section>
        <section className="source-editor" aria-labelledby="remote-lib-editor-title">
          <div className="section-heading"><h3 id="remote-lib-editor-title">{mode === 'create' ? '创建远程媒体库' : '编辑远程媒体库'}</h3><span>{selectedLibrary ? selectedLibrary.id : 'new'}</span></div>
          <div className="form-grid">
            <label><span>唯一标识</span><input disabled={mode === 'edit'} value={form.id} onChange={(e) => updateField('id', e.target.value)} /></label>
            <label><span>名称</span><input value={form.name} onChange={(e) => updateField('name', e.target.value)} /></label>
            <label><span>媒体类型</span><select value={form.media_type} onChange={(e) => updateField('media_type', e.target.value)}>
              <option value="movie">电影</option><option value="series">剧集</option><option value="unclassified">未分类</option>
            </select></label>
            <label><span>SMB 连接</span><select value={form.connection_id} onChange={(e) => updateField('connection_id', e.target.value)}>
              <option value="">选择连接</option>{connections.map((c) => <option key={c.id} value={c.id}>{c.name} ({c.host}/{c.share})</option>)}
            </select></label>
            <label><span>目录路径</span><input value={form.base_path} onChange={(e) => updateField('base_path', e.target.value)} /></label>
          </div>
          <div className="form-actions">
            <button className="primary-button" disabled={isSaving} onClick={() => void saveLibrary()} type="button">{isSaving ? '保存中' : mode === 'create' ? '创建' : '保存'}</button>
            {selectedLibrary && <>
              <button className="ghost-button" disabled={isSaving} onClick={() => void toggleLibrary(!selectedLibrary.enabled)} type="button">{selectedLibrary.enabled ? '禁用' : '启用'}</button>
              <button className="ghost-button" disabled={isSaving} onClick={() => void testLibrary()} type="button">测试</button>
            </>}
          </div>
        </section>
      </div>
    </section>
  )
}

function SyncPanel({ onTransfersChanged }: { onTransfersChanged: () => Promise<void> }) {
  const [configForm, setConfigForm] = useState<DtlConfigFormState>(emptyDtlConfigForm())
  const [bindings, setBindings] = useState<DtlBindingResponse[]>([])
  const [connections, setConnections] = useState<SmbConnectionResponse[]>([])
  const [libraries, setLibraries] = useState<MediaLibraryResponse[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [form, setForm] = useState<DtlBindingFormState>(emptyDtlBindingForm())
  const [mode, setMode] = useState<'create' | 'edit'>('create')
  const [discovered, setDiscovered] = useState<DtlDiscoveredFileResponse[]>([])
  const [scanResult, setScanResult] = useState<DtlScanResponse | null>(null)
  const [createdTasks, setCreatedTasks] = useState<DtlTaskCreateResponse | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [isScanning, setIsScanning] = useState(false)
  const [isCreatingTasks, setIsCreatingTasks] = useState(false)

  useEffect(() => { void loadDtl() }, [])

  const selectedBinding = bindings.find((b) => b.id === selectedId) || null

  async function loadDtl(nextSelectedId = selectedId) {
    setIsLoading(true); setError(null)
    try {
      const [config, bindingList, discoveredList, connList, libList] = await Promise.all([
        api.get<DtlConfigResponse>('/download-to-local/config'),
        api.get<DtlBindingListResponse>('/download-to-local/bindings'),
        api.get<DtlDiscoveredListResponse>('/download-to-local/discovered'),
        api.get<SmbConnectionListResponse>('/storage/smb-connections'),
        api.get<MediaLibraryListResponse>('/media-libraries'),
      ])
      setConfigForm(dtlConfigFormFromResponse(config))
      setBindings(bindingList.results)
      setDiscovered(discoveredList.results)
      setConnections(connList.results)
      setLibraries(libList.results)
      const next = bindingList.results.find((b) => b.id === nextSelectedId) || bindingList.results[0] || null
      if (next) { selectBinding(next, false) } else { startCreate() }
    } catch (exc) { setError(exc instanceof Error ? exc.message : '无法读取下载到本地配置。') }
    finally { setIsLoading(false) }
  }

  function selectBinding(binding: DtlBindingResponse, clearFeedback = true) {
    setMode('edit'); setSelectedId(binding.id)
    setForm({ id: binding.id, name: binding.name, enabled: binding.enabled, media_type: binding.media_type, source_connection_id: binding.source_connection_id, source_path: binding.source_path, target_library_id: binding.target_library_id, delete_source_after_success: triStateFromBoolean(binding.delete_source_after_success), delete_empty_source_dirs: triStateFromBoolean(binding.delete_empty_source_dirs) })
    if (clearFeedback) { setMessage(null); setError(null); setScanResult(null); setCreatedTasks(null) }
  }

  function startCreate() {
    setMode('create'); setSelectedId(null)
    setForm(emptyDtlBindingForm()); setMessage(null); setError(null); setScanResult(null); setCreatedTasks(null)
  }

  async function saveConfig() {
    setIsSaving(true); setError(null); setMessage(null)
    try {
      const saved = await api.post<DtlConfigResponse>('/download-to-local/config/save', dtlConfigRequestFromForm(configForm))
      setConfigForm(dtlConfigFormFromResponse(saved)); setMessage('下载到本地全局配置已保存。')
    } catch (exc) { setError(exc instanceof Error ? exc.message : '保存配置失败。') }
    finally { setIsSaving(false) }
  }

  async function saveBinding() {
    if (!window.confirm(`确认${mode === 'create' ? '创建' : '保存'}下载绑定？`)) return
    setIsSaving(true); setError(null); setMessage(null)
    try {
      const payload = { name: form.name.trim(), enabled: form.enabled, media_type: form.media_type, source_connection_id: form.source_connection_id.trim(), source_path: form.source_path.trim(), target_library_id: form.target_library_id.trim(), delete_source_after_success: triStateToBoolean(form.delete_source_after_success), delete_empty_source_dirs: triStateToBoolean(form.delete_empty_source_dirs) }
      const saved = mode === 'create'
        ? await api.post<DtlBindingResponse>('/download-to-local/bindings/create', { id: form.id.trim(), ...payload })
        : await api.post<DtlBindingResponse>(`/download-to-local/bindings/${encodeURIComponent(form.id)}/update`, payload)
      setMessage(mode === 'create' ? '下载绑定已创建。' : '下载绑定已保存。')
      await loadDtl(saved.id)
    } catch (exc) { setError(exc instanceof Error ? exc.message : '保存下载绑定失败。') }
    finally { setIsSaving(false) }
  }

  async function toggleBinding(enabled: boolean) {
    if (!selectedBinding) return
    if (!window.confirm(`确认${enabled ? '启用' : '禁用'}下载绑定 ${selectedBinding.name}？`)) return
    setIsSaving(true); setError(null); setMessage(null)
    try {
      await api.post<DtlBindingResponse>(`/download-to-local/bindings/${encodeURIComponent(selectedBinding.id)}/${enabled ? 'enable' : 'disable'}`)
      setMessage(enabled ? '下载绑定已启用。' : '下载绑定已禁用。')
      await loadDtl(selectedBinding.id)
    } catch (exc) { setError(exc instanceof Error ? exc.message : '切换状态失败。') }
    finally { setIsSaving(false) }
  }

  async function testBinding() {
    if (!selectedBinding) { setError('请先选择已保存的下载绑定。'); return }
    setIsSaving(true); setError(null); setMessage(null)
    try {
      const result = await api.post<DtlBindingTestResponse>(`/download-to-local/bindings/${encodeURIComponent(selectedBinding.id)}/test`)
      setMessage(result.ok ? '来源和目标测试通过。' : `${result.error_code || 'TEST_FAILED'}：${result.error_message || '测试失败。'}`)
    } catch (exc) { setError(exc instanceof Error ? exc.message : '测试下载绑定失败。') }
    finally { setIsSaving(false) }
  }

  async function scanSources(bindingId?: string) {
    setIsScanning(true); setError(null); setMessage(null); setScanResult(null)
    try {
      const result = await api.post<DtlScanResponse>('/download-to-local/scan', bindingId ? { binding_id: bindingId } : {})
      setScanResult(result); setMessage(`扫描完成：发现 ${result.discovered_count} 个新文件，稳定 ${result.stable_count} 个文件。`)
      const discoveredList = await api.get<DtlDiscoveredListResponse>('/download-to-local/discovered')
      setDiscovered(discoveredList.results)
    } catch (exc) { setError(exc instanceof Error ? exc.message : '扫描来源目录失败。') }
    finally { setIsScanning(false) }
  }

  async function createTasks(bindingId?: string) {
    setIsCreatingTasks(true); setError(null); setMessage(null); setCreatedTasks(null)
    try {
      const result = await api.post<DtlTaskCreateResponse>('/download-to-local/tasks/create', bindingId ? { binding_id: bindingId } : {})
      setCreatedTasks(result); setMessage(`已创建 ${result.created_count} 个下载任务，跳过 ${result.skipped_count} 个文件。`)
      const discoveredList = await api.get<DtlDiscoveredListResponse>('/download-to-local/discovered')
      setDiscovered(discoveredList.results)
      window.dispatchEvent(new Event('sundarr:transfers-changed'))
      await onTransfersChanged()
    } catch (exc) { setError(exc instanceof Error ? exc.message : '创建下载任务失败。') }
    finally { setIsCreatingTasks(false) }
  }

  function updateField(key: keyof DtlBindingFormState, value: string | boolean) { setForm((c) => ({ ...c, [key]: value })) }
  function updateConfigField(key: keyof DtlConfigFormState, value: string | boolean) { setConfigForm((c) => ({ ...c, [key]: value })) }

  return (
    <section className="panel" aria-labelledby="dtl-title">
      <div className="panel-header-row">
        <div>
          <p className="panel-kicker">下载到本地</p>
          <h2 id="dtl-title">下载到本地</h2>
          <p>管理网盘目录到媒体库的下载绑定，扫描来源目录并创建下载任务。</p>
        </div>
        <button className="ghost-button" disabled={isLoading} onClick={() => void loadDtl()} type="button">{isLoading ? '读取中' : '重新读取'}</button>
      </div>
      {message && <div className="inline-message">{message}</div>}
      {error && <div className="inline-message error">{error}</div>}
      <div className="ingest-layout">
        <div className="ingest-left">
          <section className="ingest-section" aria-labelledby="dtl-config-title">
            <div className="section-heading"><h3 id="dtl-config-title">全局配置</h3></div>
            <div className="form-grid compact">
              <label className="checkbox"><input type="checkbox" checked={configForm.delete_source_after_success} onChange={(e) => updateConfigField('delete_source_after_success', e.target.checked)} /><span>成功后删除来源文件</span></label>
              <label className="checkbox"><input type="checkbox" checked={configForm.delete_empty_source_dirs} onChange={(e) => updateConfigField('delete_empty_source_dirs', e.target.checked)} /><span>成功后删除空来源目录</span></label>
              <label><span>扫描间隔(秒)</span><input value={configForm.scan_interval_seconds} onChange={(e) => updateConfigField('scan_interval_seconds', e.target.value)} /></label>
              <label><span>稳定等待(秒)</span><input value={configForm.stable_seconds} onChange={(e) => updateConfigField('stable_seconds', e.target.value)} /></label>
              <label><span>未分类媒体库 ID</span><input value={configForm.unclassified_library_id} onChange={(e) => updateConfigField('unclassified_library_id', e.target.value)} placeholder="留空使用全局默认" /></label>
            </div>
            <div className="form-actions"><button className="primary-button" disabled={isSaving} onClick={() => void saveConfig()} type="button">{isSaving ? '保存中' : '保存配置'}</button></div>
          </section>
          <section className="source-list" aria-labelledby="dtl-binding-list-title">
            <div className="section-heading"><h3 id="dtl-binding-list-title">下载绑定</h3><span>{bindings.length} 个</span></div>
            <div className="transfer-list">
              {bindings.map((b) => (
                <button key={b.id} type="button" className={`source-row ${b.id === selectedId ? 'selected' : ''}`} onClick={() => selectBinding(b)}>
                  <strong>{b.name}</strong>
                  <span>{b.media_type} · {b.source_connection_id}:{b.source_path} → {b.target_library_id} · {b.enabled ? '已启用' : '已禁用'}</span>
                </button>
              ))}
              {bindings.length === 0 && <EmptyState message="暂无下载绑定。点击新增创建。" />}
            </div>
            <div className="form-actions"><button className="primary-button" onClick={startCreate} type="button">新增</button></div>
          </section>
        </div>
        <div className="ingest-right">
          <section className="source-editor" aria-labelledby="dtl-binding-editor-title">
            <div className="section-heading"><h3 id="dtl-binding-editor-title">{mode === 'create' ? '创建绑定' : '编辑绑定'}</h3><span>{selectedBinding ? selectedBinding.id : 'new'}</span></div>
            <div className="form-grid compact">
              <label><span>唯一标识</span><input disabled={mode === 'edit'} value={form.id} onChange={(e) => updateField('id', e.target.value)} /></label>
              <label><span>名称</span><input value={form.name} onChange={(e) => updateField('name', e.target.value)} /></label>
              <label><span>媒体类型</span><select value={form.media_type} onChange={(e) => updateField('media_type', e.target.value)}>
                <option value="movie">电影</option><option value="series">剧集</option><option value="unclassified">未分类</option>
              </select></label>
              <label><span>来源 SMB 连接</span><select value={form.source_connection_id} onChange={(e) => updateField('source_connection_id', e.target.value)}>
                <option value="">选择连接</option>{connections.map((c) => <option key={c.id} value={c.id}>{c.name} ({c.host}/{c.share})</option>)}
              </select></label>
              <label><span>来源目录</span><input value={form.source_path} onChange={(e) => updateField('source_path', e.target.value)} /></label>
              <label><span>目标媒体库</span><select value={form.target_library_id} onChange={(e) => updateField('target_library_id', e.target.value)}>
                <option value="">选择媒体库</option>{libraries.map((l) => <option key={l.id} value={l.id}>{l.name} ({l.media_type})</option>)}
              </select></label>
              <label><span>成功后删除来源</span><select value={form.delete_source_after_success} onChange={(e) => updateField('delete_source_after_success', e.target.value)}>
                <option value="">使用全局默认</option><option value="true">删除</option><option value="false">保留</option>
              </select></label>
              <label><span>成功后删除空目录</span><select value={form.delete_empty_source_dirs} onChange={(e) => updateField('delete_empty_source_dirs', e.target.value)}>
                <option value="">使用全局默认</option><option value="true">删除</option><option value="false">保留</option>
              </select></label>
            </div>
            <div className="form-actions">
              <button className="primary-button" disabled={isSaving} onClick={() => void saveBinding()} type="button">{isSaving ? '保存中' : mode === 'create' ? '创建' : '保存'}</button>
              {selectedBinding && <>
                <button className="ghost-button" disabled={isSaving} onClick={() => void toggleBinding(!selectedBinding.enabled)} type="button">{selectedBinding.enabled ? '禁用' : '启用'}</button>
                <button className="ghost-button" disabled={isSaving} onClick={() => void testBinding()} type="button">测试</button>
              </>}
            </div>
          </section>
          <section className="ingest-section" aria-labelledby="dtl-actions-title">
            <div className="section-heading"><h3 id="dtl-actions-title">扫描与任务</h3><span>{discovered.length} 个发现文件</span></div>
            <div className="form-actions">
              <button className="ghost-button" disabled={isScanning} onClick={() => void scanSources(selectedBinding?.id)} type="button">{isScanning ? '扫描中' : '扫描来源目录'}</button>
              <button className="ghost-button" disabled={isCreatingTasks} onClick={() => void createTasks(selectedBinding?.id)} type="button">{isCreatingTasks ? '创建中' : '创建下载任务'}</button>
            </div>
            {scanResult && <div className="inline-message">扫描了 {scanResult.scanned_bindings} 个绑定，发现 {scanResult.discovered_count} 个新文件，稳定 {scanResult.stable_count} 个。</div>}
            {createdTasks && <div className="inline-message">已创建 {createdTasks.created_count} 个任务，跳过 {createdTasks.skipped_count} 个。</div>}
          </section>
          <section aria-labelledby="dtl-discovered-title">
            <div className="section-heading"><h3 id="dtl-discovered-title">发现文件</h3></div>
            <div className="transfer-list">
              {discovered.length === 0 && <EmptyState message="暂无发现文件。先扫描启用的下载绑定。" />}
              {discovered.map((file) => (
                <article className="discovered-row" key={file.id}>
                  <span className={`status-pill ${dtlSeenTone(file.status)}`}>{dtlSeenStatusLabel(file.status)}</span>
                  <strong>{file.source_path}</strong>
                  <small>{file.binding_id || '无绑定'} · {formatBytes(file.source_size || 0)}</small>
                  <small>{file.task_id ? `任务 ${file.task_id}` : '未创建任务'}</small>
                </article>
              ))}
            </div>
          </section>
        </div>
      </div>
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
      window.dispatchEvent(new Event('sundarr:transfers-changed'))
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
  const [connections, setConnections] = useState<SmbConnectionResponse[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [form, setForm] = useState<StorageFormState>(emptyStorageForm())
  const [passwordSet, setPasswordSet] = useState(false)
  const [mode, setMode] = useState<'create' | 'edit'>('create')
  const [browsePath, setBrowsePath] = useState('')
  const [browseResult, setBrowseResult] = useState<StorageBrowseResponse | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [isTesting, setIsTesting] = useState(false)
  const [isBrowsing, setIsBrowsing] = useState(false)

  useEffect(() => { void loadConnections() }, [])

  const selectedConnection = connections.find((c) => c.id === selectedId) || null

  async function loadConnections(nextSelectedId = selectedId) {
    setIsLoading(true)
    setError(null)
    try {
      const result = await api.get<SmbConnectionListResponse>('/storage/smb-connections')
      setConnections(result.results)
      const next = result.results.find((c) => c.id === nextSelectedId) || result.results[0] || null
      if (next) { selectConnection(next, false) } else { startCreate() }
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : '无法读取 SMB 连接。')
    } finally { setIsLoading(false) }
  }

  function selectConnection(conn: SmbConnectionResponse, clearFeedback = true) {
    setMode('edit')
    setSelectedId(conn.id)
    setForm({
      host: conn.host,
      port: String(conn.port),
      share: conn.share,
      username: conn.username,
      password: '',
      domain: conn.domain,
      base_path: conn.base_path,
      library_movies: '',
      library_tv: '',
      library_anime: '',
    })
    setPasswordSet(conn.password_set)
    if (clearFeedback) { setMessage(null); setError(null); setBrowseResult(null) }
  }

  function startCreate() {
    setMode('create')
    setSelectedId(null)
    setForm(emptyStorageForm())
    setPasswordSet(false)
    setMessage(null)
    setError(null)
    setBrowseResult(null)
  }

  async function saveConnection() {
    if (!window.confirm('确认保存 SMB 连接？')) return
    setIsSaving(true)
    setError(null)
    setMessage(null)
    try {
      const payload = {
        host: form.host.trim(),
        port: Number(form.port) || 445,
        share: form.share.trim(),
        username: form.username.trim(),
        password: form.password || null,
        domain: form.domain.trim(),
        base_path: form.base_path.trim() || '/',
      }
      if (mode === 'create') {
        const id = `conn_${Date.now()}`
        await api.post<SmbConnectionResponse>('/storage/smb-connections/create', { id, name: `${payload.host}/${payload.share}`, ...payload })
      } else {
        await api.post<SmbConnectionResponse>(`/storage/smb-connections/${encodeURIComponent(selectedId!)}/update`, { name: selectedConnection?.name || '', ...payload })
      }
      setMessage(mode === 'create' ? 'SMB 连接已创建。' : 'SMB 连接已保存。')
      await loadConnections(selectedId)
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : '保存 SMB 连接失败。')
    } finally { setIsSaving(false) }
  }

  async function testConnection() {
    if (!selectedId) { setError('请先选择已保存的连接。'); return }
    setIsTesting(true)
    setError(null)
    setMessage(null)
    try {
      const result = await api.post<StorageConfigTestResponse>(`/storage/smb-connections/${encodeURIComponent(selectedId)}/test`)
      setMessage(result.ok ? 'SMB 连接测试通过。' : `${result.error_code || 'TEST_FAILED'}：${result.error_message || 'SMB 连接测试失败。'}`)
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : '测试 SMB 连接失败。')
    } finally { setIsTesting(false) }
  }

  async function browseStorage(nextPath = browsePath) {
    if (!selectedId) { setError('请先选择已保存的连接。'); return }
    setIsBrowsing(true)
    setError(null)
    try {
      const result = await api.get<StorageBrowseResponse>(`/storage/smb-connections/${encodeURIComponent(selectedId)}/browse?path=${encodeURIComponent(nextPath.trim())}`)
      setBrowseResult(result)
      setBrowsePath(result.path)
    } catch (exc) {
      setBrowseResult(null)
      setError(exc instanceof Error ? exc.message : '浏览存储目录失败。')
    } finally { setIsBrowsing(false) }
  }

  function updateField(key: keyof StorageFormState, value: string) {
    setForm((current) => ({ ...current, [key]: value }))
  }

  return (
    <section className="panel" aria-labelledby="storage-title">
      <div className="panel-header-row">
        <div>
          <p className="panel-kicker">存储</p>
          <h2 id="storage-title">SMB 存储管理</h2>
          <p>管理多个 SMB 连接配置、测试连接，并在允许范围内浏览目标目录。</p>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button className="ghost-button" disabled={isLoading} onClick={() => void loadConnections()} type="button">{isLoading ? '读取中' : '重新读取'}</button>
          <button className="primary-button" onClick={startCreate} type="button">新增</button>
        </div>
      </div>

      {message ? <div className="notice-card"><strong>操作完成</strong><p>{message}</p></div> : null}
      {error ? <div className="notice-card error"><strong>操作失败</strong><p>{error}</p></div> : null}
      {error ? <ErrorState message={error} /> : null}
      {isLoading ? <LoadingState message="正在读取 SMB 连接。" /> : null}

      <div className="ingest-layout">
        <section className="source-list" aria-labelledby="storage-list-title">
          <div className="section-heading"><h3 id="storage-list-title">SMB 连接</h3><span>{connections.length} 个</span></div>
          <div className="transfer-list">
            {connections.map((conn) => (
              <button key={conn.id} type="button" className={`source-row ${conn.id === selectedId ? 'selected' : ''}`} onClick={() => selectConnection(conn)}>
                <strong>{conn.name}</strong>
                <span>{conn.host}/{conn.share} · {conn.username} · {conn.password_set ? '已设密码' : '未设密码'} · {conn.enabled ? '已启用' : '已禁用'}</span>
              </button>
            ))}
            {connections.length === 0 && <EmptyState message="暂无 SMB 连接。点击新增创建。" />}
          </div>
        </section>

        <section className="source-editor" aria-labelledby="storage-editor-title">
          <div className="section-heading"><h3 id="storage-editor-title">{mode === 'create' ? '创建连接' : '编辑连接'}</h3><span>{selectedConnection ? selectedConnection.id : 'new'}</span></div>
          <div className="form-grid">
            <label><span>Host</span><input value={form.host} onChange={(e) => updateField('host', e.target.value)} placeholder="SMB 服务器地址" /></label>
            <label><span>Port</span><input type="number" value={form.port} onChange={(e) => updateField('port', e.target.value)} placeholder="445" /></label>
            <label><span>Share</span><input value={form.share} onChange={(e) => updateField('share', e.target.value)} placeholder="共享名" /></label>
            <label><span>Username</span><input value={form.username} onChange={(e) => updateField('username', e.target.value)} placeholder="用户名" /></label>
            <label><span>Password</span><input type="password" value={form.password} onChange={(e) => updateField('password', e.target.value)} placeholder={passwordSet ? '留空保留原密码' : '密码'} /></label>
            <label><span>Domain</span><input value={form.domain} onChange={(e) => updateField('domain', e.target.value)} placeholder="可为空" /></label>
            <label><span>Base Path</span><input value={form.base_path} onChange={(e) => updateField('base_path', e.target.value)} placeholder="/" /></label>
          </div>
          <div className="form-actions">
            <button className="primary-button" disabled={isSaving} onClick={() => void saveConnection()} type="button">{isSaving ? '保存中' : mode === 'create' ? '创建' : '保存'}</button>
            <button className="ghost-button" disabled={isTesting} onClick={() => void testConnection()} type="button">{isTesting ? '测试中' : '测试连接'}</button>
          </div>
        </section>
      </div>

      <section className="browser-panel" aria-labelledby="storage-browser-title">
        <div className="section-heading"><h3 id="storage-browser-title">目录浏览</h3><span>只读浏览</span></div>
        <form className="lookup-form" onSubmit={(event) => { event.preventDefault(); void browseStorage() }}>
          <label>
            <span>路径</span>
            <input onChange={(event) => setBrowsePath(event.target.value)} placeholder="例如 Movies" type="text" value={browsePath} />
            <small>相对于 Base Path 的目录；留空表示浏览 Base Path。</small>
          </label>
          <button className="primary-button" disabled={isBrowsing} type="submit">{isBrowsing ? '浏览中' : '浏览目录'}</button>
        </form>
        {isBrowsing && !browseResult ? <LoadingState message="正在读取目录。" /> : null}
        {browseResult ? <StorageBrowser result={browseResult} onOpen={(path) => void browseStorage(path)} /> : <EmptyState message="选择连接后输入路径浏览 SMB 目录。" />}
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

function TransfersPanel({ onTransfersChanged, transfers }: { onTransfersChanged: () => Promise<void>; transfers: TransferResponse[] }) {
  const [taskId, setTaskId] = useState('')
  const [transfer, setTransfer] = useState<TransferResponse | null>(null)
  const [logs, setLogs] = useState<TransferLogResponse[]>([])
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [isMutating, setIsMutating] = useState(false)

  useEffect(() => {
    const handler = (event: Event) => {
      const taskIdFromEvent = (event as CustomEvent<{ taskId?: string }>).detail?.taskId
      if (taskIdFromEvent) {
        setTaskId(taskIdFromEvent)
        void loadTransfer(taskIdFromEvent)
      }
    }
    window.addEventListener('sundarr:select-transfer', handler)
    return () => window.removeEventListener('sundarr:select-transfer', handler)
  }, [])

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
      await onTransfersChanged()
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
          <h2 id="transfers-title">任务列表与控制</h2>
          <p>查看最近任务，选择任务后读取详情、关键日志，并按当前状态执行取消或重试。</p>
        </div>
      </div>

      <TransferList transfers={transfers} selectedId={transfer?.id || null} onSelect={(id) => void loadTransfer(id)} />

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
          <small>也可以从上方列表或全局任务面板选择任务。</small>
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

function TransferList({ onSelect, selectedId, transfers }: { onSelect: (id: string) => void; selectedId: string | null; transfers: TransferResponse[] }) {
  if (transfers.length === 0) {
    return <EmptyState message="暂无任务。创建任务或导入任务后会显示在这里。" />
  }

  return (
    <section className="transfer-list-section" aria-labelledby="transfer-list-title">
      <div className="section-heading">
        <h3 id="transfer-list-title">最近任务</h3>
        <span>{transfers.length} 个</span>
      </div>
      <div className="transfer-list">
        {transfers.map((item) => (
          <button className="transfer-row" data-selected={selectedId === item.id} key={item.id} onClick={() => onSelect(item.id)} type="button">
            <span className={`status-pill ${transferStatusTone(item.status)}`}>{transferStatusLabel(item.status)}</span>
            <strong>{item.target_path}</strong>
            <small>{item.current_file || item.id}</small>
            <div className="mini-progress" aria-label={`任务进度 ${item.progress.toFixed(0)}%`}>
              <span style={{ width: `${Math.min(100, Math.max(0, item.progress))}%` }} />
            </div>
            <em>{item.progress.toFixed(0)}%</em>
          </button>
        ))}
      </div>
    </section>
  )
}

function GlobalTransferPanel({
  error,
  isOpen,
  onClose,
  onOpen,
  onRefresh,
  onSelect,
  transfers,
}: {
  error: string | null
  isOpen: boolean
  onClose: () => void
  onOpen: () => void
  onRefresh: () => void
  onSelect: (taskId?: string) => void
  transfers: TransferResponse[]
}) {
  const activeTransfers = transfers.filter((transfer) => !['completed', 'failed', 'cancelled'].includes(transfer.status))
  const visibleTransfers = (activeTransfers.length > 0 ? activeTransfers : transfers).slice(0, 5)

  return (
    <aside className="global-transfer-panel" data-open={isOpen} aria-label="全局任务面板">
      <button className="global-transfer-tab" onClick={isOpen ? onClose : onOpen} type="button">
        <span>任务</span>
        <strong>{activeTransfers.length || transfers.length}</strong>
      </button>
      <div className="global-transfer-card">
        <div className="section-heading">
          <h3>当前任务</h3>
          <button className="ghost-button compact-button" onClick={onRefresh} type="button">刷新</button>
        </div>
        {error ? <ErrorState message={error} /> : null}
        {!error && visibleTransfers.length === 0 ? <EmptyState message="暂无任务。" /> : null}
        <div className="global-transfer-list">
          {visibleTransfers.map((transfer) => (
            <button className="global-transfer-row" key={transfer.id} onClick={() => onSelect(transfer.id)} type="button">
              <span className={`status-pill ${transferStatusTone(transfer.status)}`}>{transferStatusLabel(transfer.status)}</span>
              <strong>{transfer.target_path}</strong>
              <small>{transfer.progress.toFixed(0)}% · {transfer.current_file || transfer.id}</small>
            </button>
          ))}
        </div>
        <button className="primary-button full-button" onClick={() => onSelect()} type="button">打开任务页</button>
      </div>
    </aside>
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

function storedThemeMode(): ThemeMode {
  const value = window.localStorage.getItem('sundarr.theme')
  return value === 'light' || value === 'dark' || value === 'system' ? value : 'system'
}

function applyThemeMode(mode: ThemeMode) {
  const root = document.documentElement
  if (mode === 'system') {
    root.removeAttribute('data-theme')
  } else {
    root.dataset.theme = mode
  }
}

function themeModeLabel(mode: ThemeMode) {
  const labels: Record<ThemeMode, string> = {
    light: '亮色',
    dark: '暗色',
    system: '跟随系统',
  }
  return labels[mode]
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

function emptyIngestConfigForm(): IngestConfigFormState {
  return {
    delete_source_after_success: true,
    delete_empty_source_dirs: true,
    scan_interval_seconds: '60',
    stable_seconds: '120',
    unclassified_target_path: '/unclassified',
  }
}

function ingestConfigFormFromResponse(config: IngestConfigResponse): IngestConfigFormState {
  return {
    delete_source_after_success: config.delete_source_after_success,
    delete_empty_source_dirs: config.delete_empty_source_dirs,
    scan_interval_seconds: String(config.scan_interval_seconds),
    stable_seconds: String(config.stable_seconds),
    unclassified_target_path: config.unclassified_target_path,
  }
}

function ingestConfigRequestFromForm(form: IngestConfigFormState) {
  return {
    delete_source_after_success: form.delete_source_after_success,
    delete_empty_source_dirs: form.delete_empty_source_dirs,
    scan_interval_seconds: Number(form.scan_interval_seconds) || 60,
    stable_seconds: Number(form.stable_seconds) || 120,
    unclassified_target_path: form.unclassified_target_path.trim() || '/unclassified',
  }
}

function emptyIngestForm(): IngestFormState {
  return {
    id: '',
    name: '',
    enabled: true,
    media_type: 'movie',
    source_host: '',
    source_port: '445',
    source_share: '',
    source_username: '',
    source_password: '',
    source_domain: '',
    source_base_path: '/',
    target_host: '',
    target_port: '445',
    target_share: '',
    target_username: '',
    target_password: '',
    target_domain: '',
    target_base_path: '/',
    delete_source_after_success: '',
    delete_empty_source_dirs: '',
  }
}

function ingestFormFromResponse(binding: IngestBindingResponse): IngestFormState {
  return {
    id: binding.id,
    name: binding.name,
    enabled: binding.enabled,
    media_type: binding.media_type,
    source_host: binding.source_smb.host,
    source_port: String(binding.source_smb.port || 445),
    source_share: binding.source_smb.share,
    source_username: binding.source_smb.username,
    source_password: '',
    source_domain: binding.source_smb.domain || '',
    source_base_path: binding.source_smb.base_path || '/',
    target_host: binding.target_smb.host,
    target_port: String(binding.target_smb.port || 445),
    target_share: binding.target_smb.share,
    target_username: binding.target_smb.username,
    target_password: '',
    target_domain: binding.target_smb.domain || '',
    target_base_path: binding.target_smb.base_path || '/',
    delete_source_after_success: triStateFromBoolean(binding.delete_source_after_success),
    delete_empty_source_dirs: triStateFromBoolean(binding.delete_empty_source_dirs),
  }
}

function ingestBindingRequestFromForm(form: IngestFormState) {
  return {
    id: form.id.trim(),
    name: form.name.trim(),
    enabled: form.enabled,
    media_type: form.media_type,
    source_smb: ingestEndpointRequestFromForm(form, 'source'),
    target_smb: ingestEndpointRequestFromForm(form, 'target'),
    delete_source_after_success: triStateToBoolean(form.delete_source_after_success),
    delete_empty_source_dirs: triStateToBoolean(form.delete_empty_source_dirs),
  }
}

function ingestEndpointRequestFromForm(form: IngestFormState, kind: 'source' | 'target') {
  const prefix = kind === 'source' ? 'source' : 'target'
  return {
    host: String(form[`${prefix}_host` as keyof IngestFormState]).trim(),
    port: Number(form[`${prefix}_port` as keyof IngestFormState]) || 445,
    share: String(form[`${prefix}_share` as keyof IngestFormState]).trim(),
    username: String(form[`${prefix}_username` as keyof IngestFormState]).trim(),
    password: String(form[`${prefix}_password` as keyof IngestFormState]) || null,
    domain: String(form[`${prefix}_domain` as keyof IngestFormState]).trim(),
    base_path: String(form[`${prefix}_base_path` as keyof IngestFormState]).trim() || '/',
  }
}

function omitId<T extends { id: string }>(value: T): Omit<T, 'id'> {
  const { id: _id, ...rest } = value
  return rest
}

function triStateFromBoolean(value: boolean | null): '' | 'true' | 'false' {
  if (value === true) return 'true'
  if (value === false) return 'false'
  return ''
}

function triStateToBoolean(value: '' | 'true' | 'false') {
  if (value === 'true') return true
  if (value === 'false') return false
  return null
}

function ingestMediaTypeLabel(type: IngestMediaType) {
  const labels: Record<IngestMediaType, string> = {
    movie: '电影',
    series: '剧集',
    unclassified: '未分类',
  }
  return labels[type]
}

function ingestSeenStatusLabel(status: string) {
  const labels: Record<string, string> = {
    discovered: '已发现',
    stable: '已稳定',
    queued: '已排队',
    importing: '导入中',
    completed: '已完成',
    failed: '失败',
    ignored: '已忽略',
  }
  return labels[status] || status
}

function ingestSeenTone(status: string) {
  if (status === 'completed') return 'ok'
  if (status === 'failed') return 'error'
  if (status === 'discovered' || status === 'ignored') return 'unknown'
  return 'running'
}

function emptyLibraryForm(): LibraryFormState {
  return { id: '', name: '', media_type: 'movie', enabled: true, connection_id: '', base_path: '/' }
}

function emptyDtlConfigForm(): DtlConfigFormState {
  return { delete_source_after_success: true, delete_empty_source_dirs: true, scan_interval_seconds: '60', stable_seconds: '120', unclassified_library_id: '' }
}

function dtlConfigFormFromResponse(config: DtlConfigResponse): DtlConfigFormState {
  return { delete_source_after_success: config.delete_source_after_success, delete_empty_source_dirs: config.delete_empty_source_dirs, scan_interval_seconds: String(config.scan_interval_seconds), stable_seconds: String(config.stable_seconds), unclassified_library_id: config.unclassified_library_id }
}

function dtlConfigRequestFromForm(form: DtlConfigFormState) {
  return { delete_source_after_success: form.delete_source_after_success, delete_empty_source_dirs: form.delete_empty_source_dirs, scan_interval_seconds: Number(form.scan_interval_seconds) || 60, stable_seconds: Number(form.stable_seconds) || 120, unclassified_library_id: form.unclassified_library_id.trim() }
}

function emptyDtlBindingForm(): DtlBindingFormState {
  return { id: '', name: '', enabled: true, media_type: 'movie', source_connection_id: '', source_path: '', target_library_id: '', delete_source_after_success: '', delete_empty_source_dirs: '' }
}

function dtlSeenStatusLabel(status: string) {
  const labels: Record<string, string> = { discovered: '已发现', stable: '已稳定', queued: '已排队', downloading: '下载中', completed: '已完成', failed: '失败', ignored: '已忽略' }
  return labels[status] || status
}

function dtlSeenTone(status: string) {
  if (status === 'completed') return 'ok'
  if (status === 'failed') return 'error'
  if (status === 'discovered' || status === 'ignored') return 'unknown'
  return 'running'
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
    cleaning_source: '清理来源',
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
