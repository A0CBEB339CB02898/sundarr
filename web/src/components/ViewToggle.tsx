import type { ViewMode } from '../types'

export function ViewToggle({ value, onChange }: { value: ViewMode; onChange: (mode: ViewMode) => void }) {
  return (
    <div className="view-toggle">
      <button className={value === 'grid' ? 'active' : ''} onClick={() => onChange('grid')} aria-label="网格视图" type="button">
        ⊞
      </button>
      <button className={value === 'list' ? 'active' : ''} onClick={() => onChange('list')} aria-label="列表视图" type="button">
        ≡
      </button>
    </div>
  )
}
