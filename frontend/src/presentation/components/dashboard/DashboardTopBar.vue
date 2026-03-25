<script setup lang="ts">
import DashboardWorkspaceDropdown from './DashboardWorkspaceDropdown.vue'

interface WorkspaceItem {
  id: number
  name: string
}

const props = defineProps<{
  workspaces: WorkspaceItem[]
  activeWorkspaceId: number | null
  activeTab: 'details' | 'tables' | 'forms' | 'data' | 'import' | 'reports'
}>()

const emit = defineEmits<{
  (event: 'select-workspace', workspaceId: number): void
  (event: 'open-modal'): void
  (event: 'delete-workspace', workspaceId: number): void
  (event: 'go-details'): void
  (event: 'go-import'): void
  (event: 'refresh-workspaces'): void
  (event: 'create-table'): void
  (event: 'create-form'): void
  (event: 'create-report'): void
}>()
</script>

<template>
  <header class="top-bar">
    <div class="bar-main">
      <DashboardWorkspaceDropdown
        :workspaces="workspaces"
        :active-workspace-id="activeWorkspaceId"
        @select="emit('select-workspace', $event)"
        @create="emit('open-modal')"
        @delete="emit('delete-workspace', $event)"
      />
    </div>

    <div class="bar-actions">
      <template v-if="props.activeTab === 'tables'">
        <button class="bar-btn feature" @click="emit('go-import')">
          <span>Импортировать таблицу</span>
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true">
            <rect x="1" y="1" width="16" height="16" rx="3" fill="var(--bg-panel)" />
            <path d="M9 4.25v6.1" stroke="var(--accent)" stroke-width="1.8" stroke-linecap="round" />
            <path d="M6.3 8.4L9 11.1l2.7-2.7" stroke="var(--accent)" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
        </button>
        <button class="bar-btn feature" @click="emit('create-table')">
          <span>Создать таблицу</span>
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true">
            <path d="M9 3.5v11" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" />
            <path d="M3.5 9h11" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" />
          </svg>
        </button>
      </template>
    </div>
  </header>
</template>

<style scoped>
.top-bar {
  min-height: 46px;
  background: var(--bg-soft);
  border: 1px solid var(--line);
  border-radius: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 12px;
  gap: 12px;
  z-index: 10;
  align-content: center;
  border-left: none;
  border-right: none;
  border-top: none;
}

.bar-main {
  min-width: 0;
  flex: 1 1 auto;
}

.bar-actions {
  display: flex;
  align-items: center;
  gap: 18px;
  flex-wrap: nowrap;
  justify-content: flex-end;
  min-height: 30px;
  flex: 0 0 auto;
}

.bar-btn {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 12px;
  height: 32px;
  border-radius: 10px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  border: none;
  background: var(--button-primary);
  color: var(--accent-contrast);
  transition: filter 0.15s;
  white-space: nowrap;
}

.bar-btn svg {
  width: 18px;
  height: 18px;
  min-width: 18px;
  min-height: 18px;
  flex-shrink: 0;
  display: block;
}

.bar-btn.feature {
  min-width: 260px;
  height: 30px;
  justify-content: center;
  padding: 0 18px;
  border-radius: 11px;
  font-size: 13px;
  font-weight: 500;
}

.bar-btn:hover {
  filter: brightness(0.94);
}

@media (max-width: 1100px) {
  .top-bar {
    align-items: flex-start;
    flex-direction: column;
  }

  .bar-actions {
    justify-content: flex-start;
    flex-wrap: wrap;
    width: 100%;
    gap: 10px;
  }

  .bar-btn.feature {
    min-width: 0;
    width: 100%;
  }
}
</style>
