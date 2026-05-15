import type { TransferResponse } from './transfer'

export type SyncMediaType = 'movie' | 'series' | 'unclassified'

export type SyncConfigResponse = {
  delete_source_after_success: boolean
  delete_empty_source_dirs: boolean
  scan_interval_seconds: number
  stable_seconds: number
  unclassified_library_id: string
}

export type SyncBindingResponse = {
  id: string
  name: string
  enabled: boolean
  media_type: SyncMediaType
  remote_library_id: string
  local_library_id: string
  delete_source_after_success: boolean | null
  delete_empty_source_dirs: boolean | null
  created_at: string | null
  updated_at: string | null
}

export type SyncBindingListResponse = {
  count: number
  results: SyncBindingResponse[]
}

export type SyncDiscoveredFileResponse = {
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

export type SyncDiscoveredListResponse = {
  count: number
  results: SyncDiscoveredFileResponse[]
}

export type SyncScanResponse = {
  scanned_bindings: number
  discovered_count: number
  stable_count: number
  results: SyncDiscoveredFileResponse[]
}

export type SyncTaskCreateResponse = {
  created_count: number
  skipped_count: number
  tasks: TransferResponse[]
}

export type SyncBindingTestResponse = {
  ok: boolean
  remote_ok: boolean
  local_ok: boolean
  error_code: string | null
  error_message: string | null
}

export type SyncBindingFormState = {
  id: string
  name: string
  enabled: boolean
  media_type: SyncMediaType
  remote_library_id: string
  local_library_id: string
  delete_source_after_success: '' | 'true' | 'false'
  delete_empty_source_dirs: '' | 'true' | 'false'
}

export type SyncConfigFormState = {
  delete_source_after_success: boolean
  delete_empty_source_dirs: boolean
  scan_interval_seconds: string
  stable_seconds: string
  unclassified_library_id: string
}
