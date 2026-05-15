import { EmptyState as UIEmptyState } from '../ui'
import { formatBytes } from '../utils/format'
import type { StorageBrowseResponse } from '../types'

export function StorageBrowser({ result, onOpen }: { result: StorageBrowseResponse; onOpen: (path: string) => void }) {
  if (result.entries.length === 0) {
    return <UIEmptyState message="该目录为空" sub="这个目录下暂时没有可继续浏览的子目录。" />
  }

  return (
    <div className="storage-browser">
      <p>当前路径：<strong>{result.path || '/'}</strong></p>
      <div className="browser-list">
        {result.entries.map((entry) => (
          <button className="browser-row" disabled={!entry.is_dir} key={entry.path} onClick={() => onOpen(entry.path)} title={entry.name} type="button">
            <span>{entry.is_dir ? '目录' : '文件'}</span>
            <strong title={entry.name}>{entry.name}</strong>
            <small title={entry.is_dir ? entry.path : formatBytes(entry.size || 0)}>{entry.is_dir ? entry.path : formatBytes(entry.size || 0)}</small>
          </button>
        ))}
      </div>
    </div>
  )
}
