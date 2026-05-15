import type { TransferStatus } from './transfer'

export type MediaType = 'movie' | 'tv' | 'anime' | 'unknown'
export type ViewMode = 'grid' | 'list'

export type SearchResponse = {
  query: string
  count: number
  results: ResourceCandidate[]
  source_results: SourceSearchResult[]
}

export type SourceSearchResult = {
  source_id: string
  source_name: string
  count: number
  results: ResourceCandidate[]
  error: string | null
}

export type FetchDetailRequest = {
  source_id: string
  detail_url: string
}

export type ResourceCandidate = {
  id: string
  title: string
  normalized_title: string
  original_title: string | null
  year: number | null
  source_id: string
  source_url: string | null
  is_favorited: boolean
  favorited_at: string | null
  has_more_links: boolean
  links: ResourceLinkResult[]
}

export type ResourceLinkResult = {
  id: string
  provider: string
  name: string | null
  url: string
  code: string | null
  quality: string | null
  valid: boolean | null
  validation_status: 'unchecked' | 'checking' | 'valid' | 'invalid' | 'unknown' | 'error'
  validation_message: string | null
  checked_at: string | null
  source_id: string | null
  source_url: string | null
  is_favorited: boolean
  favorited_at: string | null
  published_at: string | null
}

export type ResourceFavoritesListResponse = {
  count: number
  page: number
  page_size: number
  results: ResourceCandidate[]
}

export type ResourceFavoriteRequest = {
  id: string
  title: string
  normalized_title: string
  original_title: string | null
  year: number | null
}

export type ResourceLinkFavoriteRequest = {
  resource: ResourceFavoriteRequest
  link: ResourceLinkResult
}

export type SearchFormState = {
  q: string
}

export function suggestedTargetPath(resource: ResourceCandidate) {
  const year = resource.year ? ` (${resource.year})` : ''
  return `Movies/${resource.normalized_title || resource.title}${year}`
}
