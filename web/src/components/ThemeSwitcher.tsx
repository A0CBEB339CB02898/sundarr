import { themeModeLabel } from '../utils/theme'
import type { ThemeMode } from '../types'
import { ThemeModeIcon } from './ThemeModeIcon'

export function ThemeSwitcher({ mode, onChange }: { mode: ThemeMode; onChange: (mode: ThemeMode) => void }) {
  return (
    <div className="theme-switcher" aria-label="主题模式">
      <span>主题</span>
      <div>
        {(['light', 'dark', 'system'] as ThemeMode[]).map((item) => (
          <button
            aria-label={`切换到${themeModeLabel(item)}`}
            aria-pressed={mode === item}
            className="theme-button"
            data-active={mode === item}
            key={item}
            onClick={() => onChange(item)}
            title={themeModeLabel(item)}
            type="button"
          >
            <ThemeModeIcon mode={item} />
          </button>
        ))}
      </div>
    </div>
  )
}
