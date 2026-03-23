<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import type { Workspace } from '../../domain/entities/Auth'
import { WorkspaceUseCase } from '../../application/usecases/WorkspaceUseCase'
import { useAuthStore } from '../stores/authStore'

const authStore = useAuthStore()
const router = useRouter()
const workspaceUseCase = new WorkspaceUseCase()

const workspaces = ref<Workspace[]>([])
const loading = ref(false)
const deleting = ref(false)
const workspaceName = ref('')
const workspaceDescription = ref('')
const selectedWorkspaceId = ref<number | null>(null)

const selectedWorkspace = computed(() => {
  if (selectedWorkspaceId.value === null) return null
  return workspaces.value.find((workspace) => workspace.id === selectedWorkspaceId.value) ?? null
})

const load = async () => {
  if (!authStore.token) return
  loading.value = true
  try {
    await authStore.fetchMe()
    workspaces.value = await workspaceUseCase.list(authStore.token)
    if (workspaces.value.length > 0) {
      const selectedExists = workspaces.value.some((workspace) => workspace.id === selectedWorkspaceId.value)
      selectedWorkspaceId.value = selectedExists ? selectedWorkspaceId.value : workspaces.value[0].id
    } else {
      selectedWorkspaceId.value = null
    }
  } finally {
    loading.value = false
  }
}

const createWorkspace = async () => {
  if (!authStore.token || !workspaceName.value.trim()) return

  await workspaceUseCase.create(authStore.token, workspaceName.value.trim(), workspaceDescription.value.trim())
  workspaceName.value = ''
  workspaceDescription.value = ''
  await load()
}

const deleteWorkspace = async () => {
  if (!authStore.token || !selectedWorkspace.value || deleting.value) return

  const shouldDelete = window.confirm(
    `Удалить workspace \"${selectedWorkspace.value.name}\"? Это действие нельзя отменить.`
  )
  if (!shouldDelete) return

  deleting.value = true
  try {
    await workspaceUseCase.delete(authStore.token, selectedWorkspace.value.id)
    await load()
  } finally {
    deleting.value = false
  }
}

const selectWorkspace = (workspaceId: number) => {
  selectedWorkspaceId.value = workspaceId
}

const formatDate = (value: string): string => {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat('ru-RU', {
    day: '2-digit',
    month: 'long',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  }).format(date)
}

const logout = () => {
  authStore.logout()
  router.push({ name: 'login' })
}

onMounted(load)
</script>

<template>
  <main class="dashboard">
    <aside class="sidebar">
      <header class="sidebar-header">
        <h1>Workspace</h1>
        <p>{{ authStore.me?.email }}</p>
      </header>

      <section class="create-widget">
        <h2>Новый workspace</h2>
        <div class="fields">
          <input v-model="workspaceName" type="text" placeholder="Название" maxlength="255" />
          <textarea
            v-model="workspaceDescription"
            rows="3"
            placeholder="Описание (опционально)"
            maxlength="2000"
          />
          <button @click="createWorkspace">Создать</button>
        </div>
      </section>

      <section class="workspace-nav">
        <div class="nav-title">
          <h2>Список</h2>
          <span>{{ workspaces.length }}</span>
        </div>
        <p v-if="loading" class="muted">Загрузка...</p>
        <p v-else-if="workspaces.length === 0" class="muted">Пока нет workspace</p>

        <ul v-else>
          <li v-for="workspace in workspaces" :key="workspace.id">
            <button
              class="workspace-link"
              :class="{ active: selectedWorkspaceId === workspace.id }"
              @click="selectWorkspace(workspace.id)"
            >
              <strong>{{ workspace.name }}</strong>
              <span>{{ workspace.description || 'Без описания' }}</span>
            </button>
          </li>
        </ul>
      </section>

      <button class="ghost" @click="logout">Выйти</button>
    </aside>

    <section class="content">
      <article v-if="selectedWorkspace" class="workspace-content">
        <header>
          <h2>{{ selectedWorkspace.name }}</h2>
          <p>{{ selectedWorkspace.description || 'Описание пока не добавлено' }}</p>
        </header>

        <div class="actions">
          <button class="danger" :disabled="deleting" @click="deleteWorkspace">
            {{ deleting ? 'Удаляем...' : 'Удалить workspace' }}
          </button>
        </div>

        <div class="info-grid">
          <section class="info-card">
            <h3>Детали</h3>
            <dl>
              <div>
                <dt>ID</dt>
                <dd>#{{ selectedWorkspace.id }}</dd>
              </div>
              <div>
                <dt>Владелец</dt>
                <dd>{{ authStore.me?.email }}</dd>
              </div>
              <div>
                <dt>Создан</dt>
                <dd>{{ formatDate(selectedWorkspace.created_at) }}</dd>
              </div>
            </dl>
          </section>

          <section class="info-card placeholder">
            <h3>Содержимое workspace</h3>
            <p>
              Здесь будет контур 2: конструктор структуры таблиц, затем формы ввода и отчеты.
            </p>
          </section>
        </div>
      </article>

      <article v-else class="empty-content">
        <h2>Выберите workspace</h2>
        <p>Создайте новое пространство в боковой панели или выберите существующее из списка.</p>
      </article>
    </section>
  </main>
</template>

<style scoped>
.dashboard {
  min-height: 100vh;
  padding: 18px;
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: 16px;
}

.sidebar {
  background: var(--bg-panel);
  border-radius: 18px;
  border: 1px solid var(--line);
  padding: 16px;
  display: grid;
  gap: 14px;
  align-content: start;
}

.sidebar-header h1 {
  margin: 0;
  letter-spacing: 0.02em;
}

.sidebar-header p {
  margin: 6px 0 0;
  color: var(--text-muted);
}

h2 {
  margin: 0;
}

.create-widget,
.workspace-nav {
  border: 1px solid var(--line);
  border-radius: 14px;
  background: var(--bg-soft);
  padding: 12px;
}

.fields {
  display: grid;
  gap: 10px;
  margin-top: 10px;
}

input,
textarea {
  border: 1px solid var(--line);
  background: #edf4f5;
  padding: 10px 12px;
  border-radius: 10px;
  color: var(--text-main);
  font: inherit;
  resize: vertical;
}

button {
  border: none;
  background: var(--accent);
  color: #e8fbff;
  border-radius: 10px;
  padding: 10px 16px;
  font-weight: 700;
}

button.ghost {
  background: #d9e3e5;
  color: #1f353b;
}

ul {
  list-style: none;
  padding: 0;
  margin: 0;
  display: grid;
  gap: 8px;
  margin-top: 10px;
}

.workspace-link {
  width: 100%;
  text-align: left;
  background: #dbe8ea;
  color: var(--text-main);
  border: 1px solid transparent;
  padding: 10px;
  border-radius: 10px;
  display: grid;
  gap: 4px;
}

.workspace-link.active {
  background: linear-gradient(135deg, #3c6f7f, #2b8f86);
  color: #f0fffd;
  border-color: #70ada5;
}

.workspace-link span,
.muted {
  color: var(--text-muted);
}

.workspace-link.active span {
  color: #c6f7f0;
}

.nav-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.nav-title span {
  border: 1px solid var(--line);
  border-radius: 999px;
  font-size: 0.82rem;
  padding: 2px 9px;
  color: var(--text-muted);
}

.content {
  border-radius: 18px;
  border: 1px solid var(--line);
  background: var(--bg-panel);
  padding: 20px;
}

.workspace-content header h2 {
  margin: 0;
  font-size: clamp(1.3rem, 2.2vw, 1.8rem);
}

.workspace-content header p {
  color: var(--text-muted);
  margin: 8px 0 0;
}

.actions {
  margin-top: 12px;
}

.danger {
  background: var(--danger);
  color: #fff;
}

.danger:disabled {
  opacity: 0.7;
}

.info-grid {
  margin-top: 16px;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 12px;
}

.info-card {
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 14px;
  background: var(--bg-soft);
}

.info-card h3 {
  margin: 0 0 10px;
}

dl {
  margin: 0;
  display: grid;
  gap: 10px;
}

dl div {
  display: grid;
  gap: 2px;
}

dt {
  font-size: 0.85rem;
  color: var(--text-muted);
}

dd {
  margin: 0;
  font-weight: 600;
}

.placeholder p,
.empty-content p {
  color: var(--text-muted);
}

.empty-content {
  min-height: 320px;
  display: grid;
  place-content: center;
  text-align: center;
  gap: 6px;
}

@media (max-width: 760px) {
  .dashboard {
    grid-template-columns: 1fr;
  }

  .content {
    padding: 16px;
  }
}
</style>
