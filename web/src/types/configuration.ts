export type ConfigurationIssue = {
  id: string
  category: string
  severity: 'required' | 'recommended'
  title: string
  message: string
  action_label: string
  action_path: string
}

export type ConfigurationReadinessResponse = {
  ready: boolean
  fingerprint: string
  issues: ConfigurationIssue[]
}
