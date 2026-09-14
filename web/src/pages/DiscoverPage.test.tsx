import { act, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { api } from '../api/client'
import type { CatalogProvider, DiscoverPageResponse, MediaSubjectSummary } from '../types'
import DiscoverPage from './DiscoverPage'

vi.mock('../api/client', () => ({
  api: {
    delete: vi.fn(),
    get: vi.fn(),
    post: vi.fn(),
  },
}))

const providers: CatalogProvider[] = [
  {
    id: 'tmdb-catalog',
    identity_namespaces: ['tmdb'],
    operations: ['search', 'trending', 'categories', 'detail'],
    media_types: ['movie', 'series'],
    filters: ['genre', 'region', 'year'],
    sorts: ['popularity'],
    operation_filters: { categories: ['genre', 'region', 'year'] },
    operation_sorts: { categories: ['popularity'] },
    attribution: {
      provider_name: 'TMDb',
      homepage_url: 'https://www.themoviedb.org/',
      notice: '测试数据来源',
      logo_url: null,
      image_referer_url: null,
    },
    filter_options: {
      genre: [{ value: '18', label: '剧情' }],
      region: [{ value: 'CN', label: '中国大陆' }],
    },
  },
  {
    id: 'douban-catalog',
    identity_namespaces: ['douban'],
    operations: ['search', 'trending', 'categories', 'detail'],
    media_types: ['movie', 'series'],
    filters: ['genre', 'region', 'year'],
    sorts: ['popularity'],
    operation_filters: { categories: ['genre', 'region', 'year'] },
    operation_sorts: { categories: ['popularity'] },
    attribution: {
      provider_name: '豆瓣',
      homepage_url: 'https://movie.douban.com/',
      notice: '测试数据来源',
      logo_url: null,
      image_referer_url: null,
    },
    filter_options: {
      genre: [{ value: '剧情', label: '剧情' }],
      region: [{ value: '中国大陆', label: '中国大陆' }],
    },
  },
]

function subject(id: string, title: string, providerId = 'tmdb-catalog'): MediaSubjectSummary {
  return {
    media_subject_id: id,
    media_type: 'movie',
    canonical_title: title,
    release_year: 2026,
    poster_url: 'https://example.com/poster.jpg',
    poster_provider_id: providerId,
    provider_id: providerId,
    external_id: id,
    external_ids: { [providerId === 'douban-catalog' ? 'douban' : 'tmdb']: id },
    followed: false,
    watchlisted: false,
    degraded: false,
  }
}

function page(
  items: MediaSubjectSummary[],
  continuationToken: string | null = null,
  providerId = 'tmdb-catalog',
): DiscoverPageResponse {
  return {
    items,
    continuation_token: continuationToken,
    provider_id: providerId,
    degraded: false,
    cached_at: null,
  }
}

function installApiMock(
  resolveDiscover: (path: string) => DiscoverPageResponse | Promise<DiscoverPageResponse> = () => page([subject('first', '测试电影')]),
) {
  vi.mocked(api.get).mockImplementation(async (path) => {
    if (path === '/discover/providers') return providers
    return resolveDiscover(path)
  })
  vi.mocked(api.post).mockResolvedValue({})
  vi.mocked(api.delete).mockResolvedValue({})
}

function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>((next) => { resolve = next })
  return { promise, resolve }
}

describe('媒体发现页', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    window.history.replaceState({}, '', '/app/discover?provider_id=tmdb-catalog')
  })

  it('默认展示热门电影，并保留中文热门入口', async () => {
    installApiMock()

    render(<DiscoverPage showToast={vi.fn()} />)

    expect(await screen.findByText('测试电影')).toBeTruthy()
    const categoryNavigation = screen.getByRole('navigation', { name: '内容分类' })
    expect(within(categoryNavigation).getByRole('button', { name: '热门' })).toBeTruthy()
    expect(vi.mocked(api.get)).toHaveBeenCalledWith(
      expect.stringContaining('/discover/trending?media_type=movie&'),
    )
  })

  it('提交搜索后同步 URL，并展示 Provider 返回的结果', async () => {
    installApiMock((path) => path.startsWith('/discover/search?')
      ? page([subject('love-letter', '情书')])
      : page([subject('first', '测试电影')]))
    const user = userEvent.setup()
    render(<DiscoverPage showToast={vi.fn()} />)
    await screen.findByText('测试电影')

    await user.type(screen.getByLabelText('搜索目录'), '情书')
    await user.click(screen.getByRole('button', { name: '搜索' }))

    expect(await screen.findByText('情书')).toBeTruthy()
    expect(window.location.search).toContain('provider_id=tmdb-catalog')
    expect(window.location.search).toContain('q=%E6%83%85%E4%B9%A6')
    expect(vi.mocked(api.get)).toHaveBeenCalledWith(
      expect.stringMatching(/^\/discover\/search\?.*q=%E6%83%85%E4%B9%A6/),
    )
  })

  it('切换目录来源后更新 URL，并使用新 Provider 请求热门内容', async () => {
    installApiMock((path) => path.includes('provider_id=douban-catalog')
      ? page([subject('douban-first', '豆瓣电影', 'douban-catalog')], null, 'douban-catalog')
      : page([subject('first', '测试电影')]))
    const user = userEvent.setup()
    render(<DiscoverPage showToast={vi.fn()} />)
    await screen.findByText('测试电影')

    const providerGroup = screen.getByRole('group', { name: '数据来源' })
    await user.click(within(providerGroup).getByRole('button', { name: '豆瓣' }))

    expect(await screen.findByText('豆瓣电影')).toBeTruthy()
    expect(window.location.search).toContain('provider_id=douban-catalog')
    await waitFor(() => expect(vi.mocked(api.get)).toHaveBeenCalledWith(
      expect.stringContaining('provider_id=douban-catalog'),
    ))
  })

  it('Provider 返回空列表时展示明确空状态', async () => {
    installApiMock(() => page([]))

    render(<DiscoverPage showToast={vi.fn()} />)

    expect(await screen.findByText('当前分区没有内容')).toBeTruthy()
    expect(screen.getByText('Provider 暂未返回符合条件的条目。')).toBeTruthy()
  })

  it('使用 continuation token 加载下一页并合并去重', async () => {
    installApiMock((path) => path.includes('continuation_token=next-page')
      ? page([subject('second', '第二页电影')])
      : page([subject('first', '第一页电影')], 'next-page'))
    const user = userEvent.setup()
    render(<DiscoverPage showToast={vi.fn()} />)
    await screen.findByText('第一页电影')

    await user.click(screen.getByRole('button', { name: '加载更多' }))

    expect(await screen.findByText('第二页电影')).toBeTruthy()
    expect(screen.getByText('第一页电影')).toBeTruthy()
    expect(vi.mocked(api.get)).toHaveBeenCalledWith(
      expect.stringContaining('continuation_token=next-page'),
    )
  })

  it('切回全部后忽略晚到的筛选结果', async () => {
    const filteredResponse = deferred<DiscoverPageResponse>()
    let homeRequestCount = 0
    installApiMock((path) => {
      if (path.includes('/discover/categories?') && path.includes('genre=18')) {
        return filteredResponse.promise
      }
      if (path.includes('/discover/trending?')) {
        homeRequestCount += 1
        return page([subject(`home-${homeRequestCount}`, homeRequestCount === 1 ? '初始电影' : '全部电影')])
      }
      return page([])
    })
    const user = userEvent.setup()
    render(<DiscoverPage showToast={vi.fn()} />)
    await screen.findByText('初始电影')

    await user.click(screen.getByRole('button', { name: '剧情' }))
    await waitFor(() => expect(vi.mocked(api.get)).toHaveBeenCalledWith(
      expect.stringMatching(/^\/discover\/categories\?.*genre=18/),
    ))
    const genreGroup = screen.getByRole('group', { name: '题材，可多选' })
    await user.click(within(genreGroup).getByRole('button', { name: '全部' }))
    expect(await screen.findByText('全部电影')).toBeTruthy()

    await act(async () => {
      filteredResponse.resolve(page([subject('filtered', '过期筛选电影')]))
      await filteredResponse.promise
    })

    expect(screen.queryByText('过期筛选电影')).toBeNull()
    expect(screen.getByText('全部电影')).toBeTruthy()
    expect(window.location.search).not.toContain('genre=')
  })
})
