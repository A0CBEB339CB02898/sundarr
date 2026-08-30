import React, { useEffect, useState } from 'react'
import './styles.css'
import { BrandLockup } from './ui'
import type {
  PageKey,
  ThemeMode,
  TransferResponse,
  TransferListResponse,
  NavItem,
} from './types'
import { navItems } from './types'
import { api } from './api/client'
import { storedThemeMode, applyThemeMode } from './utils/theme'
import { pageFromPath } from './utils/navigation'
import { ThemeSwitcher } from './components/ThemeSwitcher'
import { GlobalTransferPanel } from './components/GlobalTransferPanel'
import { ConfigurationGuide } from './components/ConfigurationGuide'
import { PagePanel } from './pages/PagePanel'

export default function App() {
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
    navigatePath(item.path)
    setIsDrawerOpen(false)
    if (item.key === 'transfers') {
      setIsTransferPanelOpen(false)
    }
  }

  function navigatePath(path: string) {
    window.history.pushState({}, '', path)
    setActivePage(pageFromPath(new URL(path, window.location.origin).pathname))
    setIsDrawerOpen(false)
    window.dispatchEvent(new CustomEvent('sundarr:navigation', { detail: { path } }))
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
        <ConfigurationGuide onNavigate={navigatePath} />
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
