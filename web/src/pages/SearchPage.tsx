import React, { useEffect, useMemo, useRef, useState } from 'react'
import { api } from '../api/client'
import { ResourceCard } from '../components/ResourceCard'
import { ViewToggle } from '../components/ViewToggle'
import { TextField } from '../components/TextField'
import type {
  SearchFormState,
  SearchResponse,
  ViewMode,
  ResourceCandidate,
  ResourceLinkResult,
  ResourceFavoriteRequest,
  ResourceLinkFavoriteRequest,
} from '../types'
import { formatBytes } from '../utils/format'
import { suggestedTargetPath } from '../utils/helpers'
import { providerLabel, validationLabel, linkValidationTone, mediaTypeLabel } from '../utils/labels'
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
} from '../ui'

export default function SearchPage({ showToast }: { showToast: (type: 'success' | 'error' | 'info', message: string) => void }) {
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

  useEffect(() => {
    function applyDiscoverHandoff() {
      if (window.location.pathname !== '/app/search') return
      const params = new URLSearchParams(window.location.search)
      const keyword = (params.get('q') || '').trim()
      if (!keyword) return
      setForm({ q: keyword })
      void runSearch(keyword, params.get('year'))
    }
    applyDiscoverHandoff()
    window.addEventListener('popstate', applyDiscoverHandoff)
    return () => window.removeEventListener('popstate', applyDiscoverHandoff)
  }, [])

  async function runSearch(keywordOverride?: string, yearOverride?: string | null) {
    const keyword = (keywordOverride ?? form.q).trim()
    if (!keyword) {
      setError('请输入搜索关键词。')
      return
    }

    setIsSearching(true)
    setError(null)
    try {
      const params = new URLSearchParams({ q: keyword, limit: '20' })
      if (yearOverride) params.set('year', yearOverride)
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
