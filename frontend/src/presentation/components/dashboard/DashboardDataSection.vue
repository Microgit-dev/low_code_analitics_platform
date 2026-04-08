<script setup lang="ts">
import { computed, ref } from 'vue'
import type { ColumnType } from '../../../domain/entities/TableSchema'
import GeoJsonMapEditor from '../common/GeoJsonMapEditor.vue'
import UiStatusText from '../common/UiStatusText.vue'

interface TableColumn {
  key: string
  name: string
  type: ColumnType
  settings: Record<string, unknown>
}

interface TableOption {
  id: number
  name: string
}

interface DataTable {
  id: number
  name: string
  columns: TableColumn[]
}

interface DataRecord {
  id: number
  data: Record<string, unknown>
  submitted_at?: string | number | null
  created_at?: string | number | null
  submitter_email?: string | null
}

const props = defineProps<{
  selectedDataTable: DataTable | null
  tableDataRecords: DataRecord[]
  dataPagination: { skip: number; limit: number; total: number }
  dataLoading: boolean
  dataError: string
  totalPages: number
  currentPage: number
  allTableOptions: TableOption[]
  selectedDataTableId: number | null
  formatDataValue: (value: unknown, columnType: ColumnType) => string
  formatDate: (value: unknown) => string
}>()

const emit = defineEmits<{
  (event: 'update:selectedDataTableId', value: number | null): void
  (event: 'update:dataLimit', value: number): void
  (event: 'data-table-change'): void
  (event: 'data-limit-change'): void
  (event: 'delete-record', recordId: number): void
  (event: 'save-record', payload: { recordId: number; data: Record<string, unknown> }): void
  (event: 'go-to-page', page: number): void
}>()

const selectedDataTableIdModel = computed({
  get: () => props.selectedDataTableId,
  set: (value: number | null) => emit('update:selectedDataTableId', value)
})

const dataLimitModel = computed({
  get: () => props.dataPagination.limit,
  set: (value: number) => emit('update:dataLimit', value)
})

const editModalOpen = ref(false)
const editRecordId = ref<number | null>(null)
const editValues = ref<Record<string, unknown>>({})
const listDraftValues = ref<Record<string, string>>({})
const geoPreviewMode = ref<'text' | 'geojson' | 'map'>('text')

const editableColumns = computed(() => props.selectedDataTable?.columns ?? [])
const hasGeoColumns = computed(() =>
  editableColumns.value.some((column) => column.type === 'geoPoint' || column.type === 'geoPolygon')
)

const isTextareaColumn = (type: ColumnType) => type === 'geoPoint' || type === 'geoPolygon'

const getColumnOptions = (column: TableColumn): string[] => {
  const options = column.settings?.options
  if (!Array.isArray(options)) return []
  return options.map((item) => String(item)).filter(Boolean)
}

const getListItemType = (column: TableColumn): 'text' | 'number' | 'boolean' | 'enum' => {
  const raw = String(column.settings?.itemType ?? 'text')
  if (raw === 'number' || raw === 'boolean' || raw === 'enum') return raw
  return 'text'
}

const isListEnumColumn = (column: TableColumn): boolean =>
  column.type === 'list' && getListItemType(column) === 'enum' && getColumnOptions(column).length > 0

const normalizeArrayValue = (value: unknown): string[] => {
  if (Array.isArray(value)) return value.map((item) => String(item))
  if (typeof value === 'string') {
    const prepared = value.trim()
    if (!prepared) return []
    try {
      const parsed = JSON.parse(prepared)
      if (Array.isArray(parsed)) return parsed.map((item) => String(item))
    } catch {
      return prepared
        .split(/[,\n]/g)
        .map((item) => item.trim())
        .filter(Boolean)
    }
  }
  return []
}

const toPrettyGeoJson = (value: unknown): string => {
  if (value === null || value === undefined || value === '') return '—'
  if (typeof value === 'string') {
    try {
      return JSON.stringify(JSON.parse(value), null, 2)
    } catch {
      return value
    }
  }
  try {
    return JSON.stringify(value, null, 2)
  } catch {
    return String(value)
  }
}

const formatMapTitle = (value: unknown): string => {
  if (!value) return 'Геоданные'
  if (typeof value === 'string') return value
  return 'Геоданные'
}

const valueToInput = (value: unknown, type: ColumnType): string | number => {
  if (value === null || value === undefined) return ''
  if (type === 'boolean') return Boolean(value) ? 'true' : 'false'
  if (type === 'list') {
    return normalizeArrayValue(value).join('\n')
  }
  if (type === 'geoPoint' || type === 'geoPolygon') {
    return typeof value === 'string' ? value : JSON.stringify(value, null, 2)
  }
  return typeof value === 'number' ? value : String(value)
}

const parseInputValue = (raw: string, type: ColumnType, column?: TableColumn): unknown => {
  const value = raw.trim()
  if (!value) return null

  if (type === 'number') {
    const parsed = Number(value)
    return Number.isFinite(parsed) ? parsed : value
  }

  if (type === 'boolean') {
    return value === 'true' || value === '1' || value.toLowerCase() === 'yes'
  }

  if (type === 'list') {
    if (column && isListEnumColumn(column)) {
      return normalizeArrayValue(raw)
    }
    return normalizeArrayValue(raw)
  }

  if (type === 'geoPoint' || type === 'geoPolygon') {
    try {
      return JSON.parse(value)
    } catch {
      return value
    }
  }

  return value
}

const openEditModal = (record: DataRecord) => {
  if (!props.selectedDataTable) return
  const initial: Record<string, unknown> = {}
  for (const column of props.selectedDataTable.columns) {
    if (column.type === 'list') {
      initial[column.key] = normalizeArrayValue(record.data[column.key])
      continue
    }
    if (column.type === 'geoPoint' || column.type === 'geoPolygon') {
      if (typeof record.data[column.key] === 'string') {
        try {
          initial[column.key] = JSON.parse(String(record.data[column.key]))
        } catch {
          initial[column.key] = record.data[column.key]
        }
      } else {
        initial[column.key] = record.data[column.key] ?? null
      }
      continue
    }
    initial[column.key] = valueToInput(record.data[column.key], column.type)
  }
  editValues.value = initial
  editRecordId.value = record.id
  editModalOpen.value = true
}

const closeEditModal = () => {
  editModalOpen.value = false
  editRecordId.value = null
  editValues.value = {}
  listDraftValues.value = {}
}

const ensureListField = (columnKey: string) => {
  if (!Array.isArray(editValues.value[columnKey])) {
    editValues.value[columnKey] = []
  }
}

const addListItem = (columnKey: string) => {
  const draft = String(listDraftValues.value[columnKey] ?? '').trim()
  if (!draft) return
  ensureListField(columnKey)
  const current = editValues.value[columnKey] as string[]
  if (!current.includes(draft)) {
    current.push(draft)
  }
  listDraftValues.value[columnKey] = ''
}

const removeListItem = (columnKey: string, index: number) => {
  ensureListField(columnKey)
  const current = editValues.value[columnKey] as string[]
  if (index < 0 || index >= current.length) return
  current.splice(index, 1)
}

const toggleListEnumOption = (columnKey: string, option: string, checked: boolean) => {
  ensureListField(columnKey)
  const current = editValues.value[columnKey] as string[]
  if (checked) {
    if (!current.includes(option)) current.push(option)
    return
  }
  editValues.value[columnKey] = current.filter((item) => item !== option)
}

const saveEditedRecord = () => {
  if (!props.selectedDataTable || editRecordId.value === null) return

  const parsed: Record<string, unknown> = {}
  for (const column of props.selectedDataTable.columns) {
    if (column.type === 'list') {
      parsed[column.key] = normalizeArrayValue(editValues.value[column.key])
      continue
    }

    if (column.type === 'geoPoint' || column.type === 'geoPolygon') {
      const geoRaw = editValues.value[column.key]
      if (geoRaw === null || geoRaw === undefined || geoRaw === '') {
        parsed[column.key] = null
      } else if (typeof geoRaw === 'string') {
        parsed[column.key] = parseInputValue(geoRaw, column.type, column)
      } else {
        parsed[column.key] = geoRaw
      }
      continue
    }

    const raw = String(editValues.value[column.key] ?? '')
    parsed[column.key] = parseInputValue(raw, column.type, column)
  }

  emit('save-record', { recordId: editRecordId.value, data: parsed })
  closeEditModal()
}
</script>

<template>
  <section class="data-section">
    <div class="data-header">
      <h3>{{ selectedDataTable ? selectedDataTable.name : 'Таблица' }}: Данные</h3>
      <p v-if="selectedDataTable">Показано {{ tableDataRecords.length }} из {{ dataPagination.total }} записей</p>
    </div>

    <div class="field-settings-row">
      <select v-model.number="selectedDataTableIdModel" @change="emit('data-table-change')">
        <option :value="null">Выберите таблицу</option>
        <option v-for="table in allTableOptions" :key="`data-t-${table.id}`" :value="table.id">
          {{ table.name }}
        </option>
      </select>
      <select v-model.number="dataLimitModel" @change="emit('data-limit-change')">
        <option :value="10">10 записей</option>
        <option :value="25">25 записей</option>
        <option :value="50">50 записей</option>
        <option :value="100">100 записей</option>
      </select>
      <select v-if="hasGeoColumns" v-model="geoPreviewMode">
        <option value="text">Geo: краткий текст</option>
        <option value="geojson">Geo: GeoJSON</option>
        <option value="map">Geo: карта</option>
      </select>
    </div>

    <UiStatusText v-if="dataLoading" as="div">Загрузка данных...</UiStatusText>
    <UiStatusText v-if="dataError" as="div" variant="error">{{ dataError }}</UiStatusText>

    <div v-if="tableDataRecords.length > 0 && selectedDataTable" class="data-table-wrap">
      <table class="data-table">
        <thead>
          <tr>
            <th>#</th>
            <th v-for="column in selectedDataTable.columns" :key="column.key">{{ column.name }}</th>
            <th>Отправлено</th>
            <th>Email</th>
            <th>Действие</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(record, index) in tableDataRecords" :key="record.id">
            <td>{{ dataPagination.skip + index + 1 }}</td>
            <td v-for="column in selectedDataTable.columns" :key="column.key">
              <template v-if="(column.type === 'geoPoint' || column.type === 'geoPolygon') && geoPreviewMode === 'geojson'">
                <pre class="geojson-preview" :title="toPrettyGeoJson(record.data[column.key])">{{ toPrettyGeoJson(record.data[column.key]) }}</pre>
              </template>
              <template v-else-if="(column.type === 'geoPoint' || column.type === 'geoPolygon') && geoPreviewMode === 'map'">
                <GeoJsonMapEditor
                  :model-value="record.data[column.key]"
                  :geometry-type="column.type === 'geoPoint' ? 'point' : 'polygon'"
                  :height="150"
                  readonly
                />
              </template>
              <span v-else :title="JSON.stringify(record.data[column.key])">
                {{ formatDataValue(record.data[column.key], column.type) }}
              </span>
            </td>
            <td>{{ formatDate(record.submitted_at || record.created_at || '') }}</td>
            <td>{{ record.submitter_email || '—' }}</td>
            <td class="actions-cell">
              <button class="small" @click="openEditModal(record)">Редактировать</button>
              <button class="small danger" @click="emit('delete-record', record.id)">Удалить</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <UiStatusText v-else-if="!dataLoading && selectedDataTable" class="empty-table-state" as="div">
      Нет записей в этой таблице
    </UiStatusText>

    <div v-if="totalPages > 1" class="pagination">
      <button @click="emit('go-to-page', currentPage - 1)" :disabled="currentPage === 1">← Назад</button>
      <span>Страница {{ currentPage }} из {{ totalPages }}</span>
      <button @click="emit('go-to-page', currentPage + 1)" :disabled="currentPage === totalPages">Вперёд →</button>
    </div>

    <div v-if="editModalOpen && selectedDataTable" class="edit-modal-overlay" @click.self="closeEditModal">
      <div class="edit-modal">
        <header class="edit-modal-header">
          <h4>Редактирование записи #{{ editRecordId }}</h4>
          <button class="small" @click="closeEditModal">Закрыть</button>
        </header>

        <div class="edit-modal-body">
          <div v-for="column in editableColumns" :key="`edit-${column.key}`" class="edit-field">
            <label>{{ column.name }} ({{ column.key }})</label>

            <textarea
              v-if="isTextareaColumn(column.type)"
              :value="String(editValues[column.key] ?? '')"
              rows="3"
              @input="editValues[column.key] = ($event.target as HTMLTextAreaElement).value"
            />

            <select
              v-else-if="column.type === 'boolean'"
              :value="String(editValues[column.key] ?? '')"
              @change="editValues[column.key] = ($event.target as HTMLSelectElement).value"
            >
              <option value="">Пусто</option>
              <option value="true">Да</option>
              <option value="false">Нет</option>
            </select>

            <select
              v-else-if="column.type === 'enum'"
              :value="String(editValues[column.key] ?? '')"
              @change="editValues[column.key] = ($event.target as HTMLSelectElement).value"
            >
              <option value="">Пусто</option>
              <option v-for="opt in getColumnOptions(column)" :key="`enum-${column.key}-${opt}`" :value="opt">
                {{ opt }}
              </option>
            </select>

            <div v-else-if="column.type === 'list' && isListEnumColumn(column)" class="list-edit-box">
              <label v-for="opt in getColumnOptions(column)" :key="`list-enum-${column.key}-${opt}`" class="checkbox-inline">
                <input
                  type="checkbox"
                  :checked="Array.isArray(editValues[column.key]) && editValues[column.key].includes(opt)"
                  @change="toggleListEnumOption(column.key, opt, ($event.target as HTMLInputElement).checked)"
                />
                <span>{{ opt }}</span>
              </label>
            </div>

            <div v-else-if="column.type === 'list'" class="list-edit-box">
              <div class="list-editor-add-row">
                <input
                  :value="String(listDraftValues[column.key] ?? '')"
                  placeholder="Добавить элемент"
                  @input="listDraftValues[column.key] = ($event.target as HTMLInputElement).value"
                  @keydown.enter.prevent="addListItem(column.key)"
                />
                <button class="small" type="button" @click="addListItem(column.key)">Добавить</button>
              </div>
              <ul v-if="Array.isArray(editValues[column.key]) && editValues[column.key].length > 0" class="list-items">
                <li v-for="(item, index) in editValues[column.key]" :key="`item-${column.key}-${index}`">
                  <span>{{ item }}</span>
                  <button class="small danger" type="button" @click="removeListItem(column.key, Number(index))">Удалить</button>
                </li>
              </ul>
            </div>

            <GeoJsonMapEditor
              v-else-if="column.type === 'geoPoint'"
              v-model="editValues[column.key]"
              geometry-type="point"
              :height="250"
            />

            <GeoJsonMapEditor
              v-else-if="column.type === 'geoPolygon'"
              v-model="editValues[column.key]"
              geometry-type="polygon"
              :height="250"
            />

            <input
              v-else
              :type="column.type === 'number' ? 'number' : (column.type === 'date' ? 'date' : (column.type === 'datetime' ? 'datetime-local' : 'text'))"
              :value="String(editValues[column.key] ?? '')"
              @input="editValues[column.key] = ($event.target as HTMLInputElement).value"
            />
          </div>
        </div>

        <footer class="edit-modal-footer">
          <button class="small" @click="closeEditModal">Отмена</button>
          <button class="small" @click="saveEditedRecord">Сохранить</button>
        </footer>
      </div>
    </div>
  </section>
</template>

<style scoped src="../../styles/dashboard/dashboard-data-section.css"></style>
