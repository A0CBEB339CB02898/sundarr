import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { api } from '../api/client'
import { ConfigurationGuide } from './ConfigurationGuide'

vi.mock('../api/client', () => ({
  api: { get: vi.fn() },
}))

describe('ConfigurationGuide', () => {
  beforeEach(() => {
    window.localStorage.clear()
  })

  it('系统可执行时仍展示非阻断配置提醒', async () => {
    vi.mocked(api.get).mockResolvedValue({
      ready: true,
      fingerprint: 'warning-fingerprint',
      issues: [{
        id: 'remote-library-unbound:remote',
        category: 'sync',
        severity: 'recommended',
        title: '远程媒体库未绑定目标',
        message: '该目录不会自动同步。',
        action_label: '绑定目标媒体库',
        action_path: '/app/remote-libraries',
      }],
    })

    render(<ConfigurationGuide onNavigate={vi.fn()} />)

    expect(await screen.findByText('配置提醒')).toBeTruthy()
    expect(screen.getByText('远程媒体库未绑定目标')).toBeTruthy()
  })
})
