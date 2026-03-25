<script setup lang="ts">
import { nextTick, onMounted, onUnmounted, ref } from 'vue'

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
const menuRef = ref<HTMLElement | null>(null)
const menuOpen = ref(false)
const menuX = ref(0)
const menuY = ref(0)
const menuWorkspaceId = ref<number | null>(null)
const MENU_OFFSET = 8
const VIEWPORT_PADDING = 12

const selectWorkspace = (workspaceId: number) => {
  emit('select', workspaceId)
  menuOpen.value = false
}

const openCreate = () => {
  emit('create')
  menuOpen.value = false
}

const positionMenuAtCursor = async (clientX: number, clientY: number) => {
  await nextTick()

  const menuEl = menuRef.value
  if (!menuEl) return

  const { innerWidth, innerHeight } = window
  const menuWidth = menuEl.offsetWidth
  const menuHeight = menuEl.offsetHeight

  menuX.value = Math.min(clientX + MENU_OFFSET, innerWidth - menuWidth - VIEWPORT_PADDING)
  menuY.value = Math.min(clientY + MENU_OFFSET, innerHeight - menuHeight - VIEWPORT_PADDING)
}

const openContextMenu = async (event: MouseEvent, workspaceId: number) => {
  event.preventDefault()
  menuWorkspaceId.value = workspaceId
  menuOpen.value = true
  menuX.value = event.clientX + MENU_OFFSET
  menuY.value = event.clientY + MENU_OFFSET
  await positionMenuAtCursor(event.clientX, event.clientY)
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
        ref="menuRef"
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
  min-width: 240px;
  max-width: 100%;
}

.tabs-strip {
  display: flex;
  align-items: center;
  gap: 6px;
  overflow-x: auto;
  max-width: 100%;
  padding-bottom: 0;
}

.tab {
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--bg-panel);
  min-width: 130px;
  max-width: 240px;
  height: 30px;
  padding: 0 10px;
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
  background: var(--bg-tab);
  box-shadow: inset 0 0 0 1px var(--line);
}

.tab-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--accent);
}

.tab-title {
  color: var(--text-main);
  font-size: 12px;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.new-tab {
  border: 1px dashed var(--line-strong);
  border-radius: 10px;
  background: var(--bg-panel);
  color: var(--accent);
  width: 30px;
  min-width: 30px;
  height: 30px;
  display: grid;
  place-items: center;
  font-size: 18px;
  cursor: pointer;
}

.context-menu {
  position: fixed;
  z-index: 120;
  width: 180px;
  border: 1px solid var(--line);
  background: var(--bg-panel);
  border-radius: 10px;
  padding: 6px;
  box-shadow: var(--shadow-soft);
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
  color: var(--text-main);
}

.context-item:hover {
  background: var(--bg-soft);
}

.context-item.danger {
  color: var(--danger);
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
