export type SourceResponse = {
  id: string
  name: string
  description: string
  homepage_url: string
}

export type SourceListResponse = {
  count: number
  page: number
  page_size: number
  results: SourceResponse[]
}

export type SourceTestResponse = {
  ok: boolean
  source_id: string
  items: Record<string, unknown>[]
  logs: SourceTestLog[]
  error_code: string | null
  error_message: string | null
  tested_at: string
}

export type SourceTestLog = {
  step: string
  status: string
  message: string
  data: Record<string, unknown>
}

export type SourceTestFormState = {
  keyword: string
  limit: string
}
