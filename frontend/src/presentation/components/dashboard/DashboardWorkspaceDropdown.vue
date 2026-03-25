<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'

interface WorkspaceItem {
  id: number
  name: string
}

defineProps<{
  workspaces: WorkspaceItem[]
  activeWorkspaceId: number | null
}>()

const emit = defineEmits<{
  (event: 'select', workspaceId: number): void
  (event: 'create'): void
  (event: 'delete', workspaceId: number): void
}>()

const widgetRef = ref<HTMLElement | null>(null)
const menuOpen = ref(false)
const menuX = ref(0)
const menuY = ref(0)
const menuWorkspaceId = ref<number | null>(null)

const selectWorkspace = (workspaceId: number) => {
  emit('select', workspaceId)
  menuOpen.value = false
}

const openCreate = () => {
  emit('create')
  menuOpen.value = false
}

const openContextMenu = (event: MouseEvent, workspaceId: number) => {
  event.preventDefault()
  menuWorkspaceId.value = workspaceId
  menuX.value = event.clientX
  menuY.value = event.clientY
  menuOpen.value = true
}

const closeMenu = () => {
  menuOpen.value = false
}

const onDeleteFromMenu = () => {
  if (menuWorkspaceId.value !== null) {
    emit('delete', menuWorkspaceId.value)
  }
  closeMenu()
}

const onOpenFromMenu = () => {
  if (menuWorkspaceId.value !== null) {
    selectWorkspace(menuWorkspaceId.value)
  }
}

const onClickOutside = (event: MouseEvent) => {
  if (widgetRef.value && !widgetRef.value.contains(event.target as Node)) {
    closeMenu()
  }
}

onMounted(() => document.addEventListener('mousedown', onClickOutside))
onUnmounted(() => document.removeEventListener('mousedown', onClickOutside))
</script>

<template>
  <div ref="widgetRef" class="workspace-tabs-widget">
    <div class="tabs-strip">
      <button
        v-for="workspace in workspaces"
        :key="workspace.id"
        class="tab"
        :class="{ active: activeWorkspaceId === workspace.id }"
        :title="workspace.name"
        @click="selectWorkspace(workspace.id)"
        @contextmenu="openContextMenu($event, workspace.id)"
      >
        <span class="tab-dot" />
        <span class="tab-title">{{ workspace.name }}</span>
      </button>

      <button class="new-tab" title="Создать пространство" @click="openCreate">+</button>
    </div>

    <Transition name="menu-fade">
      <div
        v-if="menuOpen"
        class="context-menu"
        :style="{ left: `${menuX}px`, top: `${menuY}px` }"
      >
        <button class="context-item" @click="onOpenFromMenu">Открыть</button>
        <button class="context-item danger" @click="onDeleteFromMenu">Удалить workspace</button>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.workspace-tabs-widget {
  position: relative;
  min-width: 320px;
  max-width: 100%;
}

.tabs-strip {
  display: flex;
  align-items: center;
  gap: 6px;
  overflow-x: auto;
  max-width: 100%;
  padding-bottom: 2px;
}

.tab {
  border: 1px solid #cfdcdf;
  border-bottom-color: #b8c9ce;
  border-radius: 10px 10px 0 0;
  background: linear-gradient(180deg, #f9fcfd 0%, #eaf2f4 100%);
  min-width: 150px;
  max-width: 240px;
  height: 34px;
  padding: 0 12px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  transition: filter 0.15s ease;
}

.tab:hover {
  filter: brightness(0.96);
}

.tab.active {
  background: #ffffff;
  border-bottom-color: #ffffff;
  box-shadow: 0 -1px 0 #ffffff inset;
}

.tab-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #2f8486;
}

.tab-title {
  color: #445766;
  font-size: 13px;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.new-tab {
  border: 1px dashed #9ab8be;
  border-radius: 10px;
  background: transparent;
  color: #2f8486;
  width: 34px;
  min-width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  font-size: 20px;
  cursor: pointer;
}

.context-menu {
  position: fixed;
  z-index: 120;
  width: 180px;
  border: 1px solid #d5e2e5;
  background: #ffffff;
  border-radius: 10px;
  padding: 6px;
  box-shadow: 0 8px 20px rgba(41, 62, 78, 0.18);
}

.context-item {
  display: flex;
  align-items: center;
  width: 100%;
  padding: 8px 10px;
  border-radius: 8px;
  background: transparent;
  border: none;
  cursor: pointer;
  font-size: 13px;
  color: #4d6070;
}

.context-item:hover {
  background: #f1f7f8;
}

.context-item.danger {
  color: #b04259;
}

.menu-fade-enter-active,
.menu-fade-leave-active {
  transition: opacity 0.12s ease;
}

.menu-fade-enter-from,
.menu-fade-leave-to {
  opacity: 0;
}

@media (max-width: 900px) {
  .workspace-tabs-widget {
    width: 100%;
  }

  .tab {
    min-width: 120px;
  }
}
</style>
