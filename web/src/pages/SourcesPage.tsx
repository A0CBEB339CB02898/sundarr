import React, { useEffect, useMemo, useState } from 'react'
import { api } from '../api/client'
import { formatDateTime } from '../utils/format'
import { StatusStack } from '../components/StatusStack'
import { PaginationControls } from '../components/PaginationControls'
import type {
  SourceResponse,
  SourceListResponse,
  SourceTestResponse,
  SourceTestFormState,
} from '../types'
import {
  Card,
  Button,
  Field,
  StatusBadge,
  LoadingState as UILoadingState,
  EmptyState as UIEmptyState,
  ErrorState as UIErrorState,
  Kbd,
} from '../ui'

function SourceDetailModal({
  source,
  testForm,
  testStatus,
  testResult,
  isExpanded,
  onClose,
  onTest,
  onTestFormChange,
  onToggleTestDetail,
}: {
  source: SourceResponse | null
  testForm: SourceTestFormState | null
  testStatus: 'running' | 'ok' | 'error' | undefined
  testResult: SourceTestResponse | null
  isExpanded: boolean
  onClose: () => void
  onTest: () => void | undefined
  onTestFormChange: (patch: Partial<SourceTestFormState>) => void | undefined
  onToggleTestDetail: () => void | undefined
}) {
  useEffect(() => {
    if (!source) return
    function onKey(event: KeyboardEvent) {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      window.removeEventListener('keydown', onKey)
      document.body.style.overflow = prev
    }
  }, [source, onClose])

  if (!source || !testForm) return null

  return (
    <div className="sc-modal-overlay" onClick={onClose}>
      <div className="sc-modal sc-modal-lg" role="dialog" aria-modal="true" aria-labelledby="sc-source-modal-title" onClick={(event) => event.stopPropagation()}>
        <header className="sc-modal-head">
          <div>
            <p className="ui-eyebrow">搜索源详情</p>
            <h3 id="sc-source-modal-title">{source.name}</h3>
          </div>
          <Button variant="ghost" size="sm" onClick={onClose} aria-label="关闭">×</Button>
        </header>

        <div className="sc-modal-body">
          <section className="sc-source-detail-block" aria-label="基础信息">
            <div className="sc-source-identity">
              <span className="status-pill running">搜索源</span>
              <h4>{source.name}</h4>
              <p>{source.description || '暂无说明。'}</p>
            </div>
            <dl className="sc-source-detail-list">
              <div>
                <dt>ID</dt>
                <dd>{source.id}</dd>
              </div>
              <div>
                <dt>原网址</dt>
                <dd>
                  {source.homepage_url ? (
                    <a href={source.homepage_url} target="_blank" rel="noreferrer">{source.homepage_url}</a>
                  ) : '未配置'}
                </dd>
              </div>
            </dl>
          </section>

          <section className="sc-source-test-block" aria-label={`${source.name} 测试搜索`}>
            <div className="sc-source-test-head">
              <div>
                <p className="ui-eyebrow">测试搜索</p>
                <h4>验证请求、解析和结果预览</h4>
              </div>
              <Button
                variant="primary"
                size="sm"
                disabled={testStatus === 'running'}
                onClick={onTest}
              >
                {testStatus === 'running' ? '测试中…' : '运行测试'}
              </Button>
            </div>

            <div className="sc-source-test-form">
              <label>
                <span>关键词</span>
                <input
                  value={testForm.keyword}
                  onChange={(event) => onTestFormChange({ keyword: event.target.value })}
                  placeholder="例如：星际穿越"
                />
              </label>
              <label>
                <span>预览数</span>
                <input
                  inputMode="numeric"
                  min="1"
                  max="20"
                  value={testForm.limit}
                  onChange={(event) => onTestFormChange({ limit: event.target.value })}
                />
              </label>
            </div>

            {testResult ? (
              <div className="sc-card-test" data-tone={testStatus || 'idle'}>
                <button
                  className="sc-card-test-summary"
                  type="button"
                  onClick={onToggleTestDetail}
                  aria-expanded={isExpanded}
                >
                  <span className="sc-card-test-dot" aria-hidden="true" />
                  <span className="sc-card-test-text">
                    {testResult.ok ? '测试通过' : '测试失败'}
                  </span>
                  <time className="sc-mono">{formatDateTime(testResult.tested_at)}</time>
                  <span className="sc-card-test-chevron" aria-hidden="true" data-expanded={isExpanded || undefined}>
                    <svg viewBox="0 0 12 12" width="12" height="12" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M3 4.5l3 3 3-3" />
                    </svg>
                  </span>
                </button>
                {isExpanded ? (
                  <div className="sc-card-test-body">
                    {testResult.logs.length > 0 ? (
                      <ol className="sc-source-log-list">
                        {testResult.logs.map((log, index) => (
                          <li key={`${log.step}-${index}`} data-status={log.status}>
                            <span className="sc-source-log-step">{log.step}</span>
                            <strong>{log.message}</strong>
                            {Object.keys(log.data).length > 0 ? (
                              <code>{JSON.stringify(log.data)}</code>
                            ) : null}
                          </li>
                        ))}
                      </ol>
                    ) : null}
                    {testResult.error_code ? (
                      <div className="sc-card-test-error">
                        <strong>{testResult.error_code}</strong>
                        <p>{testResult.error_message || '无错误详情。'}</p>
                      </div>
                    ) : null}
                    {testResult.items.length === 0 && !testResult.error_code ? (
                      <p className="sc-card-test-hint">测试未返回预览条目。</p>
                    ) : null}
                    {testResult.items.slice(0, 3).map((item, index) => (
                      <code className="sc-card-test-item" key={index}>
                        {JSON.stringify(item)}
                      </code>
                    ))}
                    {testResult.items.length > 3 ? (
                      <p className="sc-card-test-hint">
                        共 {testResult.items.length} 条，已展示前 3 条。
                      </p>
                    ) : null}
                  </div>
                ) : null}
              </div>
            ) : null}
          </section>
        </div>
        <footer className="sc-modal-actions">
          <Button variant="ghost" onClick={onClose} type="button">关闭</Button>
        </footer>
      </div>
    </div>
  )
}

export default function SourcesPage() {
  const [sources, setSources] = useState<SourceResponse[]>([])
  const [totalCount, setTotalCount] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [isLoading, setIsLoading] = useState(false)
  const [loadError, setLoadError] = useState<string | null>(null)

  const [testState, setTestState] = useState<Record<string, 'running' | 'ok' | 'error'>>({})
  const [viewingSource, setViewingSource] = useState<SourceResponse | null>(null)

  const [testResults, setTestResults] = useState<Record<string, SourceTestResponse>>({})
  const [testForms, setTestForms] = useState<Record<string, SourceTestFormState>>({})
  const [expandedTestId, setExpandedTestId] = useState<string | null>(null)

  useEffect(() => {
    void loadSources()
  }, [page, pageSize])

  async function loadSources() {
    setIsLoading(true)
    setLoadError(null)
    try {
      const response = await api.get<SourceListResponse>(`/sources?page=${page}&page_size=${pageSize}`)
      setSources(response.results)
      setTotalCount(response.count)
    } catch (exc) {
      setSources([])
      setLoadError(exc instanceof Error ? exc.message : '无法读取媒体源。')
    } finally {
      setIsLoading(false)
    }
  }

  function getTestForm(sourceId: string): SourceTestFormState {
    return testForms[sourceId] || { keyword: '星际穿越', limit: '5' }
  }

  function updateTestForm(sourceId: string, patch: Partial<SourceTestFormState>) {
    setTestForms((prev) => ({
      ...prev,
      [sourceId]: { ...(prev[sourceId] || { keyword: '星际穿越', limit: '5' }), ...patch },
    }))
  }

  async function testSource(source: SourceResponse) {
    const form = getTestForm(source.id)
    const keyword = form.keyword.trim()
    if (!keyword) {
      setTestResults((prev) => ({
        ...prev,
        [source.id]: {
          ok: false,
          source_id: source.id,
          items: [],
          logs: [{ step: 'prepare', status: 'error', message: '请输入测试关键词。', data: {} }],
          error_code: 'KEYWORD_REQUIRED',
          error_message: '请输入测试关键词。',
          tested_at: new Date().toISOString(),
        },
      }))
      setTestState((prev) => ({ ...prev, [source.id]: 'error' }))
      setExpandedTestId(source.id)
      return
    }
    setTestState((prev) => ({ ...prev, [source.id]: 'running' }))
    try {
      const result = await api.post<SourceTestResponse>(
        `/sources/${encodeURIComponent(source.id)}/test`,
        {
          keyword,
          limit: Math.max(1, Math.min(20, Number(form.limit) || 5)),
        },
      )
      setTestResults((prev) => ({ ...prev, [source.id]: result }))
      setTestState((prev) => ({ ...prev, [source.id]: result.ok ? 'ok' : 'error' }))
      setExpandedTestId(source.id)
    } catch (exc) {
      const msg = exc instanceof Error ? exc.message : '测试媒体源失败。'
      setTestResults((prev) => ({
        ...prev,
        [source.id]: {
          ok: false,
          source_id: source.id,
          items: [],
          logs: [{ step: 'request', status: 'error', message: msg, data: {} }],
          error_code: 'REQUEST_FAILED',
          error_message: msg,
          tested_at: new Date().toISOString(),
        },
      }))
      setTestState((prev) => ({ ...prev, [source.id]: 'error' }))
      setExpandedTestId(source.id)
    }
  }

  const showEmpty = !isLoading && !loadError && sources.length === 0
  const totalPages = Math.max(1, Math.ceil(totalCount / pageSize))

  return (
    <section className="sc-page" aria-labelledby="sources-title">
      <Card className="sc-overview">
        <div className="sc-overview-head">
          <div>
            <p className="ui-eyebrow">媒体源</p>
            <h2 id="sources-title">媒体源管理</h2>
            <p className="sc-overview-lead">
              查看当前安装的搜索源。详情弹窗中可以运行测试搜索，检查请求、解析和结果预览。
            </p>
          </div>
          <div className="sc-overview-actions">
            <Button variant="ghost" disabled={isLoading} onClick={() => void loadSources()}>
              {isLoading ? '读取中' : '重新读取'}
            </Button>
          </div>
        </div>
      </Card>

      {loadError ? (
        <Card>
          <UIErrorState
            message="无法读取媒体源"
            sub={loadError}
            action={
              <Button variant="secondary" onClick={() => void loadSources()}>
                重试
              </Button>
            }
          />
        </Card>
      ) : null}

      {isLoading && sources.length === 0 ? (
        <Card>
          <UILoadingState message="正在读取媒体源列表。" />
        </Card>
      ) : null}

      {showEmpty ? (
        <Card>
          <UIEmptyState
            message="暂无媒体源"
            sub="请在后端代码中实现 Source Adapter，并注册到 sources/registry.py。"
          />
        </Card>
      ) : null}

      {sources.length > 0 ? (
        <>
          <div className="sc-source-table" role="table" aria-label="搜索源列表">
            <div className="sc-source-table-header" role="row">
              <span role="columnheader">名称</span>
              <span role="columnheader">原网址</span>
              <span role="columnheader">说明</span>
              <span role="columnheader" aria-label="操作" />
            </div>
            {sources.map((source) => (
              <div className="sc-source-row" key={source.id} role="row">
                <span className="sc-source-name" role="cell">
                  <strong title={source.name}>{source.name}</strong>
                  <code>{source.id}</code>
                </span>
                <span className="sc-source-url" role="cell">
                  <a href={source.homepage_url} target="_blank" rel="noreferrer" title={source.homepage_url}>
                    {source.homepage_url || '未配置'}
                  </a>
                </span>
                <span className="sc-source-description" role="cell" title={source.description}>
                  {source.description || '暂无说明'}
                </span>
                <span className="sc-source-actions" role="cell">
                  <Button variant="secondary" size="sm" onClick={() => { setViewingSource(source); setExpandedTestId(source.id) }}>
                    详情
                  </Button>
                </span>
              </div>
            ))}
          </div>
          <PaginationControls page={page} totalPages={totalPages} pageSize={pageSize} onPageChange={setPage} onPageSizeChange={setPageSize} />
        </>
      ) : null}

      <SourceDetailModal
        source={viewingSource}
        testForm={viewingSource ? getTestForm(viewingSource.id) : null}
        testStatus={viewingSource ? testState[viewingSource.id] : undefined}
        testResult={viewingSource ? testResults[viewingSource.id] || null : null}
        isExpanded={viewingSource ? expandedTestId === viewingSource.id : false}
        onClose={() => setViewingSource(null)}
        onTest={() => viewingSource ? void testSource(viewingSource) : undefined}
        onTestFormChange={(patch) => viewingSource ? updateTestForm(viewingSource.id, patch) : undefined}
        onToggleTestDetail={() => viewingSource ? setExpandedTestId((prev) => (prev === viewingSource.id ? null : viewingSource.id)) : undefined}
      />
    </section>
  )
}
