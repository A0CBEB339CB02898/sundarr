import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { api } from '../api/client'
import type { PluginActivationDiagnostic, PluginRepositoryResponse, PluginResponse } from '../types'
import PluginsPage from './PluginsPage'

vi.mock('../api/client', () => ({
  api: {
    delete: vi.fn(),
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
  },
}))

const repository: PluginRepositoryResponse = {
  id: 'official',
  name: 'Sundarr 官方插件',
  repo_url: 'https://example.invalid/sundarr-plugin.git',
  branch: 'main',
  current_commit: '1111111111111111111111111111111111111111',
  previous_commit: null,
  enabled: true,
  status: 'active',
  last_error: null,
  plugin_ids: ['fixture-catalog'],
  last_checked_at: null,
  last_loaded_at: '2026-09-22T08:00:00Z',
}

const plugin: PluginResponse = {
  id: 'fixture-catalog',
  name: 'Fixture 目录',
  version: '0.1.0',
  plugin_type: 'catalog_provider',
  description: '用于界面验收的目录插件。',
  author: 'Sundarr',
  homepage_url: 'https://example.invalid',
  repository_id: repository.id,
  enabled: true,
  status: 'active',
  error: null,
  commit_hash: repository.current_commit,
  config: { api_key: '***' },
  config_schema: {
    api_key: { type: 'password', label: 'API Key', required: true, secret: true },
  },
  missing_required_config: [],
  configuration_required: false,
  requires: ['core.http.v1'],
  provides: ['catalog.fixture.v1'],
}

const activation: PluginActivationDiagnostic = {
  plugin_id: plugin.id,
  repository_id: repository.id,
  commit_hash: repository.current_commit!,
  status: 'active',
  requires: ['core.http.v1'],
  provides: ['catalog.fixture.v1'],
  cleanup_count: 1,
  error: null,
  activated_at: '2026-09-22T08:00:00Z',
}

function installApiMock() {
  vi.mocked(api.get).mockImplementation(async (path) => {
    if (path === '/plugins/repositories') return [repository]
    if (path === '/plugins/plugins') return [plugin]
    if (path === '/plugins/activations') return [activation]
    throw new Error(`未处理的 GET：${path}`)
  })
  vi.mocked(api.post).mockImplementation(async (path) => {
    if (path === '/plugins/repositories/official/check') {
      return {
        repository_id: repository.id,
        current_commit: repository.current_commit,
        latest_commit: '2222222222222222222222222222222222222222',
        update_available: true,
        checked_at: '2026-09-22T09:00:00Z',
      }
    }
    if (path === '/plugins/plugins/fixture-catalog/test') {
      return {
        plugin_id: plugin.id,
        ok: true,
        message: '健康检查通过。',
        details: {},
        checked_at: '2026-09-22T09:01:00Z',
      }
    }
    return {}
  })
  vi.mocked(api.put).mockResolvedValue({ status: 'success' })
  vi.mocked(api.delete).mockResolvedValue({ status: 'success' })
}

describe('插件运维页', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    window.history.replaceState({}, '', '/app/settings?tab=plugins&plugin_id=fixture-catalog')
    installApiMock()
  })

  it('先只读检查更新，再显式应用检查到的 commit', async () => {
    const user = userEvent.setup()
    render(<PluginsPage showToast={vi.fn()} />)

    await screen.findByText('Sundarr 官方插件')
    await user.click(screen.getByRole('button', { name: '检查更新' }))

    expect(await screen.findByText(/发现新版本 2222222222/)).toBeTruthy()
    expect(api.put).not.toHaveBeenCalled()

    await user.click(screen.getByRole('button', { name: '应用更新' }))
    await waitFor(() => expect(api.put).toHaveBeenCalledWith(
      '/plugins/repositories/official',
      { new_commit: '2222222222222222222222222222222222222222' },
    ))
  })

  it('展示 Activation 诊断并运行当前实例健康检查', async () => {
    const user = userEvent.setup()
    render(<PluginsPage showToast={vi.fn()} />)

    expect(await screen.findByText('Fixture 目录')).toBeTruthy()
    await user.click(screen.getByText('Activation 诊断'))
    expect(screen.getByText('catalog.fixture.v1')).toBeTruthy()

    await user.click(screen.getByRole('button', { name: '运行健康检查' }))
    expect(await screen.findByText('健康检查通过')).toBeTruthy()
    expect(api.post).toHaveBeenCalledWith('/plugins/plugins/fixture-catalog/test')
  })
})
