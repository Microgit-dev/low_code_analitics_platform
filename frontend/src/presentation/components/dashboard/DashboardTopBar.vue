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
    <DashboardWorkspaceDropdown
      :workspaces="workspaces"
      :active-workspace-id="activeWorkspaceId"
      @select="emit('select-workspace', $event)"
      @create="emit('open-modal')"
      @delete="emit('delete-workspace', $event)"
    />

    <div class="bar-actions">
      <button class="bar-btn ghost" @click="emit('go-details')">Детали</button>
      <button class="bar-btn ghost" @click="emit('go-import')">Импорт</button>
      <button class="bar-btn ghost" @click="emit('refresh-workspaces')">Обновить</button>

      <button v-if="props.activeTab === 'tables'" class="bar-btn" @click="emit('create-table')">Создать таблицу</button>
      <button v-else-if="props.activeTab === 'forms'" class="bar-btn" @click="emit('create-form')">Создать форму</button>
      <button v-else-if="props.activeTab === 'reports'" class="bar-btn" @click="emit('create-report')">Создать отчет</button>
    </div>
  </header>
</template>

<style scoped>
.top-bar {
  min-height: 62px;
  background: #e9f1f3;
  border: 1px solid #d3e1e4;
  border-radius: 14px;
  display: flex;
  align-items: center;
  padding: 10px 12px;
  gap: 12px;
  z-index: 10;
  flex-wrap: wrap;
}

.bar-actions {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.bar-btn {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 0 14px;
  height: 36px;
  border-radius: 10px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  border: none;
  background: #2f8486;
  color: #ffffff;
  transition: filter 0.15s;
  white-space: nowrap;
}

.bar-btn.ghost {
  background: #ffffff;
  color: #5a5d72;
}

.bar-btn:hover {
  filter: brightness(0.94);
}

@media (max-width: 1100px) {
  .bar-actions {
    margin-left: 0;
  }
}
</style>
