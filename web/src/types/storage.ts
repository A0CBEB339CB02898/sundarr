export type StorageConfigResponse = {
  type: 'smb'
  host: string
  port: number
  share: string
  username: string
  password_set: boolean
  domain: string
  base_path: string
  libraries: Record<string, string>
}

export type SmbConnectionResponse = {
  id: string
  name: string
  enabled: boolean
  host: string
  port: number
  share: string
  username: string
  password_set: boolean
  domain: string
  base_path: string
  bound_local_libraries: string[]
  bound_remote_libraries: string[]
  last_test_ok: boolean | null
  last_test_error_code: string | null
  last_test_error_message: string | null
  created_at: string | null
  updated_at: string | null
}

export type SmbConnectionListResponse = {
  count: number
  page: number
  page_size: number
  results: SmbConnectionResponse[]
}

export type StorageConfigRequest = Omit<StorageConfigResponse, 'password_set'> & {
  password: string | null
}

export type StorageConfigTestResponse = {
  ok: boolean
  error_code: string | null
  error_message: string | null
}

export type StorageBrowseResponse = {
  path: string
  entries: StorageBrowseEntry[]
}

export type StorageBrowseEntry = {
  name: string
  path: string
  is_dir: boolean
  size: number | null
  modified_at: string | null
}

export type StorageFormState = {
  host: string
  port: string
  share: string
  username: string
  password: string
  domain: string
  base_path: string
  library_movies: string
  library_tv: string
  library_anime: string
}
