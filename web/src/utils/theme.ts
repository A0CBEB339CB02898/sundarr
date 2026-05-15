import type { ThemeMode } from '../types'

export function storedThemeMode(): ThemeMode {
  const value = window.localStorage.getItem('sundarr.theme')
  return value === 'light' || value === 'dark' || value === 'system' ? value : 'system'
}

export function applyThemeMode(mode: ThemeMode) {
  const root = document.documentElement
  if (mode === 'system') {
    root.removeAttribute('data-theme')
  } else {
    root.dataset.theme = mode
  }
}

export function themeModeLabel(mode: ThemeMode) {
  const labels: Record<ThemeMode, string> = {
    light: '亮色',
    dark: '暗色',
    system: '跟随系统',
  }
  return labels[mode]
}
