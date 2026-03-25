<script setup lang="ts">
import WorkspaceDropdown from './WorkspaceDropdown.vue'
import type { Workspace } from '../types'

defineProps<{
  workspaces: Workspace[]
  activeWorkspace: Workspace | null
  activeNavItem: string
}>()

defineEmits<{
  'select-workspace': [workspace: Workspace]
  'open-modal': []
  'delete-workspace': [id: number]
  'create-table': []
  'import-table': []
  'create-form': []
  'import-data': []
  'create-report': []
}>()
</script>

<template>
  <header class="top-bar">
    <WorkspaceDropdown
      :workspaces="workspaces"
      :active-workspace="activeWorkspace"
      @select="$emit('select-workspace', $event)"
      @create="$emit('open-modal')"
      @delete="$emit('delete-workspace', $event)"
    />

    <!-- Tables buttons -->
    <div v-if="activeNavItem === 'tables' && activeWorkspace" class="bar-actions">
      <button class="bar-btn" @click="$emit('import-table')">
        <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
          <path d="M9 3v9" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/>
          <path d="M5.5 8.5L9 12l3.5-3.5" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/>
          <path d="M2 14h14" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/>
        </svg>
        Импортировать таблицу
      </button>
      <button class="bar-btn" @click="$emit('create-table')">
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
          <path d="M8 3v10M3 8h10" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
        </svg>
        Создать таблицу
      </button>
    </div>

    <!-- Reports button -->
    <div v-else-if="activeNavItem === 'reports' && activeWorkspace" class="bar-actions">
      <button class="bar-btn" @click="$emit('create-report')">
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
          <path d="M8 3v10M3 8h10" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
        </svg>
        Создать отчёт
      </button>
    </div>

    <!-- Forms buttons -->
    <div v-else-if="activeNavItem === 'forms' && activeWorkspace" class="bar-actions">
      <button class="bar-btn" @click="$emit('import-data')">
        <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
          <path d="M9 3v9" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/>
          <path d="M5.5 8.5L9 12l3.5-3.5" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/>
          <path d="M2 14h14" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/>
        </svg>
        Импортировать данные
      </button>
      <button class="bar-btn" @click="$emit('create-form')">
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
          <path d="M8 3v10M3 8h10" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
        </svg>
        Создать форму
      </button>
    </div>
  </header>
</template>

<style scoped>
.top-bar {
  height: 62px;
  flex-shrink: 0;
  background: #e9f1f3;
  display: flex;
  align-items: center;
  padding: 0 16px 0 14px;
  gap: 12px;
  z-index: 50;
}

.bar-actions {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 10px;
}

/* Shared button base */
.bar-btn {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 0 18px;
  height: 38px;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 500;
  font-family: inherit;
  cursor: pointer;
  border: none;
  background: #2f8486;
  color: #ffffff;
  transition: filter 0.15s;
  white-space: nowrap;
}

.bar-btn:hover  { filter: brightness(0.92); }
.bar-btn:active { filter: brightness(0.85); }
</style>
