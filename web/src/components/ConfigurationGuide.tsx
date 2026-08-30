import React, { useEffect, useState } from 'react'
import { api } from '../api/client'
import type { ConfigurationReadinessResponse } from '../types'
import { Button } from '../ui'

const DISMISSED_KEY = 'sundarr.configuration-guide.dismissed-fingerprint'

export function ConfigurationGuide({ onNavigate }: { onNavigate: (path: string) => void }) {
  const [readiness, setReadiness] = useState<ConfigurationReadinessResponse | null>(null)
  const [hiddenFingerprint, setHiddenFingerprint] = useState<string | null>(null)

  useEffect(() => {
    void loadReadiness()
    const reload = () => void loadReadiness()
    window.addEventListener('sundarr:configuration-changed', reload)
    return () => window.removeEventListener('sundarr:configuration-changed', reload)
  }, [])

  async function loadReadiness() {
    try {
      const next = await api.get<ConfigurationReadinessResponse>('/configuration/readiness')
      setReadiness(next)
      setHiddenFingerprint(null)
    } catch {
      setReadiness(null)
    }
  }

  if (!readiness || readiness.ready || readiness.issues.length === 0) return null
  if (window.localStorage.getItem(DISMISSED_KEY) === readiness.fingerprint) return null
  if (hiddenFingerprint === readiness.fingerprint) return null

  const [primary, ...remaining] = readiness.issues

  function dismissPermanently() {
    window.localStorage.setItem(DISMISSED_KEY, readiness!.fingerprint)
    setHiddenFingerprint(readiness!.fingerprint)
  }

  return (
    <section className="configuration-guide" aria-labelledby="configuration-guide-title">
      <div className="configuration-guide-mark" aria-hidden="true">{readiness.issues.length}</div>
      <div className="configuration-guide-copy">
        <span className="ui-eyebrow">配置提示</span>
        <h2 id="configuration-guide-title">{primary.title}</h2>
        <p>{primary.message}</p>
        {remaining.length > 0 ? (
          <details>
            <summary>另有 {remaining.length} 项待配置</summary>
            <ul>
              {remaining.map((issue) => (
                <li key={issue.id}>
                  <div><strong>{issue.title}</strong><span>{issue.message}</span></div>
                  <Button size="sm" variant="ghost" onClick={() => onNavigate(issue.action_path)}>{issue.action_label}</Button>
                </li>
              ))}
            </ul>
          </details>
        ) : null}
      </div>
      <div className="configuration-guide-actions">
        <Button size="sm" variant="primary" onClick={() => onNavigate(primary.action_path)}>{primary.action_label}</Button>
        <Button size="sm" variant="ghost" onClick={() => setHiddenFingerprint(readiness.fingerprint)}>稍后</Button>
        <Button size="sm" variant="ghost" onClick={dismissPermanently}>下次不再询问</Button>
      </div>
    </section>
  )
}
