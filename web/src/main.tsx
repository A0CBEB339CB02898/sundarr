import React, { useEffect, useState } from 'react'
import ReactDOM from 'react-dom/client'
import './styles.css'
import {
  Card,
  Button,
  Field,
  StatusBadge,
  ProgressBar,
  LoadingState as UILoadingState,
  EmptyState as UIEmptyState,
  ErrorState as UIErrorState,
  Kbd,
} from './ui'
import type { StatusTone } from './ui'

type PageKey = 'search' | 'transfers' | 'storage' | 'sources' | 'libraries' | 'remote-libraries' | 'status'
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
  sync_seen_file_id: string | null
  total_bytes: number
  done_bytes: number
  speed_bytes_per_sec: number
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
  | 'paused'

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
  bound_local_libraries: string[]
  bound_remote_libraries: string[]
  created_at: string | null
  updated_at: string | null
}

type SmbConnectionListResponse = {
  count: number
  page: number
  page_size: number
  results: SmbConnectionResponse[]
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

type MediaLibraryResponse = {
  id: string
  name: string
  media_type: DtlMediaType
  enabled: boolean
  connection_id: string
  base_path: string
  bound_remote_libraries: string[]
  created_at: string | null
  updated_at: string | null
}

type MediaLibraryListResponse = {
  count: number
  page: number
  page_size: number
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

type SyncMediaType = 'movie' | 'series' | 'unclassified'

type SyncConfigResponse = {
  delete_source_after_success: boolean
  delete_empty_source_dirs: boolean
  scan_interval_seconds: number
  stable_seconds: number
  unclassified_library_id: string
}

type SyncBindingResponse = {
  id: string
  name: string
  enabled: boolean
  media_type: SyncMediaType
  remote_library_id: string
  local_library_id: string
  delete_source_after_success: boolean | null
  delete_empty_source_dirs: boolean | null
  created_at: string | null
  updated_at: string | null
}

type SyncBindingListResponse = {
  count: number
  results: SyncBindingResponse[]
}

type SyncDiscoveredFileResponse = {
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

type SyncDiscoveredListResponse = {
  count: number
  results: SyncDiscoveredFileResponse[]
}

type SyncScanResponse = {
  scanned_bindings: number
  discovered_count: number
  stable_count: number
  results: SyncDiscoveredFileResponse[]
}

type SyncTaskCreateResponse = {
  created_count: number
  skipped_count: number
  tasks: TransferResponse[]
}

type SyncBindingTestResponse = {
  ok: boolean
  remote_ok: boolean
  local_ok: boolean
  error_code: string | null
  error_message: string | null
}

type SyncBindingFormState = {
  id: string
  name: string
  enabled: boolean
  media_type: SyncMediaType
  remote_library_id: string
  local_library_id: string
  delete_source_after_success: '' | 'true' | 'false'
  delete_empty_source_dirs: '' | 'true' | 'false'
}

type SyncConfigFormState = {
  delete_source_after_success: boolean
  delete_empty_source_dirs: boolean
  scan_interval_seconds: string
  stable_seconds: string
  unclassified_library_id: string
}

type RemoteMediaLibraryFormState = {
  id: string
  name: string
  media_type: DtlMediaType
  enabled: boolean
  connection_id: string
  base_path: string
  target_library_id: string
  scan_interval_seconds: string
  stable_seconds: string
  delete_source_after_success: '' | 'true' | 'false'
  delete_empty_source_dirs: '' | 'true' | 'false'
}

type RemoteMediaLibraryResponse = {
  id: string
  name: string
  media_type: DtlMediaType
  enabled: boolean
  connection_id: string
  base_path: string
  target_library_id: string | null
  target_library_name: string | null
  scan_interval_seconds: number
  stable_seconds: number
  delete_source_after_success: boolean | null
  delete_empty_source_dirs: boolean | null
  created_at: string | null
  updated_at: string | null
}

type RemoteMediaLibraryListResponse = {
  count: number
  page: number
  page_size: number
  results: RemoteMediaLibraryResponse[]
}

type MediaLibraryFormState = {
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
  { key: 'sources', path: '/app/sources', label: '媒体源', description: '管理已安装 Adapter' },
  { key: 'search', path: '/app/search', label: '搜索', description: '搜索资源并创建搬运任务' },
  { key: 'storage', path: '/app/storage', label: '存储', description: '管理 SMB 配置和目录浏览' },
  { key: 'libraries', path: '/app/libraries', label: '本地媒体库', description: '管理本地媒体库目录绑定' },
  { key: 'remote-libraries', path: '/app/remote-libraries', label: '远程媒体库', description: '管理远程媒体库目录绑定' },
  { key: 'transfers', path: '/app/transfers', label: '任务', description: '查看进度、日志、取消和重试' },
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
    title: '本地媒体库管理',
    body: '管理 movie / series / unclassified 等本地媒体库目录绑定。',
    next: '当前页面暂不可用，请从左侧导航重新进入。',
  },
  'remote-libraries': {
    eyebrow: 'Remote Libraries',
    title: '远程媒体库管理',
    body: '管理远程媒体库目录绑定，配置同步目标和扫描参数。',
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
  const [isTransferPanelOpen, setIsTransferPanelOpen] = useState(true)
  const [isDrawerOpen, setIsDrawerOpen] = useState(false)
  const [toasts, setToasts] = useState<{ id: number; type: 'success' | 'error' | 'info'; message: string; duration: number }[]>([])
  const TOAST_DURATION_MS = 4500

  function showToast(type: 'success' | 'error' | 'info', message: string) {
    const id = Date.now() + Math.random()
    setToasts((prev) => [...prev, { id, type, message, duration: TOAST_DURATION_MS }])
    setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), TOAST_DURATION_MS)
  }

  function removeToast(id: number) {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }

  useEffect(() => {
    const onPopState = () => setActivePage(pageFromPath(window.location.pathname))
    window.addEventListener('popstate', onPopState)
    return () => window.removeEventListener('popstate', onPopState)
  }, [])

  useEffect(() => {
    applyThemeMode(themeMode)
    window.localStorage.setItem('sundarr.theme', themeMode)
  }, [themeMode])

  // Drawer · 手机/平板：Esc 关闭 + 首次打开时滚动锁定
  useEffect(() => {
    if (!isDrawerOpen) return
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') setIsDrawerOpen(false)
    }
    const prevOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    window.addEventListener('keydown', onKey)
    return () => {
      window.removeEventListener('keydown', onKey)
      document.body.style.overflow = prevOverflow
    }
  }, [isDrawerOpen])

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

  async function clearNonRunningTasks() {
    const nonRunning = transfers.filter((t) => !['pending', 'downloading', 'verifying', 'renaming', 'cleaning_source', 'cleaning_cloud'].includes(t.status))
    if (nonRunning.length === 0) { showToast('info', '没有可清空的任务。'); return }
    if (!window.confirm(`确认清空 ${nonRunning.length} 个非运行中的任务？（包括已完成、失败、取消的任务）`)) return
    try {
      const result = await api.post<{ ok: boolean; deleted_count: number }>('/transfers/clear-completed')
      showToast('success', `已清空 ${result.deleted_count} 个任务。`)
      void loadTransfers()
    } catch (exc) { showToast('error', exc instanceof Error ? exc.message : '清空失败。') }
  }

  function navigate(item: NavItem) {
    window.history.pushState({}, '', item.path)
    setActivePage(item.key)
    setIsDrawerOpen(false)
    if (item.key === 'transfers') {
      setIsTransferPanelOpen(false)
    }
  }

  function navigateToTransfers(taskId?: string) {
    window.history.pushState({}, '', '/app/transfers')
    setActivePage('transfers')
    setIsDrawerOpen(false)
    setIsTransferPanelOpen(false)
    window.dispatchEvent(new CustomEvent('sundarr:select-transfer', { detail: { taskId } }))
  }

  return (
    <div className="app-shell">
      <header className="top-bar" role="banner">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true">S</span>
          <div>
            <p>Sundarr</p>
            <small>Web Console</small>
          </div>
        </div>
        <div className="top-bar-actions">
          <button
            className="icon-button"
            type="button"
            aria-label="打开导航"
            aria-expanded={isDrawerOpen}
            onClick={() => setIsDrawerOpen(true)}
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <line x1="4" y1="7" x2="20" y2="7" />
              <line x1="4" y1="12" x2="20" y2="12" />
              <line x1="4" y1="17" x2="20" y2="17" />
            </svg>
          </button>
        </div>
      </header>
      <div
        className="scrim"
        data-open={isDrawerOpen || undefined}
        onClick={() => setIsDrawerOpen(false)}
        aria-hidden="true"
      />
      <aside className="sidebar" aria-label="主导航" data-open={isDrawerOpen || undefined}>
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
        <PagePanel activePage={activePage} onTransfersChanged={loadTransfers} transfers={transfers} showToast={showToast} />
      </main>
      <GlobalTransferPanel
        error={transferError}
        isOpen={isTransferPanelOpen}
        onClose={() => setIsTransferPanelOpen(false)}
        onOpen={() => setIsTransferPanelOpen(true)}
        onRefresh={() => void loadTransfers()}
        onClear={() => void clearNonRunningTasks()}
        onSelect={navigateToTransfers}
        transfers={transfers}
      />
      <div className="toast-container" aria-live="polite" aria-atomic="false">
        {toasts.map((toast) => (
          <div className={`toast toast-${toast.type}`} key={toast.id} role="status">
            <span className="toast-icon" aria-hidden="true">
              {toast.type === 'success' ? (
                <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M4 10.5l4 4 8-9" /></svg>
              ) : toast.type === 'error' ? (
                <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M5 5l10 10M15 5L5 15" /></svg>
              ) : (
                <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M10 14V9M10 6.5v.01" /></svg>
              )}
            </span>
            <span className="toast-message">{toast.message}</span>
            <button className="toast-close" onClick={() => removeToast(toast.id)} type="button" aria-label="关闭">
              <svg viewBox="0 0 12 12" width="12" height="12" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"><path d="M3 3l6 6M9 3l-6 6" /></svg>
            </button>
            <span
              className="toast-progress"
              style={{ animationDuration: `${toast.duration}ms` }}
              aria-hidden="true"
            />
          </div>
        ))}
      </div>
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
  showToast,
}: {
  activePage: PageKey
  onTransfersChanged: () => Promise<void>
  transfers: TransferResponse[]
  showToast: (type: 'success' | 'error' | 'info', message: string) => void
}) {
  const copy = pageCopy[activePage]
  if (activePage === 'status') {
    return <StatusPanel />
  }
  if (activePage === 'transfers') {
    return <TransfersPanel onTransfersChanged={onTransfersChanged} transfers={transfers} showToast={showToast} />
  }
  if (activePage === 'storage') {
    return <StoragePanel showToast={showToast} />
  }
  if (activePage === 'search') {
    return <SearchPanel />
  }
  if (activePage === 'sources') {
    return <SourcesPanel />
  }
  if (activePage === 'libraries') {
    return <LibrariesPanel showToast={showToast} />
  }
  if (activePage === 'remote-libraries') {
    return <RemoteLibrariesPanel showToast={showToast} />
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

function LibrariesPanel({ showToast }: { showToast: (type: 'success' | 'error' | 'info', message: string) => void }) {
  const [libraries, setLibraries] = useState<MediaLibraryResponse[]>([])
  const [connections, setConnections] = useState<SmbConnectionResponse[]>([])
  const [totalCount, setTotalCount] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize] = useState(20)
  const [isLoading, setIsLoading] = useState(false)

  const [showForm, setShowForm] = useState(false)
  const [formMode, setFormMode] = useState<'create' | 'edit'>('create')
  const [editingId, setEditingId] = useState<string | null>(null)
  const [form, setForm] = useState<MediaLibraryFormState>(emptyLibraryForm())
  const [isSaving, setIsSaving] = useState(false)
  const [isTesting, setIsTesting] = useState(false)

  const [showDelete, setShowDelete] = useState(false)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<MediaLibraryResponse | null>(null)

  const [showBrowse, setShowBrowse] = useState(false)
  const [browseConnectionId, setBrowseConnectionId] = useState<string | null>(null)
  const [browsePath, setBrowsePath] = useState('')
  const [browseResult, setBrowseResult] = useState<StorageBrowseResponse | null>(null)
  const [isBrowsing, setIsBrowsing] = useState(false)

  useEffect(() => { void loadAll() }, [page])

  async function loadAll() {
    setIsLoading(true)
    try {
      const [libResult, connResult] = await Promise.all([
        api.get<MediaLibraryListResponse>(`/media-libraries?page=${page}&page_size=${pageSize}`),
        api.get<SmbConnectionListResponse>('/storage/smb-connections?page_size=100'),
      ])
      setLibraries(libResult.results); setTotalCount(libResult.count)
      setConnections(connResult.results)
    } catch (exc) { showToast('error', exc instanceof Error ? exc.message : '无法读取媒体库。') }
    finally { setIsLoading(false) }
  }

  function openCreate() {
    setFormMode('create'); setEditingId(null)
    setForm(emptyLibraryForm()); setShowForm(true)
  }

  function openEdit(lib: MediaLibraryResponse) {
    setFormMode('edit'); setEditingId(lib.id)
    setForm({ id: lib.id, name: lib.name, media_type: lib.media_type, enabled: lib.enabled, connection_id: lib.connection_id, base_path: lib.base_path })
    setShowForm(true)
  }

  async function saveLibrary() {
    setIsSaving(true)
    try {
      const payload = { name: form.name.trim(), media_type: form.media_type, enabled: form.enabled, connection_id: form.connection_id.trim(), base_path: form.base_path.trim() || '/' }
      if (formMode === 'create') {
        await api.post('/media-libraries/create', { id: form.id.trim(), ...payload })
      } else {
        await api.post(`/media-libraries/${encodeURIComponent(editingId!)}/update`, payload)
      }
      setShowForm(false); showToast('success', formMode === 'create' ? '媒体库已创建。' : '媒体库已保存。')
      await loadAll()
    } catch (exc) { showToast('error', exc instanceof Error ? exc.message : '保存失败。') }
    finally { setIsSaving(false) }
  }

  async function testLibrary(lib: MediaLibraryResponse) {
    try {
      const result = await api.post<{ ok: boolean; error_code: string | null; error_message: string | null }>(`/media-libraries/${encodeURIComponent(lib.id)}/test`)
      showToast(result.ok ? 'success' : 'error', result.ok ? `${lib.name} 测试通过。` : `${result.error_code || 'TEST_FAILED'}：${result.error_message || '测试失败。'}`)
    } catch (exc) { showToast('error', exc instanceof Error ? exc.message : '测试失败。') }
  }

  async function testLibraryInForm() {
    setIsTesting(true)
    try {
      const payload = { id: form.id.trim() || '', name: form.name.trim(), media_type: form.media_type, enabled: form.enabled, connection_id: form.connection_id.trim(), base_path: form.base_path.trim() || '/' }
      const endpoint = formMode === 'edit' && editingId
        ? `/media-libraries/${encodeURIComponent(editingId)}/test`
        : '/media-libraries/test-new'
      const result = await api.post<{ ok: boolean; error_code: string | null; error_message: string | null }>(endpoint, payload)
      showToast(result.ok ? 'success' : 'error', result.ok ? '媒体库目录测试通过。' : `${result.error_code || 'TEST_FAILED'}：${result.error_message || '测试失败。'}`)
    } catch (exc) { showToast('error', exc instanceof Error ? exc.message : '测试失败。') }
    finally { setIsTesting(false) }
  }

  function openBrowse(lib: MediaLibraryResponse) {
    const conn = connections.find((c) => c.id === lib.connection_id)
    if (!conn) { showToast('error', '未找到关联的 SMB 连接。'); return }
    setBrowseConnectionId(conn.id)
    setBrowsePath(lib.base_path || '')
    setBrowseResult(null)
    setShowBrowse(true)
    void doBrowse(lib.base_path || '', conn.id)
  }

  async function doBrowse(nextPath = browsePath, connectionId: string | null = browseConnectionId) {
    if (!connectionId) { showToast('error', '未选择 SMB 连接。'); return }
    setIsBrowsing(true)
    try {
      const result = await api.get<StorageBrowseResponse>(`/storage/smb-connections/${encodeURIComponent(connectionId)}/browse?path=${encodeURIComponent(nextPath.trim())}`)
      setBrowseResult(result); setBrowsePath(result.path)
    } catch (exc) { setBrowseResult(null); showToast('error', exc instanceof Error ? exc.message : '浏览失败。') }
    finally { setIsBrowsing(false) }
  }

  async function toggleEnabled(lib: MediaLibraryResponse) {
    setIsSaving(true)
    try {
      await api.post(`/media-libraries/${encodeURIComponent(lib.id)}/${lib.enabled ? 'disable' : 'enable'}`)
      showToast('success', lib.enabled ? '媒体库已禁用。' : '媒体库已启用。')
      await loadAll()
    } catch (exc) { showToast('error', exc instanceof Error ? exc.message : '操作失败。') }
    finally { setIsSaving(false) }
  }

  function openDeleteModal(lib: MediaLibraryResponse) {
    setDeletingId(lib.id); setDeleteTarget(lib); setShowDelete(true)
  }

  async function executeDelete(action: 'delete' | 'unbind' | 'cancel') {
    if (action === 'cancel') { setShowDelete(false); return }
    setIsSaving(true)
    try {
      await api.post(`/media-libraries/${encodeURIComponent(deletingId!)}/delete`, { action })
      setShowDelete(false); showToast('success', action === 'delete' ? '媒体库已删除。' : '媒体库已删除，绑定的远程媒体库已解绑。')
      await loadAll()
    } catch (exc) { showToast('error', exc instanceof Error ? exc.message : '删除失败。') }
    finally { setIsSaving(false) }
  }

  function updateForm(key: keyof MediaLibraryFormState, value: string | boolean) { setForm((c) => ({ ...c, [key]: value })) }
  const totalPages = Math.max(1, Math.ceil(totalCount / pageSize))
  const connName = (id: string) => connections.find((c) => c.id === id)?.name || id

  return (
    <section className="panel" aria-labelledby="libraries-title">
      <div className="panel-header-row">
        <div>
          <p className="panel-kicker">媒体库</p>
          <h2 id="libraries-title">本地媒体库管理</h2>
          <p>管理 movie / series / unclassified 等本地媒体库目录绑定。</p>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button className="ghost-button" disabled={isLoading} onClick={() => void loadAll()} type="button">{isLoading ? '读取中' : '重新读取'}</button>
          <button className="primary-button" onClick={openCreate} type="button">新增</button>
        </div>
      </div>

      {isLoading && <LoadingState message="正在读取媒体库。" />}

      <div className="transfer-list-section">
        <div className="section-heading"><h3>媒体库列表</h3><span>{totalCount} 个</span></div>
        {libraries.length === 0 ? <EmptyState message="暂无媒体库。点击新增创建。" /> : (
          <div className="transfer-list">
            {libraries.map((lib) => (
              <div key={lib.id} className="transfer-row">
                <div className="transfer-row-main">
                  <strong>{lib.name}</strong>
                  <span>{lib.media_type} · {connName(lib.connection_id)} · {lib.base_path} · {lib.enabled ? '已启用' : '已禁用'}</span>
                  <small>绑定远程库: {lib.bound_remote_libraries.length > 0 ? lib.bound_remote_libraries.join('、') : '无'}</small>
                </div>
                <div className="transfer-row-actions">
                  <button className="ghost-button" onClick={() => openEdit(lib)} type="button">编辑</button>
                  <button className="ghost-button" onClick={() => void testLibrary(lib)} type="button">测试</button>
                  <button className="ghost-button" onClick={() => openBrowse(lib)} type="button">浏览</button>
                  <button className="ghost-button" onClick={() => void toggleEnabled(lib)} type="button">{lib.enabled ? '禁用' : '启用'}</button>
                  <button className="ghost-button danger" onClick={() => openDeleteModal(lib)} type="button">删除</button>
                </div>
              </div>
            ))}
          </div>
        )}
        {totalPages > 1 && (
          <div className="pagination">
            <button className="ghost-button" disabled={page <= 1} onClick={() => setPage(page - 1)} type="button">上一页</button>
            <span>第 {page} / {totalPages} 页</span>
            <button className="ghost-button" disabled={page >= totalPages} onClick={() => setPage(page + 1)} type="button">下一页</button>
          </div>
        )}
      </div>

      {showForm && (
        <div className="modal-overlay">
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>{formMode === 'create' ? '创建媒体库' : '编辑媒体库'}</h3>
              <button className="ghost-button" onClick={() => setShowForm(false)} type="button">×</button>
            </div>
            <div className="form-grid">
              <TextField disabled={formMode === 'edit'} helper="唯一 ID，保存后不可改。" label="唯一标识" onChange={(v) => updateForm('id', v)} required value={form.id} />
              <TextField helper="页面展示名称。" label="名称" onChange={(v) => updateForm('name', v)} required value={form.name} />
              <label className="field"><span>媒体类型</span><select value={form.media_type} onChange={(e) => updateForm('media_type', e.target.value)}>
                <option value="movie">电影</option><option value="series">剧集</option><option value="unclassified">未分类</option>
              </select><small>电影、剧集或未分类。</small></label>
              <label className="field"><span>SMB 连接</span><select value={form.connection_id} onChange={(e) => updateForm('connection_id', e.target.value)}>
                <option value="">选择连接</option>{connections.map((c) => <option key={c.id} value={c.id}>{c.name} ({c.host}/{c.share})</option>)}
              </select><small>绑定到某个已配置的 SMB 连接。</small></label>
              <TextField helper="相对于 SMB 连接 Base Path 的本地目录。" label="目录路径" onChange={(v) => updateForm('base_path', v)} required value={form.base_path} />
            </div>
            <div className="form-actions">
              <button className="ghost-button" onClick={() => setShowForm(false)} type="button">取消</button>
              <button className="ghost-button" disabled={isTesting} onClick={() => void testLibraryInForm()} type="button">{isTesting ? '测试中' : '测试连接'}</button>
              <button className="primary-button" disabled={isSaving} onClick={() => void saveLibrary()} type="button">{isSaving ? '保存中' : formMode === 'create' ? '创建' : '保存'}</button>
            </div>
          </div>
        </div>
      )}

      {showBrowse && (
        <div className="modal-overlay">
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>目录浏览</h3>
              <button className="ghost-button" onClick={() => { setShowBrowse(false); setBrowseResult(null); setBrowsePath('') }} type="button">×</button>
            </div>
            <form className="lookup-form" onSubmit={(event) => { event.preventDefault(); void doBrowse() }}>
              <label>
                <span>路径</span>
                <input onChange={(event) => setBrowsePath(event.target.value)} placeholder="例如 Movies" type="text" value={browsePath} />
              </label>
              <button className="primary-button" disabled={isBrowsing} type="submit">{isBrowsing ? '浏览中' : '浏览'}</button>
            </form>
            <p className="lookup-form-hint">相对于 Base Path 的目录。</p>
            {isBrowsing && !browseResult ? <LoadingState message="正在读取目录。" /> : null}
            {browseResult ? <StorageBrowser result={browseResult} onOpen={(path) => void doBrowse(path)} /> : <EmptyState message="输入路径后浏览目录。" />}
          </div>
        </div>
      )}

      {showDelete && deleteTarget && (
        <div className="modal-overlay">
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>删除媒体库</h3>
              <button className="ghost-button" onClick={() => setShowDelete(false)} type="button">×</button>
            </div>
            <p>删除 <strong>{deleteTarget.name}</strong> 将影响以下绑定：</p>
            {deleteTarget.bound_remote_libraries.length > 0 && (
              <div><strong>远程媒体库：</strong>{deleteTarget.bound_remote_libraries.join('、')}</div>
            )}
            {deleteTarget.bound_remote_libraries.length === 0 && (
              <p>此媒体库没有绑定的远程媒体库。</p>
            )}
            <div className="form-actions">
              <button className="ghost-button" onClick={() => void executeDelete('cancel')} type="button">取消</button>
              {deleteTarget.bound_remote_libraries.length > 0 && (
                <button className="ghost-button" disabled={isSaving} onClick={() => void executeDelete('unbind')} type="button">仅解绑</button>
              )}
              <button className="ghost-button danger" disabled={isSaving} onClick={() => void executeDelete('delete')} type="button">删除所有</button>
            </div>
          </div>
        </div>
      )}

      <ApiClientPreview />
    </section>
  )
}

function RemoteLibrariesPanel({ showToast }: { showToast: (type: 'success' | 'error' | 'info', message: string) => void }) {
  const [libraries, setLibraries] = useState<RemoteMediaLibraryResponse[]>([])
  const [connections, setConnections] = useState<SmbConnectionResponse[]>([])
  const [localLibraries, setLocalLibraries] = useState<MediaLibraryResponse[]>([])
  const [totalCount, setTotalCount] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize] = useState(20)
  const [isLoading, setIsLoading] = useState(false)

  const [showForm, setShowForm] = useState(false)
  const [formMode, setFormMode] = useState<'create' | 'edit'>('create')
  const [editingId, setEditingId] = useState<string | null>(null)
  const [form, setForm] = useState<RemoteMediaLibraryFormState>(emptyRemoteLibraryForm())
  const [isSaving, setIsSaving] = useState(false)
  const [isTesting, setIsTesting] = useState(false)

  const [showDelete, setShowDelete] = useState(false)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<RemoteMediaLibraryResponse | null>(null)

  const [showBrowse, setShowBrowse] = useState(false)
  const [browseConnectionId, setBrowseConnectionId] = useState<string | null>(null)
  const [browsePath, setBrowsePath] = useState('')
  const [browseResult, setBrowseResult] = useState<StorageBrowseResponse | null>(null)
  const [isBrowsing, setIsBrowsing] = useState(false)

  useEffect(() => { void loadAll() }, [page])

  async function loadAll() {
    setIsLoading(true)
    try {
      const [libResult, connResult, localResult] = await Promise.all([
        api.get<RemoteMediaLibraryListResponse>(`/remote-media-libraries?page=${page}&page_size=${pageSize}`),
        api.get<SmbConnectionListResponse>('/storage/smb-connections?page_size=100'),
        api.get<MediaLibraryListResponse>('/media-libraries?page_size=100'),
      ])
      setLibraries(libResult.results); setTotalCount(libResult.count)
      setConnections(connResult.results)
      setLocalLibraries(localResult.results)
    } catch (exc) { showToast('error', exc instanceof Error ? exc.message : '无法读取远程媒体库。') }
    finally { setIsLoading(false) }
  }

  function openCreate() {
    setFormMode('create'); setEditingId(null)
    setForm(emptyRemoteLibraryForm()); setShowForm(true)
  }

  function openEdit(lib: RemoteMediaLibraryResponse) {
    setFormMode('edit'); setEditingId(lib.id)
    setForm({
      id: lib.id, name: lib.name, media_type: lib.media_type, enabled: lib.enabled,
      connection_id: lib.connection_id, base_path: lib.base_path,
      target_library_id: lib.target_library_id || '',
      scan_interval_seconds: String(lib.scan_interval_seconds),
      stable_seconds: String(lib.stable_seconds),
      delete_source_after_success: triStateFromBoolean(lib.delete_source_after_success),
      delete_empty_source_dirs: triStateFromBoolean(lib.delete_empty_source_dirs),
    })
    setShowForm(true)
  }

  async function saveLibrary() {
    setIsSaving(true)
    try {
      const payload = {
        name: form.name.trim(), media_type: form.media_type, enabled: form.enabled,
        connection_id: form.connection_id.trim(), base_path: form.base_path.trim() || '/',
        target_library_id: form.target_library_id || null,
        scan_interval_seconds: Number(form.scan_interval_seconds) || 60,
        stable_seconds: Number(form.stable_seconds) || 120,
        delete_source_after_success: triStateToBoolean(form.delete_source_after_success),
        delete_empty_source_dirs: triStateToBoolean(form.delete_empty_source_dirs),
      }
      if (formMode === 'create') {
        await api.post('/remote-media-libraries/create', { id: form.id.trim(), ...payload })
      } else {
        await api.post(`/remote-media-libraries/${encodeURIComponent(editingId!)}/update`, payload)
      }
      setShowForm(false); showToast('success', formMode === 'create' ? '远程媒体库已创建。' : '远程媒体库已保存。')
      await loadAll()
    } catch (exc) { showToast('error', exc instanceof Error ? exc.message : '保存失败。') }
    finally { setIsSaving(false) }
  }

  async function testLibrary(lib: RemoteMediaLibraryResponse) {
    try {
      const result = await api.post<{ ok: boolean; error_code: string | null; error_message: string | null }>(`/remote-media-libraries/${encodeURIComponent(lib.id)}/test`)
      showToast(result.ok ? 'success' : 'error', result.ok ? `${lib.name} 测试通过。` : `${result.error_code || 'TEST_FAILED'}：${result.error_message || '测试失败。'}`)
    } catch (exc) { showToast('error', exc instanceof Error ? exc.message : '测试失败。') }
  }

  async function testLibraryInForm() {
    setIsTesting(true)
    try {
      const payload = {
        id: form.id.trim() || '', name: form.name.trim(), media_type: form.media_type, enabled: form.enabled,
        connection_id: form.connection_id.trim(), base_path: form.base_path.trim() || '/',
        target_library_id: form.target_library_id || null,
        scan_interval_seconds: Number(form.scan_interval_seconds) || 60,
        stable_seconds: Number(form.stable_seconds) || 120,
        delete_source_after_success: triStateToBoolean(form.delete_source_after_success),
        delete_empty_source_dirs: triStateToBoolean(form.delete_empty_source_dirs),
      }
      const endpoint = formMode === 'edit' && editingId
        ? `/remote-media-libraries/${encodeURIComponent(editingId)}/test`
        : '/remote-media-libraries/test-new'
      const result = await api.post<{ ok: boolean; error_code: string | null; error_message: string | null }>(endpoint, payload)
      showToast(result.ok ? 'success' : 'error', result.ok ? '远程媒体库目录测试通过。' : `${result.error_code || 'TEST_FAILED'}：${result.error_message || '测试失败。'}`)
    } catch (exc) { showToast('error', exc instanceof Error ? exc.message : '测试失败。') }
    finally { setIsTesting(false) }
  }

  function openBrowse(lib: RemoteMediaLibraryResponse) {
    const conn = connections.find((c) => c.id === lib.connection_id)
    if (!conn) { showToast('error', '未找到关联的 SMB 连接。'); return }
    setBrowseConnectionId(conn.id)
    setBrowsePath(lib.base_path || '')
    setBrowseResult(null)
    setShowBrowse(true)
    void doBrowse(lib.base_path || '', conn.id)
  }

  async function doBrowse(nextPath = browsePath, connectionId: string | null = browseConnectionId) {
    if (!connectionId) { showToast('error', '未选择 SMB 连接。'); return }
    setIsBrowsing(true)
    try {
      const result = await api.get<StorageBrowseResponse>(`/storage/smb-connections/${encodeURIComponent(connectionId)}/browse?path=${encodeURIComponent(nextPath.trim())}`)
      setBrowseResult(result); setBrowsePath(result.path)
    } catch (exc) { setBrowseResult(null); showToast('error', exc instanceof Error ? exc.message : '浏览失败。') }
    finally { setIsBrowsing(false) }
  }

  async function triggerScan(lib: RemoteMediaLibraryResponse) {
    try {
      await api.post('/sync/scan', { binding_id: lib.id })
      showToast('success', `${lib.name} 扫描完成。`)
    } catch (exc) { showToast('error', exc instanceof Error ? exc.message : '扫描失败。') }
  }

  async function toggleEnabled(lib: RemoteMediaLibraryResponse) {
    setIsSaving(true)
    try {
      await api.post(`/remote-media-libraries/${encodeURIComponent(lib.id)}/${lib.enabled ? 'disable' : 'enable'}`)
      showToast('success', lib.enabled ? '远程媒体库已禁用。' : '远程媒体库已启用。')
      await loadAll()
    } catch (exc) { showToast('error', exc instanceof Error ? exc.message : '操作失败。') }
    finally { setIsSaving(false) }
  }

  function openDeleteModal(lib: RemoteMediaLibraryResponse) {
    setDeletingId(lib.id); setDeleteTarget(lib); setShowDelete(true)
  }

  async function executeDelete(action: 'delete' | 'cancel') {
    if (action === 'cancel') { setShowDelete(false); return }
    setIsSaving(true)
    try {
      await api.post(`/remote-media-libraries/${encodeURIComponent(deletingId!)}/delete`, { action })
      setShowDelete(false); showToast('success', '远程媒体库已删除。')
      await loadAll()
    } catch (exc) { showToast('error', exc instanceof Error ? exc.message : '删除失败。') }
    finally { setIsSaving(false) }
  }

  function updateForm(key: keyof RemoteMediaLibraryFormState, value: string | boolean) { setForm((c) => ({ ...c, [key]: value })) }
  const totalPages = Math.max(1, Math.ceil(totalCount / pageSize))
  const connName = (id: string) => connections.find((c) => c.id === id)?.name || id
  const libName = (id: string) => localLibraries.find((l) => l.id === id)?.name || id

  return (
    <section className="panel" aria-labelledby="remote-libraries-title">
      <div className="panel-header-row">
        <div>
          <p className="panel-kicker">远程媒体库</p>
          <h2 id="remote-libraries-title">远程媒体库管理</h2>
          <p>管理远程媒体库目录绑定，配置同步目标和扫描参数。</p>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button className="ghost-button" disabled={isLoading} onClick={() => void loadAll()} type="button">{isLoading ? '读取中' : '重新读取'}</button>
          <button className="primary-button" onClick={openCreate} type="button">新增</button>
        </div>
      </div>

      {isLoading && <LoadingState message="正在读取远程媒体库。" />}

      <div className="transfer-list-section">
        <div className="section-heading"><h3>远程媒体库列表</h3><span>{totalCount} 个</span></div>
        {libraries.length === 0 ? <EmptyState message="暂无远程媒体库。点击新增创建。" /> : (
          <div className="transfer-list">
            {libraries.map((lib) => (
              <div key={lib.id} className="transfer-row">
                <div className="transfer-row-main">
                  <strong>{lib.name}</strong>
                  <span>{lib.media_type} · {connName(lib.connection_id)} · {lib.base_path} · {lib.enabled ? '已启用' : '已禁用'}</span>
                  <small>同步目标: {lib.target_library_id ? libName(lib.target_library_id) : '未绑定'} · 扫描间隔: {lib.scan_interval_seconds}s</small>
                </div>
                <div className="transfer-row-actions">
                  <button className="ghost-button" onClick={() => openEdit(lib)} type="button">编辑</button>
                  <button className="ghost-button" onClick={() => void testLibrary(lib)} type="button">测试</button>
                  <button className="ghost-button" onClick={() => openBrowse(lib)} type="button">浏览</button>
                  {lib.target_library_id && <button className="ghost-button" onClick={() => void triggerScan(lib)} type="button">扫描</button>}
                  <button className="ghost-button" onClick={() => void toggleEnabled(lib)} type="button">{lib.enabled ? '禁用' : '启用'}</button>
                  <button className="ghost-button danger" onClick={() => openDeleteModal(lib)} type="button">删除</button>
                </div>
              </div>
            ))}
          </div>
        )}
        {totalPages > 1 && (
          <div className="pagination">
            <button className="ghost-button" disabled={page <= 1} onClick={() => setPage(page - 1)} type="button">上一页</button>
            <span>第 {page} / {totalPages} 页</span>
            <button className="ghost-button" disabled={page >= totalPages} onClick={() => setPage(page + 1)} type="button">下一页</button>
          </div>
        )}
      </div>

      {showForm && (
        <div className="modal-overlay">
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>{formMode === 'create' ? '创建远程媒体库' : '编辑远程媒体库'}</h3>
              <button className="ghost-button" onClick={() => setShowForm(false)} type="button">×</button>
            </div>
            <div className="form-grid">
              <TextField disabled={formMode === 'edit'} helper="唯一 ID，保存后不可改。" label="唯一标识" onChange={(v) => updateForm('id', v)} required value={form.id} />
              <TextField helper="页面展示名称。" label="名称" onChange={(v) => updateForm('name', v)} required value={form.name} />
              <label className="field"><span>媒体类型</span><select value={form.media_type} onChange={(e) => updateForm('media_type', e.target.value)}>
                <option value="movie">电影</option><option value="series">剧集</option><option value="unclassified">未分类</option>
              </select><small>电影、剧集或未分类。</small></label>
              <label className="field"><span>SMB 连接</span><select value={form.connection_id} onChange={(e) => updateForm('connection_id', e.target.value)}>
                <option value="">选择连接</option>{connections.map((c) => <option key={c.id} value={c.id}>{c.name} ({c.host}/{c.share})</option>)}
              </select><small>绑定到某个已配置的 SMB 连接。</small></label>
              <TextField helper="相对于 SMB 连接 Base Path 的远程目录。" label="目录路径" onChange={(v) => updateForm('base_path', v)} required value={form.base_path} />
            </div>
            <div className="section-heading" style={{ marginTop: 16 }}><h3>同步配置</h3></div>
            <div className="form-grid">
              <label className="field"><span>同步目标本地媒体库</span><select value={form.target_library_id} onChange={(e) => updateForm('target_library_id', e.target.value)}>
                <option value="">不绑定（禁用自动同步）</option>{localLibraries.map((l) => <option key={l.id} value={l.id}>{l.name} ({l.media_type})</option>)}
              </select><small>绑定后 Worker 将自动扫描并下载到此本地媒体库。</small></label>
              <TextField helper="两次扫描之间的间隔秒数。" label="扫描间隔(秒)" onChange={(v) => updateForm('scan_interval_seconds', v)} type="number" value={form.scan_interval_seconds} />
              <TextField helper="文件 size/mtime 不变超过该秒数后才创建任务。" label="稳定等待(秒)" onChange={(v) => updateForm('stable_seconds', v)} type="number" value={form.stable_seconds} />
              <label className="field"><span>成功后删除来源</span><select value={form.delete_source_after_success} onChange={(e) => updateForm('delete_source_after_success', e.target.value)}>
                <option value="">使用全局默认</option><option value="true">删除</option><option value="false">保留</option>
              </select><small>为空时使用全局配置。</small></label>
              <label className="field"><span>成功后删除空目录</span><select value={form.delete_empty_source_dirs} onChange={(e) => updateForm('delete_empty_source_dirs', e.target.value)}>
                <option value="">使用全局默认</option><option value="true">删除</option><option value="false">保留</option>
              </select><small>为空时使用全局配置。</small></label>
            </div>
            <div className="form-actions">
              <button className="ghost-button" onClick={() => setShowForm(false)} type="button">取消</button>
              <button className="ghost-button" disabled={isTesting} onClick={() => void testLibraryInForm()} type="button">{isTesting ? '测试中' : '测试连接'}</button>
              <button className="primary-button" disabled={isSaving} onClick={() => void saveLibrary()} type="button">{isSaving ? '保存中' : formMode === 'create' ? '创建' : '保存'}</button>
            </div>
          </div>
        </div>
      )}

      {showBrowse && (
        <div className="modal-overlay">
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>目录浏览</h3>
              <button className="ghost-button" onClick={() => { setShowBrowse(false); setBrowseResult(null); setBrowsePath('') }} type="button">×</button>
            </div>
            <form className="lookup-form" onSubmit={(event) => { event.preventDefault(); void doBrowse() }}>
              <label>
                <span>路径</span>
                <input onChange={(event) => setBrowsePath(event.target.value)} placeholder="例如 Movies" type="text" value={browsePath} />
              </label>
              <button className="primary-button" disabled={isBrowsing} type="submit">{isBrowsing ? '浏览中' : '浏览'}</button>
            </form>
            <p className="lookup-form-hint">相对于 Base Path 的目录。</p>
            {isBrowsing && !browseResult ? <LoadingState message="正在读取目录。" /> : null}
            {browseResult ? <StorageBrowser result={browseResult} onOpen={(path) => void doBrowse(path)} /> : <EmptyState message="输入路径后浏览目录。" />}
          </div>
        </div>
      )}

      {showDelete && deleteTarget && (
        <div className="modal-overlay">
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>删除远程媒体库</h3>
              <button className="ghost-button" onClick={() => setShowDelete(false)} type="button">×</button>
            </div>
            <p>确认删除远程媒体库 <strong>{deleteTarget.name}</strong>？关联的同步记录将被清理。</p>
            <div className="form-actions">
              <button className="ghost-button" onClick={() => void executeDelete('cancel')} type="button">取消</button>
              <button className="ghost-button danger" disabled={isSaving} onClick={() => void executeDelete('delete')} type="button">确认删除</button>
            </div>
          </div>
        </div>
      )}

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

function StoragePanel({ showToast }: { showToast: (type: 'success' | 'error' | 'info', message: string) => void }) {
  const [connections, setConnections] = useState<SmbConnectionResponse[]>([])
  const [totalCount, setTotalCount] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize] = useState(20)
  const [isLoading, setIsLoading] = useState(false)

  const [showForm, setShowForm] = useState(false)
  const [formMode, setFormMode] = useState<'create' | 'edit'>('create')
  const [editingId, setEditingId] = useState<string | null>(null)
  const [form, setForm] = useState<StorageFormState>(emptyStorageForm())
  const [formName, setFormName] = useState('')
  const [passwordSet, setPasswordSet] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [isTesting, setIsTesting] = useState(false)

  const [showDelete, setShowDelete] = useState(false)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<SmbConnectionResponse | null>(null)

  const [showBrowse, setShowBrowse] = useState(false)
  const [browseId, setBrowseId] = useState<string | null>(null)
  const [browsePath, setBrowsePath] = useState('')
  const [browseResult, setBrowseResult] = useState<StorageBrowseResponse | null>(null)
  const [isBrowsing, setIsBrowsing] = useState(false)

  useEffect(() => { void loadConnections() }, [page])

  async function loadConnections() {
    setIsLoading(true)
    try {
      const result = await api.get<SmbConnectionListResponse>(`/storage/smb-connections?page=${page}&page_size=${pageSize}`)
      setConnections(result.results)
      setTotalCount(result.count)
    } catch (exc) { showToast('error', exc instanceof Error ? exc.message : '无法读取 SMB 连接。') }
    finally { setIsLoading(false) }
  }

  function openCreate() {
    setFormMode('create'); setEditingId(null)
    setForm(emptyStorageForm()); setFormName(''); setPasswordSet(false)
    setShowForm(true)
  }

  function openEdit(conn: SmbConnectionResponse) {
    setFormMode('edit'); setEditingId(conn.id)
    setForm({ host: conn.host, port: String(conn.port), share: conn.share, username: conn.username, password: '', domain: conn.domain, base_path: conn.base_path, library_movies: '', library_tv: '', library_anime: '' })
    setFormName(conn.name); setPasswordSet(conn.password_set)
    setShowForm(true)
  }

  async function saveConnection() {
    setIsSaving(true)
    try {
      const payload = { host: form.host.trim(), port: Number(form.port) || 445, share: form.share.trim(), username: form.username.trim(), password: form.password || null, domain: form.domain.trim(), base_path: form.base_path.trim() || '/' }
      if (formMode === 'create') {
        const id = `conn_${Date.now()}`
        await api.post('/storage/smb-connections/create', { id, name: formName.trim() || `${payload.host}/${payload.share}`, ...payload })
      } else {
        await api.post(`/storage/smb-connections/${encodeURIComponent(editingId!)}/update`, { name: formName.trim(), ...payload })
      }
      setShowForm(false); showToast('success', formMode === 'create' ? 'SMB 连接已创建。' : 'SMB 连接已保存。')
      await loadConnections()
    } catch (exc) { showToast('error', exc instanceof Error ? exc.message : '保存失败。') }
    finally { setIsSaving(false) }
  }

  async function testConnection() {
    setIsTesting(true)
    try {
      const payload = { id: editingId || '', name: formName, host: form.host.trim(), port: Number(form.port) || 445, share: form.share.trim(), username: form.username.trim(), password: form.password || null, domain: form.domain.trim(), base_path: form.base_path.trim() || '/' }
      const endpoint = formMode === 'edit' && editingId
        ? `/storage/smb-connections/${encodeURIComponent(editingId)}/test`
        : '/storage/smb-connections/test-new'
      const result = await api.post<StorageConfigTestResponse>(endpoint, payload)
      showToast(result.ok ? 'success' : 'error', result.ok ? 'SMB 连接测试通过。' : `${result.error_code || 'TEST_FAILED'}：${result.error_message || '测试失败。'}`)
    } catch (exc) { showToast('error', exc instanceof Error ? exc.message : '测试失败。') }
    finally { setIsTesting(false) }
  }

  async function testConnectionRow(conn: SmbConnectionResponse) {
    try {
      const result = await api.post<StorageConfigTestResponse>(`/storage/smb-connections/${encodeURIComponent(conn.id)}/test`)
      showToast(result.ok ? 'success' : 'error', result.ok ? `${conn.name} 测试通过。` : `${result.error_code || 'TEST_FAILED'}：${result.error_message || '测试失败。'}`)
    } catch (exc) { showToast('error', exc instanceof Error ? exc.message : '测试失败。') }
  }

  function openDeleteModal(conn: SmbConnectionResponse) {
    setDeletingId(conn.id); setDeleteTarget(conn); setShowDelete(true)
  }

  async function executeDelete(action: 'delete' | 'unbind' | 'cancel') {
    if (action === 'cancel') { setShowDelete(false); return }
    setIsSaving(true)
    try {
      await api.post(`/storage/smb-connections/${encodeURIComponent(deletingId!)}/delete`, { action })
      setShowDelete(false); showToast('success', action === 'delete' ? 'SMB 连接及绑定的媒体库已删除。' : 'SMB 连接已删除，绑定的媒体库已解绑。')
      await loadConnections()
    } catch (exc) { showToast('error', exc instanceof Error ? exc.message : '删除失败。') }
    finally { setIsSaving(false) }
  }

  function openBrowse(conn: SmbConnectionResponse) {
    setBrowseId(conn.id)
    setBrowsePath(conn.base_path || '')
    setBrowseResult(null)
    setShowBrowse(true)
    void doBrowse(conn.base_path || '', conn.id)
  }

  async function doBrowse(nextPath = browsePath, connectionId: string | null = browseId) {
    if (!connectionId) { showToast('error', '未选择 SMB 连接。'); return }
    setIsBrowsing(true)
    try {
      const result = await api.get<StorageBrowseResponse>(`/storage/smb-connections/${encodeURIComponent(connectionId)}/browse?path=${encodeURIComponent(nextPath.trim())}`)
      setBrowseResult(result); setBrowsePath(result.path)
    } catch (exc) { setBrowseResult(null); showToast('error', exc instanceof Error ? exc.message : '浏览失败。') }
    finally { setIsBrowsing(false) }
  }

  function updateForm(key: keyof StorageFormState, value: string) { setForm((c) => ({ ...c, [key]: value })) }

  const totalPages = Math.max(1, Math.ceil(totalCount / pageSize))

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
          <button className="primary-button" onClick={openCreate} type="button">新增</button>
        </div>
      </div>

      {isLoading && <LoadingState message="正在读取 SMB 连接。" />}

      <div className="transfer-list-section">
        <div className="section-heading"><h3>SMB 连接列表</h3><span>{totalCount} 个</span></div>
        {connections.length === 0 ? <EmptyState message="暂无 SMB 连接。点击新增创建。" /> : (
          <div className="transfer-list">
            {connections.map((conn) => (
              <div key={conn.id} className="transfer-row">
                <div className="transfer-row-main">
                  <strong>{conn.name}</strong>
                  <span>{conn.host}/{conn.share} · {conn.username} · {conn.password_set ? '已设密码' : '未设密码'} · {conn.enabled ? '已启用' : '已禁用'}</span>
                  <small>绑定: 本地 {conn.bound_local_libraries.length} 个, 远程 {conn.bound_remote_libraries.length} 个</small>
                </div>
                <div className="transfer-row-actions">
                  <button className="ghost-button" onClick={() => openEdit(conn)} type="button">编辑</button>
                  <button className="ghost-button" onClick={() => void testConnectionRow(conn)} type="button">测试</button>
                  <button className="ghost-button" onClick={() => openBrowse(conn)} type="button">浏览</button>
                  <button className="ghost-button danger" onClick={() => openDeleteModal(conn)} type="button">删除</button>
                </div>
              </div>
            ))}
          </div>
        )}
        {totalPages > 1 && (
          <div className="pagination">
            <button className="ghost-button" disabled={page <= 1} onClick={() => setPage(page - 1)} type="button">上一页</button>
            <span>第 {page} / {totalPages} 页</span>
            <button className="ghost-button" disabled={page >= totalPages} onClick={() => setPage(page + 1)} type="button">下一页</button>
          </div>
        )}
      </div>

      {showForm && (
        <div className="modal-overlay">
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>{formMode === 'create' ? '创建 SMB 连接' : '编辑 SMB 连接'}</h3>
              <button className="ghost-button" onClick={() => setShowForm(false)} type="button">×</button>
            </div>
            <div className="form-grid">
              <TextField helper="连接名称，用于在其他模块中引用。" label="名称" onChange={setFormName} required value={formName} />
              <TextField helper="SMB 服务器地址，只填主机名或 IP。" label="Host" onChange={(v) => updateForm('host', v)} required value={form.host} />
              <TextField helper="SMB 端口，通常是 445。" label="Port" onChange={(v) => updateForm('port', v)} required type="number" value={form.port} />
              <TextField helper="SMB 共享名。" label="Share" onChange={(v) => updateForm('share', v)} required value={form.share} />
              <TextField helper="SMB 登录账号。" label="Username" onChange={(v) => updateForm('username', v)} required value={form.username} />
              <TextField helper={passwordSet ? '已保存密码且不会回显。留空表示保留旧密码。' : 'SMB 登录密码。'} label="Password" onChange={(v) => updateForm('password', v)} type="password" value={form.password} />
              <TextField helper="SMB 域或工作组；个人 NAS 通常留空。" label="Domain" onChange={(v) => updateForm('domain', v)} value={form.domain} />
              <TextField helper="共享内的工作根目录。" label="Base Path" onChange={(v) => updateForm('base_path', v)} value={form.base_path} />
            </div>
            <div className="form-actions">
              <button className="ghost-button" onClick={() => setShowForm(false)} type="button">取消</button>
              <button className="ghost-button" disabled={isTesting} onClick={() => void testConnection()} type="button">{isTesting ? '测试中' : '测试连接'}</button>
              <button className="primary-button" disabled={isSaving} onClick={() => void saveConnection()} type="button">{isSaving ? '保存中' : formMode === 'create' ? '创建' : '保存'}</button>
            </div>
          </div>
        </div>
      )}

      {showDelete && deleteTarget && (
        <div className="modal-overlay">
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>删除 SMB 连接</h3>
              <button className="ghost-button" onClick={() => setShowDelete(false)} type="button">×</button>
            </div>
            <p>删除 <strong>{deleteTarget.name}</strong> 将影响以下绑定：</p>
            {deleteTarget.bound_local_libraries.length > 0 && (
              <div><strong>本地媒体库：</strong>{deleteTarget.bound_local_libraries.join('、')}</div>
            )}
            {deleteTarget.bound_remote_libraries.length > 0 && (
              <div><strong>远程媒体库：</strong>{deleteTarget.bound_remote_libraries.join('、')}</div>
            )}
            {deleteTarget.bound_local_libraries.length === 0 && deleteTarget.bound_remote_libraries.length === 0 && (
              <p>此连接没有绑定的媒体库。</p>
            )}
            <div className="form-actions">
              <button className="ghost-button" onClick={() => void executeDelete('cancel')} type="button">取消</button>
              {(deleteTarget.bound_local_libraries.length > 0 || deleteTarget.bound_remote_libraries.length > 0) && (
                <button className="ghost-button" disabled={isSaving} onClick={() => void executeDelete('unbind')} type="button">仅解绑</button>
              )}
              <button className="ghost-button danger" disabled={isSaving} onClick={() => void executeDelete('delete')} type="button">删除所有</button>
            </div>
          </div>
        </div>
      )}

      {showBrowse && (
        <div className="modal-overlay">
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>目录浏览</h3>
              <button className="ghost-button" onClick={() => { setShowBrowse(false); setBrowseResult(null); setBrowsePath('') }} type="button">×</button>
            </div>
            <form className="lookup-form" onSubmit={(event) => { event.preventDefault(); void doBrowse() }}>
              <label>
                <span>路径</span>
                <input onChange={(event) => setBrowsePath(event.target.value)} placeholder="例如 Movies" type="text" value={browsePath} />
              </label>
              <button className="primary-button" disabled={isBrowsing} type="submit">{isBrowsing ? '浏览中' : '浏览'}</button>
            </form>
            <p className="lookup-form-hint">相对于 Base Path 的目录。</p>
            {isBrowsing && !browseResult ? <LoadingState message="正在读取目录。" /> : null}
            {browseResult ? <StorageBrowser result={browseResult} onOpen={(path) => void doBrowse(path)} /> : <EmptyState message="输入路径后浏览 SMB 目录。" />}
          </div>
        </div>
      )}

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

function TransfersPanel({ onTransfersChanged, transfers, showToast }: { onTransfersChanged: () => Promise<void>; transfers: TransferResponse[]; showToast: (type: 'success' | 'error' | 'info', message: string) => void }) {
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

  async function runTaskAction(action: 'cancel' | 'retry' | 'pause' | 'resume') {
    if (!transfer) return
    const actionText =
      action === 'cancel' ? '取消' : action === 'retry' ? '重试' : action === 'pause' ? '暂停' : '继续'
    if (action !== 'resume' && !window.confirm(`确认${actionText}任务 ${transfer.id}？`)) {
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

  async function pauseTaskById(id: string) {
    try {
      await api.post(`/transfers/${encodeURIComponent(id)}/pause`)
      showToast('success', '任务已暂停。')
      if (transfer?.id === id) await loadTransfer(id)
      await onTransfersChanged()
    } catch (exc) { showToast('error', exc instanceof Error ? exc.message : '暂停失败。') }
  }

  async function resumeTaskById(id: string) {
    try {
      await api.post(`/transfers/${encodeURIComponent(id)}/resume`)
      showToast('success', '任务已恢复。')
      if (transfer?.id === id) await loadTransfer(id)
      await onTransfersChanged()
    } catch (exc) { showToast('error', exc instanceof Error ? exc.message : '恢复失败。') }
  }

  async function deleteTask(taskId: string) {
    if (!window.confirm(`确认删除任务 ${taskId}？`)) return
    try {
      await api.post(`/transfers/${encodeURIComponent(taskId)}/delete`)
      showToast('success', '任务已删除。')
      if (transfer?.id === taskId) { setTransfer(null); setLogs([]) }
      await onTransfersChanged()
    } catch (exc) { showToast('error', exc instanceof Error ? exc.message : '删除失败。') }
  }

  async function clearCompleted() {
    if (!window.confirm('确认清空所有已完成的任务？')) return
    try {
      const result = await api.post<{ ok: boolean; deleted_count: number }>('/transfers/clear-completed')
      showToast('success', `已清空 ${result.deleted_count} 个已完成任务。`)
      setTransfer(null); setLogs([])
      await onTransfersChanged()
    } catch (exc) { showToast('error', exc instanceof Error ? exc.message : '清空失败。') }
  }

  const canCancel = transfer ? canCancelTransfer(transfer.status) : false
  const canRetry = transfer?.status === 'failed' && transfer.retryable === true
  const canPause = transfer ? canPauseTransfer(transfer.status) : false
  const canResume = transfer ? canResumeTransfer(transfer.status) : false

  return (
    <section className="tx-page" aria-labelledby="transfers-title">
      <Card className="tx-overview">
        <div className="tx-overview-head">
          <div>
            <p className="ui-eyebrow">任务</p>
            <h2 id="transfers-title">任务列表与控制</h2>
            <p className="tx-overview-lead">
              查看最近任务，选择后读取详情与关键日志，并按当前状态执行取消、暂停或重试。
            </p>
          </div>
          <div className="tx-overview-actions">
            <Button variant="ghost" onClick={() => void clearCompleted()}>
              清空已完成
            </Button>
          </div>
        </div>
      </Card>

      <TransferTable
        transfers={transfers}
        selectedId={transfer?.id || null}
        onSelect={(id) => void loadTransfer(id)}
        onDelete={(id) => void deleteTask(id)}
        onPause={(id) => void pauseTaskById(id)}
        onResume={(id) => void resumeTaskById(id)}
      />

      <Card>
        <form
          className="tx-lookup"
          onSubmit={(event) => {
            event.preventDefault()
            void loadTransfer()
          }}
        >
          <Field
            label="任务 ID"
            htmlFor="tx-lookup-id"
            helper={
              <>
                也可以从上方列表或右侧浮动面板选择任务。按 <Kbd>Enter</Kbd> 查询。
              </>
            }
          >
            <input
              id="tx-lookup-id"
              onChange={(event) => setTaskId(event.target.value)}
              placeholder="例如 task_001"
              type="text"
              value={taskId}
            />
          </Field>
          <Button variant="primary" disabled={isLoading} type="submit">
            {isLoading ? '查询中' : '查询任务'}
          </Button>
        </form>
      </Card>

      {isLoading && !transfer ? (
        <Card>
          <UILoadingState message="正在读取任务详情和日志。" />
        </Card>
      ) : null}
      {error ? (
        <Card>
          <UIErrorState message="请求失败" sub={error} />
        </Card>
      ) : null}
      {!isLoading && !error && !transfer ? (
        <Card>
          <UIEmptyState
            message="选择一个任务查看详情"
            sub="在上方任务表格点选，或在下方输入任务 ID。"
          />
        </Card>
      ) : null}

      {transfer ? (
        <>
          <TransferSummary transfer={transfer} />
          <Card>
            <div className="tx-action-row">
              <Button
                variant="primary"
                disabled={!canCancel || isMutating}
                onClick={() => void runTaskAction('cancel')}
              >
                {isMutating ? '处理中' : '取消任务'}
              </Button>
              {canPause && (
                <Button
                  variant="secondary"
                  disabled={isMutating}
                  onClick={() => void runTaskAction('pause')}
                >
                  {isMutating ? '处理中' : '暂停任务'}
                </Button>
              )}
              {canResume && (
                <Button
                  variant="secondary"
                  disabled={isMutating}
                  onClick={() => void runTaskAction('resume')}
                >
                  {isMutating ? '处理中' : '继续任务'}
                </Button>
              )}
              <Button
                variant="secondary"
                disabled={!canRetry || isMutating}
                onClick={() => void runTaskAction('retry')}
              >
                {isMutating ? '处理中' : '重试任务'}
              </Button>
              <Button
                variant="ghost"
                disabled={isLoading || isMutating}
                onClick={() => void loadTransfer(transfer.id)}
              >
                刷新详情
              </Button>
            </div>
          </Card>
          <TransferNotice transfer={transfer} />
          <TransferLogs logs={logs} />
        </>
      ) : null}
    </section>
  )
}

function TransferTable({
  onSelect,
  selectedId,
  transfers,
  onDelete,
  onPause,
  onResume,
}: {
  onSelect: (id: string) => void
  selectedId: string | null
  transfers: TransferResponse[]
  onDelete: (id: string) => void
  onPause: (id: string) => void
  onResume: (id: string) => void
}) {
  if (transfers.length === 0) {
    return (
      <Card emphasis="sunken">
        <UIEmptyState
          message="还没有任务"
          sub="创建搜索任务或下载到本地任务后，会显示在这里。"
        />
      </Card>
    )
  }

  return (
    <Card emphasis="sunken" className="tx-table-card">
      <div className="tx-table-head">
        <p className="ui-eyebrow">最近任务</p>
        <span className="tx-table-count">{transfers.length}</span>
      </div>
      <div className="tx-table" role="table" aria-label="任务列表">
        <div className="tx-table-header" role="row">
          <span role="columnheader">状态</span>
          <span role="columnheader">目标 / 文件</span>
          <span role="columnheader">进度</span>
          <span role="columnheader">速度</span>
          <span role="columnheader">更新</span>
          <span role="columnheader" aria-label="操作" />
        </div>
        {transfers.map((item) => {
          const running = isTransferRunning(item.status)
          const progress = Math.max(0, Math.min(100, item.progress))
          return (
            <div
              className="tx-row"
              key={item.id}
              role="row"
              data-selected={selectedId === item.id || undefined}
            >
              <button
                className="tx-row-main"
                onClick={() => onSelect(item.id)}
                type="button"
                aria-label={`查看任务 ${item.target_path}`}
              >
                <span className="tx-col-status" role="cell">
                  <StatusBadge tone={transferStatusToneUI(item.status)} pulse={running}>
                    {transferStatusLabel(item.status)}
                  </StatusBadge>
                </span>
                <span className="tx-col-title" role="cell">
                  <strong title={item.target_path}>{item.target_path}</strong>
                  <small title={item.current_file || item.id}>
                    {item.current_file || item.id}
                  </small>
                </span>
                <span className="tx-col-progress" role="cell">
                  <ProgressBar value={progress / 100} />
                  <em>{progress.toFixed(0)}%</em>
                </span>
                <span className="tx-col-num" role="cell">
                  {item.status === 'downloading' && item.speed_bytes_per_sec > 0
                    ? `${formatBytes(item.speed_bytes_per_sec)}/s`
                    : '--'}
                </span>
                <span className="tx-col-num" role="cell">
                  {formatRelative(item.updated_at)}
                </span>
              </button>
              <div className="tx-row-actions" role="cell">
                {canPauseTransfer(item.status) && (
                  <Button variant="ghost" size="sm" onClick={() => onPause(item.id)}>
                    暂停
                  </Button>
                )}
                {canResumeTransfer(item.status) && (
                  <Button variant="ghost" size="sm" onClick={() => onResume(item.id)}>
                    继续
                  </Button>
                )}
                {(item.status === 'completed' ||
                  item.status === 'failed' ||
                  item.status === 'cancelled') && (
                  <Button variant="danger" size="sm" onClick={() => onDelete(item.id)}>
                    删除
                  </Button>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </Card>
  )
}

function GlobalTransferPanel({
  error,
  isOpen,
  onClose,
  onOpen,
  onRefresh,
  onClear,
  onSelect,
  transfers,
}: {
  error: string | null
  isOpen: boolean
  onClose: () => void
  onOpen: () => void
  onRefresh: () => void
  onClear: () => void
  onSelect: (taskId?: string) => void
  transfers: TransferResponse[]
}) {
  const activeTransfers = transfers.filter(
    (transfer) => !['completed', 'failed', 'cancelled'].includes(transfer.status),
  )
  const visibleTransfers = (activeTransfers.length > 0 ? activeTransfers : transfers).slice(0, 5)

  return (
    <aside className="tx-dock" data-open={isOpen || undefined} aria-label="全局任务面板">
      <button
        className="tx-dock-tab"
        onClick={isOpen ? onClose : onOpen}
        type="button"
        aria-expanded={isOpen}
      >
        <span>任务</span>
        <strong>{activeTransfers.length || transfers.length}</strong>
      </button>
      <div className="tx-dock-card" role="region" aria-label="当前任务">
        <div className="tx-dock-head">
          <p className="ui-eyebrow">当前任务</p>
          <div className="tx-dock-head-actions">
            <Button variant="ghost" size="sm" onClick={onRefresh}>
              刷新
            </Button>
            <Button variant="ghost" size="sm" onClick={onClear}>
              清空
            </Button>
          </div>
        </div>
        {error ? <UIErrorState message="无法读取任务列表" sub={error} /> : null}
        {!error && visibleTransfers.length === 0 ? (
          <UIEmptyState message="暂无任务" sub="创建任务后会出现在这里。" />
        ) : null}
        <div className="tx-dock-list">
          {visibleTransfers.map((transfer) => {
            const running = isTransferRunning(transfer.status)
            const progress = Math.max(0, Math.min(100, transfer.progress))
            return (
              <button
                className="tx-dock-row"
                key={transfer.id}
                onClick={() => onSelect(transfer.id)}
                type="button"
              >
                <div className="tx-dock-row-head">
                  <StatusBadge tone={transferStatusToneUI(transfer.status)} pulse={running}>
                    {transferStatusLabel(transfer.status)}
                  </StatusBadge>
                  <strong title={transfer.target_path}>{transfer.target_path}</strong>
                </div>
                <ProgressBar
                  value={progress / 100}
                  valueLabel={
                    <>
                      {progress.toFixed(0)}%
                      {transfer.status === 'downloading' && transfer.speed_bytes_per_sec > 0
                        ? ` · ${formatBytes(transfer.speed_bytes_per_sec)}/s`
                        : ''}
                    </>
                  }
                />
                <small title={transfer.current_file || transfer.id}>
                  {transfer.current_file || transfer.id}
                </small>
              </button>
            )
          })}
        </div>
        <Button
          variant="primary"
          className="tx-dock-cta"
          onClick={() => onSelect()}
        >
          打开任务页
        </Button>
      </div>
    </aside>
  )
}

function TransferSummary({ transfer }: { transfer: TransferResponse }) {
  const running = isTransferRunning(transfer.status)
  const progress = Math.max(0, Math.min(100, transfer.progress))
  return (
    <Card emphasis="featured" className="tx-summary">
      <div className="tx-summary-head">
        <StatusBadge tone={transferStatusToneUI(transfer.status)} pulse={running}>
          {transferStatusLabel(transfer.status)}
        </StatusBadge>
        <div>
          <p className="tx-summary-id">{transfer.id}</p>
          <p className="tx-summary-path">{transfer.target_path}</p>
        </div>
      </div>
      <ProgressBar
        value={progress / 100}
        label="进度"
        valueLabel={`${progress.toFixed(2)}%`}
      />
      <dl className="tx-detail-grid">
        <TransferDetail label="当前文件" value={transfer.current_file || '无'} />
        <TransferDetail label="目标类型" value={transfer.target_type} />
        <TransferDetail label="已完成" value={formatBytes(transfer.done_bytes)} mono />
        <TransferDetail label="总大小" value={formatBytes(transfer.total_bytes)} mono />
        <TransferDetail
          label="速度"
          value={
            transfer.speed_bytes_per_sec > 0 ? `${formatBytes(transfer.speed_bytes_per_sec)}/s` : '--'
          }
          mono
        />
        <TransferDetail label="重试次数" value={String(transfer.retry_count)} mono />
        <TransferDetail label="可重试" value={transfer.retryable === true ? '是' : '否'} />
      </dl>
      {transfer.error_code || transfer.error_message ? (
        <div className="tx-error-card" role="alert">
          <strong>{transfer.error_code || '任务错误'}</strong>
          <p>{transfer.error_message || '无错误详情。'}</p>
        </div>
      ) : null}
    </Card>
  )
}

function TransferDetail({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="tx-detail-item">
      <dt>{label}</dt>
      <dd data-mono={mono ? 'true' : undefined}>{value}</dd>
    </div>
  )
}

// Legacy 详情项（Sources / Ingest 扫描结果等仍在用，Step 5 迁移到对应页面时替换）
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
    <Card className="tx-notice">
      <strong>{message.title}</strong>
      <p>{message.body}</p>
    </Card>
  )
}

function TransferLogs({ logs }: { logs: TransferLogResponse[] }) {
  if (logs.length === 0) {
    return (
      <Card>
        <UIEmptyState message="该任务暂无日志" />
      </Card>
    )
  }

  return (
    <Card emphasis="sunken" className="tx-logs">
      <div className="tx-logs-head">
        <p className="ui-eyebrow">任务日志</p>
        <span className="tx-logs-count">{logs.length} 条</span>
      </div>
      <ol className="tx-log-list">
        {logs.map((log) => (
          <li className="tx-log-item" key={log.id}>
            <div className="tx-log-head">
              <span className="tx-log-level" data-level={log.level}>
                {log.level}
              </span>
              <strong>{log.event}</strong>
              <time>{formatDateTime(log.created_at)}</time>
            </div>
            <p>{log.message || '无日志说明。'}</p>
            {log.data ? <code>{JSON.stringify(log.data)}</code> : null}
          </li>
        ))}
      </ol>
    </Card>
  )
}

function StatusPanel() {
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [workerState, setWorkerState] = useState<{ enabled: boolean; running: boolean; pid: number | null } | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [isMutating, setIsMutating] = useState(false)
  const [lastCheckedAt, setLastCheckedAt] = useState<Date | null>(null)

  useEffect(() => { void loadHealth() }, [])

  async function loadHealth() {
    setIsLoading(true); setError(null)
    try {
      const [h, w] = await Promise.all([
        api.get<HealthResponse>('/health'),
        api.get<{ enabled: boolean; running: boolean; pid: number | null }>('/worker/status'),
      ])
      setHealth(h); setWorkerState(w)
      setLastCheckedAt(new Date())
    } catch (exc) {
      setHealth(null); setWorkerState(null)
      setError(exc instanceof Error ? exc.message : '无法读取系统状态。')
    } finally { setIsLoading(false) }
  }

  async function toggleWorker(enable: boolean) {
    setIsMutating(true); setError(null)
    try {
      await api.post(enable ? '/worker/resume' : '/worker/pause')
      void loadHealth()
    } catch (exc) { setError(exc instanceof Error ? exc.message : '操作失败。') }
    finally { setIsMutating(false) }
  }

  const items: { label: string; value: string }[] = health ? [
    { label: 'API', value: health.status },
    { label: 'Database', value: health.database },
    { label: 'Redis', value: health.redis },
    { label: 'Worker', value: health.worker },
  ] : []

  const lastCheckedLabel = lastCheckedAt ? formatClock(lastCheckedAt) : '--:--:--'

  return (
    <section className="st-page" aria-labelledby="status-title">
      <Card className="st-overview">
        <div className="st-overview-head">
          <div>
            <p className="ui-eyebrow">状态</p>
            <h2 id="status-title">系统状态概览</h2>
            <p className="st-overview-lead">
              调用 <code>GET /health</code> 与 <code>GET /worker/status</code>，展示 API、Database、Redis 与 Worker 的当前状态。
            </p>
          </div>
          <div className="st-overview-actions">
            <Button variant="primary" disabled={isLoading} onClick={() => void loadHealth()}>
              {isLoading ? '刷新中' : '刷新状态'}
            </Button>
          </div>
        </div>
      </Card>

      {isLoading && !health ? (
        <Card>
          <UILoadingState message="正在读取系统状态。" />
        </Card>
      ) : null}
      {error ? (
        <Card>
          <UIErrorState message="请求失败" sub={error} />
        </Card>
      ) : null}

      {health ? (
        <>
          <div className="st-grid" role="list" aria-label="系统状态卡片">
            {items.map((item) => (
              <StatusCard key={item.label} label={item.label} value={item.value} lastChecked={lastCheckedLabel} />
            ))}
          </div>

          {workerState ? (
            <Card className="st-worker-card">
              <div className="st-worker-head">
                <div>
                  <p className="ui-eyebrow">Worker 控制</p>
                  <strong className="st-worker-title">
                    {workerState.enabled ? '已启用' : '已暂停'}
                  </strong>
                  <p className="st-worker-sub">
                    PID <span className="st-mono">{workerState.pid ?? '--'}</span>
                    {' · '}
                    进程{workerState.running ? '运行中' : '未运行'}
                  </p>
                </div>
                <div className="st-worker-actions">
                  <Button
                    variant="secondary"
                    disabled={isMutating || !workerState.enabled}
                    onClick={() => void toggleWorker(false)}
                  >
                    暂停 Worker
                  </Button>
                  <Button
                    variant="secondary"
                    disabled={isMutating || workerState.enabled}
                    onClick={() => void toggleWorker(true)}
                  >
                    恢复 Worker
                  </Button>
                </div>
              </div>
            </Card>
          ) : null}

          <Card emphasis="sunken" className="st-diag">
            <details className="st-diag-details">
              <summary className="st-diag-summary">
                <span>
                  <p className="ui-eyebrow">Diagnostics</p>
                  <strong>原始 /health 返回</strong>
                </span>
                <span className="st-diag-chevron" aria-hidden="true">
                  <svg viewBox="0 0 12 12" width="12" height="12" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M3 4.5l3 3 3-3" />
                  </svg>
                </span>
              </summary>
              <pre className="st-diag-body">
                {JSON.stringify({ health, worker: workerState }, null, 2)}
              </pre>
            </details>
          </Card>
        </>
      ) : null}
    </section>
  )
}

function StatusCard({ label, value, lastChecked }: { label: string; value: string; lastChecked: string }) {
  const tone: StatusTone =
    value === 'ok' ? 'success' : value === 'unknown' ? 'paused' : 'danger'
  return (
    <Card className="st-card" data-tone={tone} role="listitem">
      <p className="ui-eyebrow">{label}</p>
      <h3 className="st-card-value">{statusLabel(value)}</h3>
      <p className="st-card-line">
        <span className="st-card-dot" aria-hidden="true" />
        <span className="st-card-desc">{statusDescription(label, value)}</span>
      </p>
      <p className="st-card-meta">
        <span>last checked</span>
        <time>{lastChecked}</time>
      </p>
    </Card>
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

function emptyLibraryForm(): MediaLibraryFormState {
  return { id: '', name: '', media_type: 'movie', enabled: true, connection_id: '', base_path: '/' }
}

function emptyRemoteLibraryForm(): RemoteMediaLibraryFormState {
  return { id: '', name: '', media_type: 'movie', enabled: true, connection_id: '', base_path: '/', target_library_id: '', scan_interval_seconds: '60', stable_seconds: '120', delete_source_after_success: '', delete_empty_source_dirs: '' }
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

function emptySyncConfigForm(): SyncConfigFormState {
  return { delete_source_after_success: true, delete_empty_source_dirs: true, scan_interval_seconds: '60', stable_seconds: '120', unclassified_library_id: '' }
}

function syncConfigFormFromResponse(config: SyncConfigResponse): SyncConfigFormState {
  return { delete_source_after_success: config.delete_source_after_success, delete_empty_source_dirs: config.delete_empty_source_dirs, scan_interval_seconds: String(config.scan_interval_seconds), stable_seconds: String(config.stable_seconds), unclassified_library_id: config.unclassified_library_id }
}

function syncConfigRequestFromForm(form: SyncConfigFormState) {
  return { delete_source_after_success: form.delete_source_after_success, delete_empty_source_dirs: form.delete_empty_source_dirs, scan_interval_seconds: Number(form.scan_interval_seconds) || 60, stable_seconds: Number(form.stable_seconds) || 120, unclassified_library_id: form.unclassified_library_id.trim() }
}

function emptySyncBindingForm(): SyncBindingFormState {
  return { id: '', name: '', enabled: true, media_type: 'movie', remote_library_id: '', local_library_id: '', delete_source_after_success: '', delete_empty_source_dirs: '' }
}

function syncSeenStatusLabel(status: string) {
  const labels: Record<string, string> = { discovered: '已发现', stable: '已稳定', queued: '已排队', downloading: '下载中', completed: '已完成', failed: '失败', ignored: '已忽略' }
  return labels[status] || status
}

function syncSeenTone(status: string) {
  if (status === 'completed') return 'ok'
  if (status === 'failed') return 'error'
  if (status === 'discovered' || status === 'ignored') return 'unknown'
  return 'running'
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
  return ['pending', 'staging_to_cloud', 'cloud_ready', 'downloading', 'verifying', 'paused'].includes(status)
}

function canPauseTransfer(status: TransferStatus) {
  return ['pending', 'staging_to_cloud', 'cloud_ready', 'downloading', 'verifying'].includes(status)
}

function canResumeTransfer(status: TransferStatus) {
  return status === 'paused'
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
    paused: '已暂停',
  }
  return labels[status]
}

function transferStatusTone(status: TransferStatus) {
  if (status === 'completed') return 'ok'
  if (status === 'failed') return 'error'
  if (status === 'cancelled') return 'unknown'
  if (status === 'paused') return 'unknown'
  return 'running'
}

function transferStatusToneUI(status: TransferStatus): StatusTone {
  // docs/16-design-system.md §6.6 · Transfer 状态到 5 tone 映射。
  if (status === 'completed') return 'success'
  if (status === 'failed' || status === 'cancelled') return 'danger'
  if (status === 'paused') return 'paused'
  if (status === 'pending') return 'info'
  return 'running' // staging_to_cloud / cloud_ready / downloading / verifying / renaming / cleaning_*
}

function isTransferRunning(status: TransferStatus) {
  return [
    'staging_to_cloud',
    'cloud_ready',
    'downloading',
    'verifying',
    'renaming',
    'cleaning_cloud',
    'cleaning_source',
  ].includes(status)
}

function formatRelative(value: string | null) {
  if (!value) return '--'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  const diff = (Date.now() - date.getTime()) / 1000
  if (diff < 30) return '刚刚'
  if (diff < 60) return `${Math.floor(diff)} 秒前`
  if (diff < 3600) return `${Math.floor(diff / 60)} 分钟前`
  if (diff < 86400) return `${Math.floor(diff / 3600)} 小时前`
  const days = Math.floor(diff / 86400)
  if (days < 30) return `${days} 天前`
  return date.toLocaleDateString('zh-CN')
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

function formatClock(date: Date) {
  if (Number.isNaN(date.getTime())) return '--:--:--'
  const hh = String(date.getHours()).padStart(2, '0')
  const mm = String(date.getMinutes()).padStart(2, '0')
  const ss = String(date.getSeconds()).padStart(2, '0')
  return `${hh}:${mm}:${ss}`
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
