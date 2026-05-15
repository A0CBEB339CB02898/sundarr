import React, { useEffect, useMemo, useState } from 'react'
import {
  Card,
  Button,
  StatusBadge,
  LoadingState as UILoadingState,
  EmptyState as UIEmptyState,
  ErrorState as UIErrorState,
} from '../ui'
import type {
  ResourceCandidate,
  ResourceLinkResult,
  ViewMode,
  SearchResponse,
  ResourceFavoritesListResponse,
} from '../types'
import { api } from '../api/client'
import { PaginationControls } from '../components/PaginationControls'
import { ViewToggle } from '../components/ViewToggle'
import { ResourceCard } from '../components/ResourceCard'
import { formatDate } from '../utils/format'
import { providerLabel, validationLabel, linkValidationTone } from '../utils/labels'

export default function FavoritesPage({ showToast }: { showToast: (type: 'success' | 'error' | 'info', message: string) => void }) {
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
