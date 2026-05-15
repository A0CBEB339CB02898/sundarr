import React, { useEffect, useState } from 'react'
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
import type {
  SmbConnectionResponse,
  SmbConnectionListResponse,
  StorageBrowseResponse,
  StorageBrowseEntry,
  StorageConfigTestResponse,
  StorageFormState,
} from '../types'
import { api } from '../api/client'
import { StorageBrowser } from '../components/StorageBrowser'
import { PaginationControls } from '../components/PaginationControls'
import { StatusStack } from '../components/StatusStack'
import { newUuid, normalizeBrowsePath } from '../utils/helpers'
import { emptyStorageForm } from '../utils/forms'

export default function StoragePage({ showToast }: { showToast: (type: 'success' | 'error' | 'info', message: string) => void }) {

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
