import type { CatalogFilterOption, CatalogProvider, MediaSubjectSummary } from '../../types'

export type HomeSectionKey = 'movie' | 'series' | 'category' | 'watchlist'

export type DiscoverSection = {
  key: HomeSectionKey
  title: string
  description: string
  items: MediaSubjectSummary[]
  error?: string
  path?: string
  continuationToken?: string | null
  isLoading?: boolean
  isLoadingMore?: boolean
}

export type CategoryKey = 'popular' | 'movie' | 'series' | 'anime' | 'variety'

export type FilterState = {
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

export type ActiveFilter = {
  key: string
  label: string
  remove: () => void
}

export const categoryItems: Array<{ key: CategoryKey; label: string }> = [
  { key: 'popular', label: '热门' },
  { key: 'movie', label: '电影' },
  { key: 'series', label: '剧集' },
  { key: 'anime', label: '动漫' },
  { key: 'variety', label: '综艺' },
]

export const homeSectionItems: Array<{
  key: HomeSectionKey
  title: string
  description: string
}> = [
  { key: 'movie', title: '热门电影', description: '当前目录来源返回的热门电影' },
  { key: 'series', title: '热门剧集', description: '当前目录来源返回的热门剧集' },
  { key: 'category', title: '分类推荐', description: '按当前目录能力生成的推荐' },
  { key: 'watchlist', title: '关注更新', description: '来自独立想看 Provider，不受当前目录来源选择影响' },
]

export const categoryGenreLabels: Partial<Record<CategoryKey, string[]>> = {
  anime: ['动画', '动漫', 'Animation'],
  variety: ['综艺', '真人秀', '脱口秀', 'Reality', 'Talk'],
}

export const preferredGenreLabels = [
  '剧情', '科幻', '动作', '喜剧', '爱情', '惊悚', '恐怖', '动画', '犯罪', '悬疑',
  '纪录片', '战争', '历史', '音乐', '家庭', '校园', '真人秀', '脱口秀',
]

export const preferredRegions = [
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

export const sortItems: Array<{
  key: string
  label: string
  value: string | null
  hint?: string
}> = [
  { key: 'popular', label: '热门', value: 'popularity' },
  { key: 'rating', label: '评分最高', value: 'rating' },
  { key: 'published', label: '最新发布', value: null, hint: '目录模型尚无内容发布时间' },
  { key: 'release', label: '最新上映', value: 'release_date' },
  { key: 'favorites', label: '收藏最多', value: null, hint: '当前单用户模型没有收藏次数' },
  { key: 'views', label: '观看最多', value: null, hint: 'Sundarr 不记录播放次数' },
]

export const advancedFilters = [
  { label: 'IMDb 评分', hint: '当前目录合同没有 IMDb 评分筛选' },
  { label: '评分人数', hint: '列表查询合同没有评分人数筛选' },
  { label: '资源质量', hint: '资源质量属于具体资源搜索，不属于目录发现' },
  { label: '语言', hint: '当前目录合同没有语言筛选' },
  { label: '字幕类型', hint: '目录数据不包含字幕信息' },
]

export function emptyFilters(providerId = ''): FilterState {
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

export function isCategoryKey(value: string | null): value is CategoryKey {
  return categoryItems.some((item) => item.key === value)
}

export function filtersForOperation(provider: CatalogProvider | undefined, operation: string) {
  return provider?.operation_filters && operation in provider.operation_filters
    ? provider.operation_filters[operation]
    : provider?.filters || []
}

export function sortsForOperation(provider: CatalogProvider | undefined, operation: string) {
  return provider?.operation_sorts && operation in provider.operation_sorts
    ? provider.operation_sorts[operation]
    : provider?.sorts || []
}

export function filtersFromSearch(search: string): FilterState {
  const params = new URLSearchParams(search)
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

export function filtersFromUrl(): FilterState {
  return filtersFromSearch(window.location.search)
}

export function detailIdFromPath(pathname = window.location.pathname) {
  const match = pathname.match(/^\/app\/discover\/([^/]+)$/)
  return match ? decodeURIComponent(match[1]) : null
}

export function isResourceModeFromLocation(
  pathname = window.location.pathname,
  search = window.location.search,
) {
  if (pathname === '/app/search') return true
  return pathname === '/app/discover'
    && new URLSearchParams(search).get('mode') === 'resources'
}

export function optionForCategory(
  provider: CatalogProvider | undefined,
  category: CategoryKey,
) {
  const candidates = categoryGenreLabels[category]
  if (!provider || !candidates) return undefined
  return (provider.filter_options.genre || []).find((option) =>
    candidates.some((candidate) => candidate.toLocaleLowerCase() === option.label.toLocaleLowerCase()),
  )
}

export function orderedOptions(options: CatalogFilterOption[], preferredLabels: string[]) {
  const rank = new Map(preferredLabels.map((label, index) => [label, index]))
  return [...options].sort((left, right) => {
    const leftRank = rank.get(left.label) ?? preferredLabels.length
    const rightRank = rank.get(right.label) ?? preferredLabels.length
    return leftRank - rightRank || left.label.localeCompare(right.label, 'zh-CN')
  })
}

export function optionLabel(options: CatalogFilterOption[], value: string) {
  return options.find((option) => option.value === value)?.label || value
}

export function yearPresets() {
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

export function yearFilterLabel(state: FilterState) {
  if (!state.year_from && !state.year_to) return ''
  if (state.year_from && state.year_from === state.year_to) return `${state.year_from}年`
  const preset = yearPresets().find((item) => item.from === state.year_from && item.to === state.year_to)
  return preset?.label || `${state.year_from || '最早'}至${state.year_to || '现在'}`
}

export function remapValue(
  value: string,
  previousOptions: CatalogFilterOption[],
  nextOptions: CatalogFilterOption[],
) {
  if (!value) return ''
  const previousLabel = optionLabel(previousOptions, value)
  return nextOptions.find((option) => option.label === previousLabel)?.value || ''
}

export function mergeUniqueItems(
  current: MediaSubjectSummary[],
  incoming: MediaSubjectSummary[],
) {
  const seen = new Set(current.map((item) => item.media_subject_id))
  return [...current, ...incoming.filter((item) => !seen.has(item.media_subject_id))]
}

export function chunkItems<T>(items: T[], size: number) {
  return Array.from({ length: Math.ceil(items.length / size) }, (_, index) =>
    items.slice(index * size, (index + 1) * size),
  )
}

export function providerRecognizesItem(
  provider: CatalogProvider,
  item: MediaSubjectSummary,
) {
  const namespaces = new Set([provider.id, ...provider.identity_namespaces])
  return item.provider_id === provider.id
    || Object.keys(item.external_ids).some((namespace) => namespaces.has(namespace))
}

export function apiQueryParams(
  forceRefresh: boolean,
  state: FilterState,
  providerId?: string,
  presetGenre?: string,
) {
  const params = new URLSearchParams()
  if (providerId) params.set('provider_id', providerId)
  if (state.q.trim()) {
    params.set('q', state.q.trim())
  } else {
    if (state.media_type) params.set('media_type', state.media_type)
    Array.from(new Set([presetGenre, ...state.genres].filter(Boolean) as string[]))
      .forEach((genre) => params.append('genre', genre))
    if (state.region) params.set('region', state.region)
    if (state.year_from) params.set('year_from', state.year_from)
    if (state.year_to) params.set('year_to', state.year_to)
    if (state.sort) params.set('sort', state.sort)
  }
  params.set('limit', '24')
  if (forceRefresh) params.set('refresh', 'true')
  return params
}

export function urlParams(state: FilterState) {
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
