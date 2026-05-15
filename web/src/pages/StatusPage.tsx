import React, { useEffect, useState } from 'react'
import { api } from '../api/client'
import { formatClockFromISO } from '../utils/format'
import { statusLabel, statusDescription } from '../utils/labels'
import type { HealthResponse } from '../types'
import type { StatusTone } from '../ui'
import { Card, Button, LoadingState as UILoadingState, ErrorState as UIErrorState } from '../ui'

function StatusCard({ label, value, lastChecked }: { label: string; value: string; lastChecked: string }) {
  const tone: StatusTone =
    value === 'ok' ? 'success' : value === 'unknown' ? 'paused' : 'danger'
  return (
    <Card className="st-card" data-tone={tone} role="listitem">
      <p className="ui-eyebrow">{label}</p>
      <h3 className="st-card-value">{statusLabel(value)}</h3>
      <p className="st-card-line">
        <span className="st-card-dot" aria-hidden="true" />
        <span className="st-card-desc">{statusDescription(label, value)}</span>
      </p>
      <p className="st-card-meta">
        <span>last checked</span>
        <time>{lastChecked}</time>
      </p>
    </Card>
  )
}

export default function StatusPage() {
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [workerState, setWorkerState] = useState<{ enabled: boolean; running: boolean; pid: number | null } | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [isMutating, setIsMutating] = useState(false)

  useEffect(() => { void loadHealth() }, [])

  async function loadHealth() {
    setIsLoading(true); setError(null)
    try {
      const [h, w] = await Promise.all([
        api.get<HealthResponse>('/health'),
        api.get<{ enabled: boolean; running: boolean; pid: number | null }>('/worker/status'),
      ])
      setHealth(h); setWorkerState(w)
    } catch (exc) {
      setHealth(null); setWorkerState(null)
      setError(exc instanceof Error ? exc.message : '无法读取系统状态。')
    } finally { setIsLoading(false) }
  }

  async function toggleWorker(enable: boolean) {
    setIsMutating(true); setError(null)
    try {
      await api.post(enable ? '/worker/resume' : '/worker/pause')
      void loadHealth()
    } catch (exc) { setError(exc instanceof Error ? exc.message : '操作失败。') }
    finally { setIsMutating(false) }
  }

  const items: { label: string; value: string; checkedAt: string | null }[] = health ? [
    { label: 'API', value: health.status, checkedAt: health.components.api.checked_at },
    { label: 'Database', value: health.database, checkedAt: health.components.database.checked_at },
    { label: 'Redis', value: health.redis, checkedAt: health.components.redis.checked_at },
    { label: 'Worker', value: health.worker, checkedAt: health.components.worker.checked_at },
  ] : []

  return (
    <section className="st-page" aria-labelledby="status-title">
      <Card className="st-overview">
        <div className="st-overview-head">
          <div>
            <p className="ui-eyebrow">状态</p>
            <h2 id="status-title">系统状态概览</h2>
            <p className="st-overview-lead">
              调用 <code>GET /health</code> 与 <code>GET /worker/status</code>，展示 API、Database、Redis 与 Worker 的当前状态。
            </p>
          </div>
          <div className="st-overview-actions">
            <Button variant="primary" disabled={isLoading} onClick={() => void loadHealth()}>
              {isLoading ? '刷新中' : '刷新状态'}
            </Button>
          </div>
        </div>
      </Card>

      {isLoading && !health ? (
        <Card>
          <UILoadingState message="正在读取系统状态。" />
        </Card>
      ) : null}
      {error ? (
        <Card>
          <UIErrorState message="请求失败" sub={error} />
        </Card>
      ) : null}

      {health ? (
        <>
          <div className="st-grid" role="list" aria-label="系统状态卡片">
            {items.map((item) => (
              <StatusCard
                key={item.label}
                label={item.label}
                value={item.value}
                lastChecked={formatClockFromISO(item.checkedAt)}
              />
            ))}
          </div>

          {workerState ? (
            <Card className="st-worker-card">
              <div className="st-worker-head">
                <div>
                  <p className="ui-eyebrow">Worker 控制</p>
                  <strong className="st-worker-title">
                    {workerState.enabled ? '已启用' : '已暂停'}
                  </strong>
                  <p className="st-worker-sub">
                    PID <span className="st-mono">{workerState.pid ?? '--'}</span>
                    {' · '}
                    进程{workerState.running ? '运行中' : '未运行'}
                  </p>
                </div>
                <div className="st-worker-actions">
                  <Button
                    variant="secondary"
                    disabled={isMutating || !workerState.enabled}
                    onClick={() => void toggleWorker(false)}
                  >
                    暂停 Worker
                  </Button>
                  <Button
                    variant="secondary"
                    disabled={isMutating || workerState.enabled}
                    onClick={() => void toggleWorker(true)}
                  >
                    恢复 Worker
                  </Button>
                </div>
              </div>
            </Card>
          ) : null}

          <Card emphasis="sunken" className="st-diag">
            <details className="st-diag-details">
              <summary className="st-diag-summary">
                <span>
                  <p className="ui-eyebrow">Diagnostics</p>
                  <strong>原始 /health 返回</strong>
                </span>
                <span className="st-diag-chevron" aria-hidden="true">
                  <svg viewBox="0 0 12 12" width="12" height="12" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M3 4.5l3 3 3-3" />
                  </svg>
                </span>
              </summary>
              <pre className="st-diag-body">
                {JSON.stringify({ health, worker: workerState }, null, 2)}
              </pre>
            </details>
          </Card>
        </>
      ) : null}
    </section>
  )
}
