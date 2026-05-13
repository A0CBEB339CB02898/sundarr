import React, { useEffect, useId, useState } from 'react'
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
  BrandLockup,
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

type ComponentHealth = {
  status: string
  checked_at: string
}

type HealthResponse = {
  status: string
  database: string
  redis: string
  worker: string
  checked_at: string
  components: {
    api: ComponentHealth
    database: ComponentHealth
    redis: ComponentHealth
    worker: ComponentHealth
  }
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

type TransferListResponse = {
  count: number
  page: number
  page_size: number
  results: TransferResponse[]
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
  last_test_ok: boolean | null
  last_test_error_code: string | null
  last_test_error_message: string | null
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
  page: number
  page_size: number
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

type MediaLibraryResponse = {
  id: string
  name: string
  media_type: DtlMediaType
  enabled: boolean
  connection_id: string
  base_path: string
  bound_remote_libraries: string[]
  last_test_ok: boolean | null
  last_test_error_code: string | null
  last_test_error_message: string | null
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
  last_test_ok: boolean | null
  last_test_error_code: string | null
  last_test_error_message: string | null
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
  const [transferPage, setTransferPage] = useState(1)
  const [transferTotalCount, setTransferTotalCount] = useState(0)
  const [transferPageSize, setTransferPageSize] = useState(20)
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
    const timer = window.setInterval(() => void loadTransfers(), 5000)
    const onTransfersChanged = () => void loadTransfers()
    window.addEventListener('sundarr:transfers-changed', onTransfersChanged)
    return () => {
      window.clearInterval(timer)
      window.removeEventListener('sundarr:transfers-changed', onTransfersChanged)
    }
  }, [transferPage, transferPageSize])

  async function loadTransfers(nextPage = transferPage) {
    try {
      const result = await api.get<TransferListResponse>(`/transfers?page=${nextPage}&page_size=${transferPageSize}`)
      setTransfers(result.results)
      setTransferTotalCount(result.count)
      setTransferError(null)
    } catch (exc) {
      setTransferError(exc instanceof Error ? exc.message : '无法读取任务列表。')
    }
  }

  async function clearNonRunningTasks() {
    const clearable = transfers.filter((t) => ['completed', 'cancelled'].includes(t.status))
    if (clearable.length === 0) { showToast('info', '没有可清理的任务。'); return }
    if (!window.confirm(`确认清理 ${clearable.length} 个已完成或已取消的任务？`)) return
    try {
      const result = await api.post<{ ok: boolean; deleted_count: number }>('/transfers/clear-completed')
      showToast('success', `已清理 ${result.deleted_count} 个任务。`)
      void loadTransfers()
    } catch (exc) { showToast('error', exc instanceof Error ? exc.message : '清理失败。') }
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
        <BrandLockup compact />
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
        <BrandLockup />
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
      <div className="utility-bar">
        <ThemeSwitcher mode={themeMode} onChange={setThemeMode} />
      </div>

      <main className="content-shell">
        <PagePanel
          activePage={activePage}
          onTransfersChanged={loadTransfers}
          transferPage={transferPage}
          transferPageSize={transferPageSize}
          transferTotalCount={transferTotalCount}
          onTransferPageChange={setTransferPage}
          onTransferPageSizeChange={setTransferPageSize}
          transfers={transfers}
          showToast={showToast}
        />
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
          <button
            aria-label={`切换到${themeModeLabel(item)}`}
            aria-pressed={mode === item}
            className="theme-button"
            data-active={mode === item}
            key={item}
            onClick={() => onChange(item)}
            title={themeModeLabel(item)}
            type="button"
          >
            <ThemeModeIcon mode={item} />
          </button>
        ))}
      </div>
    </div>
  )
}

function ThemeModeIcon({ mode }: { mode: ThemeMode }) {
  if (mode === 'light') {
    return (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <circle cx="12" cy="12" r="4" />
        <path d="M12 2v2.2M12 19.8V22M4.9 4.9l1.6 1.6M17.5 17.5l1.6 1.6M2 12h2.2M19.8 12H22M4.9 19.1l1.6-1.6M17.5 6.5l1.6-1.6" />
      </svg>
    )
  }
  if (mode === 'dark') {
    return (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M20.3 14.4A7.8 7.8 0 0 1 9.6 3.7 8.7 8.7 0 1 0 20.3 14.4Z" />
      </svg>
    )
  }
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <rect x="4" y="5" width="16" height="11" rx="2" />
      <path d="M9 20h6M12 16v4" />
    </svg>
  )
}

function PagePanel({
  activePage,
  onTransfersChanged,
  transferPage,
  transferPageSize,
  transferTotalCount,
  onTransferPageChange,
  onTransferPageSizeChange,
  transfers,
  showToast,
}: {
  activePage: PageKey
  onTransfersChanged: () => Promise<void>
  transferPage: number
  transferPageSize: number
  transferTotalCount: number
  onTransferPageChange: (page: number) => void
  onTransferPageSizeChange: (pageSize: number) => void
  transfers: TransferResponse[]
  showToast: (type: 'success' | 'error' | 'info', message: string) => void
}) {
  const copy = pageCopy[activePage]
  if (activePage === 'status') {
    return <StatusPanel />
  }
  if (activePage === 'transfers') {
    return <TransfersPanel onTransfersChanged={onTransfersChanged} page={transferPage} pageSize={transferPageSize} totalCount={transferTotalCount} onPageChange={onTransferPageChange} onPageSizeChange={onTransferPageSizeChange} transfers={transfers} showToast={showToast} />
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
        <UILoadingState message="后续页面加载数据时使用此状态。" />
        <UIErrorState message="API 错误会统一显示在这里。" />
        <UIEmptyState message="没有数据时展示明确的空状态。" />
      </div>
      <ApiClientPreview />
    </section>
  )
}

/**
 * 本地媒体库页面 · docs/16-design-system.md §7.4
 *
 * §7.4 要求：name · type · path · scan settings · stats · actions。
 * Local library schema 没有 scan_interval/stable_seconds/last_scan 字段
 * （这些属于 remote_media_libraries 同步配置），所以 stats 列用
 * `bound_remote_libraries` 的引用数代替，path 列显示 SMB 连接名 + mono path。
 */
function LibrariesPanel({ showToast }: { showToast: (type: 'success' | 'error' | 'info', message: string) => void }) {
  const [libraries, setLibraries] = useState<MediaLibraryResponse[]>([])
  const [connections, setConnections] = useState<SmbConnectionResponse[]>([])
  const [remoteLibraries, setRemoteLibraries] = useState<RemoteMediaLibraryResponse[]>([])
  const [totalCount, setTotalCount] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [isLoading, setIsLoading] = useState(false)
  const [loadError, setLoadError] = useState<string | null>(null)

  const [showForm, setShowForm] = useState(false)
  const [formMode, setFormMode] = useState<'create' | 'edit'>('create')
  const [editingId, setEditingId] = useState<string | null>(null)
  const [form, setForm] = useState<MediaLibraryFormState>(emptyLibraryForm())
  const [selectedRemoteIds, setSelectedRemoteIds] = useState<string[]>([])
  const [isSaving, setIsSaving] = useState(false)
  const [isTesting, setIsTesting] = useState(false)

  const [showDelete, setShowDelete] = useState(false)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<MediaLibraryResponse | null>(null)

  const [showBrowse, setShowBrowse] = useState(false)
  const [browseConnectionId, setBrowseConnectionId] = useState<string | null>(null)
  const [browseLibraryName, setBrowseLibraryName] = useState('')
  const [browsePath, setBrowsePath] = useState('')
  const [browseResult, setBrowseResult] = useState<StorageBrowseResponse | null>(null)
  const [isBrowsing, setIsBrowsing] = useState(false)

  useEffect(() => { void loadAll() }, [page, pageSize])

  async function loadAll() {
    setIsLoading(true)
    setLoadError(null)
    try {
      const [libResult, connResult, remoteResult] = await Promise.all([
        api.get<MediaLibraryListResponse>(`/media-libraries?page=${page}&page_size=${pageSize}`),
        api.get<SmbConnectionListResponse>('/storage/smb-connections?page_size=100'),
        api.get<RemoteMediaLibraryListResponse>('/remote-media-libraries?page_size=100'),
      ])
      setLibraries(libResult.results); setTotalCount(libResult.count)
      setConnections(connResult.results)
      setRemoteLibraries(remoteResult.results)
    } catch (exc) {
      const message = exc instanceof Error ? exc.message : '无法读取媒体库。'
      setLoadError(message)
      showToast('error', message)
    }
    finally { setIsLoading(false) }
  }

  function openCreate() {
    setFormMode('create'); setEditingId(null)
    setForm(emptyLibraryForm()); setSelectedRemoteIds([]); setShowForm(true)
  }

  function openEdit(lib: MediaLibraryResponse) {
    setFormMode('edit'); setEditingId(lib.id)
    setForm({ id: lib.id, name: lib.name, media_type: lib.media_type, enabled: lib.enabled, connection_id: lib.connection_id, base_path: lib.base_path })
    setSelectedRemoteIds(remoteLibraries.filter((item) => item.target_library_id === lib.id).map((item) => item.id))
    setShowForm(true)
  }

  async function saveLibrary() {
    setIsSaving(true)
    try {
      const payload = { name: form.name.trim(), media_type: form.media_type, enabled: form.enabled, connection_id: form.connection_id.trim(), base_path: normalizeLibraryPath(form.base_path) }
      if (formMode === 'create') {
        await api.post('/media-libraries/create', { id: newUuid(), ...payload })
      } else {
        await api.post(`/media-libraries/${encodeURIComponent(editingId!)}/update`, payload)
        await saveRemoteBindings(editingId!, selectedRemoteIds)
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
      await loadAll()
    } catch (exc) { showToast('error', exc instanceof Error ? exc.message : '测试失败。') }
  }

  async function testLibraryInForm() {
    setIsTesting(true)
    try {
      const payload = { id: formMode === 'edit' && editingId ? editingId : newUuid(), name: form.name.trim(), media_type: form.media_type, enabled: form.enabled, connection_id: form.connection_id.trim(), base_path: normalizeLibraryPath(form.base_path) }
      const result = await api.post<{ ok: boolean; error_code: string | null; error_message: string | null }>('/media-libraries/test-new', payload)
      showToast(result.ok ? 'success' : 'error', result.ok ? '媒体库目录测试通过。' : `${result.error_code || 'TEST_FAILED'}：${result.error_message || '测试失败。'}`)
    } catch (exc) { showToast('error', exc instanceof Error ? exc.message : '测试失败。') }
    finally { setIsTesting(false) }
  }

  function openBrowse(lib: MediaLibraryResponse) {
    const conn = connections.find((c) => c.id === lib.connection_id)
    if (!conn) { showToast('error', '未找到关联的 SMB 连接。'); return }
    setBrowseConnectionId(conn.id)
    setBrowseLibraryName(lib.name)
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
      setBrowseResult(result); setBrowsePath(normalizeBrowsePath(result.path))
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

  function addRemoteBinding(remoteId: string) {
    setSelectedRemoteIds((current) => [...new Set([...current, remoteId])])
  }

  function removeRemoteBinding(remoteId: string) {
    setSelectedRemoteIds((current) => current.filter((id) => id !== remoteId))
  }

  async function saveRemoteBindings(localLibraryId: string, nextRemoteIds: string[]) {
    const candidates = remoteLibraries.filter((remote) => remote.media_type === form.media_type)
    await Promise.all(candidates.map((remote) => {
      const nextTargetId = nextRemoteIds.includes(remote.id) ? localLibraryId : remote.target_library_id === localLibraryId ? null : remote.target_library_id
      if (nextTargetId === remote.target_library_id) return Promise.resolve()
      return api.post(`/remote-media-libraries/${encodeURIComponent(remote.id)}/update`, {
        name: remote.name,
        media_type: remote.media_type,
        enabled: remote.enabled,
        connection_id: remote.connection_id,
        base_path: remote.base_path,
        target_library_id: nextTargetId,
        scan_interval_seconds: remote.scan_interval_seconds,
        stable_seconds: remote.stable_seconds,
        delete_source_after_success: remote.delete_source_after_success,
        delete_empty_source_dirs: remote.delete_empty_source_dirs,
      })
    }))
  }

  const totalPages = Math.max(1, Math.ceil(totalCount / pageSize))
  const connName = (id: string) => connections.find((c) => c.id === id)?.name || id
  const showEmpty = !isLoading && !loadError && libraries.length === 0
  const showList = libraries.length > 0

  return (
    <section className="lb-page" aria-labelledby="libraries-title">
      <Card className="lb-overview">
        <div className="lb-overview-head">
          <div>
            <p className="ui-eyebrow">本地媒体库</p>
            <h2 id="libraries-title">本地媒体库管理</h2>
            <p className="lb-overview-lead">
              管理 movie / series / unclassified 本地媒体库目录绑定。每个媒体库绑定一个 SMB 连接及其共享内的子路径，
              随后可被远程媒体库作为同步目标引用。
            </p>
          </div>
          <div className="lb-overview-actions">
            <Button variant="ghost" disabled={isLoading} onClick={() => void loadAll()}>
              {isLoading ? '读取中' : '重新读取'}
            </Button>
            <Button variant="primary" onClick={openCreate}>新增本地媒体库</Button>
          </div>
        </div>
      </Card>

      <Card emphasis="sunken" className="lb-table-card">
        <div className="lb-table-head">
          <p className="ui-eyebrow">媒体库</p>
          <span className="lb-table-count">
            {totalCount} 个{totalPages > 1 ? ` · 第 ${page} / ${totalPages} 页` : ''}
          </span>
        </div>

        {isLoading && libraries.length === 0 ? (
          <UILoadingState message="正在读取媒体库…" />
        ) : null}

        {loadError ? (
          <UIErrorState
            message="无法读取媒体库"
            sub={loadError}
            action={<Button variant="secondary" onClick={() => void loadAll()}>重试</Button>}
          />
        ) : null}

        {showEmpty ? (
          <UIEmptyState
            message="暂无媒体库"
            sub="点击上方 新增本地媒体库 创建第一个本地媒体库。"
            action={<Button variant="primary" onClick={openCreate}>新增本地媒体库</Button>}
          />
        ) : null}

        {showList ? (
          <>
            <div className="lb-table" role="table" aria-label="媒体库列表">
              <div className="lb-table-header" role="row">
                <span role="columnheader">状态</span>
                <span role="columnheader">名称</span>
                <span role="columnheader">类型</span>
                <span role="columnheader">路径</span>
                <span role="columnheader">绑定</span>
                <span role="columnheader" aria-label="操作" />
              </div>
              {libraries.map((lib) => {
                const bindingStatus = lib.bound_remote_libraries.length === 0 ? '未绑定' : null
                const typeLabel =
                  lib.media_type === 'movie' ? '电影'
                  : lib.media_type === 'series' ? '剧集'
                  : '未分类'
                const typeTone: StatusTone =
                  lib.media_type === 'movie' ? 'info'
                  : lib.media_type === 'series' ? 'running'
                  : 'paused'
                const bindingPreview = remoteBindingPreview(lib.bound_remote_libraries)
                return (
                  <div className="lb-row" key={lib.id} role="row">
                    <span className="lb-col-status" role="cell">
                      <StatusStack
                        enabled={lib.enabled}
                        bindingStatus={bindingStatus}
                        lastTestOk={lib.last_test_ok}
                        errorCode={lib.last_test_error_code}
                        errorMessage={lib.last_test_error_message}
                        onDetail={(message) => showToast('error', message)}
                      />
                    </span>
                    <span className="lb-col-title" role="cell">
                      <strong title={lib.name}>{lib.name}</strong>
                      <small title={lib.id}>{lib.id}</small>
                    </span>
                    <span className="lb-col-type" role="cell">
                      <StatusBadge tone={typeTone}>{typeLabel}</StatusBadge>
                    </span>
                    <span className="lb-col-path" role="cell">
                      <span title={connName(lib.connection_id)}>{connName(lib.connection_id)}</span>
                      <code title={lib.base_path}>{lib.base_path || '/'}</code>
                    </span>
                    <span className="lb-col-bindings" role="cell">
                      {lib.bound_remote_libraries.length > 0 ? (
                        <span
                          className="lb-bindings-count"
                          title={lib.bound_remote_libraries.join('、')}
                        >
                          {bindingPreview}
                        </span>
                      ) : (
                        <span className="lb-bindings-empty">—</span>
                      )}
                    </span>
                    <div className="lb-row-actions" role="cell">
                      <Button variant="ghost" size="sm" onClick={() => openEdit(lib)}>编辑</Button>
                      <Button variant="ghost" size="sm" onClick={() => void testLibrary(lib)}>测试</Button>
                      <Button variant="ghost" size="sm" onClick={() => openBrowse(lib)}>浏览</Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        disabled={isSaving}
                        onClick={() => void toggleEnabled(lib)}
                      >
                        {lib.enabled ? '禁用' : '启用'}
                      </Button>
                      <Button variant="danger" size="sm" onClick={() => openDeleteModal(lib)}>删除</Button>
                    </div>
                  </div>
                )
              })}
            </div>
            <PaginationControls page={page} totalPages={totalPages} pageSize={pageSize} onPageChange={setPage} onPageSizeChange={setPageSize} />
          </>
        ) : null}
      </Card>

      {showForm ? (
        <LibraryEditModal
          mode={formMode}
          form={form}
          connections={connections}
          remoteLibraries={remoteLibraries}
          selectedRemoteIds={selectedRemoteIds}
          isSaving={isSaving}
          isTesting={isTesting}
          onFieldChange={updateForm}
          onRemoteBindingAdd={addRemoteBinding}
          onRemoteBindingRemove={removeRemoteBinding}
          onClose={() => setShowForm(false)}
          onTest={() => void testLibraryInForm()}
          onSubmit={() => void saveLibrary()}
        />
      ) : null}

      {showDelete && deleteTarget ? (
        <LibraryDeleteModal
          target={deleteTarget}
          isSaving={isSaving}
          onClose={() => setShowDelete(false)}
          onAction={(action) => void executeDelete(action)}
        />
      ) : null}

      {showBrowse ? (
        <LibraryBrowseModal
          libraryName={browseLibraryName}
          connectionName={browseConnectionId ? connName(browseConnectionId) : ''}
          browsePath={browsePath}
          browseResult={browseResult}
          isBrowsing={isBrowsing}
          onPathChange={setBrowsePath}
          onBrowse={() => void doBrowse()}
          onOpenEntry={(path) => void doBrowse(path, browseConnectionId)}
          onClose={() => {
            setShowBrowse(false)
            setBrowseResult(null)
            setBrowsePath('')
            setBrowseConnectionId(null)
            setBrowseLibraryName('')
          }}
        />
      ) : null}
    </section>
  )
}

function LibraryEditModal({
  mode,
  form,
  connections,
  remoteLibraries,
  selectedRemoteIds,
  isSaving,
  isTesting,
  onFieldChange,
  onRemoteBindingAdd,
  onRemoteBindingRemove,
  onClose,
  onTest,
  onSubmit,
}: {
  mode: 'create' | 'edit'
  form: MediaLibraryFormState
  connections: SmbConnectionResponse[]
  remoteLibraries: RemoteMediaLibraryResponse[]
  selectedRemoteIds: string[]
  isSaving: boolean
  isTesting: boolean
  onFieldChange: (key: keyof MediaLibraryFormState, value: string | boolean) => void
  onRemoteBindingAdd: (remoteId: string) => void
  onRemoteBindingRemove: (remoteId: string) => void
  onClose: () => void
  onTest: () => void
  onSubmit: () => void
}) {
  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      window.removeEventListener('keydown', onKey)
      document.body.style.overflow = prev
    }
  }, [onClose])

  const availableRemoteLibraries = remoteLibraries.filter((remote) => !selectedRemoteIds.includes(remote.id))
  const selectedRemoteLibraries = remoteLibraries.filter((remote) => selectedRemoteIds.includes(remote.id))

  return (
    <div
      className="lb-modal-overlay"
      role="dialog"
      aria-modal="true"
      aria-labelledby="lb-form-title"
    >
      <div className="lb-modal" onClick={(event) => event.stopPropagation()}>
        <header className="lb-modal-head">
          <div>
            <p className="ui-eyebrow">{mode === 'create' ? '新增' : '编辑'}</p>
            <h3 id="lb-form-title">{mode === 'create' ? '创建媒体库' : '编辑媒体库'}</h3>
          </div>
          <Button variant="ghost" size="sm" onClick={onClose} aria-label="关闭">×</Button>
        </header>
        <form
          className="lb-modal-body"
          onSubmit={(event) => {
            event.preventDefault()
            onSubmit()
          }}
        >
          <div className="lb-form-grid">
            <Field label="名称" helper="页面展示名称。" htmlFor="lb-f-name">
              <input
                id="lb-f-name"
                type="text"
                value={form.name}
                required
                onChange={(event) => onFieldChange('name', event.target.value)}
              />
            </Field>
            <Field label="媒体类型" helper="电影、剧集或未分类。" htmlFor="lb-f-type">
              <select
                id="lb-f-type"
                value={form.media_type}
                onChange={(event) => onFieldChange('media_type', event.target.value)}
              >
                <option value="movie">电影</option>
                <option value="series">剧集</option>
                <option value="unclassified">未分类</option>
              </select>
            </Field>
            <Field label="SMB 连接" helper="绑定到某个已配置的 SMB 连接。" htmlFor="lb-f-conn">
              <select
                id="lb-f-conn"
                value={form.connection_id}
                onChange={(event) => onFieldChange('connection_id', event.target.value)}
                required
              >
                <option value="">选择连接</option>
                {connections.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name} ({c.host}/{c.share})
                  </option>
                ))}
              </select>
            </Field>
            <Field
              label="目录路径"
              helper="相对于 SMB 连接 Base Path 的子目录。"
              htmlFor="lb-f-path"
              className="lb-field-wide"
            >
              <input
                id="lb-f-path"
                type="text"
                value={form.base_path}
                required
                onChange={(event) => onFieldChange('base_path', event.target.value)}
              />
            </Field>
          </div>
          <div className="lb-modal-toggle">
            <label>
              <input
                type="checkbox"
                checked={form.enabled}
                onChange={(event) => onFieldChange('enabled', event.target.checked)}
              />
              <span>启用媒体库</span>
            </label>
            <small>禁用后远程媒体库不会向该目录写入。</small>
          </div>
          {mode === 'edit' ? (
            <div className="lb-remote-picker">
              <div className="lb-remote-picker-head">
                <span className="ui-eyebrow">绑定远程媒体库</span>
                <p>从左侧添加到右侧，保存后更新这些远程媒体库的同步目标。</p>
              </div>
              <div className="lb-remote-picker-grid">
                <div className="lb-remote-list">
                  <div className="lb-remote-list-title">
                    <strong>全部远程媒体库</strong>
                    <span>{availableRemoteLibraries.length}</span>
                  </div>
                  {availableRemoteLibraries.length === 0 ? (
                    <p className="lb-bindings-empty">没有可添加的远程媒体库。</p>
                  ) : (
                    availableRemoteLibraries.map((remote) => {
                      const typeMismatch = remote.media_type !== form.media_type
                      return (
                        <div className="lb-remote-item" key={remote.id} data-disabled={typeMismatch || undefined}>
                          <div>
                            <strong>{remote.name}</strong>
                            <small>{remote.base_path} · {remote.media_type} · {remote.enabled ? '已启用' : '已禁用'}</small>
                          </div>
                          <Button variant="ghost" size="sm" disabled={typeMismatch} onClick={() => onRemoteBindingAdd(remote.id)} type="button">
                            添加 →
                          </Button>
                        </div>
                      )
                    })
                  )}
                </div>
                <div className="lb-remote-list">
                  <div className="lb-remote-list-title">
                    <strong>已绑定到当前媒体库</strong>
                    <span>{selectedRemoteLibraries.length}</span>
                  </div>
                  {selectedRemoteLibraries.length === 0 ? (
                    <p className="lb-bindings-empty">尚未绑定远程媒体库。</p>
                  ) : (
                    selectedRemoteLibraries.map((remote) => (
                      <div className="lb-remote-item" key={remote.id}>
                        <div>
                          <strong>{remote.name}</strong>
                          <small>{remote.base_path} · {remote.media_type} · {remote.enabled ? '已启用' : '已禁用'}</small>
                        </div>
                        <Button variant="ghost" size="sm" onClick={() => onRemoteBindingRemove(remote.id)} type="button">
                          ← 移除
                        </Button>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>
          ) : null}
          <footer className="lb-modal-actions">
            <Button variant="ghost" onClick={onClose} type="button">取消</Button>
            <Button variant="secondary" onClick={onTest} disabled={isTesting} type="button">
              {isTesting ? '测试中…' : '测试连接'}
            </Button>
            <Button variant="primary" disabled={isSaving} type="submit">
              {isSaving ? '保存中…' : mode === 'create' ? '创建' : '保存'}
            </Button>
          </footer>
        </form>
      </div>
    </div>
  )
}

function LibraryDeleteModal({
  target,
  isSaving,
  onClose,
  onAction,
}: {
  target: MediaLibraryResponse
  isSaving: boolean
  onClose: () => void
  onAction: (action: 'delete' | 'unbind' | 'cancel') => void
}) {
  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  const hasBindings = target.bound_remote_libraries.length > 0

  return (
    <div
      className="lb-modal-overlay"
      role="dialog"
      aria-modal="true"
      aria-labelledby="lb-del-title"
      onClick={onClose}
    >
      <div className="lb-modal lb-modal-sm" onClick={(event) => event.stopPropagation()}>
        <header className="lb-modal-head">
          <div>
            <p className="ui-eyebrow">删除</p>
            <h3 id="lb-del-title">删除媒体库</h3>
          </div>
          <Button variant="ghost" size="sm" onClick={onClose} aria-label="关闭">×</Button>
        </header>
        <div className="lb-modal-body">
          <p className="lb-danger-lede">
            确定要删除 <strong>{target.name}</strong> 吗？
          </p>
          {hasBindings ? (
            <div className="lb-bindings">
              <div className="lb-binding-row">
                <span className="ui-eyebrow">关联的远程媒体库</span>
                <p>{target.bound_remote_libraries.join('、')}</p>
              </div>
              <p className="lb-danger-hint">
                选择 <em>仅解绑</em> 会保留以上远程媒体库但解除对该本地媒体库的引用；
                选择 <em>删除所有</em> 将连同上述远程媒体库一起移除。
              </p>
            </div>
          ) : (
            <p className="lb-danger-hint">该媒体库没有被任何远程媒体库引用，可以安全删除。</p>
          )}
        </div>
        <footer className="lb-modal-actions">
          <Button variant="ghost" onClick={() => onAction('cancel')} type="button">取消</Button>
          {hasBindings ? (
            <Button
              variant="secondary"
              onClick={() => onAction('unbind')}
              disabled={isSaving}
              type="button"
            >
              仅解绑
            </Button>
          ) : null}
          <Button
            variant="danger"
            onClick={() => onAction('delete')}
            disabled={isSaving}
            type="button"
          >
            {isSaving ? '删除中…' : hasBindings ? '删除所有' : '删除'}
          </Button>
        </footer>
      </div>
    </div>
  )
}

function LibraryBrowseModal({
  libraryName,
  connectionName,
  browsePath,
  browseResult,
  isBrowsing,
  onPathChange,
  onBrowse,
  onOpenEntry,
  onClose,
}: {
  libraryName: string
  connectionName: string
  browsePath: string
  browseResult: StorageBrowseResponse | null
  isBrowsing: boolean
  onPathChange: (value: string) => void
  onBrowse: () => void
  onOpenEntry: (path: string) => void
  onClose: () => void
}) {
  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      window.removeEventListener('keydown', onKey)
      document.body.style.overflow = prev
    }
  }, [onClose])

  return (
    <div
      className="lb-modal-overlay"
      role="dialog"
      aria-modal="true"
      aria-labelledby="lb-browse-title"
      onClick={onClose}
    >
      <div className="lb-modal lb-modal-lg" onClick={(event) => event.stopPropagation()}>
        <header className="lb-modal-head">
          <div>
            <p className="ui-eyebrow">浏览</p>
            <h3 id="lb-browse-title">目录浏览</h3>
            {libraryName || connectionName ? (
              <p className="lb-browse-subtitle">
                {libraryName}
                {connectionName ? <> · {connectionName}</> : null}
              </p>
            ) : null}
          </div>
          <Button variant="ghost" size="sm" onClick={onClose} aria-label="关闭">×</Button>
        </header>
        <form
          className="lb-modal-body lb-browse-body"
          onSubmit={(event) => {
            event.preventDefault()
            onBrowse()
          }}
        >
          <div className="lb-browse-toolbar">
            <Field
              label="路径"
              htmlFor="lb-browse-path"
              helper={<>相对于 SMB 连接 Base Path 的目录。按 <Kbd>Enter</Kbd> 浏览。</>}
            >
              <input
                id="lb-browse-path"
                type="text"
                value={browsePath}
                placeholder="例如 Movies"
                onChange={(event) => onPathChange(event.target.value)}
              />
            </Field>
            <Button variant="primary" type="submit" disabled={isBrowsing}>
              {isBrowsing ? '浏览中…' : '浏览'}
            </Button>
          </div>
          {isBrowsing && !browseResult ? (
            <UILoadingState message="正在读取目录…" />
          ) : browseResult ? (
            <StorageBrowser result={browseResult} onOpen={onOpenEntry} />
          ) : (
            <UIEmptyState
              message="输入路径后浏览 SMB 目录"
              sub="空值表示浏览连接 Base Path 下的根目录。"
            />
          )}
        </form>
      </div>
    </div>
  )
}

function RemoteLibrariesPanel({ showToast }: { showToast: (type: 'success' | 'error' | 'info', message: string) => void }) {
  const [libraries, setLibraries] = useState<RemoteMediaLibraryResponse[]>([])
  const [connections, setConnections] = useState<SmbConnectionResponse[]>([])
  const [localLibraries, setLocalLibraries] = useState<MediaLibraryResponse[]>([])
  const [totalCount, setTotalCount] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [isLoading, setIsLoading] = useState(false)
  const [loadError, setLoadError] = useState<string | null>(null)

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

  useEffect(() => { void loadAll() }, [page, pageSize])

  async function loadAll() {
    setIsLoading(true)
    setLoadError(null)
    try {
      const [libResult, connResult, localResult] = await Promise.all([
        api.get<RemoteMediaLibraryListResponse>(`/remote-media-libraries?page=${page}&page_size=${pageSize}`),
        api.get<SmbConnectionListResponse>('/storage/smb-connections?page_size=100'),
        api.get<MediaLibraryListResponse>('/media-libraries?page_size=100'),
      ])
      setLibraries(libResult.results); setTotalCount(libResult.count)
      setConnections(connResult.results)
      setLocalLibraries(localResult.results)
    } catch (exc) {
      const message = exc instanceof Error ? exc.message : '无法读取远程媒体库。'
      setLoadError(message)
      showToast('error', message)
    }
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
        await api.post('/remote-media-libraries/create', { id: newUuid(), ...payload })
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
      await loadAll()
    } catch (exc) { showToast('error', exc instanceof Error ? exc.message : '测试失败。') }
  }

  async function testLibraryInForm() {
    setIsTesting(true)
    try {
      const payload = {
        id: formMode === 'edit' && editingId ? editingId : newUuid(), name: form.name.trim(), media_type: form.media_type, enabled: form.enabled,
        connection_id: form.connection_id.trim(), base_path: form.base_path.trim() || '/',
        target_library_id: form.target_library_id || null,
        scan_interval_seconds: Number(form.scan_interval_seconds) || 60,
        stable_seconds: Number(form.stable_seconds) || 120,
        delete_source_after_success: triStateToBoolean(form.delete_source_after_success),
        delete_empty_source_dirs: triStateToBoolean(form.delete_empty_source_dirs),
      }
      const result = await api.post<{ ok: boolean; error_code: string | null; error_message: string | null }>('/remote-media-libraries/test-new', payload)
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
      setBrowseResult(result); setBrowsePath(normalizeBrowsePath(result.path))
    } catch (exc) { setBrowseResult(null); showToast('error', exc instanceof Error ? exc.message : '浏览失败。') }
    finally { setIsBrowsing(false) }
  }

  async function triggerScan(lib: RemoteMediaLibraryResponse) {
    try {
      await api.post('/sync/scan', { remote_library_id: lib.id })
      showToast('success', `${lib.name} 扫描完成。`)
    } catch (exc) { showToast('error', exc instanceof Error ? exc.message : '扫描失败。') }
  }

  async function triggerScanAll() {
    try {
      const result = await api.post<DtlScanResponse>('/sync/scan', {})
      showToast('success', `扫描完成：扫描 ${result.scanned_bindings} 个绑定，发现 ${result.discovered_count} 个文件。`)
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
  const showEmpty = !isLoading && !loadError && libraries.length === 0
  const showList = !loadError && libraries.length > 0

  return (
    <section className="rm-page" aria-labelledby="remote-libraries-title">
      <Card className="rm-overview">
      <div className="rm-overview-head">
        <div>
          <p className="ui-eyebrow">远程媒体库</p>
          <h2 id="remote-libraries-title">远程媒体库管理</h2>
          <p className="rm-overview-lead">管理远程媒体库目录绑定，配置同步目标和扫描参数。</p>
        </div>
        <div className="rm-overview-actions">
          <Button variant="ghost" disabled={isLoading} onClick={() => void loadAll()}>{isLoading ? '读取中' : '重新读取'}</Button>
          <Button variant="secondary" disabled={isLoading || libraries.length === 0} onClick={() => void triggerScanAll()}>扫描全部媒体库</Button>
          <Button variant="primary" onClick={openCreate}>新增远程媒体库</Button>
        </div>
      </div>
      </Card>

      <Card emphasis="sunken" className="rm-table-card">
      {isLoading && libraries.length === 0 ? <UILoadingState message="正在读取远程媒体库…" /> : null}
      {loadError ? <UIErrorState message="无法读取远程媒体库" sub={loadError} action={<Button variant="secondary" onClick={() => void loadAll()}>重试</Button>} /> : null}

      <div className="rm-list-section">
        <div className="rm-table-head">
          <p className="ui-eyebrow">远程媒体库</p>
          <span className="rm-table-count">
            {totalCount} 个{totalPages > 1 ? ` · 第 ${page} / ${totalPages} 页` : ''}
          </span>
        </div>
        {showEmpty ? <UIEmptyState message="暂无远程媒体库" sub="点击上方 新增远程媒体库 创建。" action={<Button variant="primary" onClick={openCreate}>新增远程媒体库</Button>} /> : null}
        {showList ? (
          <div className="rm-table" role="table" aria-label="远程媒体库列表">
            <div className="rm-table-header" role="row">
              <span role="columnheader">状态</span>
              <span role="columnheader">名称</span>
              <span role="columnheader">类型</span>
              <span role="columnheader">路径</span>
              <span role="columnheader">绑定</span>
              <span role="columnheader" aria-label="操作" />
            </div>
            {libraries.map((lib) => {
              const typeLabel = dtlMediaTypeLabel(lib.media_type)
              const typeTone: StatusTone =
                lib.media_type === 'movie' ? 'info'
                : lib.media_type === 'series' ? 'running'
                : 'paused'
              const targetName = lib.target_library_id ? lib.target_library_name || libName(lib.target_library_id) : ''
              return (
                <div className="rm-row" key={lib.id} role="row">
                  <span className="rm-col-status" role="cell">
                    <StatusStack
                      enabled={lib.enabled}
                      bindingStatus={targetName ? null : '未绑定'}
                      lastTestOk={lib.last_test_ok}
                      errorCode={lib.last_test_error_code}
                      errorMessage={lib.last_test_error_message}
                      onDetail={(message) => showToast('error', message)}
                    />
                  </span>
                  <span className="rm-col-title" role="cell">
                    <strong title={lib.name}>{lib.name}</strong>
                    <small title={lib.id}>{lib.id}</small>
                  </span>
                  <span className="rm-col-type" role="cell">
                    <StatusBadge tone={typeTone}>{typeLabel}</StatusBadge>
                  </span>
                  <span className="rm-col-path" role="cell">
                    <span title={connName(lib.connection_id)}>{connName(lib.connection_id)}</span>
                    <code title={lib.base_path}>{lib.base_path || '/'}</code>
                  </span>
                  <span className="rm-col-bindings" role="cell">
                    {targetName ? (
                      <span className="rm-bindings-count" title={targetName}>{targetName}</span>
                    ) : (
                      <span className="rm-bindings-empty">—</span>
                    )}
                  </span>
                  <div className="rm-row-actions" role="cell">
                    <Button variant="ghost" size="sm" onClick={() => openEdit(lib)}>编辑</Button>
                    <Button variant="ghost" size="sm" onClick={() => void testLibrary(lib)}>测试</Button>
                    <Button variant="ghost" size="sm" onClick={() => openBrowse(lib)}>浏览</Button>
                    {lib.target_library_id ? <Button variant="ghost" size="sm" onClick={() => void triggerScan(lib)}>扫描</Button> : null}
                    <Button variant="ghost" size="sm" onClick={() => void toggleEnabled(lib)}>{lib.enabled ? '禁用' : '启用'}</Button>
                    <Button variant="danger" size="sm" onClick={() => openDeleteModal(lib)}>删除</Button>
                  </div>
                </div>
              )
            })}
          </div>
        ) : null}
        {showList ? (
          <PaginationControls page={page} totalPages={totalPages} pageSize={pageSize} onPageChange={setPage} onPageSizeChange={setPageSize} />
        ) : null}
      </div>
      </Card>

      {showForm && (
        <div className="rm-modal-overlay">
          <div className="rm-modal rm-modal-lg" onClick={(e) => e.stopPropagation()}>
            <header className="rm-modal-head">
              <div>
                <p className="ui-eyebrow">{formMode === 'create' ? '新增' : '编辑'}</p>
                <h3>{formMode === 'create' ? '创建远程媒体库' : '编辑远程媒体库'}</h3>
              </div>
              <Button variant="ghost" size="sm" onClick={() => setShowForm(false)} aria-label="关闭">×</Button>
            </header>
            <div className="rm-modal-body">
            <div className="rm-form-grid">
              <TextField helper="页面展示名称。" label="名称" onChange={(v) => updateForm('name', v)} required value={form.name} />
              <Field label="媒体类型" helper="电影、剧集或未分类。"><select value={form.media_type} onChange={(e) => updateForm('media_type', e.target.value)}>
                <option value="movie">电影</option><option value="series">剧集</option><option value="unclassified">未分类</option>
              </select></Field>
              <Field label="SMB 连接" helper="绑定到某个已配置的 SMB 连接。"><select value={form.connection_id} onChange={(e) => updateForm('connection_id', e.target.value)}>
                <option value="">选择连接</option>{connections.map((c) => <option key={c.id} value={c.id}>{c.name} ({c.host}/{c.share})</option>)}
              </select></Field>
              <TextField helper="相对于 SMB 连接 Base Path 的远程目录。" label="目录路径" onChange={(v) => updateForm('base_path', v)} required value={form.base_path} />
            </div>
            <div className="rm-section-heading"><p className="ui-eyebrow">同步配置</p></div>
            <div className="rm-form-grid">
              <Field label="同步目标本地媒体库" helper="绑定后 Worker 将自动扫描并下载到此本地媒体库。"><select value={form.target_library_id} onChange={(e) => updateForm('target_library_id', e.target.value)}>
                <option value="">不绑定（禁用自动同步）</option>{localLibraries.map((l) => <option key={l.id} value={l.id}>{l.name} ({dtlMediaTypeLabel(l.media_type)})</option>)}
              </select></Field>
              <TextField helper="两次扫描之间的间隔秒数。" label="扫描间隔(秒)" onChange={(v) => updateForm('scan_interval_seconds', v)} type="number" value={form.scan_interval_seconds} />
              <TextField helper="文件 size/mtime 不变超过该秒数后才创建任务。" label="稳定等待(秒)" onChange={(v) => updateForm('stable_seconds', v)} type="number" value={form.stable_seconds} />
              <Field label="成功后删除来源" helper="为空时使用全局配置。"><select value={form.delete_source_after_success} onChange={(e) => updateForm('delete_source_after_success', e.target.value)}>
                <option value="">使用全局默认</option><option value="true">删除</option><option value="false">保留</option>
              </select></Field>
              <Field label="成功后删除空目录" helper="为空时使用全局配置。"><select value={form.delete_empty_source_dirs} onChange={(e) => updateForm('delete_empty_source_dirs', e.target.value)}>
                <option value="">使用全局默认</option><option value="true">删除</option><option value="false">保留</option>
              </select></Field>
            </div>
            </div>
            <footer className="rm-modal-actions">
              <Button variant="ghost" onClick={() => setShowForm(false)}>取消</Button>
              <Button variant="secondary" disabled={isTesting} onClick={() => void testLibraryInForm()}>{isTesting ? '测试中…' : '测试连接'}</Button>
              <Button variant="primary" disabled={isSaving} onClick={() => void saveLibrary()}>{isSaving ? '保存中…' : formMode === 'create' ? '创建' : '保存'}</Button>
            </footer>
          </div>
        </div>
      )}

      {showBrowse && (
        <div className="rm-modal-overlay">
          <div className="rm-modal rm-modal-lg" onClick={(e) => e.stopPropagation()}>
            <header className="rm-modal-head">
              <div><p className="ui-eyebrow">浏览</p><h3>目录浏览</h3></div>
              <Button variant="ghost" size="sm" onClick={() => { setShowBrowse(false); setBrowseResult(null); setBrowsePath('') }} aria-label="关闭">×</Button>
            </header>
            <form className="rm-modal-body rm-browse-body" onSubmit={(event) => { event.preventDefault(); void doBrowse() }}>
              <div className="rm-browse-toolbar">
              <Field label="路径" helper={<>相对于 SMB 连接 Base Path 的目录。按 <Kbd>Enter</Kbd> 浏览。</>}>
                <input onChange={(event) => setBrowsePath(event.target.value)} placeholder="例如 Movies" type="text" value={browsePath} />
              </Field>
              <Button variant="primary" disabled={isBrowsing} type="submit">{isBrowsing ? '浏览中…' : '浏览'}</Button>
              </div>
              {isBrowsing && !browseResult ? <UILoadingState message="正在读取目录…" /> : null}
              {browseResult ? <StorageBrowser result={browseResult} onOpen={(path) => void doBrowse(path)} /> : <UIEmptyState message="输入路径后浏览目录" sub="空值表示浏览连接 Base Path 下的根目录。" />}
            </form>
          </div>
        </div>
      )}

      {showDelete && deleteTarget && (
        <div className="rm-modal-overlay">
          <div className="rm-modal rm-modal-sm" onClick={(e) => e.stopPropagation()}>
            <header className="rm-modal-head">
              <div><p className="ui-eyebrow">删除</p><h3>删除远程媒体库</h3></div>
              <Button variant="ghost" size="sm" onClick={() => setShowDelete(false)} aria-label="关闭">×</Button>
            </header>
            <div className="rm-modal-body">
              <p className="rm-danger-lede">确认删除远程媒体库 <strong>{deleteTarget.name}</strong>？关联的同步记录将被清理。</p>
              <p className="rm-danger-hint">删除远程媒体库不会删除 SMB 来源目录中的文件。</p>
            </div>
            <footer className="rm-modal-actions">
              <Button variant="ghost" onClick={() => void executeDelete('cancel')}>取消</Button>
              <Button variant="danger" disabled={isSaving} onClick={() => void executeDelete('delete')}>{isSaving ? '删除中…' : '删除'}</Button>
            </footer>
          </div>
        </div>
      )}

      <ApiClientPreview />
    </section>
  )
}

function SourcesPanel() {
  const [sources, setSources] = useState<SourceResponse[]>([])
  const [totalCount, setTotalCount] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [isLoading, setIsLoading] = useState(false)
  const [loadError, setLoadError] = useState<string | null>(null)

  const [drawerMode, setDrawerMode] = useState<'create' | 'edit' | null>(null)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [form, setForm] = useState<SourceFormState>(emptySourceForm())
  const [drawerError, setDrawerError] = useState<string | null>(null)
  const [isSaving, setIsSaving] = useState(false)

  const [testState, setTestState] = useState<Record<string, 'running' | 'ok' | 'error'>>({})
  const [togglingIds, setTogglingIds] = useState<Record<string, true>>({})

  // 最近一次测试的结果 detail（可展示条目 / 错误详情），key = source.id
  const [testResults, setTestResults] = useState<Record<string, SourceTestResponse>>({})
  const [expandedTestId, setExpandedTestId] = useState<string | null>(null)

  useEffect(() => {
    void loadSources()
  }, [page, pageSize])

  const editingSource =
    drawerMode === 'edit' && editingId
      ? sources.find((source) => source.id === editingId) || null
      : null

  async function loadSources() {
    setIsLoading(true)
    setLoadError(null)
    try {
      const response = await api.get<SourceListResponse>(`/sources?page=${page}&page_size=${pageSize}`)
      setSources(response.results)
      setTotalCount(response.count)
    } catch (exc) {
      setSources([])
      setLoadError(exc instanceof Error ? exc.message : '无法读取媒体源。')
    } finally {
      setIsLoading(false)
    }
  }

  function openCreate() {
    setDrawerMode('create')
    setEditingId(null)
    setForm(emptySourceForm())
    setDrawerError(null)
  }

  function openEdit(source: SourceResponse) {
    setDrawerMode('edit')
    setEditingId(source.id)
    setForm(sourceFormFromResponse(source))
    setDrawerError(null)
  }

  function closeDrawer() {
    setDrawerMode(null)
    setEditingId(null)
    setDrawerError(null)
  }

  async function saveSource() {
    const editable = drawerMode === 'create' || editingSource?.type !== 'code'
    if (!editable) {
      setDrawerError('代码型 Source Adapter 只能只读展示，不能在线编辑。')
      return
    }
    setIsSaving(true)
    setDrawerError(null)
    try {
      const config = parseSourceConfig(form.config_json)
      const payload = {
        name: form.name.trim(),
        enabled: form.enabled,
        legal_note: form.legal_note.trim() || null,
        trust_level: Number(form.trust_level) || 1,
        config_json: config,
      }
      if (drawerMode === 'create') {
        await api.post<SourceResponse>('/sources/create', {
          ...payload,
          id: newUuid(),
          type: form.type,
        })
      } else if (editingId) {
        await api.post<SourceResponse>(
          `/sources/${encodeURIComponent(editingId)}/update`,
          payload,
        )
      }
      closeDrawer()
      await loadSources()
    } catch (exc) {
      setDrawerError(exc instanceof Error ? exc.message : '保存媒体源失败。')
    } finally {
      setIsSaving(false)
    }
  }

  async function toggleSource(source: SourceResponse) {
    if (source.type === 'code') return
    const next = !source.enabled
    if (!window.confirm(`确认${next ? '启用' : '禁用'}媒体源 ${source.name}？`)) return
    setTogglingIds((prev) => ({ ...prev, [source.id]: true }))
    try {
      const action = next ? 'enable' : 'disable'
      await api.post<SourceResponse>(
        `/sources/${encodeURIComponent(source.id)}/${action}`,
      )
      await loadSources()
    } catch (exc) {
      window.alert(exc instanceof Error ? exc.message : '切换媒体源状态失败。')
    } finally {
      setTogglingIds((prev) => {
        const { [source.id]: _dropped, ...rest } = prev
        return rest
      })
    }
  }

  async function testSource(source: SourceResponse) {
    setTestState((prev) => ({ ...prev, [source.id]: 'running' }))
    try {
      const result = await api.post<SourceTestResponse>(
        `/sources/${encodeURIComponent(source.id)}/test`,
      )
      setTestResults((prev) => ({ ...prev, [source.id]: result }))
      setTestState((prev) => ({ ...prev, [source.id]: result.ok ? 'ok' : 'error' }))
      setExpandedTestId(source.id)
    } catch (exc) {
      const msg = exc instanceof Error ? exc.message : '测试媒体源失败。'
      setTestResults((prev) => ({
        ...prev,
        [source.id]: {
          ok: false,
          source_id: source.id,
          items: [],
          error_code: 'REQUEST_FAILED',
          error_message: msg,
          tested_at: new Date().toISOString(),
        },
      }))
      setTestState((prev) => ({ ...prev, [source.id]: 'error' }))
      setExpandedTestId(source.id)
    }
  }

  function updateField(key: keyof SourceFormState, value: string | boolean) {
    setForm((current) => ({ ...current, [key]: value }))
  }

  const showEmpty = !isLoading && !loadError && sources.length === 0
  const drawerOpen = drawerMode !== null
  const totalPages = Math.max(1, Math.ceil(totalCount / pageSize))

  return (
    <section className="sc-page" aria-labelledby="sources-title">
      <Card className="sc-overview">
        <div className="sc-overview-head">
          <div>
            <p className="ui-eyebrow">媒体源</p>
            <h2 id="sources-title">媒体源管理</h2>
            <p className="sc-overview-lead">
              管理配置型和文档/表格型 Source；代码型 Source Adapter 由后端代码提供，只读展示。
              每一个卡片提供独立的测试、启用/禁用、编辑入口。
            </p>
          </div>
          <div className="sc-overview-actions">
            <Button variant="ghost" disabled={isLoading} onClick={() => void loadSources()}>
              {isLoading ? '读取中' : '重新读取'}
            </Button>
            <Button variant="primary" onClick={openCreate}>
              新增媒体源
            </Button>
          </div>
        </div>
      </Card>

      {loadError ? (
        <Card>
          <UIErrorState
            message="无法读取媒体源"
            sub={loadError}
            action={
              <Button variant="secondary" onClick={() => void loadSources()}>
                重试
              </Button>
            }
          />
        </Card>
      ) : null}

      {isLoading && sources.length === 0 ? (
        <Card>
          <UILoadingState message="正在读取媒体源列表。" />
        </Card>
      ) : null}

      {showEmpty ? (
        <Card>
          <UIEmptyState
            message="暂无媒体源"
            sub="点击 新增媒体源 配置第一个配置型或文档型 Source。"
            action={
              <Button variant="primary" onClick={openCreate}>
                新增媒体源
              </Button>
            }
          />
        </Card>
      ) : null}

      {sources.length > 0 ? (
        <>
          <div className="sc-grid" role="list" aria-label="媒体源列表">
            {sources.map((source) => (
              <SourceCard
                key={source.id}
                source={source}
                testStatus={testState[source.id]}
                testResult={testResults[source.id] || null}
                isExpanded={expandedTestId === source.id}
                toggling={Boolean(togglingIds[source.id])}
                onTest={() => void testSource(source)}
                onEdit={() => openEdit(source)}
                onToggle={() => void toggleSource(source)}
                onToggleTestDetail={() =>
                  setExpandedTestId((prev) => (prev === source.id ? null : source.id))
                }
              />
            ))}
          </div>
          <PaginationControls page={page} totalPages={totalPages} pageSize={pageSize} onPageChange={setPage} onPageSizeChange={setPageSize} />
        </>
      ) : null}

      <SourceDrawer
        open={drawerOpen}
        mode={drawerMode || 'create'}
        form={form}
        error={drawerError}
        isSaving={isSaving}
        editingSource={editingSource}
        onFieldChange={updateField}
        onClose={closeDrawer}
        onSubmit={() => void saveSource()}
      />
    </section>
  )
}

function SourceCard({
  source,
  testStatus,
  testResult,
  isExpanded,
  toggling,
  onTest,
  onEdit,
  onToggle,
  onToggleTestDetail,
}: {
  source: SourceResponse
  testStatus: 'running' | 'ok' | 'error' | undefined
  testResult: SourceTestResponse | null
  isExpanded: boolean
  toggling: boolean
  onTest: () => void
  onEdit: () => void
  onToggle: () => void
  onToggleTestDetail: () => void
}) {
  const isCode = source.type === 'code'
  const enabledTone: StatusTone = source.enabled ? 'success' : 'paused'
  const codeTone: StatusTone = 'info'

  return (
    <Card className="sc-card" role="listitem">
      <div className="sc-card-head">
        <div className="sc-card-title">
          <p className="ui-eyebrow">{sourceTypeLabel(source.type)}</p>
          <h3>{source.name}</h3>
          <code className="sc-card-id">{source.id}</code>
        </div>
        <div className="sc-card-badges">
          <StatusBadge tone={enabledTone}>
            {source.enabled ? '已启用' : '已禁用'}
          </StatusBadge>
          {isCode ? <StatusBadge tone={codeTone}>只读</StatusBadge> : null}
        </div>
      </div>

      {source.legal_note ? (
        <p className="sc-card-note">{source.legal_note}</p>
      ) : (
        <p className="sc-card-note sc-card-note-muted">未提供合规说明。</p>
      )}

      <dl className="sc-card-meta">
        <div>
          <dt>Trust</dt>
          <dd className="sc-mono">{source.trust_level}</dd>
        </div>
        <div>
          <dt>来源</dt>
          <dd>{source.created_by_user ? '用户创建' : '内置'}</dd>
        </div>
        <div>
          <dt>最后错误</dt>
          <dd className={source.last_error_code ? 'sc-danger' : undefined}>
            {source.last_error_code || '无'}
          </dd>
        </div>
      </dl>

      {source.last_error_message ? (
        <p className="sc-card-last-error">{source.last_error_message}</p>
      ) : null}

      {testResult ? (
        <div className="sc-card-test" data-tone={testStatus || 'idle'}>
          <button
            className="sc-card-test-summary"
            type="button"
            onClick={onToggleTestDetail}
            aria-expanded={isExpanded}
          >
            <span className="sc-card-test-dot" aria-hidden="true" />
            <span className="sc-card-test-text">
              {testResult.ok ? '测试通过' : '测试失败'}
            </span>
            <time className="sc-mono">{formatDateTime(testResult.tested_at)}</time>
            <span className="sc-card-test-chevron" aria-hidden="true" data-expanded={isExpanded || undefined}>
              <svg viewBox="0 0 12 12" width="12" height="12" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                <path d="M3 4.5l3 3 3-3" />
              </svg>
            </span>
          </button>
          {isExpanded ? (
            <div className="sc-card-test-body">
              {testResult.error_code ? (
                <div className="sc-card-test-error">
                  <strong>{testResult.error_code}</strong>
                  <p>{testResult.error_message || '无错误详情。'}</p>
                </div>
              ) : null}
              {testResult.items.length === 0 && !testResult.error_code ? (
                <p className="sc-card-test-hint">测试未返回预览条目。</p>
              ) : null}
              {testResult.items.slice(0, 3).map((item, index) => (
                <code className="sc-card-test-item" key={index}>
                  {JSON.stringify(item)}
                </code>
              ))}
              {testResult.items.length > 3 ? (
                <p className="sc-card-test-hint">
                  共 {testResult.items.length} 条，已展示前 3 条。
                </p>
              ) : null}
            </div>
          ) : null}
        </div>
      ) : null}

      <div className="sc-card-actions">
        <Button
          variant="secondary"
          size="sm"
          disabled={testStatus === 'running'}
          onClick={onTest}
        >
          {testStatus === 'running' ? '测试中…' : '测试'}
        </Button>
        <Button variant="ghost" size="sm" onClick={onEdit}>
          {isCode ? '查看' : '编辑'}
        </Button>
        <Button
          variant="ghost"
          size="sm"
          disabled={isCode || toggling}
          onClick={onToggle}
        >
          {source.enabled ? '禁用' : '启用'}
        </Button>
      </div>
    </Card>
  )
}

function SourceDrawer({
  open,
  mode,
  form,
  error,
  isSaving,
  editingSource,
  onFieldChange,
  onClose,
  onSubmit,
}: {
  open: boolean
  mode: 'create' | 'edit'
  form: SourceFormState
  error: string | null
  isSaving: boolean
  editingSource: SourceResponse | null
  onFieldChange: (key: keyof SourceFormState, value: string | boolean) => void
  onClose: () => void
  onSubmit: () => void
}) {
  useEffect(() => {
    if (!open) return
    function onKey(event: KeyboardEvent) {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      window.removeEventListener('keydown', onKey)
      document.body.style.overflow = prev
    }
  }, [open, onClose])

  const isCodeSource = editingSource?.type === 'code'
  const isEditable = mode === 'create' || !isCodeSource

  return (
    <div
      className="sc-drawer-overlay"
      data-open={open || undefined}
      aria-hidden={!open}
      onClick={onClose}
    >
      <aside
        className="sc-drawer"
        role="dialog"
        aria-modal="true"
        aria-labelledby="sc-drawer-title"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="sc-drawer-head">
          <div>
            <p className="ui-eyebrow">{mode === 'create' ? '新增' : isCodeSource ? '查看' : '编辑'}</p>
            <h3 id="sc-drawer-title">
              {mode === 'create'
                ? '创建媒体源'
                : isCodeSource
                  ? `${form.name || form.id} · 只读`
                  : `编辑 ${form.name || form.id}`}
            </h3>
          </div>
          <Button variant="ghost" size="sm" onClick={onClose} aria-label="关闭">
            ×
          </Button>
        </header>
        <form
          className="sc-drawer-body"
          onSubmit={(event) => {
            event.preventDefault()
            if (isEditable) onSubmit()
          }}
        >
          <Field
            label="名称"
            htmlFor="sc-f-name"
            helper="在搜索结果和来源列表中展示的人类可读名称。"
          >
            <input
              id="sc-f-name"
              type="text"
              disabled={!isEditable}
              required
              value={form.name}
              onChange={(event) => onFieldChange('name', event.target.value)}
            />
          </Field>
          <Field
            label="类型"
            htmlFor="sc-f-type"
            helper="配置型用于规则化网页源；文档/表格型用于维护静态条目；代码型只能只读展示。"
          >
            <select
              id="sc-f-type"
              disabled={mode === 'edit'}
              value={form.type}
              onChange={(event) =>
                onFieldChange('type', event.target.value as EditableSourceType)
              }
            >
              <option value="configurable">配置型</option>
              <option value="document">文档/表格型</option>
              {form.type === 'code' ? <option value="code">代码型</option> : null}
            </select>
          </Field>
          <Field
            label="Trust Level"
            htmlFor="sc-f-trust"
            helper="1 到 5，数字越大表示该 source 可信度越高。"
          >
            <input
              id="sc-f-trust"
              type="number"
              disabled={!isEditable}
              required
              value={form.trust_level}
              onChange={(event) => onFieldChange('trust_level', event.target.value)}
            />
          </Field>
          <div className="sc-drawer-toggle">
            <label>
              <input
                type="checkbox"
                disabled={!isEditable}
                checked={form.enabled}
                onChange={(event) => onFieldChange('enabled', event.target.checked)}
              />
              <span>启用</span>
            </label>
            <small>禁用后不会参与搜索，但配置会保留。</small>
          </div>
          <Field
            label="合规说明"
            htmlFor="sc-f-legal"
            helper="记录该 source 的来源范围、使用限制或合法性说明。"
          >
            <textarea
              id="sc-f-legal"
              rows={3}
              disabled={!isEditable}
              value={form.legal_note}
              onChange={(event) => onFieldChange('legal_note', event.target.value)}
            />
          </Field>
          <Field
            label="Config JSON"
            htmlFor="sc-f-config"
            helper={sourceConfigHint(form.type)}
          >
            <textarea
              id="sc-f-config"
              className="sc-drawer-json"
              rows={12}
              disabled={!isEditable}
              spellCheck={false}
              value={form.config_json}
              onChange={(event) => onFieldChange('config_json', event.target.value)}
            />
          </Field>

          {isCodeSource ? (
            <div className="sc-drawer-notice">
              <strong>只读 Source Adapter</strong>
              <p>代码型 source 不允许通过 Web Console 在线编辑、启用或禁用。</p>
            </div>
          ) : null}

          {error ? (
            <div className="sc-drawer-error" role="alert">
              <strong>保存失败</strong>
              <p>{error}</p>
            </div>
          ) : null}
        </form>
        <footer className="sc-drawer-actions">
          <Button variant="ghost" onClick={onClose} type="button">
            取消
          </Button>
          <Button
            variant="primary"
            disabled={!isEditable || isSaving}
            onClick={onSubmit}
            type="button"
          >
            {isSaving ? '保存中…' : mode === 'create' ? '创建' : '保存'}
          </Button>
        </footer>
      </aside>
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
    <section className="sx-page" aria-labelledby="search-title">
      <Card className="sx-overview">
      <div className="sx-overview-head">
        <div>
          <p className="ui-eyebrow">搜索</p>
          <h2 id="search-title">搜索与创建任务</h2>
          <p className="sx-overview-lead">搜索候选资源，选择网盘链接，填写目标路径后创建 Transfer 任务。</p>
        </div>
      </div>
      </Card>

      <Card className="sx-search-card">
      <form className="sx-form" onSubmit={(event) => { event.preventDefault(); void runSearch() }}>
        <TextField helper="要搜索的片名、剧名或关键词。" label="关键词" onChange={(value) => updateField('q', value)} required value={form.q} />
        <Field label="类型" helper="用于缩小搜索范围；不确定时选“未知”。">
          <select onChange={(event) => updateField('type', event.target.value)} value={form.type}>
            <option value="unknown">未知</option>
            <option value="movie">电影</option>
            <option value="tv">剧集</option>
            <option value="anime">动画</option>
          </select>
        </Field>
        <TextField helper="可选，用于区分同名作品。" label="年份" onChange={(value) => updateField('year', value)} type="number" value={form.year} />
        <TextField helper="最多返回多少个候选结果。" label="数量限制" onChange={(value) => updateField('limit', value)} type="number" value={form.limit} />
        <div className="sx-form-actions">
          <Button variant="primary" disabled={isSearching} type="submit">{isSearching ? '搜索中…' : '搜索资源'}</Button>
        </div>
      </form>
      </Card>

      {isSearching ? <UILoadingState message="正在聚合搜索候选资源…" /> : null}
      {error ? <UIErrorState message="搜索或创建任务失败" sub={error} /> : null}

      {response ? (
        <Card emphasis="sunken" className="sx-results-card">
          <div className="sx-section-head"><p className="ui-eyebrow">候选资源</p><span>{response.count} 个结果</span></div>
          {response.results.length === 0 ? <UIEmptyState message="没有搜索到候选资源" sub="可以换一个关键词、年份或类型后重新搜索。" /> : null}
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
        </Card>
      ) : null}

      <Card className="sx-create-card" aria-labelledby="create-transfer-title">
        <div className="sx-section-head"><p className="ui-eyebrow" id="create-transfer-title">创建任务</p><span>{selectedLink ? selectedLink.link.provider : '未选择链接'}</span></div>
        {selectedLink ? <div className="selected-link-card"><strong>{selectedLink.resource.title}</strong><p>{selectedLink.link.url}</p></div> : <UIEmptyState message="请先选择一个资源链接" sub="选择候选资源里的链接后，再确认目标路径。" />}
        <form className="sx-form" onSubmit={(event) => { event.preventDefault(); void createTransfer() }}>
          <TextField helper="逻辑媒体库名称，例如 movies、tv、anime。" label="目标 Library" onChange={(value) => updateField('target_library', value)} value={form.target_library} />
          <TextField helper="相对目标路径，不要填写 SMB host/share；例如 Movies/Movie Name (2024)。" label="目标路径" onChange={(value) => updateField('target_path', value)} required value={form.target_path} />
          <div className="sx-form-actions">
            <Button variant="primary" disabled={!selectedLink || isCreating} type="submit">{isCreating ? '创建中…' : '创建 Transfer'}</Button>
          </div>
        </form>
        {!form.target_path.trim() ? <div className="sx-notice"><strong>需要确认目标路径</strong><p>目标路径为空时不会创建任务，请先确认 library 和最终文件路径。</p></div> : null}
        {createdTask ? <div className="sx-notice"><strong>任务已创建</strong><p>任务 ID：{createdTask.id}。可前往任务页查询进度。</p></div> : null}
      </Card>

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
        {resource.links.length === 0 ? <UIEmptyState message="该候选资源没有可用链接" /> : null}
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
  const [pageSize, setPageSize] = useState(20)
  const [isLoading, setIsLoading] = useState(false)
  const [loadError, setLoadError] = useState<string | null>(null)

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
  const [browseName, setBrowseName] = useState('')
  const [browsePath, setBrowsePath] = useState('')
  const [browseResult, setBrowseResult] = useState<StorageBrowseResponse | null>(null)
  const [isBrowsing, setIsBrowsing] = useState(false)

  useEffect(() => { void loadConnections() }, [page, pageSize])

  async function loadConnections() {
    setIsLoading(true)
    setLoadError(null)
    try {
      const result = await api.get<SmbConnectionListResponse>(`/storage/smb-connections?page=${page}&page_size=${pageSize}`)
      setConnections(result.results)
      setTotalCount(result.count)
    } catch (exc) {
      const message = exc instanceof Error ? exc.message : '无法读取 SMB 连接。'
      setLoadError(message)
      showToast('error', message)
    }
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
        const id = newUuid()
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
        ? `/storage/smb-connections/${encodeURIComponent(editingId)}/test-new`
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
      await loadConnections()
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
    setBrowseName(conn.name)
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
      setBrowseResult(result); setBrowsePath(normalizeBrowsePath(result.path))
    } catch (exc) { setBrowseResult(null); showToast('error', exc instanceof Error ? exc.message : '浏览失败。') }
    finally { setIsBrowsing(false) }
  }

  function updateForm(key: keyof StorageFormState, value: string) { setForm((c) => ({ ...c, [key]: value })) }

  const totalPages = Math.max(1, Math.ceil(totalCount / pageSize))
  const showEmptyState = !isLoading && !loadError && connections.length === 0
  const showList = connections.length > 0

  return (
    <section className="sg-page" aria-labelledby="storage-title">
      <Card className="sg-overview">
        <div className="sg-overview-head">
          <div>
            <p className="ui-eyebrow">存储</p>
            <h2 id="storage-title">SMB 存储管理</h2>
            <p className="sg-overview-lead">
              管理多个 SMB 连接、测试连接，并在允许范围内浏览目标目录。每个连接可被本地媒体库或远程媒体库引用。
            </p>
          </div>
          <div className="sg-overview-actions">
            <Button
              variant="ghost"
              disabled={isLoading}
              onClick={() => void loadConnections()}
            >
              {isLoading ? '读取中' : '重新读取'}
            </Button>
            <Button variant="primary" onClick={openCreate}>
              新增连接
            </Button>
          </div>
        </div>
      </Card>

      <Card emphasis="sunken" className="sg-table-card">
        <div className="sg-table-head">
          <p className="ui-eyebrow">SMB 连接</p>
          <span className="sg-table-count">
            {totalCount} 个{totalPages > 1 ? ` · 第 ${page} / ${totalPages} 页` : ''}
          </span>
        </div>

        {isLoading && connections.length === 0 ? (
          <UILoadingState message="正在读取 SMB 连接…" />
        ) : null}

        {loadError ? (
          <UIErrorState
            message="无法读取 SMB 连接"
            sub={loadError}
            action={
              <Button variant="secondary" onClick={() => void loadConnections()}>
                重试
              </Button>
            }
          />
        ) : null}

        {showEmptyState ? (
          <UIEmptyState
            message="暂无 SMB 连接"
            sub="点击上方 新增连接 开始配置第一个 SMB 连接。"
            action={
              <Button variant="primary" onClick={openCreate}>
                新增连接
              </Button>
            }
          />
        ) : null}

        {showList ? (
          <>
            <div className="sg-table" role="table" aria-label="SMB 连接列表">
              <div className="sg-table-header" role="row">
                <span role="columnheader">状态</span>
                <span role="columnheader">名称 / 主机</span>
                <span role="columnheader">账号</span>
                <span role="columnheader">绑定</span>
                <span role="columnheader" aria-label="操作" />
              </div>
              {connections.map((conn) => {
                const bindingsSummary = [
                  conn.bound_local_libraries.length > 0
                    ? `本地 ${conn.bound_local_libraries.length}`
                    : null,
                  conn.bound_remote_libraries.length > 0
                    ? `远程 ${conn.bound_remote_libraries.length}`
                    : null,
                ]
                  .filter(Boolean)
                  .join(' · ')
                return (
                  <div className="sg-row" key={conn.id} role="row">
                    <span className="sg-col-status" role="cell">
                      <StatusStack
                        enabled={conn.enabled}
                        lastTestOk={conn.last_test_ok}
                        errorCode={conn.last_test_error_code}
                        errorMessage={conn.last_test_error_message}
                        onDetail={(message) => showToast('error', message)}
                      />
                    </span>
                    <span className="sg-col-title" role="cell">
                      <strong title={conn.name}>{conn.name}</strong>
                      <small title={`${conn.host}:${conn.port}/${conn.share}${conn.base_path || ''}`}>
                        {conn.host}:{conn.port}/{conn.share}
                        {conn.base_path ? <> · {conn.base_path}</> : null}
                      </small>
                    </span>
                    <span className="sg-col-account" role="cell">
                      <span>{conn.username || '—'}</span>
                      <small>{conn.password_set ? '已设密码' : '未设密码'}</small>
                    </span>
                    <span className="sg-col-bindings" role="cell">
                      {bindingsSummary || '—'}
                    </span>
                    <div className="sg-row-actions" role="cell">
                      <Button variant="ghost" size="sm" onClick={() => openEdit(conn)}>
                        编辑
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => void testConnectionRow(conn)}
                      >
                        测试
                      </Button>
                      <Button variant="ghost" size="sm" onClick={() => openBrowse(conn)}>
                        浏览
                      </Button>
                      <Button
                        variant="danger"
                        size="sm"
                        onClick={() => openDeleteModal(conn)}
                      >
                        删除
                      </Button>
                    </div>
                  </div>
                )
              })}
            </div>
            <PaginationControls page={page} totalPages={totalPages} pageSize={pageSize} onPageChange={setPage} onPageSizeChange={setPageSize} />
          </>
        ) : null}
      </Card>

      {showForm ? (
        <SmbConnectionModal
          mode={formMode}
          form={form}
          formName={formName}
          passwordSet={passwordSet}
          isSaving={isSaving}
          isTesting={isTesting}
          onNameChange={setFormName}
          onFieldChange={updateForm}
          onClose={() => setShowForm(false)}
          onTest={() => void testConnection()}
          onSubmit={() => void saveConnection()}
        />
      ) : null}

      {showDelete && deleteTarget ? (
        <SmbDeleteModal
          target={deleteTarget}
          isSaving={isSaving}
          onClose={() => setShowDelete(false)}
          onAction={(action) => void executeDelete(action)}
        />
      ) : null}

      {showBrowse ? (
        <SmbBrowseModal
          connectionName={browseName}
          browsePath={browsePath}
          browseResult={browseResult}
          isBrowsing={isBrowsing}
          onPathChange={setBrowsePath}
          onBrowse={() => void doBrowse()}
          onOpenEntry={(path) => void doBrowse(path, browseId)}
          onClose={() => {
            setShowBrowse(false)
            setBrowseResult(null)
            setBrowsePath('')
            setBrowseName('')
          }}
        />
      ) : null}
    </section>
  )
}

function SmbConnectionModal({
  mode,
  form,
  formName,
  passwordSet,
  isSaving,
  isTesting,
  onNameChange,
  onFieldChange,
  onClose,
  onTest,
  onSubmit,
}: {
  mode: 'create' | 'edit'
  form: StorageFormState
  formName: string
  passwordSet: boolean
  isSaving: boolean
  isTesting: boolean
  onNameChange: (value: string) => void
  onFieldChange: (key: keyof StorageFormState, value: string) => void
  onClose: () => void
  onTest: () => void
  onSubmit: () => void
}) {
  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      window.removeEventListener('keydown', onKey)
      document.body.style.overflow = prev
    }
  }, [onClose])

  return (
    <div
      className="sg-modal-overlay"
      role="dialog"
      aria-modal="true"
      aria-labelledby="sg-conn-modal-title"
    >
      <div className="sg-modal" onClick={(event) => event.stopPropagation()}>
        <header className="sg-modal-head">
          <div>
            <p className="ui-eyebrow">{mode === 'create' ? '新增' : '编辑'}</p>
            <h3 id="sg-conn-modal-title">
              {mode === 'create' ? '创建 SMB 连接' : '编辑 SMB 连接'}
            </h3>
          </div>
          <Button variant="ghost" size="sm" onClick={onClose} aria-label="关闭">
            ×
          </Button>
        </header>
        <form
          className="sg-modal-body"
          onSubmit={(event) => {
            event.preventDefault()
            onSubmit()
          }}
        >
          <div className="sg-form-grid">
            <Field label="名称" helper="连接名称，用于在其他模块中引用。" htmlFor="sg-f-name">
              <input
                id="sg-f-name"
                type="text"
                value={formName}
                required
                onChange={(event) => onNameChange(event.target.value)}
              />
            </Field>
            <Field label="Host" helper="SMB 服务器地址，只填主机名或 IP。" htmlFor="sg-f-host">
              <input
                id="sg-f-host"
                type="text"
                value={form.host}
                required
                onChange={(event) => onFieldChange('host', event.target.value)}
              />
            </Field>
            <Field label="Port" helper="SMB 端口，通常是 445。" htmlFor="sg-f-port">
              <input
                id="sg-f-port"
                type="number"
                value={form.port}
                required
                onChange={(event) => onFieldChange('port', event.target.value)}
              />
            </Field>
            <Field label="Share" helper="SMB 共享名。" htmlFor="sg-f-share">
              <input
                id="sg-f-share"
                type="text"
                value={form.share}
                required
                onChange={(event) => onFieldChange('share', event.target.value)}
              />
            </Field>
            <Field label="Username" helper="SMB 登录账号。" htmlFor="sg-f-user">
              <input
                id="sg-f-user"
                type="text"
                value={form.username}
                required
                onChange={(event) => onFieldChange('username', event.target.value)}
              />
            </Field>
            <Field
              label="Password"
              helper={
                passwordSet
                  ? '已保存密码且不会回显。留空表示保留旧密码。'
                  : 'SMB 登录密码。'
              }
              htmlFor="sg-f-pwd"
            >
              <input
                id="sg-f-pwd"
                type="password"
                value={form.password}
                placeholder={passwordSet ? '保留旧密码' : ''}
                onChange={(event) => onFieldChange('password', event.target.value)}
              />
            </Field>
            <Field
              label="Domain"
              helper="SMB 域或工作组；个人 NAS 通常留空。"
              htmlFor="sg-f-domain"
            >
              <input
                id="sg-f-domain"
                type="text"
                value={form.domain}
                onChange={(event) => onFieldChange('domain', event.target.value)}
              />
            </Field>
            <Field
              label="Base Path"
              helper="共享内的工作根目录。"
              htmlFor="sg-f-base"
            >
              <input
                id="sg-f-base"
                type="text"
                value={form.base_path}
                onChange={(event) => onFieldChange('base_path', event.target.value)}
              />
            </Field>
          </div>
          <footer className="sg-modal-actions">
            <Button variant="ghost" onClick={onClose} type="button">
              取消
            </Button>
            <Button
              variant="secondary"
              onClick={onTest}
              disabled={isTesting}
              type="button"
            >
              {isTesting ? '测试中…' : '测试连接'}
            </Button>
            <Button variant="primary" disabled={isSaving} type="submit">
              {isSaving ? '保存中…' : mode === 'create' ? '创建' : '保存'}
            </Button>
          </footer>
        </form>
      </div>
    </div>
  )
}

function SmbDeleteModal({
  target,
  isSaving,
  onClose,
  onAction,
}: {
  target: SmbConnectionResponse
  isSaving: boolean
  onClose: () => void
  onAction: (action: 'delete' | 'unbind' | 'cancel') => void
}) {
  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  const hasBindings =
    target.bound_local_libraries.length > 0 || target.bound_remote_libraries.length > 0

  return (
    <div
      className="sg-modal-overlay"
      role="dialog"
      aria-modal="true"
      aria-labelledby="sg-del-modal-title"
      onClick={onClose}
    >
      <div
        className="sg-modal sg-modal-sm"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="sg-modal-head">
          <div>
            <p className="ui-eyebrow">删除</p>
            <h3 id="sg-del-modal-title">删除 SMB 连接</h3>
          </div>
          <Button variant="ghost" size="sm" onClick={onClose} aria-label="关闭">
            ×
          </Button>
        </header>
        <div className="sg-modal-body">
          <p className="sg-danger-lede">
            确定要删除 <strong>{target.name}</strong> 吗？
          </p>
          {hasBindings ? (
            <div className="sg-bindings">
              {target.bound_local_libraries.length > 0 ? (
                <div className="sg-binding-row">
                  <span className="ui-eyebrow">本地媒体库</span>
                  <p>{target.bound_local_libraries.join('、')}</p>
                </div>
              ) : null}
              {target.bound_remote_libraries.length > 0 ? (
                <div className="sg-binding-row">
                  <span className="ui-eyebrow">远程媒体库</span>
                  <p>{target.bound_remote_libraries.join('、')}</p>
                </div>
              ) : null}
              <p className="sg-danger-hint">
                选择 <em>仅解绑</em> 会保留以上媒体库但解除对该连接的引用；
                选择 <em>删除所有</em> 将连同上述媒体库一起移除。
              </p>
            </div>
          ) : (
            <p className="sg-danger-hint">该连接没有被任何媒体库引用，可以安全删除。</p>
          )}
        </div>
        <footer className="sg-modal-actions">
          <Button variant="ghost" onClick={() => onAction('cancel')} type="button">
            取消
          </Button>
          {hasBindings ? (
            <Button
              variant="secondary"
              onClick={() => onAction('unbind')}
              disabled={isSaving}
              type="button"
            >
              仅解绑
            </Button>
          ) : null}
          <Button
            variant="danger"
            onClick={() => onAction('delete')}
            disabled={isSaving}
            type="button"
          >
            {isSaving ? '删除中…' : hasBindings ? '删除所有' : '删除'}
          </Button>
        </footer>
      </div>
    </div>
  )
}

function SmbBrowseModal({
  connectionName,
  browsePath,
  browseResult,
  isBrowsing,
  onPathChange,
  onBrowse,
  onOpenEntry,
  onClose,
}: {
  connectionName: string
  browsePath: string
  browseResult: StorageBrowseResponse | null
  isBrowsing: boolean
  onPathChange: (value: string) => void
  onBrowse: () => void
  onOpenEntry: (path: string) => void
  onClose: () => void
}) {
  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      window.removeEventListener('keydown', onKey)
      document.body.style.overflow = prev
    }
  }, [onClose])

  return (
    <div
      className="sg-modal-overlay"
      role="dialog"
      aria-modal="true"
      aria-labelledby="sg-browse-modal-title"
      onClick={onClose}
    >
      <div
        className="sg-modal sg-modal-lg"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="sg-modal-head">
          <div>
            <p className="ui-eyebrow">浏览</p>
            <h3 id="sg-browse-modal-title">目录浏览</h3>
            {connectionName ? (
              <p className="sg-browse-subtitle">{connectionName}</p>
            ) : null}
          </div>
          <Button variant="ghost" size="sm" onClick={onClose} aria-label="关闭">
            ×
          </Button>
        </header>
        <form
          className="sg-modal-body sg-browse-body"
          onSubmit={(event) => {
            event.preventDefault()
            onBrowse()
          }}
        >
          <div className="sg-browse-toolbar">
            <Field
              label="路径"
              htmlFor="sg-browse-path"
              helper={
                <>
                  相对于 Base Path 的目录。按 <Kbd>Enter</Kbd> 浏览。
                </>
              }
            >
              <input
                id="sg-browse-path"
                type="text"
                value={browsePath}
                placeholder="例如 Movies"
                onChange={(event) => onPathChange(event.target.value)}
              />
            </Field>
            <Button variant="primary" type="submit" disabled={isBrowsing}>
              {isBrowsing ? '浏览中…' : '浏览'}
            </Button>
          </div>
          {isBrowsing && !browseResult ? (
            <UILoadingState message="正在读取目录…" />
          ) : browseResult ? (
            <StorageBrowser result={browseResult} onOpen={onOpenEntry} />
          ) : (
            <UIEmptyState
              message="输入路径后浏览 SMB 目录"
              sub="空值表示浏览连接 Base Path 下的根目录。"
            />
          )}
        </form>
      </div>
    </div>
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
  const id = useId()

  return (
    <Field label={label} helper={helper} htmlFor={id}>
      <input id={id} disabled={disabled} onChange={(event) => onChange(event.target.value)} required={required} type={type} value={value} />
    </Field>
  )
}

function StatusStack({
  enabled,
  bindingStatus,
  lastTestOk,
  errorCode,
  errorMessage,
  onDetail,
}: {
  enabled: boolean
  bindingStatus?: string | null
  lastTestOk: boolean | null
  errorCode?: string | null
  errorMessage?: string | null
  onDetail: (message: string) => void
}) {
  const detail = `${errorCode || 'TEST_FAILED'}：${errorMessage || '测试失败。'}`
  return (
    <span className="status-stack">
      <StatusBadge tone={enabled ? 'success' : 'paused'}>{enabled ? '已启用' : '已禁用'}</StatusBadge>
      {bindingStatus ? <StatusBadge tone="paused">{bindingStatus}</StatusBadge> : null}
      {lastTestOk === true ? <StatusBadge tone="success">测试通过</StatusBadge> : null}
      {lastTestOk === false ? (
        <button className="status-detail-button" onClick={() => onDetail(detail)} title={detail} type="button">
          测试不通过
        </button>
      ) : null}
    </span>
  )
}

function PaginationControls({
  page,
  totalPages,
  pageSize,
  onPageChange,
  onPageSizeChange,
}: {
  page: number
  totalPages: number
  pageSize?: number
  onPageChange: (page: number) => void
  onPageSizeChange?: (pageSize: number) => void
}) {
  return (
    <div className="pagination">
      <Button variant="ghost" size="sm" disabled={page <= 1} onClick={() => onPageChange(page - 1)}>
        上一页
      </Button>
      <span>第 {page} / {totalPages} 页</span>
      <Button variant="ghost" size="sm" disabled={page >= totalPages} onClick={() => onPageChange(page + 1)}>
        下一页
      </Button>
      {pageSize && onPageSizeChange ? (
        <label className="pagination-size">
          每页
          <select
            value={pageSize}
            onChange={(event) => {
              onPageChange(1)
              onPageSizeChange(Number(event.target.value))
            }}
          >
            {[10, 20, 50, 100].map((size) => <option key={size} value={size}>{size}</option>)}
          </select>
        </label>
      ) : null}
    </div>
  )
}

function StorageBrowser({ result, onOpen }: { result: StorageBrowseResponse; onOpen: (path: string) => void }) {
  if (result.entries.length === 0) {
    return <UIEmptyState message="该目录为空" sub="这个目录下暂时没有可继续浏览的子目录。" />
  }

  return (
    <div className="storage-browser">
      <p>当前路径：<strong>{result.path || '/'}</strong></p>
      <div className="browser-list">
        {result.entries.map((entry) => (
          <button className="browser-row" disabled={!entry.is_dir} key={entry.path} onClick={() => onOpen(entry.path)} title={entry.name} type="button">
            <span>{entry.is_dir ? '目录' : '文件'}</span>
            <strong title={entry.name}>{entry.name}</strong>
            <small title={entry.is_dir ? entry.path : formatBytes(entry.size || 0)}>{entry.is_dir ? entry.path : formatBytes(entry.size || 0)}</small>
          </button>
        ))}
      </div>
    </div>
  )
}

function TransfersPanel({
  onTransfersChanged,
  page,
  pageSize,
  totalCount,
  onPageChange,
  onPageSizeChange,
  transfers,
  showToast,
}: {
  onTransfersChanged: () => Promise<void>
  page: number
  pageSize: number
  totalCount: number
  onPageChange: (page: number) => void
  onPageSizeChange: (pageSize: number) => void
  transfers: TransferResponse[]
  showToast: (type: 'success' | 'error' | 'info', message: string) => void
}) {
  const [transfer, setTransfer] = useState<TransferResponse | null>(null)
  const [logs, setLogs] = useState<TransferLogResponse[]>([])
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [isMutating, setIsMutating] = useState(false)

  useEffect(() => {
    const handler = (event: Event) => {
      const taskIdFromEvent = (event as CustomEvent<{ taskId?: string }>).detail?.taskId
      if (taskIdFromEvent) {
        void loadTransfer(taskIdFromEvent)
      }
    }
    window.addEventListener('sundarr:select-transfer', handler)
    return () => window.removeEventListener('sundarr:select-transfer', handler)
  }, [])

  useEffect(() => {
    if (!transfer) return
    const timer = window.setInterval(() => {
      void loadTransfer(transfer.id, { silent: true })
    }, 5000)
    return () => window.clearInterval(timer)
  }, [transfer?.id])

  async function loadTransfer(nextTaskId: string, options: { silent?: boolean } = {}) {
    const trimmedTaskId = nextTaskId.trim()
    if (!trimmedTaskId) {
      return
    }

    if (!options.silent) setIsLoading(true)
    setError(null)
    try {
      const [task, taskLogs] = await Promise.all([
        api.get<TransferResponse>(`/transfers/${encodeURIComponent(trimmedTaskId)}`),
        api.get<TransferLogResponse[]>(`/transfers/${encodeURIComponent(trimmedTaskId)}/logs`),
      ])
      setTransfer(task)
      setLogs(taskLogs)
    } catch (exc) {
      setTransfer(null)
      setLogs([])
      setError(exc instanceof Error ? exc.message : '无法读取任务。')
    } finally {
      if (!options.silent) setIsLoading(false)
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
    if (!window.confirm('确认清理所有已完成或已取消的任务？')) return
    try {
      const result = await api.post<{ ok: boolean; deleted_count: number }>('/transfers/clear-completed')
      showToast('success', `已清理 ${result.deleted_count} 个任务。`)
      setTransfer(null); setLogs([])
      await onTransfersChanged()
    } catch (exc) { showToast('error', exc instanceof Error ? exc.message : '清理失败。') }
  }

  const canCancel = transfer ? canCancelTransfer(transfer.status) : false
  const canRetry = transfer?.status === 'failed' && transfer.retryable === true
  const canPause = transfer ? canPauseTransfer(transfer.status) : false
  const canResume = transfer ? canResumeTransfer(transfer.status) : false
  const totalPages = Math.max(1, Math.ceil(totalCount / pageSize))

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
              清理
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
      <PaginationControls page={page} totalPages={totalPages} pageSize={pageSize} onPageChange={onPageChange} onPageSizeChange={onPageSizeChange} />

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
            sub="在上方任务表格点选，任务详情会每 5 秒自动刷新。"
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

// Legacy 详情项（部分未迁移页面仍在用，Step 5 后续页面迁移时替换）
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

  useEffect(() => { void loadHealth() }, [])

  async function loadHealth() {
    setIsLoading(true); setError(null)
    try {
      const [h, w] = await Promise.all([
        api.get<HealthResponse>('/health'),
        api.get<{ enabled: boolean; running: boolean; pid: number | null }>('/worker/status'),
      ])
      setHealth(h); setWorkerState(w)
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

  // Each component reports its own `checked_at` from the backend (see
  // sundarr/app/api/health.py). We render that directly so a stale probe
  // stays visible even if the whole panel was refreshed recently.
  const items: { label: string; value: string; checkedAt: string | null }[] = health ? [
    { label: 'API', value: health.status, checkedAt: health.components.api.checked_at },
    { label: 'Database', value: health.database, checkedAt: health.components.database.checked_at },
    { label: 'Redis', value: health.redis, checkedAt: health.components.redis.checked_at },
    { label: 'Worker', value: health.worker, checkedAt: health.components.worker.checked_at },
  ] : []

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
              <StatusCard
                key={item.label}
                label={item.label}
                value={item.value}
                lastChecked={formatClockFromISO(item.checkedAt)}
              />
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
      return responseJson<T>(response)
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
      return responseJson<T>(response)
    },
    example(path: string) {
      return `GET ${baseUrl || '<same-origin>'}/${path.replace(/^\//, '')}`
    },
  }
}

async function responseJson<T>(response: Response): Promise<T> {
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error(`请求返回了非 JSON 内容：${response.url || 'unknown'}`)
  }
  return response.json() as Promise<T>
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

function emptyLibraryForm(): MediaLibraryFormState {
  return { id: '', name: '', media_type: 'movie', enabled: true, connection_id: '', base_path: '/' }
}

function newUuid() {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return crypto.randomUUID()
  }
  return `${Date.now().toString(16)}-${Math.random().toString(16).slice(2)}`
}

function normalizeBrowsePath(path: string) {
  const normalized = path.trim().replace(/\\/g, '/').replace(/^\/+|\/+$/g, '')
  return normalized ? `/${normalized}` : '/'
}

function normalizeLibraryPath(path: string) {
  const normalized = path.trim().replace(/\\/g, '/').replace(/^\/+|\/+$/g, '')
  return normalized ? `/${normalized}` : '/'
}

function remoteBindingPreview(names: string[]) {
  if (names.length <= 2) return names.join('、')
  return `${names.slice(0, 2).join('、')}…`
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

function dtlMediaTypeLabel(type: DtlMediaType) {
  const labels: Record<DtlMediaType, string> = {
    movie: '电影',
    series: '剧集',
    unclassified: '未分类',
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

function formatClockFromISO(value: string | null) {
  if (!value) return '--:--:--'
  const date = new Date(value)
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
