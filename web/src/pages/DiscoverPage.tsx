import React, { useEffect, useMemo, useState } from 'react'
import { api } from '../api/client'
import type {
  CatalogProvider,
  DiscoverPageResponse,
  MediaSubjectDetail,
  MediaSubjectSummary,
  WatchlistPageResponse,
} from '../types'
import { Button, Card, EmptyState, ErrorState, LoadingState } from '../ui'

type DiscoverSection = {
  key: string
  title: string
  description: string
  items: MediaSubjectSummary[]
  error?: string
}

type FilterState = {
  provider_id: string
  q: string
  media_type: string
  genre: string
  region: string
  year_from: string
  year_to: string
  sort: string
}

const emptyFilters: FilterState = {
  provider_id: '',
  q: '',
  media_type: '',
  genre: '',
  region: '',
  year_from: '',
  year_to: '',
  sort: '',
}

function filtersForOperation(provider: CatalogProvider | undefined, operation: string) {
  return provider?.operation_filters && operation in provider.operation_filters
    ? provider.operation_filters[operation]
    : provider?.filters || []
}

function sortsForOperation(provider: CatalogProvider | undefined, operation: string) {
  return provider?.operation_sorts && operation in provider.operation_sorts
    ? provider.operation_sorts[operation]
    : provider?.sorts || []
}

function filtersFromUrl(): FilterState {
  const params = new URLSearchParams(window.location.search)
  return {
    provider_id: params.get('provider_id') || '',
    q: params.get('q') || '',
    media_type: params.get('media_type') || '',
    genre: params.get('genre') || '',
    region: params.get('region') || '',
    year_from: params.get('year_from') || '',
    year_to: params.get('year_to') || '',
    sort: params.get('sort') || '',
  }
}

function detailIdFromPath() {
  const match = window.location.pathname.match(/^\/app\/discover\/([^/]+)$/)
  return match ? decodeURIComponent(match[1]) : null
}

export default function DiscoverPage({ showToast }: { showToast: (type: 'success' | 'error' | 'info', message: string) => void }) {
  const [filters, setFilters] = useState<FilterState>(filtersFromUrl)
  const [providers, setProviders] = useState<CatalogProvider[]>([])
  const [sections, setSections] = useState<DiscoverSection[]>([])
  const [results, setResults] = useState<DiscoverPageResponse | null>(null)
  const [detail, setDetail] = useState<MediaSubjectDetail | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [locationVersion, setLocationVersion] = useState(0)

  const activeProvider = providers.find((provider) => provider.id === filters.provider_id) || providers[0]
  const activeOperation = filters.q.trim() ? 'search' : 'categories'
  const availableFilters = filtersForOperation(activeProvider, activeOperation)
  const availableSorts = sortsForOperation(activeProvider, activeOperation)
  const genreOptions = activeProvider?.filter_options.genre || []
  const regionOptions = activeProvider?.filter_options.region || []
  const hasCriteria = Boolean(
    filters.q || filters.media_type || filters.genre || filters.region
    || filters.year_from || filters.year_to || filters.sort,
  )

  useEffect(() => {
    const onPopState = () => {
      setFilters(filtersFromUrl())
      setLocationVersion((value) => value + 1)
    }
    window.addEventListener('popstate', onPopState)
    return () => window.removeEventListener('popstate', onPopState)
  }, [])

  useEffect(() => { void loadPage() }, [locationVersion])

  async function loadPage(forceRefresh = false) {
    setIsLoading(true)
    setError(null)
    try {
      const providerItems = await api.get<CatalogProvider[]>('/discover/providers')
      setProviders(providerItems)
      const selectedProvider = providerItems.find((provider) => provider.id === filters.provider_id) || providerItems[0]
      const providerId = selectedProvider?.id
      const detailId = detailIdFromPath()
      if (detailId) {
        const params = new URLSearchParams()
        if (providerId) params.set('provider_id', providerId)
        if (forceRefresh) params.set('refresh', 'true')
        const suffix = params.size ? `?${params.toString()}` : ''
        setDetail(await api.get<MediaSubjectDetail>(`/discover/${encodeURIComponent(detailId)}${suffix}`))
        setResults(null)
        setSections([])
        return
      }
      setDetail(null)
      if (providerItems.length === 0) {
        setResults(null)
        setSections([])
        return
      }
      if (hasCriteria) {
        const params = queryParams(forceRefresh, filters, providerId)
        const endpoint = filters.q.trim() ? '/discover/search' : '/discover/categories'
        setResults(await api.get<DiscoverPageResponse>(`${endpoint}?${params.toString()}`))
        setSections([])
      } else {
        setResults(null)
        await loadHomeSections(forceRefresh, providerId)
      }
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : '无法加载媒体发现内容。')
    } finally {
      setIsLoading(false)
    }
  }

  async function loadHomeSections(forceRefresh: boolean, providerId?: string) {
    const catalogParams = new URLSearchParams({ limit: '12' })
    if (providerId) catalogParams.set('provider_id', providerId)
    if (forceRefresh) catalogParams.set('refresh', 'true')
    const definitions = [
      { key: 'movie', title: '热门电影', description: '当前目录 Provider 返回的电影趋势', path: `/discover/trending?media_type=movie&${catalogParams.toString()}` },
      { key: 'series', title: '热门剧集', description: '当前目录 Provider 返回的剧集趋势', path: `/discover/trending?media_type=series&${catalogParams.toString()}` },
      { key: 'category', title: '分类推荐', description: '按当前目录能力生成的推荐', path: `/discover/categories?${catalogParams.toString()}` },
      { key: 'watchlist', title: '关注更新', description: '外部想看列表同步到 Sundarr 的条目', path: '/discover/watchlist?limit=12' },
    ]
    const loaded = await Promise.allSettled(definitions.map((item) => api.get<DiscoverPageResponse | WatchlistPageResponse>(item.path)))
    setSections(definitions.map((definition, index) => {
      const outcome = loaded[index]
      if (outcome.status === 'rejected') {
        return { ...definition, items: [], error: outcome.reason instanceof Error ? outcome.reason.message : '加载失败' }
      }
      return { ...definition, items: outcome.value.items }
    }))
  }

  function queryParams(forceRefresh = false, state = filters, providerId?: string) {
    const params = new URLSearchParams()
    Object.entries(state).forEach(([key, value]) => {
      if (value.trim()) params.set(key, value.trim())
    })
    if (providerId) params.set('provider_id', providerId)
    params.set('limit', '24')
    if (forceRefresh) params.set('refresh', 'true')
    return params
  }

  function submit(event: React.FormEvent) {
    event.preventDefault()
    const params = queryParams()
    params.delete('limit')
    const query = params.toString()
    window.history.pushState({}, '', `/app/discover${query ? `?${query}` : ''}`)
    setLocationVersion((value) => value + 1)
  }

  function updateKeyword(value: string) {
    const operation = value.trim() ? 'search' : 'categories'
    const nextFilters = filtersForOperation(activeProvider, operation)
    const nextSorts = sortsForOperation(activeProvider, operation)
    setFilters({
      ...filters,
      q: value,
      genre: nextFilters.includes('genre') ? filters.genre : '',
      region: nextFilters.includes('region') ? filters.region : '',
      year_from: nextFilters.includes('year') ? filters.year_from : '',
      year_to: nextFilters.includes('year') ? filters.year_to : '',
      sort: nextSorts.includes(filters.sort) ? filters.sort : '',
    })
  }

  function changeProvider(providerId: string) {
    const provider = providers.find((item) => item.id === providerId)
    if (!provider) return
    const operation = filters.q.trim() ? 'search' : 'categories'
    const nextFilters = filtersForOperation(provider, operation)
    const nextSorts = sortsForOperation(provider, operation)
    const genreValues = new Set((provider.filter_options.genre || []).map((item) => item.value))
    const regionValues = new Set((provider.filter_options.region || []).map((item) => item.value))
    const nextState: FilterState = {
      ...filters,
      provider_id: providerId,
      genre: nextFilters.includes('genre') && genreValues.has(filters.genre) ? filters.genre : '',
      region: nextFilters.includes('region') && regionValues.has(filters.region) ? filters.region : '',
      year_from: nextFilters.includes('year') ? filters.year_from : '',
      year_to: nextFilters.includes('year') ? filters.year_to : '',
      sort: nextSorts.includes(filters.sort) ? filters.sort : '',
    }
    setFilters(nextState)
    const params = queryParams(false, nextState, providerId)
    params.delete('limit')
    window.history.pushState({}, '', `/app/discover?${params.toString()}`)
    setLocationVersion((value) => value + 1)
  }

  function clearFilters() {
    const nextState = { ...emptyFilters, provider_id: activeProvider?.id || '' }
    setFilters(nextState)
    const query = nextState.provider_id ? `?provider_id=${encodeURIComponent(nextState.provider_id)}` : ''
    window.history.pushState({}, '', `/app/discover${query}`)
    setLocationVersion((value) => value + 1)
  }

  function openDetail(item: MediaSubjectSummary) {
    const discoverReturn = `${window.location.pathname}${window.location.search}`
    const providerId = activeProvider?.id || item.provider_id
    const query = providerId ? `?provider_id=${encodeURIComponent(providerId)}` : ''
    window.history.pushState({ discoverReturn }, '', `/app/discover/${encodeURIComponent(item.media_subject_id)}${query}`)
    setLocationVersion((value) => value + 1)
  }

  function returnToDiscover() {
    const discoverReturn = window.history.state?.discoverReturn
    const target = typeof discoverReturn === 'string' && discoverReturn.startsWith('/app/discover')
      ? discoverReturn
      : '/app/discover'
    window.history.pushState({}, '', target)
    setFilters(filtersFromUrl())
    setLocationVersion((value) => value + 1)
  }

  function searchResources(item: MediaSubjectSummary | MediaSubjectDetail) {
    const params = new URLSearchParams({ q: item.canonical_title })
    if (item.release_year) params.set('year', String(item.release_year))
    window.history.pushState({}, '', `/app/search?${params.toString()}`)
    window.dispatchEvent(new PopStateEvent('popstate'))
  }

  async function toggleFollow() {
    if (!detail) return
    try {
      if (detail.followed) {
        await api.delete(`/discover/${encodeURIComponent(detail.media_subject_id)}/follow`)
      } else {
        await api.post(`/discover/${encodeURIComponent(detail.media_subject_id)}/follow`)
      }
      setDetail({ ...detail, followed: !detail.followed })
      showToast('success', detail.followed ? '已取消关注。' : '已加入关注。')
    } catch (exc) {
      showToast('error', exc instanceof Error ? exc.message : '关注状态更新失败。')
    }
  }

  const resultTitle = useMemo(() => filters.q.trim() ? `“${filters.q.trim()}”的目录结果` : '筛选结果', [filters.q])

  return (
    <section className="dc-page" aria-labelledby="discover-title">
      <header className="dc-header">
        <div>
          <p className="ui-eyebrow">媒体发现</p>
          <h2 id="discover-title">{detail ? detail.canonical_title : '发现下一部想看的内容'}</h2>
          <p>{detail ? '目录详情来自当前启用的真实 Provider。' : '浏览目录、热门与关注更新，再进入资源搜索。'}</p>
        </div>
        <Button variant="secondary" onClick={() => void loadPage(true)} disabled={isLoading}>刷新真实数据</Button>
      </header>

      {detail ? (
        <DetailView detail={detail} onBack={returnToDiscover} onFollow={() => void toggleFollow()} onSearch={() => searchResources(detail)} />
      ) : (
        <>
          <form className={`dc-filters${providers.length > 1 ? ' dc-filters-multi' : ''}`} onSubmit={submit}>
            <label className="dc-search-field"><span>目录搜索</span><input value={filters.q} onChange={(event) => updateKeyword(event.target.value)} placeholder="输入电影或剧集名称" /></label>
            {providers.length > 1 ? <label className="dc-provider-field"><span>数据来源</span><select value={activeProvider?.id || ''} onChange={(event) => changeProvider(event.target.value)}>{providers.map((provider) => <option key={provider.id} value={provider.id}>{provider.attribution?.provider_name || provider.id}</option>)}</select></label> : null}
            <label><span>类型</span><select value={filters.media_type} disabled={!availableFilters.includes('media_type')} onChange={(event) => setFilters({ ...filters, media_type: event.target.value })}><option value="">全部</option>{activeProvider?.media_types.includes('movie') !== false ? <option value="movie">电影</option> : null}{activeProvider?.media_types.includes('series') !== false ? <option value="series">剧集</option> : null}</select></label>
            {genreOptions.length ? <label><span>题材{availableFilters.includes('genre') ? '' : '（当前操作不可用）'}</span><select value={filters.genre} disabled={!availableFilters.includes('genre')} onChange={(event) => setFilters({ ...filters, genre: event.target.value })}><option value="">全部</option>{genreOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select></label> : null}
            {regionOptions.length ? <label><span>地区{availableFilters.includes('region') ? '' : '（当前操作不可用）'}</span><select value={filters.region} disabled={!availableFilters.includes('region')} onChange={(event) => setFilters({ ...filters, region: event.target.value })}><option value="">全部</option>{regionOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select></label> : null}
            <label><span>起始年份{availableFilters.includes('year') ? '' : '（当前操作不可用）'}</span><input type="number" min="1" disabled={!availableFilters.includes('year')} value={filters.year_from} onChange={(event) => setFilters({ ...filters, year_from: event.target.value })} /></label>
            <label><span>结束年份{availableFilters.includes('year') ? '' : '（当前操作不可用）'}</span><input type="number" min="1" disabled={!availableFilters.includes('year')} value={filters.year_to} onChange={(event) => setFilters({ ...filters, year_to: event.target.value })} /></label>
            <label><span>排序{availableSorts.length ? '' : '（当前操作不可用）'}</span><select value={filters.sort} disabled={!availableSorts.length} onChange={(event) => setFilters({ ...filters, sort: event.target.value })}><option value="">Provider 默认</option>{availableSorts.includes('popularity') ? <option value="popularity">热度</option> : null}{availableSorts.includes('rating') ? <option value="rating">评分</option> : null}{availableSorts.includes('release_date') ? <option value="release_date">上映时间</option> : null}</select></label>
            <div className="dc-filter-actions"><Button variant="primary" type="submit">应用</Button>{hasCriteria ? <Button variant="ghost" onClick={clearFilters}>清除</Button> : null}</div>
          </form>

          {isLoading ? <LoadingState message="正在读取目录" sub="请求当前启用的真实 Provider。" /> : null}
          {error ? <ErrorState message="媒体发现暂不可用" sub={error} action={<Button onClick={() => void loadPage(true)}>重试</Button>} /> : null}
          {!isLoading && !error && providers.length === 0 ? <EmptyState message="尚未启用目录 Provider" sub="先在插件仓库中安装并启用 CATALOG_PROVIDER，Core 不会生成占位媒体数据。" /> : null}
          {!isLoading && !error && results ? <ResultSection title={resultTitle} description={results.degraded ? 'Provider 不可用，当前展示降级缓存。' : `数据来自 ${results.provider_id}`} items={results.items} degraded={results.degraded} onOpen={openDetail} onSearch={searchResources} /> : null}
          {!isLoading && !error && !results ? sections.map((section) => <ResultSection key={section.key} title={section.title} description={section.error || section.description} items={section.items} degraded={Boolean(section.error)} onOpen={openDetail} onSearch={searchResources} />) : null}
        </>
      )}
      {activeProvider?.attribution ? (
        <aside className="dc-attribution" aria-label="数据来源">
          <div>
            <span>数据来源</span>
            <a href={activeProvider.attribution.homepage_url} target="_blank" rel="noreferrer">
              {activeProvider.attribution.logo_url ? <img src={activeProvider.attribution.logo_url} alt={activeProvider.attribution.provider_name} /> : <strong>{activeProvider.attribution.provider_name}</strong>}
            </a>
          </div>
          <p>{activeProvider.attribution.notice}</p>
        </aside>
      ) : null}
    </section>
  )
}

function ResultSection({ title, description, items, degraded, onOpen, onSearch }: { title: string; description: string; items: MediaSubjectSummary[]; degraded: boolean; onOpen: (item: MediaSubjectSummary) => void; onSearch: (item: MediaSubjectSummary) => void }) {
  return (
    <section className="dc-section" aria-label={title}>
      <div className="dc-section-heading"><div><h3>{title}</h3><p>{description}</p></div>{degraded ? <span className="dc-degraded">降级</span> : null}</div>
      {items.length ? <div className="dc-poster-grid">{items.map((item) => <MediaPoster key={item.media_subject_id} item={item} onOpen={() => onOpen(item)} onSearch={() => onSearch(item)} />)}</div> : <EmptyState message="当前分区没有内容" sub={degraded ? '该分区失败，其他分区仍可继续使用。' : 'Provider 暂未返回符合条件的条目。'} />}
    </section>
  )
}

function MediaPoster({ item, onOpen, onSearch }: { item: MediaSubjectSummary; onOpen: () => void; onSearch: () => void }) {
  return (
    <article className="dc-poster">
      <button className="dc-poster-image" type="button" onClick={onOpen} aria-label={`查看 ${item.canonical_title} 详情`}>
        <PosterImage item={item} alt="" loading="lazy" />
        {item.watchlisted || item.followed ? <span className="dc-poster-state">{item.watchlisted ? '想看' : '关注'}</span> : null}
      </button>
      <div className="dc-poster-copy"><button type="button" onClick={onOpen}>{item.canonical_title}</button><p>{item.release_year || '年份未知'} · {item.media_type === 'movie' ? '电影' : '剧集'}</p></div>
      <Button size="sm" variant="ghost" onClick={onSearch}>查找资源</Button>
    </article>
  )
}

function DetailView({ detail, onBack, onFollow, onSearch }: { detail: MediaSubjectDetail; onBack: () => void; onFollow: () => void; onSearch: () => void }) {
  return (
    <div className="dc-detail">
      <Button variant="ghost" onClick={onBack}>返回发现</Button>
      <div className="dc-detail-layout">
        <div className="dc-detail-poster"><PosterImage item={detail} alt={`${detail.canonical_title} 海报`} /></div>
        <div className="dc-detail-copy">
          <p className="ui-eyebrow">{detail.media_type === 'movie' ? '电影' : '剧集'} · {detail.release_year || '年份未知'}</p>
          {detail.original_title ? <p className="dc-original-title">{detail.original_title}</p> : null}
          {detail.degraded ? <p className="dc-inline-warning">Provider 当前不可用，以下为已保存的最小快照或缓存。</p> : null}
          <p className="dc-overview">{detail.overview || 'Provider 暂未返回简介。'}</p>
          <dl className="dc-facts">
            <div><dt>题材</dt><dd>{detail.genres.join('、') || '未知'}</dd></div>
            <div><dt>地区</dt><dd>{detail.regions.join('、') || '未知'}</dd></div>
            <div><dt>评分</dt><dd>{detail.rating !== null ? `${detail.rating.toFixed(1)} · ${detail.rating_provider}` : '暂无'}</dd></div>
            <div><dt>外部 ID</dt><dd>{Object.entries(detail.external_ids).map(([key, value]) => `${key}: ${value}`).join(' · ')}</dd></div>
          </dl>
          <div className="dc-detail-actions"><Button variant="primary" onClick={onSearch}>查找具体资源</Button><Button onClick={onFollow}>{detail.followed ? '取消关注' : '加入关注'}</Button></div>
        </div>
      </div>
    </div>
  )
}

function PosterImage({ item, alt, loading }: {
  item: MediaSubjectSummary
  alt: string
  loading?: 'eager' | 'lazy'
}) {
  const [source, setSource] = useState(item.poster_url)
  const [failed, setFailed] = useState(false)
  const relayUrl = `/discover/${encodeURIComponent(item.media_subject_id)}/poster?provider_id=${encodeURIComponent(item.provider_id)}`

  useEffect(() => {
    setSource(item.poster_url)
    setFailed(false)
  }, [item.media_subject_id, item.poster_url, item.provider_id])

  if (!source || failed) return <span aria-hidden="true">暂无海报</span>
  return (
    <img
      src={source}
      alt={alt}
      loading={loading}
      onError={() => {
        if (source !== relayUrl) setSource(relayUrl)
        else setFailed(true)
      }}
    />
  )
}
