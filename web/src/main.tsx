import React, { useEffect, useId, useMemo, useState } from 'react'
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
import type {
  PageKey,
  ThemeMode,
  TransferResponse,
  TransferStatus,
  TransferLogResponse,
  TransferListResponse,
  SmbConnectionResponse,
  SmbConnectionListResponse,
  StorageBrowseResponse,
  StorageBrowseEntry,
  StorageConfigResponse,
  StorageFormState,
  StorageConfigRequest,
  MediaType,
  DtlMediaType,
  MediaLibraryResponse,
  MediaLibraryListResponse,
  DtlConfigResponse,
  DtlConfigFormState,
  DtlBindingResponse,
  DtlBindingListResponse,
  DtlDiscoveredFileResponse,
  DtlDiscoveredListResponse,
  DtlScanResponse,
  DtlTaskCreateResponse,
  DtlBindingTestResponse,
  DtlBindingFormState,
  SyncMediaType,
  SyncConfigResponse,
  SyncConfigFormState,
  SyncBindingResponse,
  SyncBindingListResponse,
  SyncDiscoveredFileResponse,
  SyncDiscoveredListResponse,
  SyncScanResponse,
  SyncTaskCreateResponse,
  SyncBindingTestResponse,
  SyncBindingFormState,
  RemoteMediaLibraryResponse,
  RemoteMediaLibraryListResponse,
  RemoteMediaLibraryFormState,
  MediaLibraryFormState,
  ResourceCandidate,
  ResourceLinkResult,
  SearchFormState,
  SourceResponse,
  SourceListResponse,
  SourceTestResponse,
  SourceTestLog,
  SourceTestFormState,
  ResourceFavoritesListResponse,
  ResourceFavoriteRequest,
  ResourceLinkFavoriteRequest,
  ViewMode,
  SearchResponse,
  SourceSearchResult,
  FetchDetailRequest,
  HealthResponse,
  ComponentHealth,
  StorageConfigTestResponse,
  NavItem,
} from './types'
import { navItems } from './types'
import { api } from './api/client'
import { storedThemeMode, applyThemeMode, themeModeLabel } from './utils/theme'
import { pageFromPath } from './utils/navigation'
import { formatRelative, formatBytes, formatDate, formatDateTime, formatClockFromISO } from './utils/format'
import { syncSeenStatusLabel, syncSeenTone, dtlSeenStatusLabel, dtlSeenTone, mediaTypeLabel, providerLabel, validationLabel, linkValidationTone, dtlMediaTypeLabel, canCancelTransfer, canPauseTransfer, canResumeTransfer, transferStatusLabel, transferStatusTone, transferStatusToneUI, isTransferRunning, noticeForTransfer, statusLabel, statusDescription } from './utils/labels'
import { emptyLibraryForm, emptyRemoteLibraryForm, emptyDtlConfigForm, dtlConfigFormFromResponse, dtlConfigRequestFromForm, emptySyncConfigForm, syncConfigFormFromResponse, syncConfigRequestFromForm, emptySyncBindingForm, emptyDtlBindingForm, emptyStorageForm, storageFormFromConfig, storageRequestFromForm } from './utils/forms'
import { newUuid, normalizeBrowsePath, normalizeLibraryPath, remoteBindingPreview, triStateFromBoolean, triStateToBoolean, detailToMessage, suggestedTargetPath } from './utils/helpers'
import { TextField } from './components/TextField'
import { StatusStack } from './components/StatusStack'
import { PaginationControls } from './components/PaginationControls'
import { StorageBrowser } from './components/StorageBrowser'
import { ViewToggle } from './components/ViewToggle'
import { ThemeSwitcher } from './components/ThemeSwitcher'
import { ThemeModeIcon } from './components/ThemeModeIcon'
import { ResourceCard } from './components/ResourceCard'
import { TransferDetail } from './components/TransferDetail'
import { DetailItem } from './components/DetailItem'
import { TransferNotice } from './components/TransferNotice'
import { TransferLogs } from './components/TransferLogs'
import { TransferSummary } from './components/TransferSummary'
import { TransferTable } from './components/TransferTable'
import { GlobalTransferPanel } from './components/GlobalTransferPanel'

function App() {
  const [activePage, setActivePage] = useState<PageKey>(() => pageFromPath(window.location.pathname))
  const [themeMode, setThemeMode] = useState<ThemeMode>(() => storedThemeMode())
  const [transfers, setTransfers] = useState<TransferResponse[]>([])
  const [transferPage, setTransferPage] = useState(1)
  const [transferTotalCount, setTransferTotalCount] = useState(0)
  const [transferPageSize, setTransferPageSize] = useState(20)
  const [transferError, setTransferError] = useState<string | null>(null)
  const [isTransferPanelOpen, setIsTransferPanelOpen] = useState(window.innerWidth > 860)
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

  useEffect(() => {
    function onMouseDown(e: MouseEvent) {
      const target = e.target as HTMLElement
      if (target.closest('[role="tablist"] button') || target.closest('.sx-result-tabs button') || target.closest('.sx-provider-tabs button') || target.closest('.favorite-module-tabs button')) {
        e.preventDefault()
      }
    }
    document.addEventListener('mousedown', onMouseDown, true)
    return () => document.removeEventListener('mousedown', onMouseDown, true)
  }, [])

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
          <ThemeSwitcher mode={themeMode} onChange={setThemeMode} />
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
            <span className="toast-progress" style={{ animationDuration: `${toast.duration}ms` }} aria-hidden="true" />
          </div>
        ))}
      </div>
    </div>
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
  return (
    <>
      <div className={activePage === 'status' ? 'panel-visible' : 'panel-hidden'}><StatusPanel /></div>
      <div className={activePage === 'transfers' ? 'panel-visible' : 'panel-hidden'}><TransfersPanel onTransfersChanged={onTransfersChanged} page={transferPage} pageSize={transferPageSize} totalCount={transferTotalCount} onPageChange={onTransferPageChange} onPageSizeChange={onTransferPageSizeChange} transfers={transfers} showToast={showToast} /></div>
      <div className={activePage === 'storage' ? 'panel-visible' : 'panel-hidden'}><StoragePanel showToast={showToast} /></div>
      <div className={activePage === 'search' ? 'panel-visible' : 'panel-hidden'}><SearchPanel showToast={showToast} /></div>
      <div className={activePage === 'favorites' ? 'panel-visible' : 'panel-hidden'}><FavoritesPanel showToast={showToast} /></div>
      <div className={activePage === 'sources' ? 'panel-visible' : 'panel-hidden'}><SourcesPanel /></div>
      <div className={activePage === 'libraries' ? 'panel-visible' : 'panel-hidden'}><LibrariesPanel showToast={showToast} /></div>
      <div className={activePage === 'remote-libraries' ? 'panel-visible' : 'panel-hidden'}><RemoteLibrariesPanel showToast={showToast} /></div>
    </>
  )
}

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

  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (event.key !== 'Escape') return
      if (showForm) { setShowForm(false); return }
      if (showBrowse) { setShowBrowse(false); setBrowseResult(null); setBrowsePath(''); return }
      if (showDelete) setShowDelete(false)
    }
    if (!showForm && !showBrowse && !showDelete) return
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [showForm, showBrowse, showDelete])

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

  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (event.key !== 'Escape') return
      if (showForm) { setShowForm(false); return }
      if (showBrowse) { setShowBrowse(false); setBrowseResult(null); setBrowsePath(''); return }
      if (showDelete) setShowDelete(false)
    }
    if (!showForm && !showBrowse && !showDelete) return
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [showForm, showBrowse, showDelete])

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
              <Field label="成功后删除来源" helper="同步成功后删除远程媒体库中的来源文件。"><select value={form.delete_source_after_success} onChange={(e) => updateForm('delete_source_after_success', e.target.value)}>
                <option value="">使用全局默认</option><option value="true">删除</option><option value="false">保留</option>
              </select></Field>
              <Field label="删除空目录" helper="扫描时自动删除远程媒体库中的空目录。"><select value={form.delete_empty_source_dirs} onChange={(e) => updateForm('delete_empty_source_dirs', e.target.value)}>
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

  const [testState, setTestState] = useState<Record<string, 'running' | 'ok' | 'error'>>({})
  const [viewingSource, setViewingSource] = useState<SourceResponse | null>(null)

  // 最近一次测试的结果 detail（可展示条目 / 错误详情），key = source.id
  const [testResults, setTestResults] = useState<Record<string, SourceTestResponse>>({})
  const [testForms, setTestForms] = useState<Record<string, SourceTestFormState>>({})
  const [expandedTestId, setExpandedTestId] = useState<string | null>(null)

  useEffect(() => {
    void loadSources()
  }, [page, pageSize])

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

  function getTestForm(sourceId: string): SourceTestFormState {
    return testForms[sourceId] || { keyword: '星际穿越', limit: '5' }
  }

  function updateTestForm(sourceId: string, patch: Partial<SourceTestFormState>) {
    setTestForms((prev) => ({
      ...prev,
      [sourceId]: { ...(prev[sourceId] || { keyword: '星际穿越', limit: '5' }), ...patch },
    }))
  }

  async function testSource(source: SourceResponse) {
    const form = getTestForm(source.id)
    const keyword = form.keyword.trim()
    if (!keyword) {
      setTestResults((prev) => ({
        ...prev,
        [source.id]: {
          ok: false,
          source_id: source.id,
          items: [],
          logs: [{ step: 'prepare', status: 'error', message: '请输入测试关键词。', data: {} }],
          error_code: 'KEYWORD_REQUIRED',
          error_message: '请输入测试关键词。',
          tested_at: new Date().toISOString(),
        },
      }))
      setTestState((prev) => ({ ...prev, [source.id]: 'error' }))
      setExpandedTestId(source.id)
      return
    }
    setTestState((prev) => ({ ...prev, [source.id]: 'running' }))
    try {
      const result = await api.post<SourceTestResponse>(
        `/sources/${encodeURIComponent(source.id)}/test`,
        {
          keyword,
          limit: Math.max(1, Math.min(20, Number(form.limit) || 5)),
        },
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
          logs: [{ step: 'request', status: 'error', message: msg, data: {} }],
          error_code: 'REQUEST_FAILED',
          error_message: msg,
          tested_at: new Date().toISOString(),
        },
      }))
      setTestState((prev) => ({ ...prev, [source.id]: 'error' }))
      setExpandedTestId(source.id)
    }
  }

  const showEmpty = !isLoading && !loadError && sources.length === 0
  const totalPages = Math.max(1, Math.ceil(totalCount / pageSize))

  return (
    <section className="sc-page" aria-labelledby="sources-title">
      <Card className="sc-overview">
        <div className="sc-overview-head">
          <div>
            <p className="ui-eyebrow">媒体源</p>
            <h2 id="sources-title">媒体源管理</h2>
            <p className="sc-overview-lead">
              查看当前安装的搜索源。详情弹窗中可以运行测试搜索，检查请求、解析和结果预览。
            </p>
          </div>
          <div className="sc-overview-actions">
            <Button variant="ghost" disabled={isLoading} onClick={() => void loadSources()}>
              {isLoading ? '读取中' : '重新读取'}
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
            sub="请在后端代码中实现 Source Adapter，并注册到 sources/registry.py。"
          />
        </Card>
      ) : null}

      {sources.length > 0 ? (
        <>
          <div className="sc-source-table" role="table" aria-label="搜索源列表">
            <div className="sc-source-table-header" role="row">
              <span role="columnheader">名称</span>
              <span role="columnheader">原网址</span>
              <span role="columnheader">说明</span>
              <span role="columnheader" aria-label="操作" />
            </div>
            {sources.map((source) => (
              <div className="sc-source-row" key={source.id} role="row">
                <span className="sc-source-name" role="cell">
                  <strong title={source.name}>{source.name}</strong>
                  <code>{source.id}</code>
                </span>
                <span className="sc-source-url" role="cell">
                  <a href={source.homepage_url} target="_blank" rel="noreferrer" title={source.homepage_url}>
                    {source.homepage_url || '未配置'}
                  </a>
                </span>
                <span className="sc-source-description" role="cell" title={source.description}>
                  {source.description || '暂无说明'}
                </span>
                <span className="sc-source-actions" role="cell">
                  <Button variant="secondary" size="sm" onClick={() => { setViewingSource(source); setExpandedTestId(source.id) }}>
                    详情
                  </Button>
                </span>
              </div>
            ))}
          </div>
          <PaginationControls page={page} totalPages={totalPages} pageSize={pageSize} onPageChange={setPage} onPageSizeChange={setPageSize} />
        </>
      ) : null}

      <SourceDetailModal
        source={viewingSource}
        testForm={viewingSource ? getTestForm(viewingSource.id) : null}
        testStatus={viewingSource ? testState[viewingSource.id] : undefined}
        testResult={viewingSource ? testResults[viewingSource.id] || null : null}
        isExpanded={viewingSource ? expandedTestId === viewingSource.id : false}
        onClose={() => setViewingSource(null)}
        onTest={() => viewingSource ? void testSource(viewingSource) : undefined}
        onTestFormChange={(patch) => viewingSource ? updateTestForm(viewingSource.id, patch) : undefined}
        onToggleTestDetail={() => viewingSource ? setExpandedTestId((prev) => (prev === viewingSource.id ? null : viewingSource.id)) : undefined}
      />
    </section>
  )
}

function SourceDetailModal({
  source,
  testForm,
  testStatus,
  testResult,
  isExpanded,
  onClose,
  onTest,
  onTestFormChange,
  onToggleTestDetail,
}: {
  source: SourceResponse | null
  testForm: SourceTestFormState | null
  testStatus: 'running' | 'ok' | 'error' | undefined
  testResult: SourceTestResponse | null
  isExpanded: boolean
  onClose: () => void
  onTest: () => void | undefined
  onTestFormChange: (patch: Partial<SourceTestFormState>) => void | undefined
  onToggleTestDetail: () => void | undefined
}) {
  useEffect(() => {
    if (!source) return
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
  }, [source, onClose])

  if (!source || !testForm) return null

  return (
    <div className="sc-modal-overlay" onClick={onClose}>
      <div className="sc-modal sc-modal-lg" role="dialog" aria-modal="true" aria-labelledby="sc-source-modal-title" onClick={(event) => event.stopPropagation()}>
        <header className="sc-modal-head">
          <div>
            <p className="ui-eyebrow">搜索源详情</p>
            <h3 id="sc-source-modal-title">{source.name}</h3>
          </div>
          <Button variant="ghost" size="sm" onClick={onClose} aria-label="关闭">×</Button>
        </header>

        <div className="sc-modal-body">
          <section className="sc-source-detail-block" aria-label="基础信息">
            <div className="sc-source-identity">
              <span className="status-pill running">搜索源</span>
              <h4>{source.name}</h4>
              <p>{source.description || '暂无说明。'}</p>
            </div>
            <dl className="sc-source-detail-list">
              <div>
                <dt>ID</dt>
                <dd>{source.id}</dd>
              </div>
              <div>
                <dt>原网址</dt>
                <dd>
                  {source.homepage_url ? (
                    <a href={source.homepage_url} target="_blank" rel="noreferrer">{source.homepage_url}</a>
                  ) : '未配置'}
                </dd>
              </div>
            </dl>
          </section>

          <section className="sc-source-test-block" aria-label={`${source.name} 测试搜索`}>
            <div className="sc-source-test-head">
              <div>
                <p className="ui-eyebrow">测试搜索</p>
                <h4>验证请求、解析和结果预览</h4>
              </div>
              <Button
                variant="primary"
                size="sm"
                disabled={testStatus === 'running'}
                onClick={onTest}
              >
                {testStatus === 'running' ? '测试中…' : '运行测试'}
              </Button>
            </div>

            <div className="sc-source-test-form">
              <label>
                <span>关键词</span>
                <input
                  value={testForm.keyword}
                  onChange={(event) => onTestFormChange({ keyword: event.target.value })}
                  placeholder="例如：星际穿越"
                />
              </label>
              <label>
                <span>预览数</span>
                <input
                  inputMode="numeric"
                  min="1"
                  max="20"
                  value={testForm.limit}
                  onChange={(event) => onTestFormChange({ limit: event.target.value })}
                />
              </label>
            </div>

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
                    {testResult.logs.length > 0 ? (
                      <ol className="sc-source-log-list">
                        {testResult.logs.map((log, index) => (
                          <li key={`${log.step}-${index}`} data-status={log.status}>
                            <span className="sc-source-log-step">{log.step}</span>
                            <strong>{log.message}</strong>
                            {Object.keys(log.data).length > 0 ? (
                              <code>{JSON.stringify(log.data)}</code>
                            ) : null}
                          </li>
                        ))}
                      </ol>
                    ) : null}
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
          </section>
        </div>
        <footer className="sc-modal-actions">
          <Button variant="ghost" onClick={onClose} type="button">关闭</Button>
        </footer>
      </div>
    </div>
  )
}

function FavoritesPanel({ showToast }: { showToast: (type: 'success' | 'error' | 'info', message: string) => void }) {
  const [activeTab, setActiveTab] = useState<'resources' | 'links'>(() => window.location.pathname === '/app/favorite-links' ? 'links' : 'resources')

  return (
    <section className="sx-page" aria-labelledby="favorites-title">
      <Card className="sx-overview">
        <div className="sx-overview-head">
          <div>
            <p className="ui-eyebrow">收藏</p>
            <h2 id="favorites-title">收藏</h2>
            <p className="sx-overview-lead">统一管理已收藏的资源和具体链接。资源用于持续跟踪媒体，链接用于保留某个具体分享版本。</p>
          </div>
        </div>
      </Card>
      <Card emphasis="sunken" className="sx-results-card favorites-card">
        <div className="sx-result-tabs favorite-module-tabs" role="tablist" aria-label="收藏类型">
          <button type="button" role="tab" data-active={activeTab === 'resources'} aria-selected={activeTab === 'resources'} onClick={() => setActiveTab('resources')}>
            收藏资源
          </button>
          <button type="button" role="tab" data-active={activeTab === 'links'} aria-selected={activeTab === 'links'} onClick={() => setActiveTab('links')}>
            收藏链接
          </button>
        </div>
        <div className="favorite-tab-body">
          {activeTab === 'resources' ? <FavoriteResourcesPanel showToast={showToast} /> : null}
          {activeTab === 'links' ? <FavoriteLinksPanel showToast={showToast} /> : null}
        </div>
      </Card>
    </section>
  )
}

function FavoriteResourcesPanel({ showToast }: { showToast: (type: 'success' | 'error' | 'info', message: string) => void }) {
  const [resources, setResources] = useState<ResourceCandidate[]>([])
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [totalCount, setTotalCount] = useState(0)
  const [activeSourceTab, setActiveSourceTab] = useState('all')
  const [activeProvider, setActiveProvider] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [viewMode, setViewMode] = useState<ViewMode>(() =>
    (window.localStorage.getItem('sundarr.viewMode') as ViewMode) || 'list'
  )

  useEffect(() => { void loadFavorites() }, [page, pageSize])

  async function loadFavorites() {
    setIsLoading(true)
    setError(null)
    try {
      const result = await api.get<ResourceFavoritesListResponse>(`/resources/favorites?page=${page}&page_size=${pageSize}`)
      setResources(result.results)
      setTotalCount(result.count)
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : '无法读取收藏资源。')
    } finally {
      setIsLoading(false)
    }
  }

  async function toggleFavoriteResource(resource: ResourceCandidate) {
    try {
      await api.post<{ ok: boolean }>(`/resources/${encodeURIComponent(resource.id)}/unfavorite`)
      setResources((current) => current.filter((item) => item.id !== resource.id))
      setTotalCount((c) => Math.max(0, c - 1))
      showToast('success', '已取消收藏资源。')
    } catch (exc) {
      showToast('error', exc instanceof Error ? exc.message : '取消收藏资源失败。')
    }
  }

  async function toggleFavoriteLink(resource: ResourceCandidate, link: ResourceLinkResult) {
    try {
      await api.post<{ ok: boolean }>(`/resource-links/${encodeURIComponent(link.id)}/unfavorite`)
      setResources((current) => current.map((item) => item.id === resource.id ? {
        ...item,
        links: item.links.filter((entry) => entry.id !== link.id),
      } : item))
      showToast('success', '已取消收藏链接。')
    } catch (exc) {
      showToast('error', exc instanceof Error ? exc.message : '取消收藏链接失败。')
    }
  }

  async function refreshResource(resource: ResourceCandidate) {
    try {
      const refreshed = await api.post<SearchResponse>(`/resources/${encodeURIComponent(resource.id)}/refresh`)
      const next = refreshed.results.find((item) => item.normalized_title === resource.normalized_title && item.year === resource.year) || refreshed.results[0]
      if (!next) {
        showToast('info', '未找到新的候选结果。')
        return
      }
      setResources((current) => current.map((item) => item.id === resource.id ? {
        ...next,
        id: item.id,
        is_favorited: true,
        favorited_at: item.favorited_at,
      } : item))
      showToast('success', `资源刷新完成，返回 ${refreshed.count} 条候选结果。`)
    } catch (exc) {
      showToast('error', exc instanceof Error ? exc.message : '刷新资源失败。')
    }
  }

  async function copyLink(link: ResourceLinkResult) {
    const text = link.code ? `${link.url} 提取码：${link.code}` : link.url
    try {
      await navigator.clipboard.writeText(text)
      showToast('success', '链接已复制。')
    } catch {
      window.prompt('复制链接', text)
    }
  }

  const sourceTabs = useMemo(() => {
    const groups = new Map<string, { label: string; results: ResourceCandidate[] }>()
    for (const r of resources) {
      const existing = groups.get(r.source_id) || { label: r.source_id, results: [] }
      existing.results.push(r)
      groups.set(r.source_id, existing)
    }
    return [
      { id: 'all', label: '全部', count: resources.length, results: resources },
      ...Array.from(groups.entries()).map(([id, group]) => ({
        id,
        label: group.label,
        count: group.results.length,
        results: group.results,
      })),
    ]
  }, [resources])

  const activeTab = sourceTabs.find((t) => t.id === activeSourceTab) || sourceTabs[0]

  const providerFilters = useMemo(() => {
    if (!activeTab) return []
    const providerSet = new Set<string>()
    for (const r of activeTab.results) {
      for (const link of r.links) {
        providerSet.add(link.provider)
      }
    }
    return Array.from(providerSet).map((id) => ({
      id,
      label: providerLabel(id),
    }))
  }, [activeTab])

  const totalPages = Math.max(1, Math.ceil(totalCount / pageSize))

  return (
    <section className="favorite-tab-panel" aria-labelledby="favorite-resources-title">
      <div className="sx-section-head">
        <p className="ui-eyebrow">收藏资源</p>
        <span>{totalCount} 个资源</span>
        <ViewToggle value={viewMode} onChange={(m) => { setViewMode(m); window.localStorage.setItem('sundarr.viewMode', m) }} />
      </div>
      {isLoading ? <UILoadingState message="正在读取收藏资源…" /> : null}
      {error ? <UIErrorState message="读取收藏资源失败" sub={error} /> : null}
      {!isLoading && !error && resources.length === 0 ? <UIEmptyState message="还没有收藏资源" sub="先在搜索结果中收藏资源。" /> : null}
      {!isLoading && !error && resources.length > 0 ? (
        <>
          <div className="sx-result-tabs" role="tablist" aria-label="按媒体源查看收藏资源">
            {sourceTabs.map((tab) => (
              <button
                key={tab.id}
                type="button"
                role="tab"
                aria-selected={activeTab?.id === tab.id}
                data-active={activeTab?.id === tab.id || undefined}
                onClick={() => { setActiveSourceTab(tab.id); setActiveProvider(null) }}
              >
                <span>{tab.label}</span>
                <strong>{tab.count}</strong>
              </button>
            ))}
          </div>
          {providerFilters.length > 0 ? (
            <div className="sx-provider-tabs" role="tablist" aria-label="按网盘类型过滤">
              <button
                type="button"
                role="tab"
                aria-selected={activeProvider === null}
                data-active={activeProvider === null || undefined}
                onClick={() => setActiveProvider(null)}
              >全部网盘</button>
              {providerFilters.map((pf) => (
                <button
                  key={pf.id}
                  type="button"
                  role="tab"
                  aria-selected={activeProvider === pf.id}
                  data-active={activeProvider === pf.id || undefined}
                  onClick={() => setActiveProvider(pf.id)}
                >
                  <span>{pf.label}</span>
                </button>
              ))}
            </div>
          ) : null}
          <div className={viewMode === 'grid' ? 'sx-results-grid' : 'sx-result-pane'} role="tabpanel">
            {activeTab && activeTab.results.length === 0 ? (
              <UIEmptyState message="该来源没有收藏资源" sub="切换到其它来源标签页查看。" />
            ) : null}
            {activeTab?.results.map((resource) => (
              <ResourceCard
                key={resource.id}
                activeProvider={activeProvider}
                onCopyLink={(link) => void copyLink(link)}
                onFavoriteLink={(link) => void toggleFavoriteLink(resource, link)}
                onFavoriteResource={() => void toggleFavoriteResource(resource)}
                onRefreshResource={() => void refreshResource(resource)}
                onSaveToCloud={() => showToast('info', '保存到网盘入口已预留。')}
                resource={resource}
                showToast={showToast}
                viewMode={viewMode}
              />
            ))}
          </div>
          <PaginationControls page={page} totalPages={totalPages} pageSize={pageSize} onPageChange={setPage} onPageSizeChange={setPageSize} />
        </>
      ) : null}
    </section>
  )
}

function FavoriteLinksPanel({ showToast }: { showToast: (type: 'success' | 'error' | 'info', message: string) => void }) {
  const [links, setLinks] = useState<ResourceLinkResult[]>([])
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [totalCount, setTotalCount] = useState(0)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => { void loadFavorites() }, [page, pageSize])

  async function loadFavorites() {
    setIsLoading(true)
    setError(null)
    try {
      const result = await api.get<{ count: number; page: number; page_size: number; results: ResourceLinkResult[] }>(`/resource-links/favorites?page=${page}&page_size=${pageSize}`)
      setLinks(result.results)
      setTotalCount(result.count)
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : '无法读取收藏链接。')
    } finally {
      setIsLoading(false)
    }
  }

  async function unfavoriteLink(link: ResourceLinkResult) {
    try {
      await api.post<{ ok: boolean }>(`/resource-links/${encodeURIComponent(link.id)}/unfavorite`)
      setLinks((current) => current.filter((item) => item.id !== link.id))
      setTotalCount((c) => Math.max(0, c - 1))
      showToast('success', '已取消收藏链接。')
    } catch (exc) {
      showToast('error', exc instanceof Error ? exc.message : '取消收藏链接失败。')
    }
  }

  async function copyLink(link: ResourceLinkResult) {
    const text = link.code ? `${link.url} 提取码：${link.code}` : link.url
    try {
      await navigator.clipboard.writeText(text)
      showToast('success', '链接已复制。')
    } catch {
      window.prompt('复制链接', text)
    }
  }

  const totalPages = Math.max(1, Math.ceil(totalCount / pageSize))

  return (
    <section className="favorite-tab-panel" aria-labelledby="favorite-links-title">
      <div className="sx-section-head">
        <p className="ui-eyebrow">收藏链接</p>
        <span>{totalCount} 条链接</span>
      </div>
      {isLoading ? <UILoadingState message="正在读取收藏链接…" /> : null}
      {error ? <UIErrorState message="读取收藏链接失败" sub={error} /> : null}
      {!isLoading && !error && links.length === 0 ? <UIEmptyState message="还没有收藏链接" sub="先在搜索结果中收藏具体链接。" /> : null}
      {!isLoading && !error && links.length > 0 ? (
        <>
          <Card emphasis="sunken" className="favorite-link-card">
            <div className="favorite-link-list">
              {links.map((link) => (
                <div className="link-row" key={link.id}>
                  <a href={link.url} target="_blank" rel="noreferrer">
                    <strong className="truncate-name">{link.name || link.url}</strong>
                    <div className="link-meta">
                      <span className="provider-badge">{providerLabel(link.provider)}</span>
                      {link.quality ? <span>{link.quality}</span> : null}
                      {link.code ? <span>提取码：{link.code}</span> : null}
                      {link.published_at ? <span>{formatDate(link.published_at)}</span> : null}
                    </div>
                    <span className="link-url-text">{link.url}</span>
                  </a>
                  <StatusBadge tone={linkValidationTone(link.validation_status)}>
                    {validationLabel(link)}
                  </StatusBadge>
                  <div className="link-actions">
                    <Button variant="secondary" size="sm" type="button" onClick={() => void unfavoriteLink(link)}>取消收藏</Button>
                    <Button variant="ghost" size="sm" type="button" onClick={() => void copyLink(link)}>复制链接</Button>
                  </div>
                </div>
              ))}
            </div>
          </Card>
          <PaginationControls page={page} totalPages={totalPages} pageSize={pageSize} onPageChange={setPage} onPageSizeChange={setPageSize} />
        </>
      ) : null}
    </section>
  )
}

function SearchPanel({ showToast }: { showToast: (type: 'success' | 'error' | 'info', message: string) => void }) {
  const [form, setForm] = useState<SearchFormState>({
    q: '',
  })
  const [response, setResponse] = useState<SearchResponse | null>(null)
  const [activeResultTab, setActiveResultTab] = useState('all')
  const [activeProvider, setActiveProvider] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isSearching, setIsSearching] = useState(false)
  const [viewMode, setViewMode] = useState<ViewMode>(() =>
    (window.localStorage.getItem('sundarr.viewMode') as ViewMode) || 'list'
  )

  async function runSearch() {
    const keyword = form.q.trim()
    if (!keyword) {
      setError('请输入搜索关键词。')
      return
    }

    setIsSearching(true)
    setError(null)
    try {
      const params = new URLSearchParams({ q: keyword, limit: '20' })
      const result = await api.get<SearchResponse>(`/search?${params.toString()}`)
      setResponse(result)
      setActiveResultTab('all')
      setActiveProvider(null)
    } catch (exc) {
      setResponse(null)
      setError(exc instanceof Error ? exc.message : '搜索失败。')
    } finally {
      setIsSearching(false)
    }
  }

  function updateField(key: keyof SearchFormState, value: string) {
    setForm((current) => ({ ...current, [key]: value }))
  }

  async function copyLink(link: ResourceLinkResult) {
    const text = link.code ? `${link.url} 提取码：${link.code}` : link.url
    try {
      await navigator.clipboard.writeText(text)
      showToast('success', '链接已复制。')
    } catch {
      window.prompt('复制链接', text)
    }
  }

  function saveToCloud(link: ResourceLinkResult) {
    showToast('info', `保存到网盘入口已预留：${providerLabel(link.provider)}。`)
  }

  function resourceFavoritePayload(resource: ResourceCandidate): ResourceFavoriteRequest & { links: ResourceLinkResult[] } {
    return {
      id: resource.id,
      title: resource.title,
      normalized_title: resource.normalized_title,
      original_title: resource.original_title,
      year: resource.year,
      links: resource.links,
    }
  }

  function updateSearchResponse(mutator: (resource: ResourceCandidate) => ResourceCandidate) {
    setResponse((current) => {
      if (!current) return current
      return {
        ...current,
        results: current.results.map(mutator),
        source_results: current.source_results.map((group) => ({
          ...group,
          results: group.results.map(mutator),
        })),
      }
    })
  }

  async function toggleFavoriteResource(resource: ResourceCandidate) {
    try {
      if (resource.is_favorited) {
        await api.post<{ ok: boolean }>(`/resources/${encodeURIComponent(resource.id)}/unfavorite`)
        updateSearchResponse((item) => item.id === resource.id ? { ...item, is_favorited: false, favorited_at: null } : item)
        showToast('success', '已取消收藏资源。')
        return
      }
      const stored = await api.post<ResourceCandidate>('/resources/favorite', resourceFavoritePayload(resource))
      updateSearchResponse((item) => item.id === resource.id ? { ...item, is_favorited: stored.is_favorited, favorited_at: stored.favorited_at } : item)
      showToast('success', '已收藏资源。')
    } catch (exc) {
      showToast('error', exc instanceof Error ? exc.message : '收藏资源失败。')
    }
  }

  async function toggleFavoriteLink(resource: ResourceCandidate, link: ResourceLinkResult) {
    try {
      if (link.is_favorited) {
        await api.post<{ ok: boolean }>(`/resource-links/${encodeURIComponent(link.id)}/unfavorite`)
        updateSearchResponse((item) => item.id === resource.id ? {
          ...item,
          links: item.links.map((entry) => entry.id === link.id ? { ...entry, is_favorited: false, favorited_at: null } : entry),
        } : item)
        showToast('success', '已取消收藏链接。')
        return
      }
      const stored = await api.post<ResourceLinkResult>('/resource-links/favorite', {
        resource: resourceFavoritePayload(resource),
        link,
      } satisfies ResourceLinkFavoriteRequest)
      updateSearchResponse((item) => item.id === resource.id ? {
        ...item,
        links: item.links.map((entry) => entry.id === link.id ? { ...entry, is_favorited: stored.is_favorited, favorited_at: stored.favorited_at } : entry),
      } : item)
      showToast('success', '已收藏链接。')
    } catch (exc) {
      showToast('error', exc instanceof Error ? exc.message : '收藏链接失败。')
    }
  }

  const sourceTabs = useMemo(() => {
    if (!response) return []
    return [
      { id: 'all', label: '全部', count: response.count, results: response.results, error: null as string | null },
      ...response.source_results.map((group) => ({
        id: group.source_id,
        label: group.source_name,
        count: group.count,
        results: group.results,
        error: group.error,
      })),
    ]
  }, [response])

  const activeTab = sourceTabs.find((tab) => tab.id === activeResultTab) || sourceTabs[0]

  const providerFilters = useMemo(() => {
    if (!activeTab) return []
    const providerSet = new Set<string>()
    for (const resource of activeTab.results) {
      for (const link of resource.links) {
        providerSet.add(link.provider)
      }
    }
    return Array.from(providerSet).map((id) => ({
      id,
      label: providerLabel(id),
    }))
  }, [activeTab])

  return (
    <section className="sx-page" aria-labelledby="search-title">
      <Card className="sx-overview">
      <div className="sx-overview-head">
        <div>
          <p className="ui-eyebrow">搜索</p>
          <h2 id="search-title">聚合搜索</h2>
          <p className="sx-overview-lead">从代码内置搜索源聚合结果，按真实链接去重，并同步检测链接有效性。</p>
        </div>
      </div>
      </Card>

      <Card className="sx-search-card">
      <form className="sx-form" onSubmit={(event) => { event.preventDefault(); void runSearch() }}>
        <TextField helper="要搜索的片名、剧名或关键词。" label="关键词" onChange={(value) => updateField('q', value)} required value={form.q} />
        <div className="sx-form-actions">
          <Button variant="primary" disabled={isSearching} type="submit">{isSearching ? '搜索中…' : '搜索资源'}</Button>
          {isSearching ? <span className="search-loading-dot" /> : null}
        </div>
      </form>
      </Card>

      {error ? <UIErrorState message="搜索失败" sub={error} /> : null}

      {response ? (
        <Card emphasis="sunken" className="sx-results-card">
          <div className="sx-section-head"><p className="ui-eyebrow">搜索结果</p><span>{response.count} 个去重结果</span><ViewToggle value={viewMode} onChange={(m) => { setViewMode(m); window.localStorage.setItem('sundarr.viewMode', m) }} /></div>
          <div className="sx-result-tabs" role="tablist" aria-label="按媒体源查看搜索结果">
            {sourceTabs.map((tab) => (
              <button
                key={tab.id}
                type="button"
                role="tab"
                aria-selected={activeTab?.id === tab.id}
                data-active={activeTab?.id === tab.id || undefined}
                data-error={tab.error ? 'true' : undefined}
                onClick={() => { setActiveResultTab(tab.id); setActiveProvider(null) }}
              >
                <span>{tab.label}</span>
                <strong>{tab.count}</strong>
                {tab.error ? <span className="source-tab-error" title={tab.error}>!</span> : null}
              </button>
            ))}
          </div>
          {activeTab && activeTab.error ? (
            <div className="source-error-banner">
              <span className="source-error-icon">!</span>
              <span>{activeTab.label} 搜索失败：{activeTab.error}</span>
            </div>
          ) : null}
          {providerFilters.length > 0 ? (
            <div className="sx-provider-tabs" role="tablist" aria-label="按网盘类型过滤">
              <button
                type="button"
                role="tab"
                aria-selected={activeProvider === null}
                data-active={activeProvider === null || undefined}
                onClick={() => setActiveProvider(null)}
              >全部网盘</button>
              {providerFilters.map((pf) => (
                <button
                  key={pf.id}
                  type="button"
                  role="tab"
                  aria-selected={activeProvider === pf.id}
                  data-active={activeProvider === pf.id || undefined}
                  onClick={() => setActiveProvider(pf.id)}
                >
                  <span>{pf.label}</span>
                </button>
              ))}
            </div>
          ) : null}
          <div className={viewMode === 'grid' ? 'sx-results-grid' : 'sx-result-pane'} role="tabpanel">
            {activeTab && activeTab.results.length === 0 ? (
              <UIEmptyState message="没有搜索到结果" sub="可以换一个关键词或结果类型后重新搜索。" />
            ) : null}
            {activeTab?.results.map((resource) => (
              <ResourceCard
                key={resource.id}
                activeProvider={activeProvider}
                onCopyLink={(link) => void copyLink(link)}
                onFavoriteLink={(link) => void toggleFavoriteLink(resource, link)}
                onFavoriteResource={() => void toggleFavoriteResource(resource)}
                onSaveToCloud={saveToCloud}
                resource={resource}
                showToast={showToast}
                viewMode={viewMode}
              />
            ))}
          </div>
        </Card>
      ) : null}

    </section>
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

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
