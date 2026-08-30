import React from 'react'
import type { PageKey, TransferResponse } from '../types'
import StatusPanel from './StatusPage'
import TransfersPanel from './TransfersPage'
import StoragePanel from './StoragePage'
import SearchPanel from './SearchPage'
import FavoritesPanel from './FavoritesPage'
import SourcesPanel from './SourcesPage'
import LibrariesPanel from './LibrariesPage'
import RemoteLibrariesPanel from './RemoteLibrariesPage'
import DiscoverPanel from './DiscoverPage'

export function PagePanel({
  activePage,
  onTransfersChanged,
  transferPage,
  transferPageSize,
  transferTotalCount,
  onTransferPageChange,
  onTransferPageSizeChange,
  transfers,
  showToast,
}: {
  activePage: PageKey
  onTransfersChanged: () => Promise<void>
  transferPage: number
  transferPageSize: number
  transferTotalCount: number
  onTransferPageChange: (page: number) => void
  onTransferPageSizeChange: (pageSize: number) => void
  transfers: TransferResponse[]
  showToast: (type: 'success' | 'error' | 'info', message: string) => void
}) {
  return (
    <>
      <div className={activePage === 'discover' ? 'panel-visible' : 'panel-hidden'}><DiscoverPanel showToast={showToast} /></div>
      <div className={activePage === 'status' ? 'panel-visible' : 'panel-hidden'}><StatusPanel /></div>
      <div className={activePage === 'transfers' ? 'panel-visible' : 'panel-hidden'}><TransfersPanel onTransfersChanged={onTransfersChanged} page={transferPage} pageSize={transferPageSize} totalCount={transferTotalCount} onPageChange={onTransferPageChange} onPageSizeChange={onTransferPageSizeChange} transfers={transfers} showToast={showToast} /></div>
      <div className={activePage === 'storage' ? 'panel-visible' : 'panel-hidden'}><StoragePanel showToast={showToast} /></div>
      <div className={activePage === 'search' ? 'panel-visible' : 'panel-hidden'}><SearchPanel showToast={showToast} /></div>
      <div className={activePage === 'favorites' ? 'panel-visible' : 'panel-hidden'}><FavoritesPanel showToast={showToast} /></div>
      <div className={activePage === 'sources' ? 'panel-visible' : 'panel-hidden'}><SourcesPanel /></div>
      <div className={activePage === 'libraries' ? 'panel-visible' : 'panel-hidden'}><LibrariesPanel showToast={showToast} /></div>
      <div className={activePage === 'remote-libraries' ? 'panel-visible' : 'panel-hidden'}><RemoteLibrariesPanel showToast={showToast} /></div>
    </>
  )
}
