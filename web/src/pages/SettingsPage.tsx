import React, { useEffect, useState } from 'react'
import LibrariesPanel from './LibrariesPage'
import PluginsPanel from './PluginsPage'
import RemoteLibrariesPanel from './RemoteLibrariesPage'
import SourcesPanel from './SourcesPage'
import StatusPanel from './StatusPage'
import StoragePanel from './StoragePage'

type SettingsTab = 'sources' | 'plugins' | 'storage' | 'libraries' | 'remote-libraries' | 'status'

const settingsTabs: Array<{ key: SettingsTab; path: string; label: string }> = [
  { key: 'sources', path: '/app/sources', label: '媒体源' },
  { key: 'plugins', path: '/app/plugins', label: '插件' },
  { key: 'storage', path: '/app/storage', label: '存储' },
  { key: 'libraries', path: '/app/libraries', label: '本地媒体库' },
  { key: 'remote-libraries', path: '/app/remote-libraries', label: '远程媒体库' },
  { key: 'status', path: '/app/status', label: '系统状态' },
]

function tabFromPath(pathname: string): SettingsTab {
  return settingsTabs.find((item) => item.path === pathname)?.key || 'sources'
}

export default function SettingsPage({ showToast }: { showToast: (type: 'success' | 'error' | 'info', message: string) => void }) {
  const [activeTab, setActiveTab] = useState<SettingsTab>(() => tabFromPath(window.location.pathname))

  useEffect(() => {
    const syncTab = () => setActiveTab(tabFromPath(window.location.pathname))
    window.addEventListener('popstate', syncTab)
    window.addEventListener('sundarr:navigation', syncTab)
    return () => {
      window.removeEventListener('popstate', syncTab)
      window.removeEventListener('sundarr:navigation', syncTab)
    }
  }, [])

  function selectTab(tab: typeof settingsTabs[number]) {
    window.history.pushState({}, '', tab.path)
    setActiveTab(tab.key)
    window.dispatchEvent(new CustomEvent('sundarr:navigation', { detail: { path: tab.path } }))
  }

  return (
    <section className="settings-page" aria-labelledby="settings-title">
      <header className="page-header settings-page-header">
        <p className="panel-kicker">系统设置</p>
        <h1 id="settings-title">设置</h1>
        <p>集中管理数据接入、插件运行、存储连接、媒体库绑定和系统状态。</p>
      </header>
      <nav className="settings-tabs" role="tablist" aria-label="设置分类">
        {settingsTabs.map((tab) => (
          <button
            key={tab.key}
            type="button"
            role="tab"
            aria-selected={activeTab === tab.key}
            data-active={activeTab === tab.key || undefined}
            onClick={() => selectTab(tab)}
          >
            {tab.label}
          </button>
        ))}
      </nav>
      <div className="settings-content" role="tabpanel">
        {activeTab === 'sources' ? <SourcesPanel /> : null}
        {activeTab === 'plugins' ? <PluginsPanel showToast={showToast} /> : null}
        {activeTab === 'storage' ? <StoragePanel showToast={showToast} /> : null}
        {activeTab === 'libraries' ? <LibrariesPanel showToast={showToast} /> : null}
        {activeTab === 'remote-libraries' ? <RemoteLibrariesPanel showToast={showToast} /> : null}
        {activeTab === 'status' ? <StatusPanel /> : null}
      </div>
    </section>
  )
}
