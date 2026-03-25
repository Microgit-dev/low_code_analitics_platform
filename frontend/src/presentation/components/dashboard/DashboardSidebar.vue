<script setup lang="ts">
import { computed } from 'vue'
import UiStatusText from '../common/UiStatusText.vue'
import { useTheme } from '../../../infrastructure/composables/useTheme'

interface WorkspaceListItem {
  id: number
  name: string
  description?: string | null
}

const props = defineProps<{
  authEmail?: string
  workspaceName: string
  workspaceDescription: string
  workspaces: WorkspaceListItem[]
  loading: boolean
  selectedWorkspaceId: number | null
}>()

const emit = defineEmits<{
  (event: 'update:workspaceName', value: string): void
  (event: 'update:workspaceDescription', value: string): void
  (event: 'create-workspace'): void
  (event: 'select-workspace', workspaceId: number): void
  (event: 'logout'): void
}>()

const { isDark, toggleTheme } = useTheme()

const workspaceNameModel = computed({
  get: () => props.workspaceName,
  set: (value: string) => emit('update:workspaceName', value)
})

const workspaceDescriptionModel = computed({
  get: () => props.workspaceDescription,
  set: (value: string) => emit('update:workspaceDescription', value)
})
</script>

<template>
  <aside class="sidebar">
    <header class="sidebar-header">
      <h1>Workspace</h1>
      <p>{{ authEmail || '—' }}</p>
    </header>

    <section class="create-widget">
      <h2>Новый workspace</h2>
      <div class="fields">
        <input v-model="workspaceNameModel" type="text" placeholder="Название" maxlength="255" />
        <textarea v-model="workspaceDescriptionModel" rows="3" placeholder="Описание (опционально)" maxlength="2000" />
        <button @click="emit('create-workspace')">Создать</button>
      </div>
    </section>

    <section class="workspace-nav">
      <div class="nav-title">
        <h2>Список</h2>
        <span>{{ workspaces.length }}</span>
      </div>
      <UiStatusText v-if="loading">Загрузка...</UiStatusText>
      <UiStatusText v-else-if="workspaces.length === 0">Пока нет workspace</UiStatusText>

      <ul v-else>
        <li v-for="workspace in workspaces" :key="workspace.id">
          <button class="workspace-link" :class="{ active: selectedWorkspaceId === workspace.id }" @click="emit('select-workspace', workspace.id)">
            <strong>{{ workspace.name }}</strong>
            <span>{{ workspace.description || 'Без описания' }}</span>
          </button>
        </li>
      </ul>
    </section>

    <div class="sidebar-actions">
      <button class="action-btn" :title="isDark ? 'Светлая тема' : 'Темная тема'" @click="toggleTheme">
        {{ isDark ? '☀️' : '🌙' }}
      </button>
      <button class="ghost" @click="emit('logout')">Выйти</button>
    </div>
  </aside>
</template>

<style scoped src="../../styles/dashboard/dashboard-sidebar.css"></style>
