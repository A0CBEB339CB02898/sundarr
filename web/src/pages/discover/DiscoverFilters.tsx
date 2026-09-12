import type { FormEvent } from 'react'
import type { CatalogFilterOption, CatalogProvider } from '../../types'
import type { ActiveFilter, CategoryKey, FilterState } from './model'
import {
  advancedFilters,
  categoryItems,
  sortItems,
  yearPresets,
} from './model'

type DiscoverFiltersProps = {
  filters: FilterState
  searchDraft: string
  providers: CatalogProvider[]
  activeProvider?: CatalogProvider
  activeFilters: ActiveFilter[]
  availableFilters: string[]
  availableSorts: string[]
  genreOptions: CatalogFilterOption[]
  categoryGenre?: CatalogFilterOption
  allRegionOptions: CatalogFilterOption[]
  visibleRegionOptions: CatalogFilterOption[]
  otherRegionOptions: CatalogFilterOption[]
  showExactYears: boolean
  showOtherRegions: boolean
  exactYears: string[]
  onSearchDraftChange: (value: string) => void
  onSubmitSearch: (event: FormEvent) => void
  onSelectCategory: (category: CategoryKey) => void
  onChangeProvider: (providerId: string) => void
  onClearFilters: () => void
  onToggleGenre: (value: string) => void
  onSelectYear: (from: string, to: string) => void
  onToggleExactYears: () => void
  onToggleOtherRegions: () => void
  onUpdateExplore: (patch: Partial<FilterState>) => void
}

export function DiscoverFilters({
  filters,
  searchDraft,
  providers,
  activeProvider,
  activeFilters,
  availableFilters,
  availableSorts,
  genreOptions,
  categoryGenre,
  allRegionOptions,
  visibleRegionOptions,
  otherRegionOptions,
  showExactYears,
  showOtherRegions,
  exactYears,
  onSearchDraftChange,
  onSubmitSearch,
  onSelectCategory,
  onChangeProvider,
  onClearFilters,
  onToggleGenre,
  onSelectYear,
  onToggleExactYears,
  onToggleOtherRegions,
  onUpdateExplore,
}: DiscoverFiltersProps) {
  return (
    <>
      <div className="dc-discovery-toolbar">
        <nav className="dc-category-tabs" aria-label="内容分类">
          {categoryItems.map((item) => (
            <button
              key={item.key}
              type="button"
              className="dc-category-tab"
              aria-current={filters.category === item.key && !filters.q ? 'page' : undefined}
              onClick={() => onSelectCategory(item.key)}
            >
              {item.label}
            </button>
          ))}
        </nav>
        <form className="dc-search" role="search" onSubmit={onSubmitSearch}>
          <label htmlFor="discover-search">搜索目录</label>
          <div className="dc-search-control">
            <span aria-hidden="true">⌕</span>
            <input
              id="discover-search"
              value={searchDraft}
              onChange={(event) => onSearchDraftChange(event.target.value)}
              placeholder="搜索片名、演员、导演或关键词"
            />
            <button type="submit">搜索</button>
          </div>
          <small>实际检索范围由当前目录来源决定</small>
        </form>
      </div>

      <section className="dc-filter-panel" aria-label="内容筛选">
        {providers.length > 1 ? (
          <div className="dc-filter-row dc-provider-row">
            <div className="dc-filter-label">数据来源</div>
            <div className="dc-tag-rail" role="group" aria-label="数据来源">
              {providers.map((provider) => (
                <button
                  key={provider.id}
                  type="button"
                  className="dc-filter-tag"
                  aria-pressed={activeProvider?.id === provider.id}
                  onClick={() => onChangeProvider(provider.id)}
                >
                  {provider.attribution?.provider_name || provider.id}
                </button>
              ))}
            </div>
          </div>
        ) : null}

        {activeFilters.length ? (
          <div className="dc-active-filters">
            <span>当前筛选</span>
            <div className="dc-active-filter-list">
              {activeFilters.map((filter) => (
                <button
                  key={filter.key}
                  type="button"
                  onClick={filter.remove}
                  aria-label={`取消筛选：${filter.label}`}
                >
                  {filter.label}<span aria-hidden="true">×</span>
                </button>
              ))}
            </div>
            <button type="button" className="dc-clear-filters" onClick={onClearFilters}>清除全部</button>
          </div>
        ) : null}

        <div className="dc-filter-row">
          <div className="dc-filter-label">类型</div>
          <div className="dc-tag-rail" role="group" aria-label="题材，可多选">
            <button
              type="button"
              className="dc-filter-tag"
              aria-pressed={!filters.genres.length && !categoryGenre}
              disabled={!availableFilters.includes('genre')}
              onClick={() => categoryGenre
                ? onSelectCategory('popular')
                : onUpdateExplore({ genres: [] })}
            >全部</button>
            {genreOptions.map((option) => {
              const selected = filters.genres.includes(option.value) || categoryGenre?.value === option.value
              return (
                <button
                  key={option.value}
                  type="button"
                  className="dc-filter-tag"
                  aria-pressed={selected}
                  disabled={!availableFilters.includes('genre')}
                  onClick={() => onToggleGenre(option.value)}
                >
                  {option.label}
                </button>
              )
            })}
          </div>
        </div>

        <div className="dc-filter-row">
          <div className="dc-filter-label">年份</div>
          <div className="dc-tag-rail" role="group" aria-label="年份">
            {yearPresets().map((preset) => (
              <button
                key={preset.key}
                type="button"
                className="dc-filter-tag"
                aria-pressed={filters.year_from === preset.from && filters.year_to === preset.to}
                disabled={!availableFilters.includes('year')}
                onClick={() => onSelectYear(preset.from, preset.to)}
              >
                {preset.label}
              </button>
            ))}
            <button
              type="button"
              className="dc-filter-tag dc-filter-expand"
              aria-expanded={showExactYears}
              disabled={!availableFilters.includes('year')}
              onClick={onToggleExactYears}
            >
              精确年份 <span aria-hidden="true">{showExactYears ? '−' : '+'}</span>
            </button>
          </div>
          {showExactYears ? (
            <div className="dc-exact-years" role="group" aria-label="精确年份">
              {exactYears.map((year) => (
                <button
                  key={year}
                  type="button"
                  className="dc-filter-tag"
                  aria-pressed={filters.year_from === year && filters.year_to === year}
                  onClick={() => onSelectYear(year, year)}
                >{year}</button>
              ))}
            </div>
          ) : null}
        </div>

        {allRegionOptions.length ? (
          <div className="dc-filter-row">
            <div className="dc-filter-label">地区</div>
            <div className="dc-tag-rail" role="group" aria-label="地区">
              <button
                type="button"
                className="dc-filter-tag"
                aria-pressed={!filters.region}
                disabled={!availableFilters.includes('region')}
                onClick={() => onUpdateExplore({ region: '' })}
              >全部</button>
              {visibleRegionOptions.map((option) => (
                <button
                  key={option.value}
                  type="button"
                  className="dc-filter-tag"
                  aria-pressed={filters.region === option.value}
                  disabled={!availableFilters.includes('region')}
                  onClick={() => onUpdateExplore({ region: option.value })}
                >{option.label}</button>
              ))}
              {otherRegionOptions.length ? (
                <button
                  type="button"
                  className="dc-filter-tag dc-filter-expand"
                  aria-expanded={showOtherRegions}
                  onClick={onToggleOtherRegions}
                >其他 <span aria-hidden="true">{showOtherRegions ? '−' : '+'}</span></button>
              ) : null}
            </div>
          </div>
        ) : null}

        <div className="dc-filter-row">
          <div className="dc-filter-label">排序</div>
          <div className="dc-tag-rail" role="group" aria-label="排序">
            {sortItems.map((item) => {
              const supported = Boolean(item.value && availableSorts.includes(item.value))
              const selected = supported
                && (filters.sort === item.value || (!filters.sort && item.value === 'popularity'))
              return (
                <button
                  key={item.key}
                  type="button"
                  className="dc-filter-tag"
                  aria-pressed={selected}
                  disabled={!supported}
                  title={!supported ? item.hint || '当前目录来源不支持此排序' : undefined}
                  onClick={() => item.value && onUpdateExplore({ sort: item.value })}
                >
                  {item.label}{!supported ? <small>暂不支持</small> : null}
                </button>
              )
            })}
          </div>
        </div>

        <details className="dc-more-filters">
          <summary>更多筛选 <span>IMDb 评分、语言、资源质量等</span></summary>
          <div className="dc-advanced-grid">
            {advancedFilters.map((item) => (
              <button key={item.label} type="button" className="dc-filter-tag" disabled title={item.hint}>
                {item.label}<small>当前不可用</small>
              </button>
            ))}
          </div>
          <p>这些条件需要目录合同或资源索引提供真实字段，当前不会发送无效请求。</p>
        </details>
      </section>
    </>
  )
}
