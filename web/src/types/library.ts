import type { TransferResponse } from './transfer'

export type DtlMediaType = 'movie' | 'series' | 'unclassified'

export type MediaLibraryResponse = {
  id: string
  name: string
  media_type: DtlMediaType
  enabled: boolean
  connection_id: string
  base_path: string
  bound_remote_libraries: string[]
  last_test_ok: boolean | null
  last_test_error_code: string | null
  last_test_error_message: string | null
  created_at: string | null
  updated_at: string | null
}

export type MediaLibraryListResponse = {
  count: number
  page: number
  page_size: number
  results: MediaLibraryResponse[]
}

export type DtlConfigResponse = {
  delete_source_after_success: boolean
  delete_empty_source_dirs: boolean
  scan_interval_seconds: number
  stable_seconds: number
  unclassified_library_id: string
}

export type DtlBindingResponse = {
  id: string
  name: string
  enabled: boolean
  media_type: DtlMediaType
  source_connection_id: string
  source_path: string
  target_library_id: string
  delete_source_after_success: boolean | null
  delete_empty_source_dirs: boolean | null
  created_at: string | null
  updated_at: string | null
}

export type DtlBindingListResponse = {
  count: number
  results: DtlBindingResponse[]
}

export type DtlDiscoveredFileResponse = {
  id: string
  binding_id: string | null
  source_fingerprint: string
  source_path: string
  source_size: number | null
  source_mtime: string | null
  status: string
  task_id: string | null
  created_at: string | null
  updated_at: string | null
}

export type DtlDiscoveredListResponse = {
  count: number
  results: DtlDiscoveredFileResponse[]
}

export type DtlScanResponse = {
  scanned_bindings: number
  discovered_count: number
  stable_count: number
  results: DtlDiscoveredFileResponse[]
}

export type DtlTaskCreateResponse = {
  created_count: number
  skipped_count: number
  tasks: TransferResponse[]
}

export type DtlBindingTestResponse = {
  ok: boolean
  source_ok: boolean
  target_ok: boolean
  error_code: string | null
  error_message: string | null
}

export type DtlBindingFormState = {
  id: string
  name: string
  enabled: boolean
  media_type: DtlMediaType
  source_connection_id: string
  source_path: string
  target_library_id: string
  delete_source_after_success: '' | 'true' | 'false'
  delete_empty_source_dirs: '' | 'true' | 'false'
}

export type DtlConfigFormState = {
  delete_source_after_success: boolean
  delete_empty_source_dirs: boolean
  scan_interval_seconds: string
  stable_seconds: string
  unclassified_library_id: string
}

export type MediaLibraryFormState = {
  id: string
  name: string
  media_type: DtlMediaType
  enabled: boolean
  connection_id: string
  base_path: string
}
