import React, { useEffect, useRef, useState } from 'react'
import { api } from '../api/client'
import type {
  CatalogFilterOption,
  CatalogProvider,
  DiscoverPageResponse,
  MediaSubjectDetail,
  MediaSubjectSummary,
  SnapshotHydrationResponse,
  WatchlistPageResponse,
  YearHydrationResponse,
} from '../types'
import { Button, EmptyState, ErrorState, LoadingState } from '../ui'
import SearchPage from './SearchPage'
import { DiscoverFilters } from './discover/DiscoverFilters'
import { DetailView, ResultSection } from './discover/DiscoverResults'
import type {
  ActiveFilter,
  CategoryKey,
  DiscoverSection,
  FilterState,
  HomeSectionKey,
} from './discover/model'
import {
  apiQueryParams,
  categoryGenreLabels,
  categoryItems,
  chunkItems,
  detailIdFromPath,
  emptyFilters,
  filtersForOperation,
  filtersFromUrl,
  homeSectionItems,
  isResourceModeFromLocation,
  mergeUniqueItems,
  optionForCategory,
  optionLabel,
  orderedOptions,
  preferredGenreLabels,
  preferredRegions,
  providerRecognizesItem,
  remapValue,
  sortItems,
  sortsForOperation,
  urlParams,
  yearFilterLabel,
} from './discover/model'

export default function DiscoverPage({ showToast }: { showToast: (type: 'success' | 'error' | 'info', message: string) => void }) {
  const initialFilters = filtersFromUrl()
  const [filters, setFilters] = useState<FilterState>(initialFilters)
  const [searchDraft, setSearchDraft] = useState(initialFilters.q)
  const [providers, setProviders] = useState<CatalogProvider[]>([])
  const [sections, setSections] = useState<DiscoverSection[]>([])
  const [results, setResults] = useState<DiscoverPageResponse | null>(null)
  const [detail, setDetail] = useState<MediaSubjectDetail | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [unsupportedCategory, setUnsupportedCategory] = useState<string | null>(null)
  const [showExactYears, setShowExactYears] = useState(
    Boolean(initialFilters.year_from && initialFilters.year_from === initialFilters.year_to),
  )
  const [showOtherRegions, setShowOtherRegions] = useState(false)
  const [locationVersion, setLocationVersion] = useState(0)
  const [isLoadingMoreResults, setIsLoadingMoreResults] = useState(false)
  const [activeHomeTab, setActiveHomeTab] = useState<HomeSectionKey>('movie')
  const [hydratingYearKeys, setHydratingYearKeys] = useState<Set<string>>(new Set())
  const [hydratingPosterKeys, setHydratingPosterKeys] = useState<Set<string>>(new Set())
  const attemptedYearKeys = useRef<Set<string>>(new Set())
  const attemptedPosterKeys = useRef<Set<string>>(new Set())
  const pageGeneration = useRef(0)

  const activeProvider = providers.find((provider) => provider.id === filters.provider_id) || providers[0]
  const availableFilters = filtersForOperation(activeProvider, 'categories')
  const availableSorts = sortsForOperation(activeProvider, 'categories')
  const genreOptions = orderedOptions(activeProvider?.filter_options.genre || [], preferredGenreLabels)
  const allRegionOptions = activeProvider?.filter_options.region || []
  const categoryGenre = optionForCategory(activeProvider, filters.category)
  const hasSecondaryCriteria = Boolean(
    filters.genres.length || filters.region || filters.year_from || filters.year_to || filters.sort,
  )
  const hasExploreCriteria = filters.category !== 'popular' || hasSecondaryCriteria

  useEffect(() => {
    const onPopState = () => {
      const nextFilters = filtersFromUrl()
      setFilters(nextFilters)
      setSearchDraft(nextFilters.q)
      setShowExactYears(Boolean(nextFilters.year_from && nextFilters.year_from === nextFilters.year_to))
      setLocationVersion((value) => value + 1)
    }
    window.addEventListener('popstate', onPopState)
    return () => window.removeEventListener('popstate', onPopState)
  }, [])

  useEffect(() => { void loadPage() }, [locationVersion])

  useEffect(() => {
    if (detail || isLoading || !activeProvider) return
    const visibleItems = results?.items || sections.find((section) => section.key === activeHomeTab)?.items || []
    const grouped = new Map<string, string[]>()
    const pendingKeys: string[] = []
    visibleItems.forEach((item) => {
      const key = `${activeProvider.id}:${item.media_subject_id}`
      if (
        item.release_year !== null
        || !item.poster_url
        || !providerRecognizesItem(activeProvider, item)
        || attemptedYearKeys.current.has(key)
      ) return
      attemptedYearKeys.current.add(key)
      pendingKeys.push(key)
      grouped.set(activeProvider.id, [...(grouped.get(activeProvider.id) || []), item.media_subject_id])
    })
    if (!pendingKeys.length) return
    setHydratingYearKeys((current) => new Set([...current, ...pendingKeys]))
    void hydrateMissingYears(grouped, pageGeneration.current)
  }, [activeHomeTab, activeProvider, detail, isLoading, results, sections])

  useEffect(() => {
    if (detail || isLoading || !activeProvider || !activeProvider.operations.includes('detail')) return
    const visibleItems = results?.items || sections.find((section) => section.key === activeHomeTab)?.items || []
    const subjectIds = visibleItems
      .filter((item) => (
        !item.poster_url || item.provider_id !== activeProvider.id
      ) && providerRecognizesItem(activeProvider, item))
      .map((item) => item.media_subject_id)
      .filter((subjectId) => !attemptedPosterKeys.current.has(`${activeProvider.id}:${subjectId}`))
      .slice(0, 4)
    if (!subjectIds.length) return
    const keys = subjectIds.map((subjectId) => `${activeProvider.id}:${subjectId}`)
    keys.forEach((key) => attemptedPosterKeys.current.add(key))
    setHydratingPosterKeys((current) => new Set([...current, ...keys]))
    void hydrateMissingSnapshots(activeProvider.id, subjectIds, pageGeneration.current)
  }, [activeHomeTab, activeProvider, detail, isLoading, results, sections])

  async function loadPage(forceRefresh = false) {
    const generation = pageGeneration.current + 1
    pageGeneration.current = generation
    attemptedYearKeys.current.clear()
    attemptedPosterKeys.current.clear()
    setHydratingYearKeys(new Set())
    setHydratingPosterKeys(new Set())
    setIsLoadingMoreResults(false)
    setIsLoading(true)
    setError(null)
    setUnsupportedCategory(null)
    if (isResourceModeFromLocation()) {
      setDetail(null)
      setResults(null)
      setSections([])
      setIsLoading(false)
      return
    }
    try {
      const providerItems = await api.get<CatalogProvider[]>('/discover/providers')
      if (generation !== pageGeneration.current) return
      setProviders(providerItems)
      const selectedProvider = providerItems.find((provider) => provider.id === filters.provider_id) || providerItems[0]
      const providerId = selectedProvider?.id
      if (providerId && filters.provider_id !== providerId) {
        const normalizedFilters = { ...filters, provider_id: providerId }
        const normalizedParams = urlParams(normalizedFilters)
        window.history.replaceState({}, '', `/app/discover?${normalizedParams.toString()}`)
        setFilters(normalizedFilters)
      }
      const detailId = detailIdFromPath()
      if (detailId) {
        const params = new URLSearchParams()
        const detailProviderId = new URLSearchParams(window.location.search).get('provider_id')
        if (detailProviderId) params.set('provider_id', detailProviderId)
        if (forceRefresh) params.set('refresh', 'true')
        const suffix = params.size ? `?${params.toString()}` : ''
        const nextDetail = await api.get<MediaSubjectDetail>(`/discover/${encodeURIComponent(detailId)}${suffix}`)
        if (generation !== pageGeneration.current) return
        setDetail(nextDetail)
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
      const selectedCategoryGenre = optionForCategory(selectedProvider, filters.category)
      if (categoryGenreLabels[filters.category] && !selectedCategoryGenre) {
        setUnsupportedCategory(`${selectedProvider.attribution?.provider_name || selectedProvider.id} 未声明“${categoryItems.find((item) => item.key === filters.category)?.label}”对应的题材能力。`)
        setResults(null)
        setSections([])
        return
      }
      if (filters.q.trim()) {
        const params = apiQueryParams(forceRefresh, filters, providerId)
        const nextResults = await api.get<DiscoverPageResponse>(`/discover/search?${params.toString()}`)
        if (generation !== pageGeneration.current) return
        setResults(nextResults)
        setSections([])
      } else if (hasExploreCriteria) {
        const params = apiQueryParams(forceRefresh, filters, providerId, selectedCategoryGenre?.value)
        const nextResults = await api.get<DiscoverPageResponse>(`/discover/categories?${params.toString()}`)
        if (generation !== pageGeneration.current) return
        setResults(nextResults)
        setSections([])
      } else {
        setResults(null)
        setSections([])
        await loadHomeSection(activeHomeTab, forceRefresh, providerId)
      }
    } catch (exc) {
      if (generation !== pageGeneration.current) return
      setError(exc instanceof Error ? exc.message : '无法加载媒体发现内容。')
    } finally {
      if (generation === pageGeneration.current) setIsLoading(false)
    }
  }

  async function loadHomeSection(sectionKey: HomeSectionKey, forceRefresh: boolean, providerId?: string) {
    const generation = pageGeneration.current
    const catalogParams = new URLSearchParams({ limit: '12' })
    if (providerId) catalogParams.set('provider_id', providerId)
    if (forceRefresh) catalogParams.set('refresh', 'true')
    const meta = homeSectionItems.find((item) => item.key === sectionKey) || homeSectionItems[0]
    const path = sectionKey === 'watchlist'
      ? '/discover/watchlist?limit=12'
      : sectionKey === 'movie' || sectionKey === 'series'
        ? `/discover/trending?media_type=${sectionKey}&${catalogParams.toString()}`
        : `/discover/categories?${catalogParams.toString()}`
    setSections((current) => [
      ...current.filter((section) => section.key !== sectionKey),
      { ...meta, path, items: [], isLoading: true },
    ])
    try {
      const response = await api.get<DiscoverPageResponse | WatchlistPageResponse>(path)
      if (generation !== pageGeneration.current) return
      setSections((current) => current.map((section) => section.key === sectionKey ? {
        ...section,
        items: response.items,
        continuationToken: 'continuation_token' in response ? response.continuation_token : null,
        isLoading: false,
        error: undefined,
      } : section))
    } catch (exc) {
      if (generation !== pageGeneration.current) return
      setSections((current) => current.map((section) => section.key === sectionKey ? {
        ...section,
        items: [],
        isLoading: false,
        error: exc instanceof Error ? exc.message : '加载失败',
      } : section))
    }
  }

  function selectHomeTab(sectionKey: HomeSectionKey) {
    setActiveHomeTab(sectionKey)
    if (!sections.some((section) => section.key === sectionKey)) {
      void loadHomeSection(sectionKey, false, activeProvider?.id)
    }
  }

  async function hydrateMissingYears(grouped: Map<string, string[]>, generation: number) {
    for (const [providerId, subjectIds] of grouped) {
      for (const batch of chunkItems(subjectIds, 6)) {
        const batchKeys = batch.map((subjectId) => `${providerId}:${subjectId}`)
        try {
          const response = await api.post<YearHydrationResponse>('/discover/hydrate-years', {
            provider_id: providerId,
            media_subject_ids: batch,
          })
          if (generation !== pageGeneration.current) return
          if (Object.keys(response.years).length) {
            const withHydratedYear = (item: MediaSubjectSummary) => {
              const year = response.years[item.media_subject_id]
              return year === undefined ? item : { ...item, release_year: year }
            }
            setResults((current) => current
              ? { ...current, items: current.items.map(withHydratedYear) }
              : current)
            setSections((current) => current.map((section) => ({
              ...section,
              items: section.items.map(withHydratedYear),
            })))
          }
        } catch {
          // 年份补全是渐进增强；单批失败不能阻断目录浏览和后续批次。
        } finally {
          if (generation === pageGeneration.current) {
            setHydratingYearKeys((current) => {
              const next = new Set(current)
              batchKeys.forEach((key) => next.delete(key))
              return next
            })
          }
        }
      }
    }
  }

  async function hydrateMissingSnapshots(providerId: string, subjectIds: string[], generation: number) {
    const keys = subjectIds.map((subjectId) => `${providerId}:${subjectId}`)
    try {
      const response = await api.post<SnapshotHydrationResponse>('/discover/hydrate-snapshots', {
        provider_id: providerId,
        media_subject_ids: subjectIds,
      })
      if (generation !== pageGeneration.current) return
      const hydrated = new Map(response.items.map((item) => [item.media_subject_id, item]))
      const mergeHydrated = (item: MediaSubjectSummary) => hydrated.get(item.media_subject_id) || item
      setResults((current) => current ? { ...current, items: current.items.map(mergeHydrated) } : current)
      setSections((current) => current.map((section) => ({
        ...section,
        items: section.items.map(mergeHydrated),
      })))
    } catch {
      // 海报补全是渐进增强；目录详情失败时保留想看列表的最小快照。
    } finally {
      if (generation === pageGeneration.current) {
        setHydratingPosterKeys((current) => {
          const next = new Set(current)
          keys.forEach((key) => next.delete(key))
          return next
        })
      }
    }
  }

  async function loadMoreResults() {
    if (!results?.continuation_token || isLoadingMoreResults || !activeProvider) return
    setIsLoadingMoreResults(true)
    try {
      const selectedCategoryGenre = optionForCategory(activeProvider, filters.category)
      const params = apiQueryParams(false, filters, activeProvider.id, selectedCategoryGenre?.value)
      params.set('continuation_token', results.continuation_token)
      const endpoint = filters.q.trim()
        ? '/discover/search'
        : '/discover/categories'
      const nextPage = await api.get<DiscoverPageResponse>(`${endpoint}?${params.toString()}`)
      setResults((current) => current ? {
        ...nextPage,
        items: mergeUniqueItems(current.items, nextPage.items),
        degraded: current.degraded || nextPage.degraded,
      } : nextPage)
    } catch (exc) {
      showToast('error', exc instanceof Error ? exc.message : '下一页加载失败。')
    } finally {
      setIsLoadingMoreResults(false)
    }
  }

  async function loadMoreSection(sectionKey: string) {
    const section = sections.find((item) => item.key === sectionKey)
    if (!section?.path || !section.continuationToken || section.isLoadingMore) return
    setSections((current) => current.map((item) => item.key === sectionKey
      ? { ...item, isLoadingMore: true }
      : item))
    try {
      const separator = section.path.includes('?') ? '&' : '?'
      const nextPage = await api.get<DiscoverPageResponse>(
        `${section.path}${separator}continuation_token=${encodeURIComponent(section.continuationToken)}`,
      )
      setSections((current) => current.map((item) => item.key === sectionKey ? {
        ...item,
        items: mergeUniqueItems(item.items, nextPage.items),
        continuationToken: nextPage.continuation_token,
        isLoadingMore: false,
      } : item))
    } catch (exc) {
      setSections((current) => current.map((item) => item.key === sectionKey
        ? { ...item, isLoadingMore: false }
        : item))
      showToast('error', exc instanceof Error ? exc.message : '下一页加载失败。')
    }
  }

  function navigate(nextState: FilterState, mode: 'push' | 'replace' = 'push') {
    const normalizedState = {
      ...nextState,
      provider_id: nextState.provider_id || activeProvider?.id || '',
    }
    const params = urlParams(normalizedState)
    const query = params.toString()
    window.history[mode === 'push' ? 'pushState' : 'replaceState']({}, '', `/app/discover${query ? `?${query}` : ''}`)
    setFilters(normalizedState)
    setSearchDraft(normalizedState.q)
    setLocationVersion((value) => value + 1)
  }

  function updateExplore(patch: Partial<FilterState>) {
    navigate({ ...filters, q: '', ...patch })
  }

  function submitSearch(event: React.FormEvent) {
    event.preventDefault()
    const keyword = searchDraft.trim()
    if (!keyword) {
      navigate({ ...emptyFilters(activeProvider?.id || filters.provider_id), category: filters.category, media_type: filters.media_type })
      return
    }
    navigate({ ...emptyFilters(activeProvider?.id || filters.provider_id), q: keyword })
  }

  function selectCategory(category: CategoryKey) {
    const mediaType = category === 'movie' ? 'movie' : category === 'series' || category === 'variety' ? 'series' : ''
    updateExplore({ category, media_type: mediaType })
  }

  function toggleGenre(value: string) {
    if (categoryGenre?.value === value) {
      selectCategory('popular')
      return
    }
    const genres = filters.genres.includes(value)
      ? filters.genres.filter((genre) => genre !== value)
      : [...filters.genres, value]
    updateExplore({ genres })
  }

  function selectYear(from: string, to: string) {
    setShowExactYears(Boolean(from && from === to))
    updateExplore({ year_from: from, year_to: to })
  }

  function changeProvider(providerId: string) {
    const provider = providers.find((item) => item.id === providerId)
    if (!provider || !activeProvider) return
    const previousGenres = activeProvider.filter_options.genre || []
    const nextGenres = provider.filter_options.genre || []
    const nextState: FilterState = {
      ...filters,
      provider_id: providerId,
      genres: filters.genres
        .map((genre) => remapValue(genre, previousGenres, nextGenres))
        .filter(Boolean),
      region: remapValue(filters.region, activeProvider.filter_options.region || [], provider.filter_options.region || []),
      sort: sortsForOperation(provider, 'categories').includes(filters.sort) ? filters.sort : '',
    }
    navigate(nextState)
  }

  function clearFilters() {
    navigate(emptyFilters(activeProvider?.id || filters.provider_id))
    setShowOtherRegions(false)
    setShowExactYears(false)
  }

  function openDetail(item: MediaSubjectSummary) {
    const discoverReturn = `${window.location.pathname}${window.location.search}`
    const compatibleProvider = activeProvider && providerRecognizesItem(activeProvider, item)
      ? activeProvider
      : providers.find((provider) => providerRecognizesItem(provider, item))
    const providerId = compatibleProvider?.id
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
    const nextFilters = filtersFromUrl()
    setFilters(nextFilters)
    setSearchDraft(nextFilters.q)
    setLocationVersion((value) => value + 1)
  }

  function searchResources(item: MediaSubjectSummary | MediaSubjectDetail) {
    const params = new URLSearchParams({ mode: 'resources', q: item.canonical_title })
    if (item.release_year) params.set('year', String(item.release_year))
    window.history.pushState({}, '', `/app/discover?${params.toString()}`)
    setLocationVersion((value) => value + 1)
  }

  function selectDiscoverMode(mode: 'catalog' | 'resources') {
    if (mode === 'resources') {
      window.history.pushState({}, '', '/app/discover?mode=resources')
      setLocationVersion((value) => value + 1)
      return
    }
    const params = new URLSearchParams()
    if (activeProvider?.id) params.set('provider_id', activeProvider.id)
    window.history.pushState({}, '', `/app/discover${params.size ? `?${params.toString()}` : ''}`)
    const nextFilters = filtersFromUrl()
    setFilters(nextFilters)
    setSearchDraft(nextFilters.q)
    setLocationVersion((value) => value + 1)
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

  const popularRegionOptions = preferredRegions
    .map((region) => {
      const option = allRegionOptions.find((item) => region.aliases.includes(item.label))
      return option ? { ...option, label: region.label } : undefined
    })
    .filter((option): option is CatalogFilterOption => Boolean(option))
  const popularRegionValues = new Set(popularRegionOptions.map((option) => option.value))
  const otherRegionOptions = allRegionOptions.filter((option) => !popularRegionValues.has(option.value))
  const visibleRegionOptions = showOtherRegions
    ? [...popularRegionOptions, ...otherRegionOptions]
    : [...popularRegionOptions, ...otherRegionOptions.filter((option) => option.value === filters.region)]
  const currentYear = new Date().getFullYear()
  const exactYears = Array.from({ length: currentYear - 1949 }, (_, index) => String(currentYear - index))
  const activeFilters: ActiveFilter[] = []
  const activeCategory = categoryItems.find((item) => item.key === filters.category)
  if (filters.q) activeFilters.push({ key: 'q', label: `搜索：${filters.q}`, remove: () => navigate(emptyFilters(activeProvider?.id || filters.provider_id)) })
  if (!filters.q && filters.category !== 'popular' && activeCategory) {
    activeFilters.push({ key: 'category', label: activeCategory.label, remove: () => selectCategory('popular') })
  }
  filters.genres.forEach((genre) => activeFilters.push({
    key: `genre-${genre}`,
    label: optionLabel(genreOptions, genre),
    remove: () => toggleGenre(genre),
  }))
  if (filters.region) activeFilters.push({
    key: 'region',
    label: optionLabel([...popularRegionOptions, ...otherRegionOptions], filters.region),
    remove: () => updateExplore({ region: '' }),
  })
  const activeYearLabel = yearFilterLabel(filters)
  if (activeYearLabel) activeFilters.push({ key: 'year', label: activeYearLabel, remove: () => selectYear('', '') })
  if (filters.sort) activeFilters.push({
    key: 'sort',
    label: sortItems.find((item) => item.value === filters.sort)?.label || filters.sort,
    remove: () => updateExplore({ sort: '' }),
  })
  const resultTitle = filters.q.trim()
    ? `“${filters.q.trim()}”的目录结果`
    : `${activeCategory?.label || '发现'}内容`
  const activeHomeSection = sections.find((section) => section.key === activeHomeTab)
  const resourceMode = isResourceModeFromLocation()
  const attributionProvider = detail
    ? providers.find((provider) => provider.id === detail.provider_id)
    : activeHomeTab === 'watchlist' && !results
      ? undefined
      : activeProvider
  const activeHomeDescription = activeHomeSection?.error || (
    activeHomeSection && ['movie', 'series'].includes(activeHomeSection.key)
      ? `${activeHomeSection.description}，数据来自 ${activeProvider?.attribution?.provider_name || activeProvider?.id || '当前 Provider'}`
      : activeHomeSection?.description
  )

  return (
    <section className="dc-page" aria-labelledby="discover-title">
      <header className="dc-header">
        <div>
          <p className="ui-eyebrow">{resourceMode ? '资源搜索' : '媒体发现'}</p>
          <h2 id="discover-title">{detail ? detail.canonical_title : resourceMode ? '查找具体资源' : '发现下一部想看的内容'}</h2>
          <p>{detail ? '目录详情来自当前启用的真实 Provider。' : resourceMode ? '从已启用的 SOURCE 插件聚合真实资源结果。' : '从分类开始浏览，再用标签逐步缩小范围。'}</p>
        </div>
        {!resourceMode ? <Button variant="secondary" onClick={() => void loadPage(true)} disabled={isLoading}>刷新真实数据</Button> : null}
      </header>

      {!detail ? (
        <nav className="dc-mode-tabs" role="tablist" aria-label="发现模式">
          <button type="button" role="tab" aria-selected={!resourceMode} data-active={!resourceMode || undefined} onClick={() => selectDiscoverMode('catalog')}>内容发现</button>
          <button type="button" role="tab" aria-selected={resourceMode} data-active={resourceMode || undefined} onClick={() => selectDiscoverMode('resources')}>资源搜索</button>
        </nav>
      ) : null}

      {resourceMode ? (
        <SearchPage embedded showToast={showToast} />
      ) : detail ? (
        <DetailView detail={detail} onBack={returnToDiscover} onFollow={() => void toggleFollow()} onSearch={() => searchResources(detail)} />
      ) : (
        <>
          <DiscoverFilters
            filters={filters}
            searchDraft={searchDraft}
            providers={providers}
            activeProvider={activeProvider}
            activeFilters={activeFilters}
            availableFilters={availableFilters}
            availableSorts={availableSorts}
            genreOptions={genreOptions}
            categoryGenre={categoryGenre}
            allRegionOptions={allRegionOptions}
            visibleRegionOptions={visibleRegionOptions}
            otherRegionOptions={otherRegionOptions}
            showExactYears={showExactYears}
            showOtherRegions={showOtherRegions}
            exactYears={exactYears}
            onSearchDraftChange={setSearchDraft}
            onSubmitSearch={submitSearch}
            onSelectCategory={selectCategory}
            onChangeProvider={changeProvider}
            onClearFilters={clearFilters}
            onToggleGenre={toggleGenre}
            onSelectYear={selectYear}
            onToggleExactYears={() => setShowExactYears((value) => !value)}
            onToggleOtherRegions={() => setShowOtherRegions((value) => !value)}
            onUpdateExplore={updateExplore}
          />

          {isLoading ? <LoadingState message="正在读取目录" sub="请求当前启用的真实 Provider。" /> : null}
          {error ? <ErrorState message="媒体发现暂不可用" sub={error} action={<Button onClick={() => void loadPage(true)}>重试</Button>} /> : null}
          {!isLoading && !error && providers.length === 0 ? <EmptyState message="尚未启用目录 Provider" sub="先在插件仓库中安装并启用 CATALOG_PROVIDER，Core 不会生成占位媒体数据。" /> : null}
          {!isLoading && !error && unsupportedCategory ? <EmptyState message="当前来源不支持这个分类" sub={unsupportedCategory} /> : null}
          {!isLoading && !error && !unsupportedCategory && results ? <ResultSection title={resultTitle} description={results.degraded ? 'Provider 不可用，当前展示降级缓存。' : `数据来自 ${activeProvider?.attribution?.provider_name || results.provider_id}`} items={results.items} degraded={results.degraded} hydrationProviderId={activeProvider?.id} hydratingYearKeys={hydratingYearKeys} hydratingPosterKeys={hydratingPosterKeys} hasMore={Boolean(results.continuation_token)} isLoadingMore={isLoadingMoreResults} onLoadMore={() => void loadMoreResults()} onOpen={openDetail} onSearch={searchResources} /> : null}
          {!isLoading && !error && !unsupportedCategory && !results ? (
            <section className="dc-home" aria-label="热门内容">
              <nav className="dc-home-tabs" role="tablist" aria-label="热门内容分类">
                {homeSectionItems.map((item) => (
                  <button
                    key={item.key}
                    type="button"
                    role="tab"
                    aria-selected={activeHomeTab === item.key}
                    data-active={activeHomeTab === item.key || undefined}
                    onClick={() => selectHomeTab(item.key)}
                  >
                    {item.title}
                  </button>
                ))}
              </nav>
              <div className="dc-home-tab-panel" role="tabpanel">
                {activeHomeSection?.isLoading ? <LoadingState message={`正在加载${activeHomeSection.title}`} /> : null}
                {activeHomeSection && !activeHomeSection.isLoading ? <ResultSection title={activeHomeSection.title} description={activeHomeDescription || activeHomeSection.description} items={activeHomeSection.items} degraded={Boolean(activeHomeSection.error)} hydrationProviderId={activeProvider?.id} hydratingYearKeys={hydratingYearKeys} hydratingPosterKeys={hydratingPosterKeys} hasMore={Boolean(activeHomeSection.continuationToken)} isLoadingMore={Boolean(activeHomeSection.isLoadingMore)} onLoadMore={() => void loadMoreSection(activeHomeSection.key)} onOpen={openDetail} onSearch={searchResources} /> : null}
              </div>
            </section>
          ) : null}
        </>
      )}
      {attributionProvider?.attribution ? (
        <aside className="dc-attribution" aria-label="数据来源">
          <div>
            <span>数据来源</span>
            <a href={attributionProvider.attribution.homepage_url} target="_blank" rel="noreferrer">
              {attributionProvider.attribution.logo_url ? <img src={attributionProvider.attribution.logo_url} alt={attributionProvider.attribution.provider_name} /> : <strong>{attributionProvider.attribution.provider_name}</strong>}
            </a>
          </div>
          <p>{attributionProvider.attribution.notice}</p>
        </aside>
      ) : null}
    </section>
  )
}
