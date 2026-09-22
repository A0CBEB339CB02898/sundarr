export type PluginConfigFieldSchema = {
  type: 'string' | 'password' | 'integer' | 'boolean' | 'select'
  label?: string
  required?: boolean
  secret?: boolean
  default?: unknown
  placeholder?: string
  options?: string[]
}

export type PluginRepositoryResponse = {
  id: string
  name: string
  repo_url: string
  branch: string
  current_commit: string | null
  previous_commit: string | null
  enabled: boolean
  status: string
  last_error: string | null
  plugin_ids: string[]
  last_checked_at: string | null
  last_loaded_at: string | null
}

export type PluginRepositoryUpdateCheck = {
  repository_id: string
  current_commit: string | null
  latest_commit: string
  update_available: boolean
  checked_at: string
}

export type PluginActivationDiagnostic = {
  plugin_id: string
  repository_id: string
  commit_hash: string
  status: string
  requires: string[]
  provides: string[]
  cleanup_count: number
  error: string | null
  activated_at: string | null
}

export type PluginHealthCheckResponse = {
  plugin_id: string
  ok: boolean
  message: string
  details: Record<string, unknown>
  checked_at: string
}

export type PluginResponse = {
  id: string
  name: string
  version: string
  plugin_type: string
  description: string
  author: string
  homepage_url: string
  repository_id: string
  enabled: boolean
  status: string
  error: string | null
  commit_hash: string | null
  config: Record<string, unknown>
  config_schema: Record<string, PluginConfigFieldSchema>
  missing_required_config: string[]
  configuration_required: boolean
  requires: string[]
  provides: string[]
}

export type PluginMutationResponse = {
  status: string
  message: string
  repository_id?: string
  commit?: string
  plugin_ids?: string[]
}
