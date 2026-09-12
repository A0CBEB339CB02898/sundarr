import { useEffect, useState } from 'react'
import type { MediaSubjectDetail, MediaSubjectSummary } from '../../types'
import { Button, EmptyState } from '../../ui'

type ResultSectionProps = {
  title: string
  description: string
  items: MediaSubjectSummary[]
  degraded: boolean
  hydrationProviderId?: string
  hydratingYearKeys: Set<string>
  hydratingPosterKeys: Set<string>
  hasMore: boolean
  isLoadingMore: boolean
  onLoadMore: () => void
  onOpen: (item: MediaSubjectSummary) => void
  onSearch: (item: MediaSubjectSummary) => void
}

export function ResultSection({
  title,
  description,
  items,
  degraded,
  hydrationProviderId,
  hydratingYearKeys,
  hydratingPosterKeys,
  hasMore,
  isLoadingMore,
  onLoadMore,
  onOpen,
  onSearch,
}: ResultSectionProps) {
  return (
    <section className="dc-section" aria-label={title}>
      <div className="dc-section-heading">
        <div><h3>{title}</h3><p>{description}</p></div>
        {degraded ? <span className="dc-degraded">降级</span> : null}
      </div>
      {items.length ? (
        <>
          <div className="dc-poster-grid">
            {items.map((item) => {
              const hydrationKey = `${hydrationProviderId || item.provider_id}:${item.media_subject_id}`
              return (
                <MediaPoster
                  key={item.media_subject_id}
                  item={item}
                  posterProviderId={hydrationProviderId}
                  isHydratingYear={hydratingYearKeys.has(hydrationKey)}
                  isHydratingPoster={hydratingPosterKeys.has(hydrationKey)}
                  onOpen={() => onOpen(item)}
                  onSearch={() => onSearch(item)}
                />
              )
            })}
          </div>
          {hasMore ? (
            <div className="dc-load-more">
              <Button variant="secondary" disabled={isLoadingMore} onClick={onLoadMore}>
                {isLoadingMore ? '正在加载…' : '加载更多'}
              </Button>
            </div>
          ) : null}
        </>
      ) : (
        <EmptyState
          message="当前分区没有内容"
          sub={degraded ? '该分区失败，其他分区仍可继续使用。' : 'Provider 暂未返回符合条件的条目。'}
        />
      )}
    </section>
  )
}

type MediaPosterProps = {
  item: MediaSubjectSummary
  posterProviderId?: string
  isHydratingYear: boolean
  isHydratingPoster: boolean
  onOpen: () => void
  onSearch: () => void
}

function MediaPoster({
  item,
  posterProviderId,
  isHydratingYear,
  isHydratingPoster,
  onOpen,
  onSearch,
}: MediaPosterProps) {
  return (
    <article className="dc-poster">
      <button
        className="dc-poster-image"
        type="button"
        onClick={onOpen}
        aria-label={`查看 ${item.canonical_title} 详情`}
      >
        <PosterImage
          item={item}
          alt=""
          loading="lazy"
          isHydrating={isHydratingPoster}
          providerId={posterProviderId}
        />
        {item.watchlisted || item.followed ? (
          <span className="dc-poster-state">{item.watchlisted ? '想看' : '关注'}</span>
        ) : null}
      </button>
      <div className="dc-poster-copy">
        <button type="button" onClick={onOpen}>{item.canonical_title}</button>
        <p>
          {item.release_year || (isHydratingYear ? '正在补全年份' : '年份待补充')}
          {' · '}{item.media_type === 'movie' ? '电影' : '剧集'}
        </p>
      </div>
      <Button size="sm" variant="ghost" onClick={onSearch}>查找资源</Button>
    </article>
  )
}

type DetailViewProps = {
  detail: MediaSubjectDetail
  onBack: () => void
  onFollow: () => void
  onSearch: () => void
}

export function DetailView({ detail, onBack, onFollow, onSearch }: DetailViewProps) {
  return (
    <div className="dc-detail">
      <Button variant="ghost" onClick={onBack}>返回发现</Button>
      <div className="dc-detail-layout">
        <div className="dc-detail-poster">
          <PosterImage item={detail} alt={`${detail.canonical_title} 海报`} />
        </div>
        <div className="dc-detail-copy">
          <p className="ui-eyebrow">
            {detail.media_type === 'movie' ? '电影' : '剧集'} · {detail.release_year || '年份未知'}
          </p>
          {detail.original_title ? <p className="dc-original-title">{detail.original_title}</p> : null}
          {detail.degraded ? (
            <p className="dc-inline-warning">Provider 当前不可用，以下为已保存的最小快照或缓存。</p>
          ) : null}
          <p className="dc-overview">{detail.overview || 'Provider 暂未返回简介。'}</p>
          <dl className="dc-facts">
            <div><dt>题材</dt><dd>{detail.genres.join('、') || '未知'}</dd></div>
            <div><dt>地区</dt><dd>{detail.regions.join('、') || '未知'}</dd></div>
            <div>
              <dt>评分</dt>
              <dd>{detail.rating !== null ? `${detail.rating.toFixed(1)} · ${detail.rating_provider}` : '暂无'}</dd>
            </div>
            <div>
              <dt>外部 ID</dt>
              <dd>{Object.entries(detail.external_ids).map(([key, value]) => `${key}: ${value}`).join(' · ')}</dd>
            </div>
          </dl>
          <div className="dc-detail-actions">
            <Button variant="primary" onClick={onSearch}>查找具体资源</Button>
            <Button onClick={onFollow}>{detail.followed ? '取消关注' : '加入关注'}</Button>
          </div>
        </div>
      </div>
    </div>
  )
}

type PosterImageProps = {
  item: MediaSubjectSummary
  alt: string
  loading?: 'eager' | 'lazy'
  isHydrating?: boolean
  providerId?: string
}

function PosterImage({
  item,
  alt,
  loading,
  isHydrating = false,
  providerId,
}: PosterImageProps) {
  const [source, setSource] = useState(item.poster_url)
  const [failed, setFailed] = useState(false)
  const relayProviderId = item.poster_provider_id || providerId || item.provider_id
  const relayUrl = `/discover/${encodeURIComponent(item.media_subject_id)}/poster?provider_id=${encodeURIComponent(relayProviderId)}`

  useEffect(() => {
    setSource(item.poster_url)
    setFailed(false)
  }, [item.media_subject_id, item.poster_url, item.poster_provider_id, item.provider_id, relayProviderId])

  if (!source || failed) {
    return <span aria-hidden="true">{isHydrating ? '正在补全海报' : '暂无海报'}</span>
  }
  return (
    <img
      src={source}
      alt={alt}
      loading={loading}
      onError={() => {
        if (source !== relayUrl) setSource(relayUrl)
        else setFailed(true)
      }}
    />
  )
}
