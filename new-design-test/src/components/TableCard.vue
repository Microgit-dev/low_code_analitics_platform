<script setup lang="ts">
import { ref } from 'vue'
import type { Table } from '../types'

const props = defineProps<{
  table: Table
  selected: boolean
  canvasWidth: number
  canvasHeight: number
}>()

const emit = defineEmits<{
  select: [id: number]
  move: [id: number, x: number, y: number]
}>()

const cardRef = ref<HTMLElement | null>(null)
let dragging = false
let hasDragged = false
let startMouseX = 0
let startMouseY = 0
let startTableX = 0
let startTableY = 0

function onMousedown(e: MouseEvent) {
  if (e.button !== 0) return
  dragging = true
  hasDragged = false
  startMouseX = e.clientX
  startMouseY = e.clientY
  startTableX = props.table.x
  startTableY = props.table.y
  e.preventDefault()
  window.addEventListener('mousemove', onMousemove)
  window.addEventListener('mouseup', onMouseup)
}

function onMousemove(e: MouseEvent) {
  if (!dragging || !cardRef.value) return
  const dx = e.clientX - startMouseX
  const dy = e.clientY - startMouseY
  if (Math.abs(dx) > 3 || Math.abs(dy) > 3) hasDragged = true

  const cardW = cardRef.value.offsetWidth
  const cardH = cardRef.value.offsetHeight
  const newX = Math.max(8, Math.min(props.canvasWidth - cardW - 8, startTableX + dx))
  const newY = Math.max(8, Math.min(props.canvasHeight - cardH - 8, startTableY + dy))
  emit('move', props.table.id, newX, newY)
}

function onMouseup() {
  dragging = false
  window.removeEventListener('mousemove', onMousemove)
  window.removeEventListener('mouseup', onMouseup)
  if (!hasDragged) {
    emit('select', props.table.id)
  }
}

const TYPE_LABELS: Record<string, string> = {
  text: 'text',
  longText: 'longText',
  number: 'number',
  datetime: 'dateTime',
  radio: 'radio',
  checkbox: 'checkbox',
  select: 'select',
  multiselect: 'multiselect',
  geoPoint: 'geoPoint',
}

function toKey(name: string) {
  return name.toLowerCase().replace(/\s+/g, '_')
}
</script>

<template>
  <div
    ref="cardRef"
    class="table-card"
    :class="{ selected }"
    :style="{ left: table.x + 'px', top: table.y + 'px' }"
    @mousedown="onMousedown"
  >
    <div class="card-header">
      <h3 class="card-title">{{ table.name }}</h3>
      <p v-if="table.description" class="card-desc">{{ table.description }}</p>
    </div>

    <div v-if="table.columns.length" class="card-columns">
      <div v-for="col in table.columns" :key="col.id" class="col-row">
        <div class="col-left">
          <span class="col-name">{{ col.name }}</span>
          <span class="col-key">{{ toKey(col.name) }}</span>
        </div>
        <span class="col-type">{{ TYPE_LABELS[col.type] ?? col.type }}</span>
      </div>
    </div>

    <div v-else class="card-empty">Нет колонок</div>
  </div>
</template>

<style scoped>
.table-card {
  position: absolute;
  width: 280px;
  background: #ffffff;
  border-radius: 14px;
  border: 1.5px solid #d3dee2;
  box-shadow: 0 2px 12px rgba(90, 93, 114, 0.1);
  cursor: grab;
  user-select: none;
  transition: border-color 0.15s, box-shadow 0.15s;
  overflow: hidden;
}

.table-card:active {
  cursor: grabbing;
}

.table-card.selected {
  border-color: #8eacb1;
  border-width: 2px;
  box-shadow: 0 4px 20px rgba(142, 172, 177, 0.25);
}

.card-header {
  padding: 16px 16px 12px;
}

.card-title {
  font-size: 18px;
  font-weight: 700;
  color: #3c3f52;
  margin: 0 0 4px;
  line-height: 1.3;
}

.card-desc {
  font-size: 12px;
  color: #9ba3b8;
  margin: 0;
  line-height: 1.4;
}

.card-columns {
  display: flex;
  flex-direction: column;
  padding: 0 8px 12px;
  gap: 4px;
}

.col-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 10px;
  background: #f3f9fa;
  border-radius: 8px;
}

.col-left {
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.col-name {
  font-size: 14px;
  font-weight: 600;
  color: #3c3f52;
}

.col-key {
  font-size: 11px;
  color: #9ba3b8;
}

.col-type {
  font-size: 12px;
  color: #9ba3b8;
  font-style: italic;
}

.card-empty {
  padding: 10px 16px 14px;
  font-size: 13px;
  color: #b0bac8;
  font-style: italic;
}
</style>
