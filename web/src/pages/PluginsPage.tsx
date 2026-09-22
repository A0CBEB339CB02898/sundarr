import React, { useEffect, useMemo, useState } from 'react'
import { api } from '../api/client'
import type {
  PluginActivationDiagnostic,
  PluginConfigFieldSchema,
  PluginHealthCheckResponse,
  PluginMutationResponse,
  PluginRepositoryResponse,
  PluginRepositoryUpdateCheck,
  PluginResponse,
} from '../types'
import { Button, EmptyState, ErrorState, Field, LoadingState, StatusBadge } from '../ui'

const OFFICIAL_REPOSITORY = 'https://github.com/A0CBEB339CB02898/sundarr-plugin.git'

function statusTone(status: string): 'info' | 'running' | 'paused' | 'success' | 'danger' {
  if (status === 'active' || status === 'loaded') return 'success'
  if (status === 'pending' || status === 'validating') return 'running'
  if (status === 'error' || status === 'failed') return 'danger'
  return 'paused'
}

const statusLabels: Record<string, string> = {
  candidate: '候选版本',
  loaded: '已加载',
  active: '运行中',
  pending: '待处理',
  validating: '校验中',
  waiting: '等待依赖',
  disabled: '已停用',
  error: '错误',
  failed: '失败',
  disposing: '正在释放',
  disposed: '已释放',
}

const pluginTypeLabels: Record<string, string> = {
  source: '媒体源',
  catalog_provider: '目录提供方',
  watchlist_provider: '想看列表',
  transfer_driver: '传输驱动',
  notification: '通知渠道',
}

function statusLabel(status: string) {
  return statusLabels[status] || '未知状态'
}

function pluginTypeLabel(type: string) {
  return pluginTypeLabels[type] || type
}

function formatCheckedAt(value: string) {
  return new Intl.DateTimeFormat('zh-CN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value))
}

export default function PluginsPage({ showToast }: { showToast: (type: 'success' | 'error' | 'info', message: string) => void }) {
  const [repositories, setRepositories] = useState<PluginRepositoryResponse[]>([])
  const [plugins, setPlugins] = useState<PluginResponse[]>([])
  const [activations, setActivations] = useState<PluginActivationDiagnostic[]>([])
  const [repositoryChecks, setRepositoryChecks] = useState<Record<string, PluginRepositoryUpdateCheck>>({})
  const [healthResults, setHealthResults] = useState<Record<string, PluginHealthCheckResponse>>({})
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [configValues, setConfigValues] = useState<Record<string, unknown>>({})
  const [showAdd, setShowAdd] = useState(false)
  const [repoForm, setRepoForm] = useState({ name: 'Sundarr 官方插件', repo_url: OFFICIAL_REPOSITORY, branch: 'master' })
  const [isLoading, setIsLoading] = useState(true)
  const [busyKey, setBusyKey] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const selected = useMemo(() => plugins.find((item) => item.id === selectedId) || null, [plugins, selectedId])
  const selectedActivation = useMemo(
    () => activations.find((item) => item.plugin_id === selectedId) || null,
    [activations, selectedId],
  )

  useEffect(() => { void loadAll() }, [])

  useEffect(() => {
    const syncSelection = () => {
      const requested = new URLSearchParams(window.location.search).get('plugin_id')
      const target = plugins.find((item) => item.id === requested)
      if (target) selectPlugin(target)
    }
    window.addEventListener('sundarr:navigation', syncSelection)
    return () => window.removeEventListener('sundarr:navigation', syncSelection)
  }, [plugins])

  useEffect(() => {
    if (plugins.length === 0) return
    const requested = new URLSearchParams(window.location.search).get('plugin_id')
    const target = plugins.find((item) => item.id === requested) || plugins.find((item) => item.id === selectedId) || plugins[0]
    if (target.id !== selectedId) selectPlugin(target)
  }, [plugins])

  async function loadAll() {
    setIsLoading(true)
    setError(null)
    try {
      const [nextRepositories, nextPlugins, nextActivations] = await Promise.all([
        api.get<PluginRepositoryResponse[]>('/plugins/repositories'),
        api.get<PluginResponse[]>('/plugins/plugins'),
        api.get<PluginActivationDiagnostic[]>('/plugins/activations'),
      ])
      setRepositories(nextRepositories)
      setPlugins(nextPlugins)
      setActivations(nextActivations)
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : '无法读取插件状态。')
    } finally {
      setIsLoading(false)
    }
  }

  function selectPlugin(plugin: PluginResponse) {
    setSelectedId(plugin.id)
    const next: Record<string, unknown> = {}
    Object.entries(plugin.config_schema).forEach(([fieldName, field]) => {
      const current = plugin.config[fieldName]
      next[fieldName] = field.type === 'password' && current === '***' ? '' : (current ?? field.default ?? (field.type === 'boolean' ? false : ''))
    })
    setConfigValues(next)
  }

  async function runMutation(key: string, action: () => Promise<unknown>, successMessage: string) {
    setBusyKey(key)
    try {
      await action()
      showToast('success', successMessage)
      await loadAll()
      window.dispatchEvent(new CustomEvent('sundarr:configuration-changed'))
      return true
    } catch (exc) {
      showToast('error', exc instanceof Error ? exc.message : '操作失败。')
      return false
    } finally {
      setBusyKey(null)
    }
  }

  async function addRepository(event: React.FormEvent) {
    event.preventDefault()
    await runMutation('add-repository', () => api.post<PluginMutationResponse>('/plugins/repositories', {
      name: repoForm.name.trim() || undefined,
      repo_url: repoForm.repo_url.trim(),
      branch: repoForm.branch.trim() || 'main',
    }), '插件仓库已添加，缺少必填配置的插件保持禁用。')
    setShowAdd(false)
  }

  async function saveConfig(event: React.FormEvent) {
    event.preventDefault()
    if (!selected) return
    const payload: Record<string, unknown> = {}
    for (const [fieldName, field] of Object.entries(selected.config_schema)) {
      const value = configValues[fieldName]
      if (field.type === 'password' && value === '' && selected.config[fieldName] === '***') payload[fieldName] = '***'
      else if (field.type === 'integer' && value !== '') payload[fieldName] = Number(value)
      else payload[fieldName] = value
    }
    await runMutation(`save:${selected.id}`, () => api.put(`/plugins/plugins/${encodeURIComponent(selected.id)}/config`, { config_data: payload }), '插件配置已保存。')
  }

  async function checkRepository(repository: PluginRepositoryResponse) {
    const key = `check:${repository.id}`
    setBusyKey(key)
    try {
      const result = await api.post<PluginRepositoryUpdateCheck>(`/plugins/repositories/${repository.id}/check`)
      setRepositoryChecks((current) => ({ ...current, [repository.id]: result }))
      showToast(result.update_available ? 'info' : 'success', result.update_available ? '发现新版本，请确认后应用。' : '当前已经是最新版本。')
      await loadAll()
    } catch (exc) {
      showToast('error', exc instanceof Error ? exc.message : '检查更新失败。')
    } finally {
      setBusyKey(null)
    }
  }

  async function applyRepositoryUpdate(repository: PluginRepositoryResponse, check: PluginRepositoryUpdateCheck) {
    const updated = await runMutation(
      `update:${repository.id}`,
      () => api.put(`/plugins/repositories/${repository.id}`, { new_commit: check.latest_commit }),
      '候选版本校验通过，仓库已更新。',
    )
    if (!updated) return
    setRepositoryChecks((current) => {
      const next = { ...current }
      delete next[repository.id]
      return next
    })
  }

  async function testPlugin(plugin: PluginResponse) {
    const key = `test:${plugin.id}`
    setBusyKey(key)
    try {
      const result = await api.post<PluginHealthCheckResponse>(`/plugins/plugins/${encodeURIComponent(plugin.id)}/test`)
      setHealthResults((current) => ({ ...current, [plugin.id]: result }))
      showToast(result.ok ? 'success' : 'error', result.message)
    } catch (exc) {
      showToast('error', exc instanceof Error ? exc.message : '健康检查失败。')
    } finally {
      setBusyKey(null)
    }
  }

  if (isLoading && repositories.length === 0 && plugins.length === 0) return <LoadingState message="正在读取插件配置" />
  if (error && repositories.length === 0 && plugins.length === 0) return <ErrorState message="无法读取插件配置" sub={error} action={<Button onClick={() => void loadAll()}>重试</Button>} />

  return (
    <>
      <header className="page-header plugin-page-header">
        <p className="panel-kicker">插件运行环境</p>
        <h1>插件</h1>
        <p>管理可信仓库、锁定版本和运行配置。平台 Token 在这里保存，不需要修改 API 或 Worker 环境变量。</p>
      </header>

      <section className="plugin-repository-section" aria-labelledby="plugin-repositories-title">
        <div className="section-heading">
          <div><span className="ui-eyebrow">插件仓库</span><h2 id="plugin-repositories-title">插件仓库</h2></div>
          <Button variant="primary" onClick={() => setShowAdd((value) => !value)}>{showAdd ? '收起' : '添加仓库'}</Button>
        </div>
        {showAdd ? (
          <form className="plugin-repository-form" onSubmit={addRepository}>
            <Field label="显示名称" htmlFor="plugin-repo-name"><input id="plugin-repo-name" value={repoForm.name} onChange={(event) => setRepoForm({ ...repoForm, name: event.target.value })} /></Field>
            <Field label="Git 仓库地址" htmlFor="plugin-repo-url" helper="只添加你信任的 Python 插件仓库。"><input id="plugin-repo-url" required value={repoForm.repo_url} onChange={(event) => setRepoForm({ ...repoForm, repo_url: event.target.value })} /></Field>
            <Field label="分支" htmlFor="plugin-repo-branch"><input id="plugin-repo-branch" required value={repoForm.branch} onChange={(event) => setRepoForm({ ...repoForm, branch: event.target.value })} /></Field>
            <div className="plugin-form-actions"><Button variant="primary" type="submit" disabled={busyKey === 'add-repository'}>{busyKey === 'add-repository' ? '正在添加…' : '添加并检查'}</Button></div>
          </form>
        ) : null}
        {repositories.length === 0 ? <EmptyState message="还没有插件仓库" sub="添加官方仓库后，再为各插件填写运行配置。" /> : (
          <div className="plugin-repository-list">
            {repositories.map((repository) => (
              <article className="plugin-repository-row" key={repository.id}>
                <div><div className="plugin-row-title"><strong>{repository.name}</strong><StatusBadge tone={statusTone(repository.status)}>{statusLabel(repository.status)}</StatusBadge></div><code>{repository.repo_url}</code><small>{repository.branch} · {repository.current_commit?.slice(0, 10) || '尚未锁定 commit'}</small>{repositoryChecks[repository.id] ? <p className="plugin-update-note" data-update-available={repositoryChecks[repository.id].update_available || undefined}>{repositoryChecks[repository.id].update_available ? `发现新版本 ${repositoryChecks[repository.id].latest_commit.slice(0, 10)}，应用前会先做候选校验。` : `已是最新版本 · ${formatCheckedAt(repositoryChecks[repository.id].checked_at)}`}</p> : null}{repository.last_error ? <p className="plugin-inline-error">{repository.last_error}</p> : null}</div>
                <div className="plugin-row-actions">
                  <Button size="sm" onClick={() => void checkRepository(repository)} disabled={busyKey !== null}>{busyKey === `check:${repository.id}` ? '正在检查…' : '检查更新'}</Button>
                  {repositoryChecks[repository.id]?.update_available ? <Button size="sm" variant="primary" onClick={() => void applyRepositoryUpdate(repository, repositoryChecks[repository.id])} disabled={busyKey !== null}>{busyKey === `update:${repository.id}` ? '正在应用…' : '应用更新'}</Button> : null}
                  <Button size="sm" variant="ghost" disabled={!repository.previous_commit || busyKey !== null} onClick={() => void runMutation(`rollback:${repository.id}`, () => api.post(`/plugins/repositories/${repository.id}/rollback`), '仓库已回滚。')}>回滚</Button>
                  <Button size="sm" variant="danger" disabled={busyKey !== null} onClick={() => { if (window.confirm(`删除插件仓库“${repository.name}”及其配置？`)) void runMutation(`delete:${repository.id}`, () => api.delete(`/plugins/repositories/${repository.id}`), '插件仓库已删除。') }}>删除</Button>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>

      <section className="plugin-runtime-section" aria-labelledby="plugin-runtime-title">
        <div className="section-heading"><div><span className="ui-eyebrow">插件实例</span><h2 id="plugin-runtime-title">插件实例</h2></div><span>{plugins.length} 个</span></div>
        {plugins.length === 0 ? <EmptyState message="没有可配置的插件" sub="先添加一个包含 Manifest v2 的仓库。" /> : (
          <div className="plugin-runtime-layout">
            <div className="plugin-instance-list" role="list">
              {plugins.map((plugin) => (
                <button className="plugin-instance-button" data-selected={selectedId === plugin.id || undefined} key={plugin.id} onClick={() => selectPlugin(plugin)} type="button">
                  <span><strong>{plugin.name}</strong><small>{pluginTypeLabel(plugin.plugin_type)} · {plugin.version}</small></span>
                  <StatusBadge tone={plugin.configuration_required ? 'paused' : statusTone(plugin.status)}>{plugin.configuration_required ? '待配置' : statusLabel(plugin.status)}</StatusBadge>
                </button>
              ))}
            </div>
            {selected ? (
              <div className="plugin-config-pane">
                <div className="plugin-config-heading"><div><span className="ui-eyebrow">{pluginTypeLabel(selected.plugin_type)}</span><h3>{selected.name}</h3><p>{selected.description}</p></div><StatusBadge tone={statusTone(selected.status)}>{statusLabel(selected.status)}</StatusBadge></div>
                {selected.error ? <div className="plugin-config-error" role="alert"><strong>最近错误</strong><p>{selected.error}</p></div> : null}
                <form className="plugin-config-form" onSubmit={saveConfig}>
                  {Object.entries(selected.config_schema).map(([fieldName, field]) => (
                    <PluginConfigField key={fieldName} fieldName={fieldName} schema={field} value={configValues[fieldName]} configured={selected.config[fieldName] === '***'} onChange={(value) => setConfigValues((current) => ({ ...current, [fieldName]: value }))} />
                  ))}
                  <div className="plugin-form-actions">
                    <Button variant="primary" type="submit" disabled={busyKey !== null}>{busyKey === `save:${selected.id}` ? '正在保存…' : '保存配置'}</Button>
                    <Button type="button" disabled={busyKey !== null || selected.configuration_required} onClick={() => void runMutation(`toggle:${selected.id}`, () => api.post(`/plugins/plugins/${encodeURIComponent(selected.id)}/${selected.enabled ? 'disable' : 'enable'}`), selected.enabled ? '插件已禁用。' : '插件已启用。')}>{selected.enabled ? '禁用' : '启用'}</Button>
                    <Button type="button" variant="ghost" disabled={busyKey !== null || selected.status !== 'active'} onClick={() => void testPlugin(selected)}>{busyKey === `test:${selected.id}` ? '正在检查…' : '运行健康检查'}</Button>
                  </div>
                </form>
                {healthResults[selected.id] ? (
                  <div className="plugin-health-result" data-ok={healthResults[selected.id].ok || undefined} role="status" aria-live="polite">
                    <div><strong>{healthResults[selected.id].ok ? '健康检查通过' : '健康检查失败'}</strong><time dateTime={healthResults[selected.id].checked_at}>{formatCheckedAt(healthResults[selected.id].checked_at)}</time></div>
                    <p>{healthResults[selected.id].message}</p>
                  </div>
                ) : null}
                <details className="plugin-diagnostics">
                  <summary>Activation 诊断</summary>
                  {selectedActivation ? (
                    <dl>
                      <div><dt>运行状态</dt><dd>{statusLabel(selectedActivation.status)}</dd></div>
                      <div><dt>锁定版本</dt><dd><code>{selectedActivation.commit_hash.slice(0, 12)}</code></dd></div>
                      <div><dt>启动时间</dt><dd>{selectedActivation.activated_at ? formatCheckedAt(selectedActivation.activated_at) : '未记录'}</dd></div>
                      <div><dt>依赖能力</dt><dd>{selectedActivation.requires.join('、') || '无'}</dd></div>
                      <div><dt>提供能力</dt><dd>{selectedActivation.provides.join('、') || '无'}</dd></div>
                      <div><dt>清理钩子</dt><dd>{selectedActivation.cleanup_count} 个</dd></div>
                    </dl>
                  ) : <p>当前进程中没有这个插件的 Activation。启用插件或检查最近错误后再试。</p>}
                </details>
              </div>
            ) : null}
          </div>
        )}
      </section>
    </>
  )
}

function PluginConfigField({ fieldName, schema, value, configured, onChange }: { fieldName: string; schema: PluginConfigFieldSchema; value: unknown; configured: boolean; onChange: (value: unknown) => void }) {
  const label = `${schema.label || fieldName}${schema.required ? ' *' : ''}`
  if (schema.type === 'boolean') return <label className="plugin-toggle"><input type="checkbox" checked={Boolean(value)} onChange={(event) => onChange(event.target.checked)} /><span><strong>{label}</strong><small>{schema.placeholder || '开启后立即应用到下一次插件请求。'}</small></span></label>
  if (schema.type === 'select') return <Field label={label} htmlFor={`plugin-field-${fieldName}`}><select id={`plugin-field-${fieldName}`} value={String(value ?? '')} onChange={(event) => onChange(event.target.value)}>{(schema.options || []).map((option) => <option key={option} value={option}>{option}</option>)}</select></Field>
  const helper = schema.type === 'password' && configured ? '已安全保存。留空表示保留原值。' : undefined
  return <Field label={label} htmlFor={`plugin-field-${fieldName}`} helper={helper}><input id={`plugin-field-${fieldName}`} type={schema.type === 'password' ? 'password' : schema.type === 'integer' ? 'number' : 'text'} required={schema.required && !(schema.type === 'password' && configured)} autoComplete="off" placeholder={schema.placeholder} value={String(value ?? '')} onChange={(event) => onChange(event.target.value)} /></Field>
}
