import React, { useEffect, useMemo, useState } from 'react'
import { api } from '../api/client'
import { TransferTable } from '../components/TransferTable'
import { PaginationControls } from '../components/PaginationControls'
import { TransferSummary } from '../components/TransferSummary'
import { TransferNotice } from '../components/TransferNotice'
import { TransferLogs } from '../components/TransferLogs'
import type { TransferResponse, TransferLogResponse, TransferListResponse, TransferStatus } from '../types'
import { formatRelative, formatBytes } from '../utils/format'
import { transferStatusLabel, isTransferRunning, canCancelTransfer, canPauseTransfer, canResumeTransfer } from '../utils/labels'
import {
  Card,
  Button,
  Field,
  StatusBadge,
  ProgressBar,
  LoadingState as UILoadingState,
  EmptyState as UIEmptyState,
  ErrorState as UIErrorState,
  Kbd,
} from '../ui'

export default function TransfersPage({
  onTransfersChanged,
  page,
  pageSize,
  totalCount,
  onPageChange,
  onPageSizeChange,
  transfers,
  showToast,
}: {
  onTransfersChanged: () => Promise<void>
  page: number
  pageSize: number
  totalCount: number
  onPageChange: (page: number) => void
  onPageSizeChange: (pageSize: number) => void
  transfers: TransferResponse[]
  showToast: (type: 'success' | 'error' | 'info', message: string) => void
}) {
  const [transfer, setTransfer] = useState<TransferResponse | null>(null)
  const [logs, setLogs] = useState<TransferLogResponse[]>([])
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [isMutating, setIsMutating] = useState(false)

  useEffect(() => {
    const handler = (event: Event) => {
      const taskIdFromEvent = (event as CustomEvent<{ taskId?: string }>).detail?.taskId
      if (taskIdFromEvent) {
        void loadTransfer(taskIdFromEvent)
      }
    }
    window.addEventListener('sundarr:select-transfer', handler)
    return () => window.removeEventListener('sundarr:select-transfer', handler)
  }, [])

  useEffect(() => {
    if (!transfer) return
    const timer = window.setInterval(() => {
      void loadTransfer(transfer.id, { silent: true })
    }, 5000)
    return () => window.clearInterval(timer)
  }, [transfer?.id])

  async function loadTransfer(nextTaskId: string, options: { silent?: boolean } = {}) {
    const trimmedTaskId = nextTaskId.trim()
    if (!trimmedTaskId) {
      return
    }

    if (!options.silent) setIsLoading(true)
    setError(null)
    try {
      const [task, taskLogs] = await Promise.all([
        api.get<TransferResponse>(`/transfers/${encodeURIComponent(trimmedTaskId)}`),
        api.get<TransferLogResponse[]>(`/transfers/${encodeURIComponent(trimmedTaskId)}/logs`),
      ])
      setTransfer(task)
      setLogs(taskLogs)
    } catch (exc) {
      setTransfer(null)
      setLogs([])
      setError(exc instanceof Error ? exc.message : '无法读取任务。')
    } finally {
      if (!options.silent) setIsLoading(false)
    }
  }

  async function runTaskAction(action: 'cancel' | 'retry' | 'pause' | 'resume') {
    if (!transfer) return
    const actionText =
      action === 'cancel' ? '取消' : action === 'retry' ? '重试' : action === 'pause' ? '暂停' : '继续'
    if (action !== 'resume' && !window.confirm(`确认${actionText}任务 ${transfer.id}？`)) {
      return
    }
    setIsMutating(true)
    setError(null)
    try {
      const updated = await api.post<TransferResponse>(`/transfers/${encodeURIComponent(transfer.id)}/${action}`)
      const taskLogs = await api.get<TransferLogResponse[]>(`/transfers/${encodeURIComponent(transfer.id)}/logs`)
      setTransfer(updated)
      setLogs(taskLogs)
      await onTransfersChanged()
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : '任务操作失败。')
    } finally {
      setIsMutating(false)
    }
  }

  async function pauseTaskById(id: string) {
    try {
      await api.post(`/transfers/${encodeURIComponent(id)}/pause`)
      showToast('success', '任务已暂停。')
      if (transfer?.id === id) await loadTransfer(id)
      await onTransfersChanged()
    } catch (exc) { showToast('error', exc instanceof Error ? exc.message : '暂停失败。') }
  }

  async function resumeTaskById(id: string) {
    try {
      await api.post(`/transfers/${encodeURIComponent(id)}/resume`)
      showToast('success', '任务已恢复。')
      if (transfer?.id === id) await loadTransfer(id)
      await onTransfersChanged()
    } catch (exc) { showToast('error', exc instanceof Error ? exc.message : '恢复失败。') }
  }

  async function deleteTask(taskId: string) {
    if (!window.confirm(`确认删除任务 ${taskId}？`)) return
    try {
      await api.post(`/transfers/${encodeURIComponent(taskId)}/delete`)
      showToast('success', '任务已删除。')
      if (transfer?.id === taskId) { setTransfer(null); setLogs([]) }
      await onTransfersChanged()
    } catch (exc) { showToast('error', exc instanceof Error ? exc.message : '删除失败。') }
  }

  async function clearCompleted() {
    if (!window.confirm('确认清理所有已完成或已取消的任务？')) return
    try {
      const result = await api.post<{ ok: boolean; deleted_count: number }>('/transfers/clear-completed')
      showToast('success', `已清理 ${result.deleted_count} 个任务。`)
      setTransfer(null); setLogs([])
      await onTransfersChanged()
    } catch (exc) { showToast('error', exc instanceof Error ? exc.message : '清理失败。') }
  }

  const canCancel = transfer ? canCancelTransfer(transfer.status) : false
  const canRetry = transfer?.status === 'failed' && transfer.retryable === true
  const canPause = transfer ? canPauseTransfer(transfer.status) : false
  const canResume = transfer ? canResumeTransfer(transfer.status) : false
  const totalPages = Math.max(1, Math.ceil(totalCount / pageSize))

  return (
    <section className="tx-page" aria-labelledby="transfers-title">
      <Card className="tx-overview">
        <div className="tx-overview-head">
          <div>
            <p className="ui-eyebrow">任务</p>
            <h2 id="transfers-title">任务列表与控制</h2>
            <p className="tx-overview-lead">
              查看最近任务，选择后读取详情与关键日志，并按当前状态执行取消、暂停或重试。
            </p>
          </div>
          <div className="tx-overview-actions">
            <Button variant="ghost" onClick={() => void clearCompleted()}>
              清理
            </Button>
          </div>
        </div>
      </Card>

      <TransferTable
        transfers={transfers}
        selectedId={transfer?.id || null}
        onSelect={(id) => void loadTransfer(id)}
        onDelete={(id) => void deleteTask(id)}
        onPause={(id) => void pauseTaskById(id)}
        onResume={(id) => void resumeTaskById(id)}
      />
      <PaginationControls page={page} totalPages={totalPages} pageSize={pageSize} onPageChange={onPageChange} onPageSizeChange={onPageSizeChange} />

      {isLoading && !transfer ? (
        <Card>
          <UILoadingState message="正在读取任务详情和日志。" />
        </Card>
      ) : null}
      {error ? (
        <Card>
          <UIErrorState message="请求失败" sub={error} />
        </Card>
      ) : null}
      {!isLoading && !error && !transfer ? (
        <Card>
          <UIEmptyState
            message="选择一个任务查看详情"
            sub="在上方任务表格点选，任务详情会每 5 秒自动刷新。"
          />
        </Card>
      ) : null}

      {transfer ? (
        <>
          <TransferSummary transfer={transfer} />
          <Card>
            <div className="tx-action-row">
              <Button
                variant="primary"
                disabled={!canCancel || isMutating}
                onClick={() => void runTaskAction('cancel')}
              >
                {isMutating ? '处理中' : '取消任务'}
              </Button>
              {canPause && (
                <Button
                  variant="secondary"
                  disabled={isMutating}
                  onClick={() => void runTaskAction('pause')}
                >
                  {isMutating ? '处理中' : '暂停任务'}
                </Button>
              )}
              {canResume && (
                <Button
                  variant="secondary"
                  disabled={isMutating}
                  onClick={() => void runTaskAction('resume')}
                >
                  {isMutating ? '处理中' : '继续任务'}
                </Button>
              )}
              <Button
                variant="secondary"
                disabled={!canRetry || isMutating}
                onClick={() => void runTaskAction('retry')}
              >
                {isMutating ? '处理中' : '重试任务'}
              </Button>
              <Button
                variant="ghost"
                disabled={isLoading || isMutating}
                onClick={() => void loadTransfer(transfer.id)}
              >
                刷新详情
              </Button>
            </div>
          </Card>
          <TransferNotice transfer={transfer} />
          <TransferLogs logs={logs} />
        </>
      ) : null}
    </section>
  )
}
