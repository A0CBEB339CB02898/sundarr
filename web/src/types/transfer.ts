export type TransferStatus =
  | 'pending'
  | 'staging_to_cloud'
  | 'cloud_ready'
  | 'downloading'
  | 'verifying'
  | 'renaming'
  | 'cleaning_cloud'
  | 'cleaning_source'
  | 'completed'
  | 'failed'
  | 'cancelled'
  | 'paused'

export type TransferResponse = {
  id: string
  resource_id: string | null
  link_id: string | null
  status: TransferStatus
  mode: string
  cloud_staging_path: string | null
  target_type: string
  target_library: string | null
  target_path: string
  source_type: string | null
  source_path: string | null
  sync_seen_file_id: string | null
  total_bytes: number
  done_bytes: number
  speed_bytes_per_sec: number
  progress: number
  current_file: string | null
  error_code: string | null
  error_message: string | null
  retryable: boolean | null
  retry_count: number
  created_at: string | null
  updated_at: string | null
}

export type TransferLogResponse = {
  id: string
  task_id: string
  level: string
  event: string
  message: string | null
  data: Record<string, unknown> | null
  created_at: string
}

export type TransferListResponse = {
  count: number
  page: number
  page_size: number
  results: TransferResponse[]
}
