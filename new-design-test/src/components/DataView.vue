<script setup lang="ts">
import { ref, computed } from 'vue'
import type { Form, Table, FormRecord } from '../types'

const props = defineProps<{
  forms: Form[]
  tables: Table[]
  records: FormRecord[]
}>()

const PAGE_SIZES = [10, 50, 100, 150]

const selectedFormId = ref<number | null>(props.forms[0]?.id ?? null)
const pageSize       = ref(10)

/* Selected form */
const selectedForm = computed(() =>
  props.forms.find(f => f.id === selectedFormId.value) ?? null
)

/* Linked tables for the selected form */
const linkedTables = computed(() =>
  selectedForm.value
    ? props.tables.filter(t => selectedForm.value!.tableIds.includes(t.id))
    : []
)

/* Dynamic column headers from linked tables */
const columns = computed(() => {
  const cols: { key: string; label: string; table: string }[] = []
  for (const table of linkedTables.value) {
    for (const col of table.columns) {
      cols.push({ key: col.name, label: col.name, table: table.name })
    }
  }
  return cols
})

/* Records for selected form, limited by page size */
const filteredRecords = computed(() => {
  if (!selectedForm.value) return []
  return props.records
    .filter(r => r.formId === selectedFormId.value)
    .slice(-pageSize.value)
    .reverse()
})

function formatDate(iso: string) {
  return new Date(iso).toLocaleString('ru-RU', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

function formatValue(val: unknown): string {
  if (val === null || val === undefined) return '—'
  if (Array.isArray(val)) {
    // geoPoint
    if (val.length === 2 && typeof val[0] === 'number') {
      return `${(val[0] as number).toFixed(4)}, ${(val[1] as number).toFixed(4)}`
    }
    return val.join(', ')
  }
  if (typeof val === 'boolean') return val ? 'Да' : 'Нет'
  return String(val)
}
</script>

<template>
  <div class="data-view">

    <!-- Controls -->
    <div class="controls">
      <!-- Form selector -->
      <div class="select-wrap">
        <select v-model="selectedFormId" class="ctrl-select">
          <option :value="null" disabled>Выберите форму...</option>
          <option v-for="form in forms" :key="form.id" :value="form.id">
            {{ form.name }}
          </option>
        </select>
        <svg class="select-arrow" width="14" height="14" viewBox="0 0 14 14" fill="none">
          <path d="M3 5l4 4 4-4" stroke="#9ba3b8" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </div>

      <!-- Page size selector -->
      <div class="select-wrap">
        <select v-model="pageSize" class="ctrl-select ctrl-select--sm">
          <option v-for="n in PAGE_SIZES" :key="n" :value="n">{{ n }} записей</option>
        </select>
        <svg class="select-arrow" width="14" height="14" viewBox="0 0 14 14" fill="none">
          <path d="M3 5l4 4 4-4" stroke="#9ba3b8" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </div>

      <span class="record-count">
        Всего записей: {{ filteredRecords.length }}
      </span>
    </div>

    <!-- Table card -->
    <div class="table-card">
      <!-- No form selected -->
      <div v-if="!selectedForm" class="empty">
        Выберите форму для просмотра данных
      </div>

      <!-- No records yet -->
      <div v-else-if="filteredRecords.length === 0" class="empty">
        <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
          <rect x="8" y="12" width="32" height="28" rx="4" stroke="#d3dee2" stroke-width="2"/>
          <path d="M16 20h16M16 26h10" stroke="#d3dee2" stroke-width="2" stroke-linecap="round"/>
        </svg>
        <p>Нет данных для выбранной формы</p>
        <p class="empty-hint">Добавьте данные через вкладку «Форма»</p>
      </div>

      <!-- Data table -->
      <div v-else class="table-scroll">
        <table class="data-table">
          <thead>
            <tr>
              <th class="th-date">Дата и время</th>
              <th v-for="col in columns" :key="col.key" :title="`Таблица: ${col.table}`">
                {{ col.label }}
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="record in filteredRecords" :key="record.id">
              <td class="td-date">{{ formatDate(record.submittedAt) }}</td>
              <td v-for="col in columns" :key="col.key">
                {{ formatValue(record.values[col.key]) }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

  </div>
</template>

<style scoped>
.data-view {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 16px;
  overflow: hidden;
  background: #eef4f6;
}

/* ── Controls ── */
.controls {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}

.select-wrap {
  position: relative;
}

.ctrl-select {
  appearance: none;
  padding: 9px 36px 9px 14px;
  border: 1.5px solid #d3dee2;
  border-radius: 12px;
  background: #ffffff;
  font-size: 14px;
  color: #3c3f52;
  font-family: inherit;
  font-weight: 500;
  outline: none;
  cursor: pointer;
  min-width: 220px;
  transition: border-color 0.15s;
}

.ctrl-select:focus { border-color: #8eacb1; }

.ctrl-select--sm { min-width: 140px; }

.select-arrow {
  position: absolute;
  right: 10px;
  top: 50%;
  transform: translateY(-50%);
  pointer-events: none;
}

.record-count {
  font-size: 13px;
  color: #9ba3b8;
  font-weight: 500;
  margin-left: 4px;
}

/* ── Table card ── */
.table-card {
  flex: 1;
  background: #ffffff;
  border-radius: 18px;
  box-shadow: 0 1px 6px rgba(90, 93, 114, 0.07);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.table-scroll {
  flex: 1;
  overflow: auto;
}

/* ── Data table ── */
.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}

.data-table thead {
  position: sticky;
  top: 0;
  z-index: 1;
}

.data-table th {
  padding: 13px 16px;
  text-align: left;
  font-size: 13px;
  font-weight: 600;
  color: #5a5d72;
  background: #f3f9fa;
  border-bottom: 1.5px solid #e2eaed;
  white-space: nowrap;
}

.data-table td {
  padding: 12px 16px;
  color: #3c3f52;
  border-bottom: 1px solid #f3f9fa;
  max-width: 280px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.data-table tbody tr:last-child td { border-bottom: none; }

.data-table tbody tr:hover td { background: #f8fbfc; }

.th-date { min-width: 150px; }
.td-date { color: #9ba3b8; font-size: 13px; }

/* ── Empty state ── */
.empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: #9ba3b8;
  font-size: 15px;
  padding: 40px;
  text-align: center;
}

.empty p { margin: 0; }

.empty-hint {
  font-size: 13px;
  color: #b0bac8;
}
</style>
