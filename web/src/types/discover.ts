export type CatalogFilterOption = { value: string; label: string }

export type CatalogProvider = {
  id: string
  identity_namespaces: string[]
  operations: string[]
  media_types: string[]
  filters: string[]
  sorts: string[]
  operation_filters?: Record<string, string[]>
  operation_sorts?: Record<string, string[]>
  filter_options: Record<string, CatalogFilterOption[]>
}

export type MediaSubjectSummary = {
  media_subject_id: string
  media_type: 'movie' | 'series'
  canonical_title: string
  release_year: number | null
  poster_url: string | null
  provider_id: string
  external_id: string
  external_ids: Record<string, string>
  followed: boolean
  watchlisted: boolean
  degraded: boolean
}

export type DiscoverPageResponse = {
  items: MediaSubjectSummary[]
  continuation_token: string | null
  provider_id: string
  degraded: boolean
  cached_at: string | null
}

export type MediaSubjectDetail = MediaSubjectSummary & {
  original_title: string | null
  overview: string | null
  release_date: string | null
  genres: string[]
  regions: string[]
  rating: number | null
  rating_provider: string | null
  vote_count: number | null
  backdrop_url: string | null
  image_urls: string[]
  snapshot_updated_at: string | null
}

export type WatchlistPageResponse = {
  items: MediaSubjectSummary[]
  count: number
}
