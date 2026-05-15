import React, { useEffect, useState } from 'react'
import { api } from '../api/client'
import { StatusStack } from '../components/StatusStack'
import { PaginationControls } from '../components/PaginationControls'
import { StorageBrowser } from '../components/StorageBrowser'
import type {
  MediaLibraryResponse,
  MediaLibraryListResponse,
  SmbConnectionResponse,
  SmbConnectionListResponse,
  RemoteMediaLibraryResponse,
  RemoteMediaLibraryListResponse,
  StorageBrowseResponse,
  MediaLibraryFormState,
} from '../types'
import type { StatusTone } from '../ui'
import {
  Card,
  Button,
  Field,
  StatusBadge,
  LoadingState as UILoadingState,
  EmptyState as UIEmptyState,
  ErrorState as UIErrorState,
  Kbd,
} from '../ui'
import { emptyLibraryForm } from '../utils/forms'
import { normalizeLibraryPath, normalizeBrowsePath, newUuid, remoteBindingPreview } from '../utils/helpers'

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

export default function LibrariesPage({ showToast }: { showToast: (type: 'success' | 'error' | 'info', message: string) => void }) {
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
