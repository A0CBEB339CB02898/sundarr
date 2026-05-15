import type { DtlMediaType } from './library'

export type RemoteMediaLibraryFormState = {
  id: string
  name: string
  media_type: DtlMediaType
  enabled: boolean
  connection_id: string
  base_path: string
  target_library_id: string
  scan_interval_seconds: string
  stable_seconds: string
  delete_source_after_success: '' | 'true' | 'false'
  delete_empty_source_dirs: '' | 'true' | 'false'
}

export type RemoteMediaLibraryResponse = {
  id: string
  name: string
  media_type: DtlMediaType
  enabled: boolean
  connection_id: string
  base_path: string
  target_library_id: string | null
  target_library_name: string | null
  scan_interval_seconds: number
  stable_seconds: number
  delete_source_after_success: boolean | null
  delete_empty_source_dirs: boolean | null
  last_test_ok: boolean | null
  last_test_error_code: string | null
  last_test_error_message: string | null
  created_at: string | null
  updated_at: string | null
}

export type RemoteMediaLibraryListResponse = {
  count: number
  page: number
  page_size: number
  results: RemoteMediaLibraryResponse[]
}
