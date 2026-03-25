<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import TableEditor from './TableEditor.vue'
import TableCard from './TableCard.vue'
import type { Table, ColumnType } from '../types'

const props = defineProps<{
  tables: Table[]
  selectedTableId: number | null
}>()

const emit = defineEmits<{
  'create-table': [name: string, description: string]
  'update-table': [id: number, name: string, description: string]
  'delete-table': [id: number]
  'add-column': [tableId: number, name: string, type: ColumnType, required: boolean]
  'select-table': [id: number | null]
  'move-table': [id: number, x: number, y: number]
}>()

const canvasRef = ref<HTMLElement | null>(null)
const canvasWidth = ref(800)
const canvasHeight = ref(600)

let ro: ResizeObserver | null = null

onMounted(() => {
  if (canvasRef.value) {
    canvasWidth.value = canvasRef.value.clientWidth
    canvasHeight.value = canvasRef.value.clientHeight
    ro = new ResizeObserver(() => {
      if (canvasRef.value) {
        canvasWidth.value = canvasRef.value.clientWidth
        canvasHeight.value = canvasRef.value.clientHeight
      }
    })
    ro.observe(canvasRef.value)
  }
})

onUnmounted(() => {
  ro?.disconnect()
})

const selectedTable = computed(
  () => props.tables.find((t) => t.id === props.selectedTableId) ?? null,
)

function onCanvasClick(e: MouseEvent) {
  if (e.target === canvasRef.value) {
    emit('select-table', null)
  }
}
</script>

<template>
  <div class="table-view">
    <TableEditor
      :selected-table="selectedTable"
      :table-count="tables.length"
      @create-table="(n, d) => emit('create-table', n, d)"
      @update-table="(id, n, d) => emit('update-table', id, n, d)"
      @delete-table="(id) => emit('delete-table', id)"
      @add-column="(tid, n, t, r) => emit('add-column', tid, n, t, r)"
    />

    <div ref="canvasRef" class="canvas" @click="onCanvasClick">
      <TableCard
        v-for="table in tables"
        :key="table.id"
        :table="table"
        :selected="table.id === selectedTableId"
        :canvas-width="canvasWidth"
        :canvas-height="canvasHeight"
        @select="(id) => emit('select-table', id)"
        @move="(id, x, y) => emit('move-table', id, x, y)"
      />
    </div>
  </div>
</template>

<style scoped>
.table-view {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.canvas {
  flex: 1;
  position: relative;
  background: #eef4f6;
  overflow: hidden;
}
</style>
