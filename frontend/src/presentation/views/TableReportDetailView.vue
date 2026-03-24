<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { FormBuilderUseCase } from '../../application/usecases/FormBuilderUseCase'
import { ReportUseCase } from '../../application/usecases/ReportUseCase'
import { TableSchemaUseCase } from '../../application/usecases/TableSchemaUseCase'
import type { TableDataRecord } from '../../domain/entities/FormBuilder'
import type { ReportConfiguration, TableReportDataset, TableReportSettings } from '../../domain/entities/Report'
import type { ColumnDefinition, TableStructure } from '../../domain/entities/TableSchema'
import { useAuthStore } from '../stores/authStore'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const workspaceId = computed(() => Number(route.params.workspaceId))
const reportId = computed(() => (route.params.reportId ? Number(route.params.reportId) : null))
const isCreateMode = computed(() => route.name === 'table-report-create')

const reportUseCase = new ReportUseCase(authStore.token || '')
const tableSchemaUseCase = new TableSchemaUseCase()
const formBuilderUseCase = new FormBuilderUseCase(authStore.token || '')

const loading = ref(false)
const saving = ref(false)
const pageError = ref('')

const reportName = ref('')
const reportDescription = ref('')
const reportIsPublished = ref(false)
const tables = ref<TableStructure[]>([])
const datasets = ref<TableReportDataset[]>([])
const selectedDatasetId = ref<string | null>(null)
const previewRows = ref<TableDataRecord[]>([])
const previewLoading = ref(false)
const previewError = ref('')
const addTableId = ref<number | null>(null)

const selectedDataset = computed(() => datasets.value.find((item) => item.id === selectedDatasetId.value) ?? null)
const selectedTable = computed(() => {
  if (!selectedDataset.value?.table_id) return null
  return tables.value.find((table) => table.id === selectedDataset.value?.table_id) ?? null
})

function createDataset(table?: TableStructure | null): TableReportDataset {
  const suffix = datasets.value.length + 1
  const columns =
    table?.columns.map((column) => ({
      key: column.key,
      label: column.name,
    })) ?? []

  return {
    id: `dataset_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`,
    title: table?.name || `Таблица ${suffix}`,
    sheet_name: (table?.name || `Sheet${suffix}`).slice(0, 31),
    table_id: table?.id ?? null,
    columns,
    sorting: [],
    filters: [],
  }
}

function normalizeTableSettings(raw: Record<string, unknown>, tableOptions: TableStructure[]): TableReportSettings {
  const datasetsRaw = Array.isArray(raw.datasets) ? raw.datasets : []
  if (datasetsRaw.length > 0) {
    return {
      datasets: datasetsRaw
        .filter((item): item is Record<string, unknown> => !!item && typeof item === 'object')
        .map((item, index) => ({
          id: String(item.id || `dataset_${index + 1}`),
          title: String(item.title || `Таблица ${index + 1}`),
          sheet_name: String(item.sheet_name || `Sheet${index + 1}`).slice(0, 31),
          table_id: typeof item.table_id === 'number' ? item.table_id : null,
          columns: Array.isArray(item.columns)
            ? item.columns
                .filter((column): column is Record<string, unknown> => !!column && typeof column === 'object')
                .map((column) => ({
                  key: String(column.key || ''),
                  label: String(column.label || column.key || ''),
                }))
                .filter((column) => column.key)
            : [],
          sorting: Array.isArray(item.sorting)
            ? item.sorting
                .filter((sorting): sorting is Record<string, unknown> => !!sorting && typeof sorting === 'object')
                .map((sorting) => ({
                  field: String(sorting.field || ''),
                  direction: sorting.direction === 'asc' ? 'asc' : 'desc',
                }))
                .filter((sorting) => sorting.field)
            : [],
          filters: [],
        })),
    }
  }

  const legacyTableId = typeof raw.table_id === 'number' ? raw.table_id : null
  const table = tableOptions.find((item) => item.id === legacyTableId) ?? null
  const dataset = createDataset(table)
  if (Array.isArray(raw.columns)) {
    dataset.columns = raw.columns
      .filter((column): column is Record<string, unknown> => !!column && typeof column === 'object')
      .map((column) => ({
        key: String(column.key || ''),
        label: String(column.label || column.key || ''),
      }))
      .filter((column) => column.key)
  }

  return { datasets: [dataset] }
}

function syncColumnsWithTable(dataset: TableReportDataset) {
  const table = tables.value.find((item) => item.id === dataset.table_id)
  if (!table) {
    dataset.columns = []
    return
  }

  const existing = new Map(dataset.columns.map((column) => [column.key, column]))
  const normalized = table.columns.map((column) => ({
    key: column.key,
    label: existing.get(column.key)?.label || column.name,
  }))

  dataset.columns = dataset.columns.length > 0
    ? [
        ...dataset.columns.filter((column) => normalized.some((normalizedColumn) => normalizedColumn.key === column.key)),
        ...normalized.filter((column) => !dataset.columns.some((existingColumn) => existingColumn.key === column.key)),
      ]
    : normalized
}

async function loadEditor() {
  if (!authStore.token || !workspaceId.value) return
  loading.value = true
  pageError.value = ''

  try {
    tables.value = await tableSchemaUseCase.listTables(authStore.token, workspaceId.value)
    addTableId.value = tables.value[0]?.id ?? null

    if (isCreateMode.value) {
      reportName.value = ''
      reportDescription.value = ''
      reportIsPublished.value = false
      datasets.value = [createDataset(tables.value[0] ?? null)]
      selectedDatasetId.value = datasets.value[0]?.id ?? null
      return
    }

    if (!reportId.value) throw new Error('Missing report id')
    const report: ReportConfiguration = await reportUseCase.getReport(workspaceId.value, reportId.value)
    if (report.report_type !== 'excel_export') {
      throw new Error('Wrong report type')
    }

    reportName.value = report.name
    reportDescription.value = report.description || ''
    reportIsPublished.value = report.is_published
    datasets.value = normalizeTableSettings(report.settings || {}, tables.value).datasets
    datasets.value.forEach(syncColumnsWithTable)
    selectedDatasetId.value = datasets.value[0]?.id ?? null
  } catch (error) {
    pageError.value = 'Не удалось загрузить табличный отчет'
    console.error(error)
  } finally {
    loading.value = false
  }
}

function addDataset() {
  const table = tables.value.find((item) => item.id === addTableId.value) ?? null
  const dataset = createDataset(table)
  datasets.value.push(dataset)
  selectedDatasetId.value = dataset.id
}

function removeDataset(datasetId: string) {
  datasets.value = datasets.value.filter((item) => item.id !== datasetId)
  selectedDatasetId.value = datasets.value[0]?.id ?? null
}

function moveDataset(datasetId: string, direction: -1 | 1) {
  const index = datasets.value.findIndex((item) => item.id === datasetId)
  const targetIndex = index + direction
  if (index < 0 || targetIndex < 0 || targetIndex >= datasets.value.length) return
  const next = [...datasets.value]
  const [dataset] = next.splice(index, 1)
  next.splice(targetIndex, 0, dataset)
  datasets.value = next
}

function toggleColumn(column: ColumnDefinition, enabled: boolean) {
  if (!selectedDataset.value || !selectedTable.value) return
  if (enabled) {
    if (selectedDataset.value.columns.some((item) => item.key === column.key)) return
    selectedDataset.value.columns.push({ key: column.key, label: column.name })
    return
  }

  selectedDataset.value.columns = selectedDataset.value.columns.filter((item) => item.key !== column.key)
}

function moveColumn(columnKey: string, direction: -1 | 1) {
  if (!selectedDataset.value) return
  const index = selectedDataset.value.columns.findIndex((column) => column.key === columnKey)
  const target = index + direction
  if (index < 0 || target < 0 || target >= selectedDataset.value.columns.length) return
  const next = [...selectedDataset.value.columns]
  const [column] = next.splice(index, 1)
  next.splice(target, 0, column)
  selectedDataset.value.columns = next
}

async function loadPreview() {
  if (!selectedDataset.value?.table_id) {
    previewRows.value = []
    previewError.value = ''
    return
  }

  previewLoading.value = true
  previewError.value = ''
  try {
    const result = await formBuilderUseCase.listTableData(workspaceId.value, selectedDataset.value.table_id, 0, 15)
    previewRows.value = result.items
  } catch (error) {
    previewRows.value = []
    previewError.value = 'Не удалось загрузить preview'
    console.error(error)
  } finally {
    previewLoading.value = false
  }
}

async function saveReport() {
  if (!workspaceId.value || !reportName.value.trim() || datasets.value.length === 0) return
  saving.value = true
  try {
    const settings: TableReportSettings = {
      datasets: datasets.value.map((dataset, index) => ({
        ...dataset,
        title: dataset.title.trim() || `Таблица ${index + 1}`,
        sheet_name: (dataset.sheet_name.trim() || `Sheet${index + 1}`).slice(0, 31),
      })),
    }

    const saved = isCreateMode.value
      ? await reportUseCase.createReport(
          workspaceId.value,
          reportName.value.trim(),
          reportDescription.value.trim(),
          'excel_export',
          settings as unknown as Record<string, unknown>,
          reportIsPublished.value
        )
      : await reportUseCase.updateReport(
          workspaceId.value,
          reportId.value as number,
          reportName.value.trim(),
          reportDescription.value.trim(),
          'excel_export',
          settings as unknown as Record<string, unknown>,
          reportIsPublished.value
        )

    if (isCreateMode.value) {
      await router.replace({
        name: 'table-report-detail',
        params: { workspaceId: workspaceId.value, reportId: saved.id },
      })
    }
  } catch (error) {
    pageError.value = 'Не удалось сохранить табличный отчет'
    console.error(error)
  } finally {
    saving.value = false
  }
}

watch(
  () => [selectedDatasetId.value, selectedDataset.value?.table_id],
  async () => {
    const dataset = selectedDataset.value
    if (!dataset) return
    syncColumnsWithTable(dataset)
    await loadPreview()
  },
  { immediate: true }
)

onMounted(loadEditor)
</script>

<template>
  <main class="table-report-page">
    <header class="topbar">
      <div>
        <button class="ghost-link" @click="router.push({ name: 'dashboard' })">← Назад</button>
        <h1>Табличный отчет</h1>
        <p>Отдельный конструктор для multi-table CSV/XLSX экспорта.</p>
      </div>
      <div class="topbar-actions">
        <button
          v-if="!isCreateMode && reportId"
          class="secondary-btn"
          @click="router.push({ name: 'table-report-view', params: { workspaceId, reportId } })"
        >
          Открыть представление
        </button>
        <label class="checkbox-inline">
          <input v-model="reportIsPublished" type="checkbox" />
          Опубликован
        </label>
        <button class="primary-btn" :disabled="saving" @click="saveReport">
          {{ saving ? 'Сохранение...' : 'Сохранить' }}
        </button>
      </div>
    </header>

    <div v-if="loading" class="surface-card">Загрузка...</div>
    <div v-else-if="pageError" class="surface-card error">{{ pageError }}</div>
    <template v-else>
      <section class="surface-card meta-grid">
        <div>
          <label>Название отчета</label>
          <input v-model="reportName" placeholder="Например: Экспорт по нескольким таблицам" />
        </div>
        <div>
          <label>Описание</label>
          <input v-model="reportDescription" placeholder="Что попадет в экспорт" />
        </div>
      </section>

      <section class="surface-card">
        <div class="section-head">
          <div>
            <h3>Наборы таблиц</h3>
            <p class="muted">Каждый набор станет отдельной таблицей preview и отдельным sheet в Excel.</p>
          </div>
          <div class="dataset-add">
            <select v-model.number="addTableId">
              <option v-for="table in tables" :key="table.id" :value="table.id">{{ table.name }}</option>
            </select>
            <button class="secondary-btn" @click="addDataset">Добавить таблицу</button>
          </div>
        </div>

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

      <section class="editor-layout" v-if="selectedDataset">
        <aside class="surface-card editor-panel">
          <div class="section-head">
            <h3>Настройки набора</h3>
            <div class="inline-actions">
              <button class="small-btn" @click="moveDataset(selectedDataset.id, -1)">↑</button>
              <button class="small-btn" @click="moveDataset(selectedDataset.id, 1)">↓</button>
              <button class="danger-btn" :disabled="datasets.length === 1" @click="removeDataset(selectedDataset.id)">Удалить</button>
            </div>
          </div>

          <div class="field-block">
            <label>Заголовок набора</label>
            <input v-model="selectedDataset.title" />
          </div>

          <div class="field-block">
            <label>Имя листа Excel</label>
            <input v-model="selectedDataset.sheet_name" maxlength="31" />
          </div>

          <div class="field-block">
            <label>Таблица</label>
            <select v-model.number="selectedDataset.table_id" @change="syncColumnsWithTable(selectedDataset)">
              <option :value="null">Выберите таблицу</option>
              <option v-for="table in tables" :key="table.id" :value="table.id">{{ table.name }}</option>
            </select>
          </div>

          <div class="field-block">
            <label>Столбцы и порядок</label>
            <div v-if="selectedTable" class="column-list">
              <div v-for="column in selectedTable.columns" :key="column.key" class="column-item">
                <label class="column-toggle">
                  <input
                    type="checkbox"
                    :checked="selectedDataset.columns.some((item) => item.key === column.key)"
                    @change="toggleColumn(column, ($event.target as HTMLInputElement).checked)"
                  />
                  <span>{{ column.name }}</span>
                </label>
                <template v-if="selectedDataset.columns.some((item) => item.key === column.key)">
                  <input
                    :value="selectedDataset.columns.find((item) => item.key === column.key)?.label || column.name"
                    placeholder="Подпись столбца"
                    @input="
                      selectedDataset.columns = selectedDataset.columns.map((item) =>
                        item.key === column.key
                          ? { ...item, label: ($event.target as HTMLInputElement).value || column.name }
                          : item
                      )
                    "
                  />
                  <div class="inline-actions">
                    <button class="small-btn" @click="moveColumn(column.key, -1)">↑</button>
                    <button class="small-btn" @click="moveColumn(column.key, 1)">↓</button>
                  </div>
                </template>
              </div>
            </div>
          </div>
        </aside>

        <section class="surface-card preview-panel">
          <div class="section-head">
            <div>
              <h3>Preview</h3>
              <p class="muted">Предпросмотр выбранной таблицы с учетом столбцов и порядка.</p>
            </div>
          </div>

          <div v-if="previewLoading" class="muted">Загрузка preview...</div>
          <div v-else-if="previewError" class="error">{{ previewError }}</div>
          <div v-else-if="selectedDataset.columns.length > 0" class="preview-table-wrap">
            <table class="preview-table">
              <thead>
                <tr>
                  <th v-for="column in selectedDataset.columns" :key="column.key">{{ column.label }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in previewRows" :key="row.id">
                  <td v-for="column in selectedDataset.columns" :key="column.key">{{ row.data[column.key] ?? '—' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <p v-else class="muted">Выберите хотя бы один столбец.</p>
        </section>
      </section>
    </template>
  </main>
</template>

<style scoped>
.table-report-page { min-height: 100vh; padding: 28px; background: linear-gradient(180deg, #f7fbfb 0%, #eef4f5 100%); display: grid; gap: 18px; }
.surface-card { border: 1px solid rgba(64, 90, 97, 0.14); border-radius: 22px; background: rgba(255,255,255,0.9); padding: 18px; box-shadow: 0 18px 50px rgba(31,61,67,0.08); }
.topbar, .topbar-actions, .section-head, .inline-actions, .dataset-add { display:flex; align-items:center; gap:12px; }
.topbar, .section-head { justify-content:space-between; }
.topbar h1, .section-head h3 { margin:0; }
.ghost-link, .primary-btn, .secondary-btn, .small-btn, .danger-btn, .dataset-tab { border:none; cursor:pointer; }
.ghost-link { background:transparent; padding:0; color:#156f69; }
.primary-btn, .secondary-btn, .danger-btn, .small-btn { border-radius:12px; padding:10px 14px; }
.primary-btn { background:#156f69; color:#fff; }
.secondary-btn, .small-btn { background:#eef5f4; color:#144c49; }
.danger-btn { background:#fff2f4; color:#b63b53; }
.checkbox-inline { display:flex; align-items:center; gap:8px; }
.meta-grid, .editor-layout { display:grid; gap:16px; }
.meta-grid { grid-template-columns: 1fr 1fr; }
.editor-layout { grid-template-columns: minmax(360px, 430px) minmax(0, 1fr); }
.dataset-tabs, .column-list, .editor-panel, .preview-panel, .field-block { display:grid; gap:12px; }
.dataset-tabs { grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); }
.dataset-tab { background:#f5f9f8; border:1px solid rgba(64, 90, 97, 0.12); border-radius:16px; padding:12px 14px; display:grid; gap:4px; text-align:left; }
.dataset-tab.active { background:#156f69; color:#fff; }
.dataset-tab small, .muted { color:#6c8189; }
.dataset-tab.active small { color:rgba(255,255,255,0.75); }
.column-item { display:grid; grid-template-columns: minmax(140px, 1fr) minmax(140px, 1fr) auto; gap:10px; align-items:center; }
.column-toggle { display:flex; gap:8px; align-items:center; }
.preview-table-wrap { overflow:auto; }
.preview-table { width:100%; border-collapse:collapse; }
.preview-table th, .preview-table td { padding:12px 14px; border-bottom:1px solid rgba(64,90,97,0.1); text-align:left; }
input, select { width:100%; border:1px solid rgba(64, 90, 97, 0.16); border-radius:12px; padding:10px 12px; background:#fff; font:inherit; }
input[type='checkbox'] { width:auto; }
.error { color:#b63b53; }
@media (max-width: 980px) { .meta-grid, .editor-layout { grid-template-columns: 1fr; } .table-report-page { padding:16px; } }
</style>
