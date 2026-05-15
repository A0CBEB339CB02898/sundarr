export type ComponentHealth = {
  status: string
  checked_at: string
}

export type HealthResponse = {
  status: string
  database: string
  redis: string
  worker: string
  checked_at: string
  components: {
    api: ComponentHealth
    database: ComponentHealth
    redis: ComponentHealth
    worker: ComponentHealth
  }
}
