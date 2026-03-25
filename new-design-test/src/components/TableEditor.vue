<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import type { Table, ColumnType } from '../types'

const props = defineProps<{
  selectedTable: Table | null
  tableCount: number
}>()

const emit = defineEmits<{
  'create-table': [name: string, description: string]
  'update-table': [id: number, name: string, description: string]
  'delete-table': [id: number]
  'add-column': [tableId: number, name: string, type: ColumnType, required: boolean]
}>()

/* ── Top panel ── */
const tableName = ref('')
const tableDesc = ref('')

watch(
  () => props.selectedTable,
  (t) => {
    tableName.value = t ? t.name : ''
    tableDesc.value = t ? t.description : ''
  },
  { immediate: true },
)

const topPanelTitle = computed(() =>
  props.selectedTable ? props.selectedTable.name : 'Создать таблицу',
)

function saveTable() {
  const name = tableName.value.trim() || `Таблица ${props.tableCount + 1}`
  const desc = tableDesc.value.trim()
  if (props.selectedTable) {
    emit('update-table', props.selectedTable.id, name, desc)
  } else {
    emit('create-table', name, desc)
    tableName.value = ''
    tableDesc.value = ''
  }
}

/* ── Column panel ── */
const COLUMN_TYPES: { value: ColumnType; label: string }[] = [
  { value: 'text',        label: 'Строка' },
  { value: 'longText',    label: 'Длинный текст' },
  { value: 'number',      label: 'Число' },
  { value: 'datetime',    label: 'Дата и время' },
  { value: 'radio',       label: 'Radio' },
  { value: 'checkbox',    label: 'Checkbox' },
  { value: 'select',      label: 'Select' },
  { value: 'multiselect', label: 'Multiselect' },
  { value: 'geoPoint',    label: 'GeoPoint' },
]

const colName     = ref('')
const colType     = ref<ColumnType>('text')
const colRequired = ref(false)

function addColumn() {
  if (!props.selectedTable || !colName.value.trim()) return
  emit('add-column', props.selectedTable.id, colName.value.trim(), colType.value, colRequired.value)
  colName.value     = ''
  colType.value     = 'text'
  colRequired.value = false
}

function deleteTable() {
  if (!props.selectedTable) return
  emit('delete-table', props.selectedTable.id)
}
</script>

<template>
  <aside class="editor">
    <!-- TOP CARD -->
    <div class="card">
      <h2 class="card-title">{{ topPanelTitle }}</h2>

      <input
        v-model="tableName"
        class="field-input"
        type="text"
        :placeholder="selectedTable ? 'Название таблицы...' : `Таблица ${tableCount + 1}`"
      />

      <textarea
        v-model="tableDesc"
        class="field-input field-textarea"
        placeholder="Описание таблицы..."
        rows="4"
      />

      <button class="btn-primary" @click="saveTable">Сохранить</button>
    </div>

    <!-- BOTTOM CARD (only when table selected) -->
    <Transition name="slide-up">
      <div v-if="selectedTable" class="card card--col">
        <h2 class="card-table-name">{{ selectedTable.name }}</h2>
        <div class="card-divider" />
        <p class="card-subtitle">Добавить колонку</p>

        <input
          v-model="colName"
          class="field-input"
          type="text"
          placeholder="Название колонки..."
        />

        <div class="select-wrapper">
          <select v-model="colType" class="field-select">
            <option v-for="t in COLUMN_TYPES" :key="t.value" :value="t.value">
              {{ t.label }}
            </option>
          </select>
          <svg class="select-arrow" width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path d="M3 5l4 4 4-4" stroke="#9ba3b8" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </div>

        <label class="checkbox-row" @click="colRequired = !colRequired">
          <span class="custom-checkbox" :class="{ checked: colRequired }">
            <svg v-if="colRequired" width="10" height="10" viewBox="0 0 10 10" fill="none">
              <path d="M2 5l2.5 2.5L8 3" stroke="#fff" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </span>
          <span class="checkbox-label">required</span>
        </label>

        <button class="btn-primary" @click="addColumn">Добавить в таблицу</button>

        <div class="spacer" />

        <button class="btn-danger" @click="deleteTable">Удалить таблицу</button>
      </div>
    </Transition>
  </aside>
</template>

<style scoped>
/* ── Sidebar wrapper ── */
.editor {
  width: 310px;
  flex-shrink: 0;
  background: #eef4f6;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px 14px;
  animation: slide-in 0.3s ease;
}

@keyframes slide-in {
  from { transform: translateX(-100%); opacity: 0; }
  to   { transform: translateX(0);     opacity: 1; }
}

/* ── Cards ── */
.card {
  background: #ffffff;
  border-radius: 18px;
  padding: 20px 18px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  box-shadow: 0 1px 6px rgba(90, 93, 114, 0.07);
}

.card--col {
  flex: 1;
  min-height: 0;
}

/* Card headers */
.card-title {
  font-size: 18px;
  font-weight: 700;
  color: #3c3f52;
  margin: 0;
}

.card-table-name {
  font-size: 24px;
  font-weight: 700;
  color: #3c3f52;
  margin: 0;
}

.card-divider {
  height: 1px;
  background: #e9f1f3;
  margin: 0 -18px;
}

.card-subtitle {
  font-size: 15px;
  font-weight: 700;
  color: #2f8486;
  margin: 0;
}

/* ── Inputs ── */
.field-input {
  padding: 10px 14px;
  border: 1.5px solid #d3dee2;
  border-radius: 12px;
  font-size: 14px;
  color: #5a5d72;
  background: #ffffff;
  outline: none;
  font-family: inherit;
  transition: border-color 0.15s;
  resize: none;
  width: 100%;
  box-sizing: border-box;
}

.field-input:focus {
  border-color: #8eacb1;
}

.field-input::placeholder {
  color: #b0bac8;
}

.field-textarea {
  min-height: 100px;
}

/* ── Select ── */
.select-wrapper {
  position: relative;
}

.field-select {
  width: 100%;
  padding: 10px 34px 10px 14px;
  border: 1.5px solid #d3dee2;
  border-radius: 12px;
  font-size: 14px;
  color: #5a5d72;
  background: #ffffff;
  outline: none;
  font-family: inherit;
  appearance: none;
  cursor: pointer;
  transition: border-color 0.15s;
  box-sizing: border-box;
}

.field-select:focus {
  border-color: #8eacb1;
}

.select-arrow {
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  pointer-events: none;
}

/* ── Checkbox ── */
.checkbox-row {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  user-select: none;
}

.custom-checkbox {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  border: 1.5px solid #d3dee2;
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: background 0.15s, border-color 0.15s;
}

.custom-checkbox.checked {
  background: #2f8486;
  border-color: #2f8486;
}

.checkbox-label {
  font-size: 14px;
  color: #8a8fa8;
}

/* ── Buttons ── */
.btn-primary {
  padding: 11px 0;
  border-radius: 12px;
  background: #2f8486;
  border: none;
  font-size: 14px;
  font-weight: 600;
  color: #ffffff;
  cursor: pointer;
  font-family: inherit;
  transition: filter 0.15s;
  width: 100%;
}

.btn-primary:hover  { filter: brightness(0.92); }
.btn-primary:active { filter: brightness(0.85); }

.btn-danger {
  padding: 11px 0;
  border-radius: 12px;
  background: #d95f5f;
  border: none;
  font-size: 14px;
  font-weight: 600;
  color: #ffffff;
  cursor: pointer;
  font-family: inherit;
  transition: filter 0.15s;
  width: 100%;
}

.btn-danger:hover  { filter: brightness(0.92); }
.btn-danger:active { filter: brightness(0.85); }

.spacer { flex: 1; }

/* ── Slide-up transition for bottom card ── */
.slide-up-enter-active {
  transition: opacity 0.25s ease, transform 0.25s ease;
}
.slide-up-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}
.slide-up-enter-from {
  opacity: 0;
  transform: translateY(12px);
}
.slide-up-leave-to {
  opacity: 0;
  transform: translateY(12px);
}
</style>
