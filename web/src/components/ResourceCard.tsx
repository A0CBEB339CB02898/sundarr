import { useState } from 'react'
import { api } from '../api/client'
import { Button, StatusBadge } from '../ui'
import { EmptyState as UIEmptyState } from '../ui'
import { providerLabel, validationLabel, linkValidationTone } from '../utils/labels'
import { formatDate } from '../utils/format'
import type { ResourceCandidate, ResourceLinkResult } from '../types'

export function ResourceCard({
  activeProvider,
  onCopyLink,
  onFavoriteLink,
  onFavoriteResource,
  onRefreshResource,
  onSaveToCloud,
  resource,
  showToast,
  viewMode,
}: {
  activeProvider: string | null
  onCopyLink: (link: ResourceLinkResult) => void
  onFavoriteLink: (link: ResourceLinkResult) => void
  onFavoriteResource: () => void
  onRefreshResource?: () => void
  onSaveToCloud: (link: ResourceLinkResult) => void
  resource: ResourceCandidate
  showToast?: (type: 'success' | 'error' | 'info', message: string) => void
  viewMode?: 'grid' | 'list'
}) {
  const [isLoadingLinks, setIsLoadingLinks] = useState(false)
  const [localLinks, setLocalLinks] = useState<ResourceLinkResult[]>(resource.links)

  const links = activeProvider
    ? (localLinks.length > 0 ? localLinks : resource.links).filter((link) => link.provider === activeProvider)
    : (localLinks.length > 0 ? localLinks : resource.links)

  async function loadLinks() {
    setIsLoadingLinks(true)
    try {
      if (!resource.source_url) {
        if (showToast) showToast('error', '缺少详情链接地址。')
        return
      }
      const result = await api.post<ResourceCandidate>('/search/detail', {
        source_id: resource.source_id,
        detail_url: resource.source_url as string,
      })
      setLocalLinks(result.links)
    } catch (exc) {
      if (showToast) showToast('error', '加载链接失败。')
    } finally {
      setIsLoadingLinks(false)
    }
  }

  if (viewMode === 'grid') {
    const linkCount = links.length
    const placeholderLetter = (resource.title || '?')[0]
    return (
      <article className="sx-grid-card">
        <div className="sx-grid-card-placeholder">{placeholderLetter}</div>
        <div className="sx-grid-card-body">
          <div className="sx-grid-card-title" title={resource.title}>
            {resource.title}{resource.year ? ` (${resource.year})` : ''}
          </div>
          {resource.original_title && resource.original_title !== resource.title ? (
            <div className="sx-grid-card-meta">{resource.original_title}</div>
          ) : null}
          <div className="sx-grid-card-source">
            <span className="source-badge">{resource.source_id}</span>
          </div>
          <div className="sx-grid-card-actions">
            <Button variant="ghost" size="sm" type="button" onClick={onFavoriteResource}>
              {resource.is_favorited ? '★' : '☆'}
            </Button>
            {resource.has_more_links && localLinks.length === 0 ? (
              <Button variant="secondary" size="sm" type="button" disabled={isLoadingLinks} onClick={() => void loadLinks()}>
                {isLoadingLinks ? '…' : '加载链接'}
              </Button>
            ) : (
              <span style={{ fontSize: 12, color: 'var(--text-subtle)' }}>{linkCount} 个链接</span>
            )}
          </div>
        </div>
      </article>
    )
  }

  return (
    <article className="resource-card">
      <div className="resource-header">
        <div>
          <h3>{resource.title}{resource.year ? ` (${resource.year})` : ''}</h3>
          {resource.original_title && resource.original_title !== resource.title ? (
            <p className="resource-original-title">{resource.original_title}</p>
          ) : null}
          <span className="source-badge">{resource.source_id}</span>
        </div>
        <div className="resource-header-actions">
          {onRefreshResource ? <Button variant="ghost" size="sm" type="button" onClick={onRefreshResource}>刷新资源</Button> : null}
          <Button variant={resource.is_favorited ? 'secondary' : 'ghost'} size="sm" type="button" onClick={onFavoriteResource}>
            {resource.is_favorited ? '已收藏资源' : '收藏资源'}
          </Button>
        </div>
      </div>
      <div className="link-list">
        {resource.has_more_links && links.length === 0 ? (
          <div style={{ display: 'flex', justifyContent: 'center', padding: 'var(--space-4)' }}>
            <Button variant="secondary" type="button" disabled={isLoadingLinks} onClick={() => void loadLinks()}>
              {isLoadingLinks ? '加载中…' : '加载链接'}
            </Button>
          </div>
        ) : links.length === 0 ? (
          <UIEmptyState message="该候选资源没有可用链接" />
        ) : null}
        {links.map((link) => (
          <div className="link-row" key={link.id}>
            <a href={link.url} target="_blank" rel="noreferrer">
              <strong className="truncate-name">{link.name || link.url}</strong>
              <div className="link-meta">
                <span className="provider-badge">{providerLabel(link.provider)}</span>
                {link.quality ? <span>{link.quality}</span> : null}
                {link.code ? <span>提取码：{link.code}</span> : null}
                {link.published_at ? <span>{formatDate(link.published_at)}</span> : null}
              </div>
              <span className="link-url-text">{link.url}</span>
            </a>
            <StatusBadge tone={linkValidationTone(link.validation_status)}>
              {validationLabel(link)}
            </StatusBadge>
            <div className="link-actions">
              <Button variant={link.is_favorited ? 'secondary' : 'ghost'} size="sm" type="button" onClick={() => onFavoriteLink(link)}>
                {link.is_favorited ? '已收藏链接' : '收藏链接'}
              </Button>
              <Button variant="ghost" size="sm" type="button" onClick={() => onSaveToCloud(link)}>保存到网盘</Button>
              <Button variant="ghost" size="sm" type="button" onClick={() => onCopyLink(link)}>复制链接</Button>
            </div>
          </div>
        ))}
      </div>
    </article>
  )
}
