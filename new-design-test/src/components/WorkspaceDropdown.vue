<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import type { Workspace } from '../types'

defineProps<{
  workspaces: Workspace[]
  activeWorkspace: Workspace | null
}>()

const emit = defineEmits<{
  'select': [workspace: Workspace]
  'create': []
  'delete': [id: number]
}>()

const isOpen = ref(false)
const dropdownRef = ref<HTMLElement | null>(null)

function toggle() {
  isOpen.value = !isOpen.value
}

function select(workspace: Workspace) {
  emit('select', workspace)
  isOpen.value = false
}

function openCreate() {
  emit('create')
  isOpen.value = false
}

function onClickOutside(e: MouseEvent) {
  if (dropdownRef.value && !dropdownRef.value.contains(e.target as Node)) {
    isOpen.value = false
  }
}

onMounted(() => document.addEventListener('mousedown', onClickOutside))
onUnmounted(() => document.removeEventListener('mousedown', onClickOutside))
</script>

<template>
  <div class="dropdown" ref="dropdownRef">
    <button class="dropdown-trigger" @click="toggle">
      <span class="dropdown-text">
        {{ activeWorkspace ? activeWorkspace.name : 'пространство...' }}
      </span>
      <svg
        class="chevron"
        :class="{ open: isOpen }"
        width="16"
        height="10"
        viewBox="0 0 16 10"
        fill="none"
      >
        <path d="M1 1L8 8L15 1" stroke="#5a5d72" stroke-width="2" stroke-linecap="round"/>
      </svg>
    </button>

    <Transition name="dropdown">
      <div v-if="isOpen" class="dropdown-menu">
        <div
          v-for="ws in workspaces"
          :key="ws.id"
          class="dropdown-item"
          :class="{ selected: activeWorkspace?.id === ws.id }"
          @click="select(ws)"
        >
          <span class="ws-dot" />
          <span class="ws-name">{{ ws.name }}</span>
          <button
            class="ws-delete"
            title="Удалить"
            @click.stop="emit('delete', ws.id)"
          >
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
              <path d="M1 1L13 13M13 1L1 13" stroke="#5a5d72" stroke-width="1.8" stroke-linecap="round"/>
            </svg>
          </button>
        </div>

        <div v-if="workspaces.length" class="dropdown-divider" />

        <button class="dropdown-create" @click="openCreate">
          <span class="create-plus">+</span>
          <span>Создать пространство</span>
        </button>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.dropdown {
  position: relative;
}

.dropdown-trigger {
  display: flex;
  align-items: center;
  gap: 10px;
  background: #ffffff;
  border: none;
  border-radius: 10px;
  padding: 8px 16px;
  width: 350px;
  cursor: pointer;
  font-family: 'Montserrat', sans-serif;
  font-size: 16px;
  font-weight: 500;
  color: #5a5d72;
  transition: background 0.15s;
}

.dropdown-trigger:hover {
  background: #e9f1f3;
}

.dropdown-text {
  flex: 1;
  text-align: left;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.chevron {
  flex-shrink: 0;
  transition: transform 0.2s;
}

.chevron.open {
  transform: rotate(180deg);
}

/* Menu */
.dropdown-menu {
  position: absolute;
  top: calc(100% + 6px);
  left: 0;
  width: 350px;
  background: #ffffff;
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(90, 93, 114, 0.15);
  padding: 6px;
  z-index: 300;
  overflow: hidden;
}

.dropdown-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 15px;
  font-weight: 500;
  color: #5a5d72;
  transition: background 0.12s;
}

.dropdown-item:hover {
  background: #f3f9fa;
}

.dropdown-item.selected {
  background: #e9f1f3;
}

.ws-delete {
  flex-shrink: 0;
  margin-left: auto;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 6px;
  background: transparent;
  border: none;
  cursor: pointer;
  opacity: 0;
  transition: opacity 0.12s, background 0.12s;
  padding: 0;
}

.dropdown-item:hover .ws-delete {
  opacity: 1;
}

.ws-delete:hover {
  background: #d3dee2;
}

.ws-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #2f8486;
  flex-shrink: 0;
}

.ws-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.dropdown-divider {
  height: 1px;
  background: #e9f1f3;
  margin: 4px 0;
}

.dropdown-create {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 10px 12px;
  border-radius: 8px;
  background: transparent;
  border: none;
  cursor: pointer;
  font-family: 'Montserrat', sans-serif;
  font-size: 15px;
  font-weight: 500;
  color: #2f8486;
  transition: background 0.12s;
}

.dropdown-create:hover {
  background: rgba(47, 132, 134, 0.08);
}

.create-plus {
  font-size: 20px;
  line-height: 1;
  font-weight: 400;
}

/* Transition */
.dropdown-enter-active,
.dropdown-leave-active {
  transition: opacity 0.15s, transform 0.15s;
}
.dropdown-enter-from,
.dropdown-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}
</style>
