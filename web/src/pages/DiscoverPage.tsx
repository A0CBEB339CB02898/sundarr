import React, { useEffect, useRef, useState } from 'react'
import { api } from '../api/client'
import type {
  CatalogFilterOption,
  CatalogProvider,
  DiscoverPageResponse,
  MediaSubjectDetail,
  MediaSubjectSummary,
  WatchlistPageResponse,
  YearHydrationResponse,
} from '../types'
import { Button, EmptyState, ErrorState, LoadingState } from '../ui'

type DiscoverSection = {
  key: string
  title: string
  description: string
  items: MediaSubjectSummary[]
  error?: string
  path?: string
  continuationToken?: string | null
  isLoadingMore?: boolean
}

type CategoryKey = 'popular' | 'movie' | 'series' | 'anime' | 'variety'

type FilterState = {
  provider_id: string
  q: string
  category: CategoryKey
  media_type: string
  genres: string[]
  region: string
  year_from: string
  year_to: string
  sort: string
}

type ActiveFilter = {
  key: string
  label: string
  remove: () => void
}

const categoryItems: Array<{ key: CategoryKey; label: string }> = [
  { key: 'popular', label: '热门' },
  { key: 'movie', label: '电影' },
  { key: 'series', label: '剧集' },
  { key: 'anime', label: '动漫' },
  { key: 'variety', label: '综艺' },
]

const categoryGenreLabels: Partial<Record<CategoryKey, string[]>> = {
  anime: ['动画', '动漫', 'Animation'],
  variety: ['综艺', '真人秀', '脱口秀', 'Reality', 'Talk'],
}

const preferredGenreLabels = [
  '剧情', '科幻', '动作', '喜剧', '爱情', '惊悚', '恐怖', '动画', '犯罪', '悬疑',
  '纪录片', '战争', '历史', '音乐', '家庭', '校园', '真人秀', '脱口秀',
]

const preferredRegions = [
  { label: '中国大陆', aliases: ['中国大陆', '中国'] },
  { label: '香港', aliases: ['香港', '中国香港', '中国香港特别行政区', 'Hong Kong'] },
  { label: '台湾', aliases: ['台湾', '中国台湾', 'Taiwan'] },
  { label: '日本', aliases: ['日本', 'Japan'] },
  { label: '韩国', aliases: ['韩国', 'South Korea'] },
  { label: '美国', aliases: ['美国', 'United States'] },
  { label: '英国', aliases: ['英国', 'United Kingdom'] },
  { label: '法国', aliases: ['法国', 'France'] },
  { label: '德国', aliases: ['德国', 'Germany'] },
  { label: '印度', aliases: ['印度', 'India'] },
  { label: '泰国', aliases: ['泰国', 'Thailand'] },
]

const sortItems: Array<{ key: string; label: string; value: string | null; hint?: string }> = [
  { key: 'popular', label: '热门', value: 'popularity' },
  { key: 'rating', label: '评分最高', value: 'rating' },
  { key: 'published', label: '最新发布', value: null, hint: '目录模型尚无内容发布时间' },
  { key: 'release', label: '最新上映', value: 'release_date' },
  { key: 'favorites', label: '收藏最多', value: null, hint: '当前单用户模型没有收藏次数' },
  { key: 'views', label: '观看最多', value: null, hint: 'Sundarr 不记录播放次数' },
]

const advancedFilters = [
  { label: 'IMDb 评分', hint: '当前目录合同没有 IMDb 评分筛选' },
  { label: '评分人数', hint: '列表查询合同没有评分人数筛选' },
  { label: '资源质量', hint: '资源质量属于具体资源搜索，不属于目录发现' },
  { label: '语言', hint: '当前目录合同没有语言筛选' },
  { label: '字幕类型', hint: '目录数据不包含字幕信息' },
]

function emptyFilters(providerId = ''): FilterState {
  return {
    provider_id: providerId,
    q: '',
    category: 'popular',
    media_type: '',
    genres: [],
    region: '',
    year_from: '',
    year_to: '',
    sort: '',
  }
}

function isCategoryKey(value: string | null): value is CategoryKey {
  return categoryItems.some((item) => item.key === value)
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
  const mediaType = params.get('media_type') || ''
  const requestedCategory = params.get('category')
  const category = isCategoryKey(requestedCategory)
    ? requestedCategory
    : mediaType === 'movie'
      ? 'movie'
      : mediaType === 'series'
        ? 'series'
        : 'popular'
  return {
    provider_id: params.get('provider_id') || '',
    q: params.get('q') || '',
    category,
    media_type: category === 'movie' ? 'movie' : category === 'series' || category === 'variety' ? 'series' : mediaType,
    genres: Array.from(new Set(params.getAll('genre').filter(Boolean))),
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

function optionForCategory(provider: CatalogProvider | undefined, category: CategoryKey) {
  const candidates = categoryGenreLabels[category]
  if (!provider || !candidates) return undefined
  return (provider.filter_options.genre || []).find((option) =>
    candidates.some((candidate) => candidate.toLocaleLowerCase() === option.label.toLocaleLowerCase()),
  )
}

function orderedOptions(options: CatalogFilterOption[], preferredLabels: string[]) {
  const rank = new Map(preferredLabels.map((label, index) => [label, index]))
  return [...options].sort((left, right) => {
    const leftRank = rank.get(left.label) ?? preferredLabels.length
    const rightRank = rank.get(right.label) ?? preferredLabels.length
    return leftRank - rightRank || left.label.localeCompare(right.label, 'zh-CN')
  })
}

function optionLabel(options: CatalogFilterOption[], value: string) {
  return options.find((option) => option.value === value)?.label || value
}

function yearPresets() {
  const currentYear = new Date().getFullYear()
  return [
    { key: 'all', label: '全部', from: '', to: '' },
    { key: 'recent', label: '近三年', from: String(currentYear - 2), to: String(currentYear) },
    { key: '2020s', label: '2020年代', from: '2020', to: '2029' },
    { key: '2010s', label: '2010年代', from: '2010', to: '2019' },
    { key: '2000s', label: '2000年代', from: '2000', to: '2009' },
    { key: '1990s', label: '90年代', from: '1990', to: '1999' },
    { key: '1980s', label: '80年代', from: '1980', to: '1989' },
    { key: 'earlier', label: '更早', from: '1', to: '1979' },
  ]
}

function yearFilterLabel(state: FilterState) {
  if (!state.year_from && !state.year_to) return ''
  if (state.year_from && state.year_from === state.year_to) return `${state.year_from}年`
  const preset = yearPresets().find((item) => item.from === state.year_from && item.to === state.year_to)
  return preset?.label || `${state.year_from || '最早'}至${state.year_to || '现在'}`
}

function remapValue(
  value: string,
  previousOptions: CatalogFilterOption[],
  nextOptions: CatalogFilterOption[],
) {
  if (!value) return ''
  const previousLabel = optionLabel(previousOptions, value)
  return nextOptions.find((option) => option.label === previousLabel)?.value || ''
}

function mergeUniqueItems(current: MediaSubjectSummary[], incoming: MediaSubjectSummary[]) {
  const seen = new Set(current.map((item) => item.media_subject_id))
  return [...current, ...incoming.filter((item) => !seen.has(item.media_subject_id))]
}

function chunkItems<T>(items: T[], size: number) {
  return Array.from({ length: Math.ceil(items.length / size) }, (_, index) =>
    items.slice(index * size, (index + 1) * size),
  )
}

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
  const [hydratingYearKeys, setHydratingYearKeys] = useState<Set<string>>(new Set())
  const attemptedYearKeys = useRef<Set<string>>(new Set())
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
    if (detail || isLoading) return
    const visibleItems = results?.items || sections.flatMap((section) => section.items)
    const grouped = new Map<string, string[]>()
    const pendingKeys: string[] = []
    visibleItems.forEach((item) => {
      const key = `${item.provider_id}:${item.media_subject_id}`
      if (item.release_year !== null || attemptedYearKeys.current.has(key)) return
      attemptedYearKeys.current.add(key)
      pendingKeys.push(key)
      grouped.set(item.provider_id, [...(grouped.get(item.provider_id) || []), item.media_subject_id])
    })
    if (!pendingKeys.length) return
    setHydratingYearKeys((current) => new Set([...current, ...pendingKeys]))
    void hydrateMissingYears(grouped, pageGeneration.current)
  }, [detail, isLoading, results, sections])

  async function loadPage(forceRefresh = false) {
    pageGeneration.current += 1
    attemptedYearKeys.current.clear()
    setHydratingYearKeys(new Set())
    setIsLoadingMoreResults(false)
    setIsLoading(true)
    setError(null)
    setUnsupportedCategory(null)
    try {
      const providerItems = await api.get<CatalogProvider[]>('/discover/providers')
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
      const selectedCategoryGenre = optionForCategory(selectedProvider, filters.category)
      if (categoryGenreLabels[filters.category] && !selectedCategoryGenre) {
        setUnsupportedCategory(`${selectedProvider.attribution?.provider_name || selectedProvider.id} 未声明“${categoryItems.find((item) => item.key === filters.category)?.label}”对应的题材能力。`)
        setResults(null)
        setSections([])
        return
      }
      if (filters.q.trim()) {
        const params = apiQueryParams(forceRefresh, filters, providerId)
        setResults(await api.get<DiscoverPageResponse>(`/discover/search?${params.toString()}`))
        setSections([])
      } else if (hasExploreCriteria) {
        const useTrending = !hasSecondaryCriteria && (filters.category === 'movie' || filters.category === 'series')
        const params = apiQueryParams(forceRefresh, filters, providerId, selectedCategoryGenre?.value)
        setResults(await api.get<DiscoverPageResponse>(`/discover/${useTrending ? 'trending' : 'categories'}?${params.toString()}`))
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
      { key: 'movie', title: '热门电影', description: '当前目录来源的电影趋势', path: `/discover/trending?media_type=movie&${catalogParams.toString()}` },
      { key: 'series', title: '热门剧集', description: '当前目录来源的剧集趋势', path: `/discover/trending?media_type=series&${catalogParams.toString()}` },
      { key: 'category', title: '分类推荐', description: '按当前目录能力生成的推荐', path: `/discover/categories?${catalogParams.toString()}` },
      { key: 'watchlist', title: '关注更新', description: '外部想看列表同步到 Sundarr 的条目', path: '/discover/watchlist?limit=12' },
    ]
    const loaded = await Promise.allSettled(definitions.map((item) => api.get<DiscoverPageResponse | WatchlistPageResponse>(item.path)))
    setSections(definitions.map((definition, index) => {
      const outcome = loaded[index]
      if (outcome.status === 'rejected') {
        return { ...definition, items: [], error: outcome.reason instanceof Error ? outcome.reason.message : '加载失败' }
      }
      return {
        ...definition,
        items: outcome.value.items,
        continuationToken: 'continuation_token' in outcome.value
          ? outcome.value.continuation_token
          : null,
      }
    }))
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

  async function loadMoreResults() {
    if (!results?.continuation_token || isLoadingMoreResults || !activeProvider) return
    setIsLoadingMoreResults(true)
    try {
      const selectedCategoryGenre = optionForCategory(activeProvider, filters.category)
      const params = apiQueryParams(false, filters, activeProvider.id, selectedCategoryGenre?.value)
      params.set('continuation_token', results.continuation_token)
      const useTrending = !filters.q.trim()
        && !hasSecondaryCriteria
        && (filters.category === 'movie' || filters.category === 'series')
      const endpoint = filters.q.trim()
        ? '/discover/search'
        : `/discover/${useTrending ? 'trending' : 'categories'}`
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

  function apiQueryParams(
    forceRefresh = false,
    state = filters,
    providerId?: string,
    presetGenre?: string,
  ) {
    const params = new URLSearchParams()
    if (providerId) params.set('provider_id', providerId)
    if (state.q.trim()) {
      params.set('q', state.q.trim())
    } else {
      if (state.media_type) params.set('media_type', state.media_type)
      Array.from(new Set([presetGenre, ...state.genres].filter(Boolean) as string[])).forEach((genre) => params.append('genre', genre))
      if (state.region) params.set('region', state.region)
      if (state.year_from) params.set('year_from', state.year_from)
      if (state.year_to) params.set('year_to', state.year_to)
      if (state.sort) params.set('sort', state.sort)
    }
    params.set('limit', '24')
    if (forceRefresh) params.set('refresh', 'true')
    return params
  }

  function urlParams(state: FilterState) {
    const params = new URLSearchParams()
    if (state.provider_id) params.set('provider_id', state.provider_id)
    if (state.q.trim()) params.set('q', state.q.trim())
    if (state.category !== 'popular') params.set('category', state.category)
    if (state.media_type) params.set('media_type', state.media_type)
    state.genres.forEach((genre) => params.append('genre', genre))
    if (state.region) params.set('region', state.region)
    if (state.year_from) params.set('year_from', state.year_from)
    if (state.year_to) params.set('year_to', state.year_to)
    if (state.sort) params.set('sort', state.sort)
    return params
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
    const nextFilters = filtersFromUrl()
    setFilters(nextFilters)
    setSearchDraft(nextFilters.q)
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

  return (
    <section className="dc-page" aria-labelledby="discover-title">
      <header className="dc-header">
        <div>
          <p className="ui-eyebrow">媒体发现</p>
          <h2 id="discover-title">{detail ? detail.canonical_title : '发现下一部想看的内容'}</h2>
          <p>{detail ? '目录详情来自当前启用的真实 Provider。' : '从分类开始浏览，再用标签逐步缩小范围。'}</p>
        </div>
        <Button variant="secondary" onClick={() => void loadPage(true)} disabled={isLoading}>刷新真实数据</Button>
      </header>

      {detail ? (
        <DetailView detail={detail} onBack={returnToDiscover} onFollow={() => void toggleFollow()} onSearch={() => searchResources(detail)} />
      ) : (
        <>
          <div className="dc-discovery-toolbar">
            <nav className="dc-category-tabs" aria-label="内容分类">
              {categoryItems.map((item) => (
                <button
                  key={item.key}
                  type="button"
                  className="dc-category-tab"
                  aria-current={filters.category === item.key && !filters.q ? 'page' : undefined}
                  onClick={() => selectCategory(item.key)}
                >
                  {item.label}
                </button>
              ))}
            </nav>
            <form className="dc-search" role="search" onSubmit={submitSearch}>
              <label htmlFor="discover-search">搜索目录</label>
              <div className="dc-search-control">
                <span aria-hidden="true">⌕</span>
                <input
                  id="discover-search"
                  value={searchDraft}
                  onChange={(event) => setSearchDraft(event.target.value)}
                  placeholder="搜索片名、演员、导演或关键词"
                />
                <button type="submit">搜索</button>
              </div>
              <small>实际检索范围由当前目录来源决定</small>
            </form>
          </div>

          <section className="dc-filter-panel" aria-label="内容筛选">
            {providers.length > 1 ? (
              <div className="dc-filter-row dc-provider-row">
                <div className="dc-filter-label">数据来源</div>
                <div className="dc-tag-rail" role="group" aria-label="数据来源">
                  {providers.map((provider) => (
                    <button
                      key={provider.id}
                      type="button"
                      className="dc-filter-tag"
                      aria-pressed={activeProvider?.id === provider.id}
                      onClick={() => changeProvider(provider.id)}
                    >
                      {provider.attribution?.provider_name || provider.id}
                    </button>
                  ))}
                </div>
              </div>
            ) : null}

            {activeFilters.length ? (
              <div className="dc-active-filters">
                <span>当前筛选</span>
                <div className="dc-active-filter-list">
                  {activeFilters.map((filter) => (
                    <button key={filter.key} type="button" onClick={filter.remove} aria-label={`取消筛选：${filter.label}`}>
                      {filter.label}<span aria-hidden="true">×</span>
                    </button>
                  ))}
                </div>
                <button type="button" className="dc-clear-filters" onClick={clearFilters}>清除全部</button>
              </div>
            ) : null}

            <div className="dc-filter-row">
              <div className="dc-filter-label">类型</div>
              <div className="dc-tag-rail" role="group" aria-label="题材，可多选">
                <button
                  type="button"
                  className="dc-filter-tag"
                  aria-pressed={!filters.genres.length && !categoryGenre}
                  disabled={!availableFilters.includes('genre')}
                  onClick={() => categoryGenre ? selectCategory('popular') : updateExplore({ genres: [] })}
                >全部</button>
                {genreOptions.map((option) => {
                  const selected = filters.genres.includes(option.value) || categoryGenre?.value === option.value
                  return (
                    <button
                      key={option.value}
                      type="button"
                      className="dc-filter-tag"
                      aria-pressed={selected}
                      disabled={!availableFilters.includes('genre')}
                      onClick={() => toggleGenre(option.value)}
                    >
                      {option.label}
                    </button>
                  )
                })}
              </div>
            </div>

            <div className="dc-filter-row">
              <div className="dc-filter-label">年份</div>
              <div className="dc-tag-rail" role="group" aria-label="年份">
                {yearPresets().map((preset) => (
                  <button
                    key={preset.key}
                    type="button"
                    className="dc-filter-tag"
                    aria-pressed={filters.year_from === preset.from && filters.year_to === preset.to}
                    disabled={!availableFilters.includes('year')}
                    onClick={() => selectYear(preset.from, preset.to)}
                  >
                    {preset.label}
                  </button>
                ))}
                <button
                  type="button"
                  className="dc-filter-tag dc-filter-expand"
                  aria-expanded={showExactYears}
                  disabled={!availableFilters.includes('year')}
                  onClick={() => setShowExactYears((value) => !value)}
                >
                  精确年份 <span aria-hidden="true">{showExactYears ? '−' : '+'}</span>
                </button>
              </div>
              {showExactYears ? (
                <div className="dc-exact-years" role="group" aria-label="精确年份">
                  {exactYears.map((year) => (
                    <button
                      key={year}
                      type="button"
                      className="dc-filter-tag"
                      aria-pressed={filters.year_from === year && filters.year_to === year}
                      onClick={() => selectYear(year, year)}
                    >{year}</button>
                  ))}
                </div>
              ) : null}
            </div>

            {allRegionOptions.length ? (
              <div className="dc-filter-row">
                <div className="dc-filter-label">地区</div>
                <div className="dc-tag-rail" role="group" aria-label="地区">
                  <button
                    type="button"
                    className="dc-filter-tag"
                    aria-pressed={!filters.region}
                    disabled={!availableFilters.includes('region')}
                    onClick={() => updateExplore({ region: '' })}
                  >全部</button>
                  {visibleRegionOptions.map((option) => (
                    <button
                      key={option.value}
                      type="button"
                      className="dc-filter-tag"
                      aria-pressed={filters.region === option.value}
                      disabled={!availableFilters.includes('region')}
                      onClick={() => updateExplore({ region: option.value })}
                    >{option.label}</button>
                  ))}
                  {otherRegionOptions.length ? (
                    <button
                      type="button"
                      className="dc-filter-tag dc-filter-expand"
                      aria-expanded={showOtherRegions}
                      onClick={() => setShowOtherRegions((value) => !value)}
                    >其他 <span aria-hidden="true">{showOtherRegions ? '−' : '+'}</span></button>
                  ) : null}
                </div>
              </div>
            ) : null}

            <div className="dc-filter-row">
              <div className="dc-filter-label">排序</div>
              <div className="dc-tag-rail" role="group" aria-label="排序">
                {sortItems.map((item) => {
                  const supported = Boolean(item.value && availableSorts.includes(item.value))
                  const selected = supported && (filters.sort === item.value || (!filters.sort && item.value === 'popularity'))
                  return (
                    <button
                      key={item.key}
                      type="button"
                      className="dc-filter-tag"
                      aria-pressed={selected}
                      disabled={!supported}
                      title={!supported ? item.hint || '当前目录来源不支持此排序' : undefined}
                      onClick={() => item.value && updateExplore({ sort: item.value })}
                    >
                      {item.label}{!supported ? <small>暂不支持</small> : null}
                    </button>
                  )
                })}
              </div>
            </div>

            <details className="dc-more-filters">
              <summary>更多筛选 <span>IMDb 评分、语言、资源质量等</span></summary>
              <div className="dc-advanced-grid">
                {advancedFilters.map((item) => (
                  <button key={item.label} type="button" className="dc-filter-tag" disabled title={item.hint}>
                    {item.label}<small>当前不可用</small>
                  </button>
                ))}
              </div>
              <p>这些条件需要目录合同或资源索引提供真实字段，当前不会发送无效请求。</p>
            </details>
          </section>

          {isLoading ? <LoadingState message="正在读取目录" sub="请求当前启用的真实 Provider。" /> : null}
          {error ? <ErrorState message="媒体发现暂不可用" sub={error} action={<Button onClick={() => void loadPage(true)}>重试</Button>} /> : null}
          {!isLoading && !error && providers.length === 0 ? <EmptyState message="尚未启用目录 Provider" sub="先在插件仓库中安装并启用 CATALOG_PROVIDER，Core 不会生成占位媒体数据。" /> : null}
          {!isLoading && !error && unsupportedCategory ? <EmptyState message="当前来源不支持这个分类" sub={unsupportedCategory} /> : null}
          {!isLoading && !error && !unsupportedCategory && results ? <ResultSection title={resultTitle} description={results.degraded ? 'Provider 不可用，当前展示降级缓存。' : `数据来自 ${activeProvider?.attribution?.provider_name || results.provider_id}`} items={results.items} degraded={results.degraded} hydratingYearKeys={hydratingYearKeys} hasMore={Boolean(results.continuation_token)} isLoadingMore={isLoadingMoreResults} onLoadMore={() => void loadMoreResults()} onOpen={openDetail} onSearch={searchResources} /> : null}
          {!isLoading && !error && !unsupportedCategory && !results ? sections.map((section) => <ResultSection key={section.key} title={section.title} description={section.error || section.description} items={section.items} degraded={Boolean(section.error)} hydratingYearKeys={hydratingYearKeys} hasMore={Boolean(section.continuationToken)} isLoadingMore={Boolean(section.isLoadingMore)} onLoadMore={() => void loadMoreSection(section.key)} onOpen={openDetail} onSearch={searchResources} />) : null}
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

function ResultSection({ title, description, items, degraded, hydratingYearKeys, hasMore, isLoadingMore, onLoadMore, onOpen, onSearch }: { title: string; description: string; items: MediaSubjectSummary[]; degraded: boolean; hydratingYearKeys: Set<string>; hasMore: boolean; isLoadingMore: boolean; onLoadMore: () => void; onOpen: (item: MediaSubjectSummary) => void; onSearch: (item: MediaSubjectSummary) => void }) {
  return (
    <section className="dc-section" aria-label={title}>
      <div className="dc-section-heading"><div><h3>{title}</h3><p>{description}</p></div>{degraded ? <span className="dc-degraded">降级</span> : null}</div>
      {items.length ? (
        <>
          <div className="dc-poster-grid">{items.map((item) => <MediaPoster key={item.media_subject_id} item={item} isHydratingYear={hydratingYearKeys.has(`${item.provider_id}:${item.media_subject_id}`)} onOpen={() => onOpen(item)} onSearch={() => onSearch(item)} />)}</div>
          {hasMore ? <div className="dc-load-more"><Button variant="secondary" disabled={isLoadingMore} onClick={onLoadMore}>{isLoadingMore ? '正在加载…' : '加载更多'}</Button></div> : null}
        </>
      ) : <EmptyState message="当前分区没有内容" sub={degraded ? '该分区失败，其他分区仍可继续使用。' : 'Provider 暂未返回符合条件的条目。'} />}
    </section>
  )
}

function MediaPoster({ item, isHydratingYear, onOpen, onSearch }: { item: MediaSubjectSummary; isHydratingYear: boolean; onOpen: () => void; onSearch: () => void }) {
  return (
    <article className="dc-poster">
      <button className="dc-poster-image" type="button" onClick={onOpen} aria-label={`查看 ${item.canonical_title} 详情`}>
        <PosterImage item={item} alt="" loading="lazy" />
        {item.watchlisted || item.followed ? <span className="dc-poster-state">{item.watchlisted ? '想看' : '关注'}</span> : null}
      </button>
      <div className="dc-poster-copy"><button type="button" onClick={onOpen}>{item.canonical_title}</button><p>{item.release_year || (isHydratingYear ? '正在补全年份' : '年份待补充')} · {item.media_type === 'movie' ? '电影' : '剧集'}</p></div>
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
