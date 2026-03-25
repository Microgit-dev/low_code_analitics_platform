import { computed, ref } from 'vue'

type ThemeMode = 'light' | 'dark'

const THEME_STORAGE_KEY = 'app-theme-mode'

const currentTheme = ref<ThemeMode>('light')
let initialized = false

export function useTheme() {
  const isDark = computed(() => currentTheme.value === 'dark')

  const setTheme = (theme: ThemeMode) => {
    currentTheme.value = theme
    document.documentElement.setAttribute('data-theme', theme)
    localStorage.setItem(THEME_STORAGE_KEY, theme)
  }

  const initTheme = () => {
    if (initialized) return
    initialized = true

    // Попытаться получить сохраненную тему
    const savedTheme = localStorage.getItem(THEME_STORAGE_KEY) as ThemeMode | null

    if (savedTheme) {
      setTheme(savedTheme)
      return
    }

    // Проверить системную предпочтение
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
    setTheme(prefersDark ? 'dark' : 'light')
  }

  const toggleTheme = () => {
    setTheme(currentTheme.value === 'light' ? 'dark' : 'light')
  }

  const getTheme = (): ThemeMode => currentTheme.value

  // Инициализируем тему при первом вызове composable
  if (typeof window !== 'undefined' && !initialized) {
    initTheme()
  }

  return {
    isDark,
    currentTheme,
    setTheme,
    toggleTheme,
    getTheme,
    initTheme,
  }
}
