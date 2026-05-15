import React, { useEffect, useState } from 'react'
import { api } from '../api/client'
import { StatusStack } from '../components/StatusStack'
import { PaginationControls } from '../components/PaginationControls'
import { StorageBrowser } from '../components/StorageBrowser'
import { TextField } from '../components/TextField'
import type {
  RemoteMediaLibraryResponse,
  RemoteMediaLibraryListResponse,
  SmbConnectionResponse,
  SmbConnectionListResponse,
  MediaLibraryResponse,
  MediaLibraryListResponse,
  StorageBrowseResponse,
  RemoteMediaLibraryFormState,
  DtlScanResponse,
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
import { emptyRemoteLibraryForm } from '../utils/forms'
import { normalizeBrowsePath, newUuid, triStateFromBoolean, triStateToBoolean } from '../utils/helpers'
import { dtlMediaTypeLabel } from '../utils/labels'

export default function RemoteLibrariesPage({ showToast }: { showToast: (type: 'success' | 'error' | 'info', message: string) => void }) {
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
