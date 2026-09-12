import { describe, expect, it } from 'vitest'
import type { CatalogProvider } from '../../types'
import { filtersForOperation, filtersFromSearch, sortsForOperation, urlParams } from './model'

describe('媒体发现 URL 状态', () => {
  it('可以从 URL 恢复筛选，并序列化为等价查询', () => {
    const filters = filtersFromSearch(
      '?provider_id=douban-catalog&category=movie&media_type=movie&genre=%E5%89%A7%E6%83%85&genre=%E7%A7%91%E5%B9%BB&region=%E4%B8%AD%E5%9B%BD%E5%A4%A7%E9%99%86&year_from=2020&year_to=2026&sort=popularity',
    )

    expect(filters).toEqual({
      provider_id: 'douban-catalog',
      q: '',
      category: 'movie',
      media_type: 'movie',
      genres: ['剧情', '科幻'],
      region: '中国大陆',
      year_from: '2020',
      year_to: '2026',
      sort: 'popularity',
    })
    const serialized = urlParams(filters)
    expect(serialized.getAll('genre')).toEqual(['剧情', '科幻'])
    expect(serialized.get('provider_id')).toBe('douban-catalog')
    expect(serialized.get('category')).toBe('movie')
  })

  it('显式空操作能力不会回退到全局能力并集', () => {
    const provider = {
      filters: ['genre'],
      sorts: ['popularity'],
      operation_filters: { search: [] },
      operation_sorts: { search: [] },
    } as unknown as CatalogProvider

    expect(filtersForOperation(provider, 'search')).toEqual([])
    expect(sortsForOperation(provider, 'search')).toEqual([])
  })
})
