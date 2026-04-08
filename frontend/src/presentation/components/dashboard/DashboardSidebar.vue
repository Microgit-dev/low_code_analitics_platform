<script setup lang="ts">
import { useTheme } from '../../../infrastructure/composables/useTheme'

const props = defineProps<{
  activeTab: 'tables' | 'forms' | 'data' | 'reports' | 'details' | 'import'
}>()

const emit = defineEmits<{
  (event: 'nav-click', tab: 'tables' | 'forms' | 'data' | 'reports'): void
  (event: 'open-profile'): void
  (event: 'logout'): void
}>()

const { isDark, toggleTheme } = useTheme()

type NavTab = 'tables' | 'forms' | 'data' | 'reports'

interface NavItem {
  id: NavTab
  label: string
  iconPaths: string[]
}

const navItems: NavItem[] = [
  {
    id: 'tables',
    label: 'Таблицы',
    iconPaths: ['M3 6h18M3 12h18M3 18h18']
  },
  {
    id: 'forms',
    label: 'Формы',
    iconPaths: ['M8 4h8l4 4v12H4V4h4z', 'M8 4v4h4', 'M8 12h8M8 16h6']
  },
  {
    id: 'data',
    label: 'Данные',
    iconPaths: ['M4 6h16v12H4z', 'M4 10h16', 'M10 6v12', 'M15 6v12']
  },
  {
    id: 'reports',
    label: 'Отчеты',
    iconPaths: ['M5 19V9M12 19V5M19 19v-7']
  }
]
</script>

<template>
  <aside class="sidebar">
    <nav class="sidebar-nav" aria-label="Разделы workspace">
      <button
        v-for="item in navItems"
        :key="item.id"
        class="nav-item"
        :class="{ active: activeTab === item.id }"
        @click="emit('nav-click', item.id)"
      >
        <span class="nav-icon" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none">
            <path
              v-for="(path, index) in item.iconPaths"
              :key="`${item.id}-icon-${index}`"
              :d="path"
              stroke="currentColor"
              stroke-width="1.8"
              stroke-linecap="round"
              stroke-linejoin="round"
            />
          </svg>
        </span>
        <span class="nav-label">{{ item.label }}</span>
      </button>
    </nav>

    <div class="sidebar-footer">
      <div class="sidebar-actions">
        <button class="icon-action profile" title="Профиль" @click="emit('open-profile')">
          <svg width="18" height="18" viewBox="0 0 20 20" fill="none">
            <circle cx="10" cy="7" r="4" stroke="currentColor" stroke-width="1.5" />
            <path d="M2 18c0-4 3.58-7 8-7s8 3 8 7" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" />
          </svg>
        </button>
        <button class="icon-action" :title="isDark ? 'Светлая тема' : 'Темная тема'" @click="toggleTheme">
          <svg v-if="isDark" width="18" height="18" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="5" stroke="currentColor" stroke-width="1.7" />
            <path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.2 2.2M16.9 16.9l2.2 2.2M19.1 4.9l-2.2 2.2M7.1 16.9l-2.2 2.2" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" />
          </svg>
          <svg v-else width="18" height="18" viewBox="0 0 24 24" fill="none">
            <path d="M20 15.2A8.5 8.5 0 1 1 8.8 4a7 7 0 0 0 11.2 11.2Z" stroke="currentColor" stroke-width="1.7" />
          </svg>
        </button>
        <button class="icon-action danger" title="Выйти" aria-label="Выйти" @click="emit('logout')">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
            <path d="M15 4h3a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-3" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" />
            <path d="M10 8l4 4-4 4" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" />
            <path d="M14 12H4" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" />
          </svg>
        </button>
      </div>
    </div>
  </aside>
</template>

<style scoped src="../../styles/dashboard/dashboard-sidebar.css"></style>
