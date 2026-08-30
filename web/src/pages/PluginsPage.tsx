import React, { useEffect, useMemo, useState } from 'react'
import { api } from '../api/client'
import type {
  PluginConfigFieldSchema,
  PluginMutationResponse,
  PluginRepositoryResponse,
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

export default function PluginsPage({ showToast }: { showToast: (type: 'success' | 'error' | 'info', message: string) => void }) {
  const [repositories, setRepositories] = useState<PluginRepositoryResponse[]>([])
  const [plugins, setPlugins] = useState<PluginResponse[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [configValues, setConfigValues] = useState<Record<string, unknown>>({})
  const [showAdd, setShowAdd] = useState(false)
  const [repoForm, setRepoForm] = useState({ name: 'Sundarr 官方插件', repo_url: OFFICIAL_REPOSITORY, branch: 'master' })
  const [isLoading, setIsLoading] = useState(true)
  const [busyKey, setBusyKey] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const selected = useMemo(() => plugins.find((item) => item.id === selectedId) || null, [plugins, selectedId])

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
      const [nextRepositories, nextPlugins] = await Promise.all([
        api.get<PluginRepositoryResponse[]>('/plugins/repositories'),
        api.get<PluginResponse[]>('/plugins/plugins'),
      ])
      setRepositories(nextRepositories)
      setPlugins(nextPlugins)
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
    } catch (exc) {
      showToast('error', exc instanceof Error ? exc.message : '操作失败。')
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

  if (isLoading && repositories.length === 0 && plugins.length === 0) return <LoadingState message="正在读取插件配置" />
  if (error && repositories.length === 0 && plugins.length === 0) return <ErrorState message="无法读取插件配置" sub={error} action={<Button onClick={() => void loadAll()}>重试</Button>} />

  return (
    <>
      <header className="page-header plugin-page-header">
        <p className="panel-kicker">Plugin runtime</p>
        <h1>插件</h1>
        <p>管理可信仓库、锁定版本和运行配置。平台 Token 在这里保存，不需要修改 API 或 Worker 环境变量。</p>
      </header>

      <section className="plugin-repository-section" aria-labelledby="plugin-repositories-title">
        <div className="section-heading">
          <div><span className="ui-eyebrow">Repositories</span><h2 id="plugin-repositories-title">插件仓库</h2></div>
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
                <div><div className="plugin-row-title"><strong>{repository.name}</strong><StatusBadge tone={statusTone(repository.status)}>{repository.status}</StatusBadge></div><code>{repository.repo_url}</code><small>{repository.branch} · {repository.current_commit?.slice(0, 10) || '尚未锁定 commit'}</small>{repository.last_error ? <p className="plugin-inline-error">{repository.last_error}</p> : null}</div>
                <div className="plugin-row-actions">
                  <Button size="sm" onClick={() => void runMutation(`update:${repository.id}`, () => api.put(`/plugins/repositories/${repository.id}`, {}), '仓库已更新。')} disabled={busyKey !== null}>检查更新</Button>
                  <Button size="sm" variant="ghost" disabled={!repository.previous_commit || busyKey !== null} onClick={() => void runMutation(`rollback:${repository.id}`, () => api.post(`/plugins/repositories/${repository.id}/rollback`), '仓库已回滚。')}>回滚</Button>
                  <Button size="sm" variant="danger" disabled={busyKey !== null} onClick={() => { if (window.confirm(`删除插件仓库“${repository.name}”及其配置？`)) void runMutation(`delete:${repository.id}`, () => api.delete(`/plugins/repositories/${repository.id}`), '插件仓库已删除。') }}>删除</Button>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>

      <section className="plugin-runtime-section" aria-labelledby="plugin-runtime-title">
        <div className="section-heading"><div><span className="ui-eyebrow">Runtime</span><h2 id="plugin-runtime-title">插件实例</h2></div><span>{plugins.length} 个</span></div>
        {plugins.length === 0 ? <EmptyState message="没有可配置的插件" sub="先添加一个包含 Manifest v2 的仓库。" /> : (
          <div className="plugin-runtime-layout">
            <div className="plugin-instance-list" role="list">
              {plugins.map((plugin) => (
                <button className="plugin-instance-button" data-selected={selectedId === plugin.id || undefined} key={plugin.id} onClick={() => selectPlugin(plugin)} type="button">
                  <span><strong>{plugin.name}</strong><small>{plugin.plugin_type} · {plugin.version}</small></span>
                  <StatusBadge tone={plugin.configuration_required ? 'paused' : statusTone(plugin.status)}>{plugin.configuration_required ? '待配置' : plugin.status}</StatusBadge>
                </button>
              ))}
            </div>
            {selected ? (
              <div className="plugin-config-pane">
                <div className="plugin-config-heading"><div><span className="ui-eyebrow">{selected.plugin_type}</span><h3>{selected.name}</h3><p>{selected.description}</p></div><StatusBadge tone={statusTone(selected.status)}>{selected.status}</StatusBadge></div>
                {selected.error ? <div className="plugin-config-error" role="alert"><strong>最近错误</strong><p>{selected.error}</p></div> : null}
                <form className="plugin-config-form" onSubmit={saveConfig}>
                  {Object.entries(selected.config_schema).map(([fieldName, field]) => (
                    <PluginConfigField key={fieldName} fieldName={fieldName} schema={field} value={configValues[fieldName]} configured={selected.config[fieldName] === '***'} onChange={(value) => setConfigValues((current) => ({ ...current, [fieldName]: value }))} />
                  ))}
                  <div className="plugin-form-actions">
                    <Button variant="primary" type="submit" disabled={busyKey !== null}>{busyKey === `save:${selected.id}` ? '正在保存…' : '保存配置'}</Button>
                    <Button type="button" disabled={busyKey !== null || selected.configuration_required} onClick={() => void runMutation(`toggle:${selected.id}`, () => api.post(`/plugins/plugins/${encodeURIComponent(selected.id)}/${selected.enabled ? 'disable' : 'enable'}`), selected.enabled ? '插件已禁用。' : '插件已启用。')}>{selected.enabled ? '禁用' : '启用'}</Button>
                  </div>
                </form>
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
