<script setup lang="ts">
import { useTheme } from '../../../infrastructure/composables/useTheme'

const props = defineProps<{
  authEmail?: string
  activeTab: 'tables' | 'forms' | 'data' | 'reports' | 'details' | 'import'
}>()

const emit = defineEmits<{
  (event: 'nav-click', tab: 'tables' | 'forms' | 'data' | 'reports'): void
  (event: 'open-profile'): void
  (event: 'logout'): void
}>()

const { isDark, toggleTheme } = useTheme()

const HOT_BAR = 'https://www.figma.com/api/mcp/asset/442052de-1a91-402a-9573-3b42e20597f7'

const navItems: Array<{ id: 'tables' | 'forms' | 'data' | 'reports'; label: string; y: number }> = [
  { id: 'tables', label: 'Таблицы', y: 134 },
  { id: 'forms', label: 'Формы', y: 206 },
  { id: 'data', label: 'Данные', y: 278 },
  { id: 'reports', label: 'Отчеты', y: 350 }
]

const spriteStyle = (y: number): Record<string, string> => ({
  backgroundImage: `url(${HOT_BAR})`,
  backgroundSize: '68px 1080px',
  backgroundPosition: `-8px -${y}px`,
  backgroundRepeat: 'no-repeat'
})
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
        <span class="nav-icon" :style="spriteStyle(item.y)" />
        <span class="nav-label">{{ item.label }}</span>
      </button>
    </nav>

    <div class="sidebar-footer">
      <p class="auth-email" :title="authEmail">{{ authEmail || 'no-user' }}</p>
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
        <button class="icon-action danger" @click="emit('logout')">Выйти</button>
      </div>
    </div>
  </aside>
</template>

<style scoped src="../../styles/dashboard/dashboard-sidebar.css"></style>
