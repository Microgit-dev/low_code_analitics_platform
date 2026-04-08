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
const draggedColumnKey = ref<string | null>(null)
const dragOverIndex = ref<number | null>(null)

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
          sorting: [],
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
    if (report.report_type !== 'table_export') {
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

function updateColumnLabel(columnKey: string, label: string) {
  if (!selectedDataset.value) return
  selectedDataset.value.columns = selectedDataset.value.columns.map((column) =>
    column.key === columnKey ? { ...column, label: label || '' } : column
  )
}

function onColumnDragStart(columnKey: string) {
  draggedColumnKey.value = columnKey
}

function onColumnDragEnd() {
  draggedColumnKey.value = null
  dragOverIndex.value = null
}

function onColumnDragOver(event: DragEvent, index: number) {
  event.preventDefault()
  dragOverIndex.value = index
}

function onColumnDrop(event: DragEvent, dropIndex: number) {
  event.preventDefault()
  if (!selectedDataset.value || !draggedColumnKey.value) return

  const dragIndex = selectedDataset.value.columns.findIndex((c) => c.key === draggedColumnKey.value)
  if (dragIndex === dropIndex || dragIndex < 0) {
    draggedColumnKey.value = null
    dragOverIndex.value = null
    return
  }

  const next = [...selectedDataset.value.columns]
  const [column] = next.splice(dragIndex, 1)
  next.splice(dropIndex, 0, column)
  selectedDataset.value.columns = next

  draggedColumnKey.value = null
  dragOverIndex.value = null
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
          'table_export',
          settings as unknown as Record<string, unknown>,
          reportIsPublished.value
        )
      : await reportUseCase.updateReport(
          workspaceId.value,
          reportId.value as number,
          reportName.value.trim(),
          reportDescription.value.trim(),
          'table_export',
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
  <main class="table-report-page editor-shell">
    <header class="header-bar editor-shell-header">
      <div class="header-content">
        <button class="back-btn" @click="router.push({ name: 'dashboard' })">← Назад</button>
        <div>
          <h1>Табличный отчет</h1>
          <p>Многотабличный экспорт в CSV/XLSX</p>
        </div>
      </div>
      <div class="header-actions editor-shell-actions">
        <button
          v-if="!isCreateMode && reportId"
          class="btn-secondary"
          @click="router.push({ name: 'table-report-view', params: { workspaceId, reportId } })"
        >
          Открыть отчет
        </button>
        <label class="checkbox-label">
          <input v-model="reportIsPublished" type="checkbox" />
          Опубликован
        </label>
        <button class="btn-primary" :disabled="saving" @click="saveReport">
          {{ saving ? 'Сохранение...' : 'Сохранить' }}
        </button>
      </div>
    </header>

    <div v-if="loading" class="card">⏳ Загрузка...</div>
    <div v-else-if="pageError" class="card error-message">❌ {{ pageError }}</div>

    <template v-else>
      <!-- Metadata -->
      <section class="card meta-section editor-shell-panel">
        <div class="form-group">
          <label>Название отчета</label>
          <input v-model="reportName" placeholder="Введите название отчета" class="input-text" />
        </div>
        <div class="form-group">
          <label>Описание</label>
          <input v-model="reportDescription" placeholder="Краткое описание содержимого" class="input-text" />
        </div>
      </section>

      <!-- Datasets Management -->
      <section class="card datasets-section editor-shell-panel">
        <div class="section-header">
          <div>
            <h3>Наборы таблиц</h3>
            <p class="muted">Каждый набор экспортируется в отдельный лист Excel</p>
          </div>
          <div class="dataset-controls">
            <select v-model.number="addTableId" class="input-text">
              <option :value="null">Выберите таблицу</option>
              <option v-for="table in tables" :key="table.id" :value="table.id">{{ table.name }}</option>
            </select>
            <button class="btn-secondary" @click="addDataset">+ Добавить</button>
          </div>
        </div>

        <div class="dataset-list">
          <button
            v-for="(ds, idx) in datasets"
            :key="ds.id"
            class="dataset-item"
            :class="{ active: ds.id === selectedDatasetId }"
            @click="selectedDatasetId = ds.id"
          >
            <span class="dataset-title">{{ ds.title }}</span>
            <span class="dataset-table">{{ tables.find((t) => t.id === ds.table_id)?.name || '—' }}</span>
            <span v-if="datasets.length > 1" class="dataset-index">{{ idx + 1 }}</span>
          </button>
        </div>
      </section>

      <!-- Editor -->
      <section v-if="selectedDataset" class="editor-section">
        <div class="editor-column editor-settings">
          <div class="card settings-card editor-shell-panel">
            <div class="card-header">
              <h3>Параметры набора</h3>
              <div v-if="datasets.length > 1" class="dataset-actions">
                <button class="btn-sm" @click="moveDataset(selectedDataset.id, -1)" title="Поднять">↑</button>
                <button class="btn-sm" @click="moveDataset(selectedDataset.id, 1)" title="Опустить">↓</button>
                <button class="btn-sm danger" @click="removeDataset(selectedDataset.id)" title="Удалить">✕</button>
              </div>
            </div>

            <div class="form-group">
              <label>Заголовок набора</label>
              <input v-model="selectedDataset.title" class="input-text" placeholder="Название для таблицы" />
            </div>

            <div class="form-group">
              <label>Имя листа (макс. 31 символ)</label>
              <input v-model="selectedDataset.sheet_name" maxlength="31" class="input-text" placeholder="Sheet1" />
            </div>

            <div class="form-group">
              <label>Исходная таблица</label>
              <select v-model.number="selectedDataset.table_id" @change="syncColumnsWithTable(selectedDataset)" class="input-text">
                <option :value="null">—</option>
                <option v-for="table in tables" :key="table.id" :value="table.id">{{ table.name }}</option>
              </select>
            </div>
          </div>
        </div>

        <div class="editor-column editor-columns">
          <div class="card columns-card editor-shell-panel">
            <div class="card-header">
              <h3>Столбцы ({{ selectedDataset.columns.length }})</h3>
            </div>

            <div v-if="!selectedTable" class="muted-text">Выберите таблицу</div>

            <div v-else-if="selectedDataset.columns.length === 0" class="muted-text">
              Добавьте столбцы скроллинг ниже ↓
            </div>

            <div v-else class="columns-list">
              <div
                v-for="(column, idx) in selectedDataset.columns"
                :key="column.key"
                class="column-row"
                :class="{ 'dragging': draggedColumnKey === column.key, 'drag-over': dragOverIndex === idx }"
                draggable="true"
                @dragstart="onColumnDragStart(column.key)"
                @dragend="onColumnDragEnd"
                @dragover="onColumnDragOver($event, idx)"
                @drop="onColumnDrop($event, idx)"
                @dragleave="dragOverIndex = null"
              >
                <div class="column-info">
                  <span class="column-index">{{ idx + 1 }}</span>
                  <span class="drag-handle">⋮</span>
                  <span class="column-key">{{ column.key }}</span>
                </div>
                <input
                  :value="column.label"
                  class="input-text column-label"
                  placeholder="Заголовок столбца"
                  @input="updateColumnLabel(column.key, ($event.target as HTMLInputElement).value)"
                />
                <div class="column-buttons">
                  <button class="btn-sm" @click="moveColumn(column.key, -1)" :disabled="idx === 0" title="Выше">↑</button>
                  <button class="btn-sm" @click="moveColumn(column.key, 1)" :disabled="idx === selectedDataset.columns.length - 1" title="Ниже">↓</button>
                  <button class="btn-sm danger" @click="toggleColumn(selectedTable.columns.find((c) => c.key === column.key)!, false)" title="Удалить">✕</button>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="editor-column editor-available">
          <div class="card available-card editor-shell-panel">
            <div class="card-header">
              <h3>Доступные столбцы</h3>
            </div>

            <div v-if="!selectedTable" class="muted-text">Выберите таблицу</div>

            <div v-else class="available-list">
              <label v-for="column in selectedTable.columns" :key="column.key" class="available-item">
                <input
                  type="checkbox"
                  :checked="selectedDataset.columns.some((c) => c.key === column.key)"
                  @change="toggleColumn(column, ($event.target as HTMLInputElement).checked)"
                />
                <span class="column-name">{{ column.name }}</span>
                <span class="column-type">{{ column.key }}</span>
              </label>
            </div>
          </div>
        </div>
      </section>

      <!-- Preview -->
      <section class="card preview-section editor-shell-panel">
        <div class="section-header">
          <h3>Предпросмотр</h3>
          <p class="muted">Первые 15 строк с выбранными столбцами</p>
        </div>

        <div v-if="previewLoading" class="muted-text">⏳ Загрузка...</div>
        <div v-else-if="previewError" class="error-message">❌ {{ previewError }}</div>
        <div v-else-if="selectedDataset && selectedDataset.columns.length > 0" class="preview-table">
          <table>
            <thead>
              <tr>
                <th v-for="col in selectedDataset.columns" :key="col.key">{{ col.label }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in previewRows" :key="row.id">
                <td v-for="col in selectedDataset.columns" :key="col.key">{{ row.data[col.key] ?? '—' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p v-else class="muted-text">Выберите таблицу и столбцы для предпросмотра</p>
      </section>
    </template>
  </main>
</template>

<style scoped>
.table-report-page {
  min-height: 100vh;
  background: linear-gradient(135deg, #f8faff 0%, #eff4fc 100%);
  padding: 24px;
}

/* Header */
.header-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  gap: 20px;
}

.header-content {
  display: flex;
  align-items: center;
  gap: 16px;
}

.back-btn {
  background: none;
  border: none;
  font-size: 1rem;
  cursor: pointer;
  color: #1e63d8;
  padding: 0;
}

.header-bar h1 {
  margin: 0;
  font-size: 1.75rem;
  color: var(--text-main);
}

.header-bar p {
  margin: 4px 0 0 0;
  color: var(--text-muted);
  font-size: 0.9rem;
}

.header-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

/* Buttons */
.btn-primary,
.btn-secondary,
.btn-sm,
.btn-sm.danger {
  border: none;
  border-radius: 8px;
  padding: 8px 16px;
  font-size: 0.9rem;
  cursor: pointer;
  font-weight: 500;
  transition: all 0.2s;
}

.btn-primary {
  background: linear-gradient(140deg, #1e63d8, #2b7df4);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: linear-gradient(140deg, #1b58bf, #256fd9);
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-secondary {
  background: #edf3ff;
  color: #2d4f86;
}

.btn-secondary:hover {
  background: #e1ebff;
}

.btn-sm {
  padding: 4px 10px;
  font-size: 0.8rem;
  background: #edf3ff;
  color: #2d4f86;
}

.btn-sm:hover:not(:disabled) {
  background: #e1ebff;
}

.btn-sm:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-sm.danger {
  background: #f9e7ec;
  color: var(--danger);
}

.btn-sm.danger:hover {
  background: #f4d7df;
}

/* Cards */
.card {
  background: var(--bg-panel);
  border: 1px solid var(--line);
  border-radius: 16px;
  padding: 20px;
  margin-bottom: 20px;
  box-shadow: var(--shadow-soft);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--line);
}

.card-header h3 {
  margin: 0;
  font-size: 1rem;
}

/* Forms */
.form-group {
  margin-bottom: 16px;
}

.form-group:last-child {
  margin-bottom: 0;
}

.form-group label {
  display: block;
  margin-bottom: 6px;
  font-weight: 500;
  color: var(--text-main);
  font-size: 0.9rem;
}

.input-text {
  width: 100%;
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 10px 12px;
  font-size: 0.9rem;
  font-family: inherit;
  background: #f8faff;
  transition: border-color 0.2s;
}

.input-text:focus {
  outline: none;
  border-color: var(--accent-soft);
  box-shadow: 0 0 0 3px rgba(30, 99, 216, 0.16);
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  user-select: none;
}

.checkbox-label input[type='checkbox'] {
  width: auto;
  cursor: pointer;
}

/* Metadata Section */
.meta-section {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

@media (max-width: 768px) {
  .meta-section {
    grid-template-columns: 1fr;
  }
}

/* Datasets Section */
.datasets-section {
}

.section-header {
  margin-bottom: 20px;
}

.section-header h3 {
  margin: 0 0 4px 0;
  font-size: 1.1rem;
}

.section-header .muted {
  margin: 0;
}

.dataset-controls {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-top: 12px;
}

.dataset-controls select {
  flex: 1;
  min-width: 200px;
}

.dataset-list {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.dataset-item {
  background: #f5f8ff;
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 12px 14px;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  gap: 4px;
  text-align: left;
  transition: all 0.2s;
  min-width: 200px;
}

.dataset-item:hover {
  border-color: #99b5eb;
  background: #edf3ff;
}

.dataset-item.active {
  background: linear-gradient(140deg, #1e63d8, #2b7df4);
  color: white;
  border-color: #1e63d8;
}

.dataset-title {
  font-weight: 500;
  font-size: 0.95rem;
}

.dataset-table {
  font-size: 0.8rem;
  color: var(--text-muted);
}

.dataset-item.active .dataset-table {
  color: rgba(255, 255, 255, 0.75);
}

.dataset-index {
  font-size: 0.75rem;
  opacity: 0.5;
}

.dataset-actions {
  display: flex;
  gap: 6px;
}

/* Editor Section */
.editor-section {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 16px;
  margin-bottom: 20px;
}

.editor-column {
}

.settings-card,
.columns-card,
.available-card {
  display: flex;
  flex-direction: column;
  height: 100%;
}

/* Columns List */
.columns-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-height: 500px;
  overflow-y: auto;
}

.column-row {
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: 8px;
  align-items: center;
  padding: 10px;
  background: #f9fbff;
  border-radius: 8px;
  border: 1px solid var(--line);
  transition: all 0.2s;
  cursor: move;
}

.column-row:hover {
  border-color: #9eb5df;
  background: #f4f8ff;
}

.column-row.dragging {
  opacity: 0.5;
  background: rgba(30, 99, 216, 0.12);
}

.column-row.drag-over {
  border-color: #1e63d8;
  border-width: 2px;
  background: rgba(30, 99, 216, 0.1);
  box-shadow: 0 0 8px rgba(30, 99, 216, 0.22);
}

.column-info {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 100px;
}

.column-index {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  background: #edf3ff;
  border-radius: 4px;
  font-size: 0.75rem;
  color: #1e63d8;
  font-weight: 600;
}

.drag-handle {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: grab;
  color: var(--text-muted);
  font-size: 1.2rem;
  user-select: none;
}

.drag-handle:active {
  cursor: grabbing;
}

.column-key {
  font-family: monospace;
  font-size: 0.8rem;
  color: var(--text-muted);
}

.column-label {
  padding: 6px 10px;
}

.column-buttons {
  display: flex;
  gap: 4px;
}

/* Available Columns List */
.available-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 500px;
  overflow-y: auto;
}

.available-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px;
  background: #f9fbff;
  border-radius: 8px;
  border: 1px solid var(--line);
  cursor: pointer;
  transition: all 0.2s;
}

.available-item:hover {
  background: #eef3ff;
  border-color: #bfd0ed;
}

.available-item input[type='checkbox'] {
  width: auto;
  cursor: pointer;
}

.column-name {
  font-weight: 500;
  flex: 1;
  color: var(--text-main);
}

.column-type {
  font-family: monospace;
  font-size: 0.75rem;
  color: var(--text-muted);
  background: var(--bg-panel);
  padding: 2px 6px;
  border-radius: 4px;
}

/* Preview Section */
.preview-section {
}

.preview-table {
  width: 100%;
  overflow-x: auto;
}

.preview-table table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 12px;
}

.preview-table th,
.preview-table td {
  padding: 10px 12px;
  text-align: left;
  border-bottom: 1px solid var(--line);
  font-size: 0.9rem;
}

.preview-table th {
  background: #f2f6ff;
  font-weight: 500;
  color: var(--text-main);
}

.preview-table td {
  color: var(--text-main);
}

.preview-table tbody tr:hover {
  background: #f5f8ff;
}

/* Utility */
.muted {
  color: var(--text-muted);
  font-size: 0.9rem;
}

.muted-text {
  color: var(--text-muted);
  text-align: center;
  padding: 20px;
  font-size: 0.9rem;
}

.error-message {
  color: var(--danger);
  border-color: rgba(193, 56, 79, 0.25);
  background: rgba(193, 56, 79, 0.08);
}

/* Responsive */
@media (max-width: 1200px) {
  .editor-section {
    grid-template-columns: 1fr 1fr;
  }

  .editor-column:nth-child(3) {
    grid-column: 1 / -1;
  }
}

@media (max-width: 768px) {
  .table-report-page {
    padding: 12px;
  }

  .header-bar {
    flex-direction: column;
    align-items: flex-start;
  }

  .header-actions {
    width: 100%;
    flex-wrap: wrap;
  }

  .editor-section {
    grid-template-columns: 1fr;
  }

  .dataset-controls {
    flex-direction: column;
  }

  .dataset-controls select,
  .dataset-controls button {
    width: 100%;
  }
}
</style>
