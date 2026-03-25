<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { FormBuilderUseCase } from '../../application/usecases/FormBuilderUseCase'
import { ReportUseCase } from '../../application/usecases/ReportUseCase'
import { TableSchemaUseCase } from '../../application/usecases/TableSchemaUseCase'
import type { TableDataRecord } from '../../domain/entities/FormBuilder'
import type { TableReportDataset, TableReportSettings } from '../../domain/entities/Report'
import type { TableStructure } from '../../domain/entities/TableSchema'
import { useAuthStore } from '../stores/authStore'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const workspaceId = computed(() => Number(route.params.workspaceId))
const reportId = computed(() => Number(route.params.reportId))

const reportUseCase = new ReportUseCase(authStore.token || '')
const tableSchemaUseCase = new TableSchemaUseCase()
const formBuilderUseCase = new FormBuilderUseCase(authStore.token || '')

const loading = ref(false)
const error = ref('')
const downloadError = ref('')
const downloading = ref<'xlsx' | 'csv' | null>(null)

const reportName = ref('')
const reportDescription = ref('')
const datasets = ref<TableReportDataset[]>([])
const tables = ref<TableStructure[]>([])
const selectedDatasetId = ref<string | null>(null)
const rows = ref<Record<string, TableDataRecord[]>>({})
const globalSearch = ref('')
const columnFilters = ref<Record<string, string>>({})
const sortKey = ref('created_at')
const sortDirection = ref<'asc' | 'desc'>('desc')

const selectedDataset = computed(() => datasets.value.find((item) => item.id === selectedDatasetId.value) ?? null)
const selectedRows = computed(() => (selectedDataset.value ? rows.value[selectedDataset.value.id] ?? [] : []))
const activeTableName = computed(() => tables.value.find((table) => table.id === selectedDataset.value?.table_id)?.name || 'Без таблицы')

const filteredRows = computed(() => {
  const search = globalSearch.value.trim().toLowerCase()
  return [...selectedRows.value]
    .filter((row) => {
      const values = [
        ...selectedDataset.value!.columns.map((column) => formatCell(row.data[column.key])),
        formatDate(row.submitted_at || row.created_at),
      ]

      if (search && !values.some((value) => value.toLowerCase().includes(search))) {
        return false
      }

      return selectedDataset.value!.columns.every((column) => {
        const filterValue = columnFilters.value[column.key] || ''
        if (!filterValue.trim()) return true
        return formatCell(row.data[column.key]).toLowerCase().includes(filterValue.trim().toLowerCase())
      })
    })
    .sort((left, right) => compareRows(left, right))
})

function normalizeTableSettings(raw: Record<string, unknown>): TableReportSettings {
  const datasetsRaw = Array.isArray(raw.datasets) ? raw.datasets : []
  if (datasetsRaw.length === 0 && typeof raw.table_id === 'number') {
    return {
      datasets: [
        {
          id: 'dataset_1',
          title: 'Таблица',
          sheet_name: 'Report',
          table_id: raw.table_id,
          columns: Array.isArray(raw.columns)
            ? raw.columns
                .filter((column): column is Record<string, unknown> => !!column && typeof column === 'object')
                .map((column) => ({
                  key: String(column.key || ''),
                  label: String(column.label || column.key || ''),
                  header_group: typeof column.header_group === 'string' ? column.header_group : null,
                }))
                .filter((column) => column.key)
            : [],
          sorting: [],
          filters: [],
        },
      ],
    }
  }

  return {
    datasets: datasetsRaw
      .filter((item): item is Record<string, unknown> => !!item && typeof item === 'object')
      .map((item, index) => ({
        id: String(item.id || `dataset_${index + 1}`),
        title: String(item.title || `Таблица ${index + 1}`),
        sheet_name: String(item.sheet_name || `Sheet${index + 1}`),
        table_id: typeof item.table_id === 'number' ? item.table_id : null,
        columns: Array.isArray(item.columns)
          ? item.columns
              .filter((column): column is Record<string, unknown> => !!column && typeof column === 'object')
              .map((column) => ({
                key: String(column.key || ''),
                label: String(column.label || column.key || ''),
                header_group: typeof column.header_group === 'string' ? column.header_group : null,
              }))
              .filter((column) => column.key)
          : [],
        sorting: [],
        filters: [],
      })),
  }
}

async function loadPage() {
  if (!authStore.token || !workspaceId.value || !reportId.value) return
  loading.value = true
  error.value = ''

  try {
    const [report, tableOptions] = await Promise.all([
      reportUseCase.getReport(workspaceId.value, reportId.value),
      tableSchemaUseCase.listTables(authStore.token, workspaceId.value),
    ])

    reportName.value = report.name
    reportDescription.value = report.description || ''
    tables.value = tableOptions
    datasets.value = normalizeTableSettings(report.settings || {}).datasets.map((dataset) => {
      if (dataset.columns.length > 0) return dataset
      const table = tableOptions.find((item) => item.id === dataset.table_id)
      return {
        ...dataset,
        columns: table?.columns.map((column) => ({ key: column.key, label: column.name })) ?? [],
      }
    })
    selectedDatasetId.value = datasets.value[0]?.id ?? null

    const allRows = await Promise.all(
      datasets.value.map(async (dataset) => {
        if (!dataset.table_id) return [dataset.id, []] as const
        const result = await formBuilderUseCase.listTableData(workspaceId.value, dataset.table_id, 0, 200)
        return [dataset.id, result.items] as const
      })
    )

    rows.value = Object.fromEntries(allRows)
  } catch (err) {
    error.value = 'Не удалось загрузить представление табличного отчета'
    console.error(err)
  } finally {
    loading.value = false
  }
}

function compareRows(left: TableDataRecord, right: TableDataRecord) {
  const factor = sortDirection.value === 'asc' ? 1 : -1
  const leftValue = sortKey.value === 'created_at' ? left.submitted_at || left.created_at : left.data[sortKey.value]
  const rightValue = sortKey.value === 'created_at' ? right.submitted_at || right.created_at : right.data[sortKey.value]

  const leftNumber = toNumber(leftValue)
  const rightNumber = toNumber(rightValue)
  if (leftNumber !== null && rightNumber !== null) return (leftNumber - rightNumber) * factor

  const leftDate = new Date(String(leftValue || '')).getTime()
  const rightDate = new Date(String(rightValue || '')).getTime()
  if (!Number.isNaN(leftDate) && !Number.isNaN(rightDate) && leftDate !== 0 && rightDate !== 0) {
    return (leftDate - rightDate) * factor
  }

  return String(leftValue ?? '').localeCompare(String(rightValue ?? ''), 'ru') * factor
}

function toggleSort(key: string) {
  if (sortKey.value === key) {
    sortDirection.value = sortDirection.value === 'asc' ? 'desc' : 'asc'
    return
  }
  sortKey.value = key
  sortDirection.value = key === 'created_at' ? 'desc' : 'asc'
}

function formatDate(value?: string | null) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat('ru-RU', {
    day: '2-digit',
    month: 'long',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)
}

function formatCell(value: unknown): string {
  if (value === null || value === undefined || value === '') return '—'
  if (Array.isArray(value)) return value.map((item) => formatCell(item)).join(', ')
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

function toNumber(value: unknown): number | null {
  if (typeof value === 'number' && Number.isFinite(value)) return value
  if (typeof value === 'string' && value.trim()) {
    const parsed = Number(value)
    return Number.isFinite(parsed) ? parsed : null
  }
  return null
}

async function download(format: 'xlsx' | 'csv') {
  if (!workspaceId.value || !reportId.value) return
  downloading.value = format
  downloadError.value = ''
  try {
    const blob = await reportUseCase.downloadExcelReport(workspaceId.value, reportId.value, format)
    const url = window.URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = format === 'xlsx' ? `report_${reportId.value}.xlsx` : `report_${reportId.value}.zip`
    document.body.appendChild(anchor)
    anchor.click()
    document.body.removeChild(anchor)
    window.URL.revokeObjectURL(url)
  } catch (err: unknown) {
    const detail =
      typeof err === 'object' &&
      err !== null &&
      'response' in err &&
      typeof (err as { response?: { data?: { detail?: string } } }).response?.data?.detail === 'string'
        ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
        : null
    downloadError.value = detail || 'Не удалось подготовить файл для скачивания'
  } finally {
    downloading.value = null
  }
}

watch(selectedDatasetId, () => {
  columnFilters.value = {}
  globalSearch.value = ''
  sortKey.value = 'created_at'
  sortDirection.value = 'desc'
})

onMounted(loadPage)
</script>

<template>
  <main class="table-report-view-page">
    <header class="topbar">
      <div>
        <button class="ghost-link" @click="router.push({ name: 'dashboard' })">← Назад</button>
        <h1>{{ reportName }}</h1>
        <p>{{ reportDescription || 'Просмотр сохраненного табличного отчета' }}</p>
      </div>
      <div class="topbar-actions">
        <button class="secondary-btn" @click="router.push({ name: 'table-report-detail', params: { workspaceId, reportId } })">
          Редактировать
        </button>
        <button class="secondary-btn" :disabled="downloading !== null" @click="download('csv')">
          {{ downloading === 'csv' ? 'Подготовка CSV...' : 'Скачать CSV' }}
        </button>
        <button class="primary-btn" :disabled="downloading !== null" @click="download('xlsx')">
          {{ downloading === 'xlsx' ? 'Подготовка Excel...' : 'Скачать Excel' }}
        </button>
      </div>
    </header>

    <div v-if="loading" class="surface-card">Загрузка...</div>
    <div v-else-if="error" class="surface-card error">{{ error }}</div>
    <template v-else-if="selectedDataset">
      <section class="surface-card">
        <div class="dataset-tabs">
          <button
            v-for="dataset in datasets"
            :key="dataset.id"
            class="dataset-tab"
            :class="{ active: dataset.id === selectedDatasetId }"
            @click="selectedDatasetId = dataset.id"
          >
            <span>{{ dataset.title }}</span>
            <small>{{ tables.find((table) => table.id === dataset.table_id)?.name || 'Без таблицы' }}</small>
          </button>
        </div>
      </section>

      <section class="surface-card">
        <div class="section-head">
          <div>
            <h3>{{ selectedDataset.title }}</h3>
            <p class="muted">Таблица: {{ activeTableName }}. Фильтрация, сортировка и предпросмотр данных перед выгрузкой.</p>
          </div>
          <input v-model="globalSearch" class="search-input" placeholder="Поиск по таблице" />
        </div>

        <p v-if="downloadError" class="error">{{ downloadError }}</p>

        <div class="table-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th
                  v-for="column in selectedDataset.columns"
                  :key="column.key"
                  class="sortable"
                  @click="toggleSort(column.key)"
                >
                  {{ column.label }}
                  <small v-if="sortKey === column.key">{{ sortDirection === 'asc' ? '↑' : '↓' }}</small>
                </th>
                <th class="sortable" @click="toggleSort('created_at')">
                  Создано
                  <small v-if="sortKey === 'created_at'">{{ sortDirection === 'asc' ? '↑' : '↓' }}</small>
                </th>
              </tr>
              <tr class="filter-row">
                <th v-for="column in selectedDataset.columns" :key="`filter-${column.key}`">
                  <input
                    :value="columnFilters[column.key] || ''"
                    placeholder="Фильтр"
                    @input="columnFilters = { ...columnFilters, [column.key]: ($event.target as HTMLInputElement).value }"
                  />
                </th>
                <th />
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in filteredRows" :key="row.id">
                <td
                  v-for="column in selectedDataset.columns"
                  :key="column.key"
                >
                  {{ formatCell(row.data[column.key]) }}
                </td>
                <td>{{ formatDate(row.submitted_at || row.created_at) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </template>
  </main>
</template>

<style scoped>
.table-report-view-page { min-height: 100vh; padding: 28px; background: linear-gradient(180deg, var(--public-page-bg-start) 0%, var(--public-page-bg-end) 100%); display: grid; gap: 18px; }
.surface-card {
  min-width: 0;
  border: 1px solid var(--line);
  border-radius: 22px;
  background: var(--public-card-bg);
  padding: 18px;
  box-shadow: var(--shadow-soft);
}
.topbar, .topbar-actions, .section-head { display:flex; align-items:center; gap:12px; }
.topbar, .section-head { justify-content:space-between; }
.topbar h1, .section-head h3 { margin:0; }
.ghost-link, .primary-btn, .secondary-btn, .dataset-tab { border:none; cursor:pointer; }
.ghost-link { background:transparent; padding:0; color:var(--public-accent); }
.primary-btn, .secondary-btn { border-radius:12px; padding:10px 16px; }
.primary-btn { background: linear-gradient(140deg, var(--public-accent), var(--public-accent-strong)); color: #ffffff; }
.secondary-btn { background: color-mix(in srgb, var(--public-accent) 10%, #ffffff); color: var(--public-accent-soft-text); }
.dataset-tabs { display:grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap:12px; }
.dataset-tab { background: var(--bg-soft); border:1px solid var(--line); border-radius:16px; padding:12px 14px; display:grid; gap:4px; text-align:left; }
.dataset-tab.active { background: linear-gradient(140deg, #1e63d8, #2b7df4); color: var(--text-main); }
.dataset-tab small, .muted { color:var(--text-muted); }
.dataset-tab.active small { color:rgba(255,255,255,0.75); }
.search-input, .filter-row input { width:100%; border:1px solid var(--line); border-radius:12px; padding:10px 12px; background: var(--bg-panel); font:inherit; }
.search-input { max-width:320px; }
.table-wrap {
  width: 100%;
  max-width: 100%;
  max-height: min(70vh, 760px);
  overflow-x: auto;
  overflow-y: auto;
  border: 1px solid var(--line);
  border-radius: 16px;
  background: var(--bg-panel);
}
.data-table {
  width: max-content;
  min-width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  table-layout: auto;
}
.data-table th, .data-table td {
  padding:10px 12px;
  border-bottom:1px solid var(--line);
  text-align:left;
  vertical-align:top;
  background: var(--bg-panel);
  white-space: nowrap;
}
.data-table th {
  font-size: 0.8rem;
  line-height: 1.2;
}
.data-table td {
  line-height:1.35;
  color: var(--text-main);
  font-size: 0.92rem;
}
.data-table thead th {
  position: sticky;
  top: 0;
  z-index: 2;
  background: var(--public-table-head-bg);
}
.data-table thead tr.filter-row th {
  top: 46px;
  z-index: 1;
  background: var(--public-table-filter-bg);
}
.data-table tbody tr:hover td {
  background: var(--public-hover-bg);
}
.sortable { cursor:pointer; user-select:none; }
.filter-row th { padding-top:10px; padding-bottom:10px; }
.filter-row input {
  min-width: 0;
  padding: 8px 10px;
  font-size: 0.9rem;
}
.error { color: var(--danger); }

@media (max-width: 980px) {
  .table-report-view-page { padding:16px; }
  .topbar, .section-head { display:grid; }
  .topbar-actions { flex-wrap: wrap; }
  .search-input { max-width:none; }
  .table-wrap { max-height: 62vh; }
  .data-table th, .data-table td { padding: 9px 10px; }
}

@media (max-width: 760px) {
  .surface-card { padding: 14px; }
  .dataset-tabs { grid-template-columns: 1fr; }
  .dataset-tab { padding: 10px 12px; }
  .topbar-actions { display:grid; grid-template-columns: 1fr; }
  .topbar-actions button { width: 100%; }
  .section-head { gap: 10px; }
  .table-wrap { max-height: 58vh; }
  .data-table th, .data-table td { padding: 8px 9px; }
  .data-table th { font-size: 0.75rem; }
  .data-table td { font-size: 0.86rem; }
}
</style>
