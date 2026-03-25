<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { ImportScanResult, ImportTargetConfig } from '../../../domain/entities/Import'
import UiSectionHeader from '../common/UiSectionHeader.vue'
import UiStatusText from '../common/UiStatusText.vue'
import DashboardTileActions from './DashboardTileActions.vue'

interface TableOption {
  id: number
  name: string
}

type ImportTargetUi = ImportTargetConfig & { localId: number }

interface ImportColumnOption {
  key: string
  name: string
}

interface ImportPreviewColumn {
  id: string
  outputKey: string
  outputName: string
  outputType: string
}

interface ImportPreviewTargetOption {
  localId: number
  label: string
}

interface ImportTargetIssue {
  sourceKey: string
  reason: string
}

const props = defineProps<{
  importScanResult: ImportScanResult | null
  importRequiresRescan: boolean
  importCanApply: boolean
  importFile: File | null
  importLoading: boolean
  importApplying: boolean
  importHeaderRowStart: number | null
  importHeaderRowEnd: number | null
  importDataRowStart: number | null
  importDataRowEnd: number | null
  importListDelimiters: string
  importTargets: ImportTargetUi[]
  allTableOptions: TableOption[]
  importSourceKeys: string[]
  importPreviewColumns: ImportPreviewColumn[]
  importPreviewRows: Record<string, string>[]
  importPreviewTargetLocalId: number | null
  importPreviewTargetOptions: ImportPreviewTargetOption[]
  importDetectedSeparators: string[]
  importVisibleSeparators: string[]
  importShowAllSeparators: boolean
  importError: string
  importSuccess: string
  importKeyMaxLength: number
  getImportTargetColumns: (target: ImportTargetUi) => ImportColumnOption[]
  formatMappedKeyPreview: (key: string | null) => string
  isMappedKeyTruncated: (key: string | null) => boolean
  onImportTargetModeChange: (target: ImportTargetUi) => void
  onImportTargetTableChange: (target: ImportTargetUi) => void
}>()

const emit = defineEmits<{
  (event: 'update:importHeaderRowStart', value: number | null): void
  (event: 'update:importHeaderRowEnd', value: number | null): void
  (event: 'update:importDataRowStart', value: number | null): void
  (event: 'update:importDataRowEnd', value: number | null): void
  (event: 'update:importListDelimiters', value: string): void
  (event: 'update:importPreviewTargetLocalId', value: number | null): void
  (event: 'import-file-change', eventObj: Event): void
  (event: 'import-scan-options-change'): void
  (event: 'refresh-import-preview'): void
  (event: 'apply-import'): void
  (event: 'toggle-separators'): void
  (event: 'add-import-target'): void
  (event: 'remove-import-target', localId: number): void
}>()

const NEW_TABLE_COLUMN_TYPES = [
  { value: 'text', label: 'text' },
  { value: 'number', label: 'number' },
  { value: 'boolean', label: 'boolean' },
  { value: 'date', label: 'date' },
  { value: 'datetime', label: 'datetime' },
  { value: 'enum', label: 'enum' },
  { value: 'list', label: 'list' },
  { value: 'geoPoint', label: 'geoPoint' },
  { value: 'geoPolygon', label: 'geoPolygon' }
]

const scanSettingsOpen = ref(false)
const activeTargetLocalId = ref<number | null>(null)

const detectedColumnsBySourceKey = computed(() =>
  Object.fromEntries((props.importScanResult?.detected_columns ?? []).map((column) => [column.source_key, column]))
)

const getDuplicateMappedKeys = (target: ImportTargetUi) => {
  const duplicateKeys = new Set<string>()
  const usedKeys = new Set<string>()

  Object.values(target.column_mappings).forEach((mappedKey) => {
    if (!mappedKey) return
    if (usedKeys.has(mappedKey)) {
      duplicateKeys.add(mappedKey)
      return
    }
    usedKeys.add(mappedKey)
  })

  return duplicateKeys
}

const getImportTargetIssues = (target: ImportTargetUi): ImportTargetIssue[] => {
  if (!props.importScanResult) return []

  if (target.mode === 'existing' && !target.table_id) {
    return props.importSourceKeys.map((sourceKey) => ({
      sourceKey,
      reason: 'Не выбрана таблица назначения'
    }))
  }

  const duplicateKeys = getDuplicateMappedKeys(target)

  return props.importSourceKeys.flatMap((sourceKey) => {
    const mappedKey = target.column_mappings[sourceKey]
    if (!mappedKey) {
      return [{ sourceKey, reason: 'Колонка будет пропущена' }]
    }

    if (duplicateKeys.has(mappedKey)) {
      return [{ sourceKey, reason: `Дублирует назначение поля "${mappedKey}"` }]
    }

    return []
  })
}

const getMappedColumnsCount = (target: ImportTargetUi) =>
  props.importSourceKeys.filter((sourceKey) => {
    const mappedKey = target.column_mappings[sourceKey]
    return typeof mappedKey === 'string' && mappedKey.trim().length > 0
  }).length

const getSkippedColumnsCount = (target: ImportTargetUi) =>
  props.importSourceKeys.length - getMappedColumnsCount(target)

const isTargetHealthy = (target: ImportTargetUi) => getImportTargetIssues(target).length === 0

const getTargetSummaryLabel = (target: ImportTargetUi) => {
  if (target.mode === 'existing') {
    const table = props.allTableOptions.find((item) => item.id === target.table_id)
    return table ? `В таблицу "${table.name}"` : 'В существующую таблицу'
  }

  return target.table_name?.trim() ? `Новая таблица "${target.table_name.trim()}"` : 'Новая таблица'
}

const activeImportTarget = computed(() =>
  props.importTargets.find((target) => target.localId === activeTargetLocalId.value) ?? props.importTargets[0] ?? null
)

const selectActiveTarget = (localId: number) => {
  activeTargetLocalId.value = localId
  emit('update:importPreviewTargetLocalId', localId)
}

const suggestTargetMapping = (target: ImportTargetUi, sourceKey: string) => {
  const detected = detectedColumnsBySourceKey.value[sourceKey]
  if (!detected) {
    return target.mode === 'new' ? sourceKey : null
  }

  if (target.mode === 'new') {
    return target.column_mappings[sourceKey] || detected.suggested_key || sourceKey
  }

  const columns = props.getImportTargetColumns(target)
  const exactByKey = columns.find((column) => column.key === detected.suggested_key)
  if (exactByKey) return exactByKey.key

  const exactByName = columns.find((column) => column.name === detected.suggested_name)
  if (exactByName) return exactByName.key

  return null
}

const isSourceColumnIncluded = (target: ImportTargetUi, sourceKey: string) =>
  Boolean(target.column_mappings[sourceKey])

const toggleSourceColumn = (target: ImportTargetUi, sourceKey: string, include: boolean) => {
  if (include) {
    const suggestedMapping = suggestTargetMapping(target, sourceKey)
    target.column_mappings[sourceKey] = suggestedMapping

    if (target.mode === 'new') {
      const detected = detectedColumnsBySourceKey.value[sourceKey]
      target.column_names = target.column_names || {}
      target.column_names[sourceKey] = target.column_names[sourceKey] || detected?.suggested_name || sourceKey
      target.column_types = target.column_types || {}
      target.column_types[sourceKey] = target.column_types[sourceKey] || detected?.suggested_type || 'text'
    }
    return
  }

  target.column_mappings[sourceKey] = null
  if (target.mode === 'new') {
    target.column_names = target.column_names || {}
    target.column_names[sourceKey] = target.column_names[sourceKey] || detectedColumnsBySourceKey.value[sourceKey]?.suggested_name || sourceKey
    target.column_types = target.column_types || {}
    target.column_types[sourceKey] = null
  }
}

const getEditableColumnName = (target: ImportTargetUi, sourceKey: string) =>
  target.column_names?.[sourceKey] || detectedColumnsBySourceKey.value[sourceKey]?.suggested_name || sourceKey

const getColumnToggleLabel = (target: ImportTargetUi, sourceKey: string) =>
  isSourceColumnIncluded(target, sourceKey) ? 'Включена' : 'Исключена'

watch(
  () => props.importTargets.map((target) => target.localId),
  (nextIds, prevIds) => {
    if (nextIds.length === 0) {
      activeTargetLocalId.value = null
      return
    }

    const currentId = activeTargetLocalId.value
    if (currentId !== null && nextIds.includes(currentId)) {
      return
    }

    const addedIds = nextIds.filter((id) => !(prevIds ?? []).includes(id))
    activeTargetLocalId.value = addedIds[0] ?? nextIds[0]
  },
  { immediate: true }
)
</script>

<template>
  <section class="import-section">
    <UiSectionHeader
      title="Импорт"
    />

    <div class="import-panel">
      <div class="import-inputs">
        <label>Файл</label>
        <input type="file" accept=".csv,.xls,.xlsx" @change="emit('import-file-change', $event)" />
      </div>

      <div class="import-advanced">
        <button class="small ghost advanced-toggle" @click="scanSettingsOpen = !scanSettingsOpen">
          {{ scanSettingsOpen ? 'Скрыть ручные настройки сканирования' : 'Проблемы со структурой? Открыть ручные настройки' }}
        </button>

        <div v-if="scanSettingsOpen" class="import-advanced-body">
          <div class="import-zones">
            <h4>Зоны поиска</h4>
            <div class="zones-grid">
              <div>
                <label>Header start</label>
                <input
                  :value="importHeaderRowStart ?? ''"
                  type="number"
                  min="0"
                  placeholder="auto"
                  @input="emit('update:importHeaderRowStart', Number(($event.target as HTMLInputElement).value) || null); emit('import-scan-options-change')"
                />
              </div>
              <div>
                <label>Header end</label>
                <input
                  :value="importHeaderRowEnd ?? ''"
                  type="number"
                  min="0"
                  placeholder="auto"
                  @input="emit('update:importHeaderRowEnd', Number(($event.target as HTMLInputElement).value) || null); emit('import-scan-options-change')"
                />
              </div>
              <div>
                <label>Data start</label>
                <input
                  :value="importDataRowStart ?? ''"
                  type="number"
                  min="0"
                  placeholder="auto"
                  @input="emit('update:importDataRowStart', Number(($event.target as HTMLInputElement).value) || null); emit('import-scan-options-change')"
                />
              </div>
              <div>
                <label>Data end</label>
                <input
                  :value="importDataRowEnd ?? ''"
                  type="number"
                  min="0"
                  placeholder="до конца"
                  @input="emit('update:importDataRowEnd', Number(($event.target as HTMLInputElement).value) || null); emit('import-scan-options-change')"
                />
              </div>
            </div>
          </div>

          <div class="import-zones">
            <h4>Списки</h4>
            <label>Разделители списка (через ;, используйте \n для новой строки)</label>
            <input
              :value="importListDelimiters"
              placeholder=",;|;\\n"
              @input="emit('update:importListDelimiters', ($event.target as HTMLInputElement).value); emit('import-scan-options-change')"
            />
          </div>
        </div>
      </div>

      <p class="import-warning" v-if="importScanResult">
        Важно: ключи колонок ограничены {{ importKeyMaxLength }} символами.
        При импорте длинные ключи автоматически сокращаются.
      </p>

      <UiStatusText v-if="importRequiresRescan">
        Параметры изменены. Обновляем распознавание файла автоматически.
      </UiStatusText>

      <UiStatusText v-if="importError" variant="error">{{ importError }}</UiStatusText>
      <UiStatusText v-if="importSuccess" variant="success">{{ importSuccess }}</UiStatusText>
    </div>

    <div v-if="importScanResult" class="import-results">
      <article class="import-card">
        <h4>Результат сканирования</h4>
        <UiStatusText>Лист: {{ importScanResult.sheet_name }} ({{ importScanResult.source_format }})</UiStatusText>
        <UiStatusText>
          Артефакты: merged cells {{ importScanResult.artifacts.merged_cells_count }},
          разделители {{ importScanResult.artifacts.sections_count }}
        </UiStatusText>
        <div v-if="importDetectedSeparators.length > 0" class="separator-artifacts">
          <UiStatusText>Найденные разделители:</UiStatusText>
          <div class="separator-list">
            <span v-for="(separator, index) in importVisibleSeparators" :key="`separator-${index}`" class="separator-pill" :title="separator">
              {{ separator }}
            </span>
          </div>
          <button v-if="importDetectedSeparators.length > 3" class="small ghost" @click="emit('toggle-separators')">
            {{ importShowAllSeparators ? 'Свернуть список' : `Показать все (${importDetectedSeparators.length})` }}
          </button>
        </div>
      </article>

      <article class="import-card">
        <div class="import-targets-head">
          <h4>Цели импорта</h4>
          <DashboardTileActions>
            <button class="small" @click="emit('add-import-target')">Добавить цель</button>
          </DashboardTileActions>
        </div>

        <UiStatusText v-if="importTargets.length === 0" as="div">Добавьте цель импорта.</UiStatusText>

        <div v-if="importTargets.length > 0" class="import-target-switcher">
          <button
            v-for="(target, index) in importTargets"
            :key="`target-tab-${target.localId}`"
            class="target-tab"
            :class="{ active: activeImportTarget?.localId === target.localId, warning: !isTargetHealthy(target) }"
            @click="selectActiveTarget(target.localId)"
          >
            <span>Цель {{ index + 1 }}</span>
            <strong>{{ getTargetSummaryLabel(target) }}</strong>
          </button>
        </div>

        <div v-for="target in activeImportTarget ? [activeImportTarget] : []" :key="`active-target-${target.localId}`" class="import-target">
          <div class="import-target-summary">
            <div>
              <strong>{{ getTargetSummaryLabel(target) }}</strong>
              <p class="muted">
                {{
                  isTargetHealthy(target)
                    ? 'Автосопоставление готово. Можно импортировать без ручной правки.'
                    : `Нужно проверить ${getImportTargetIssues(target).length} ${getImportTargetIssues(target).length === 1 ? 'поле' : 'полей'}.`
                }}
              </p>
            </div>
            <div class="import-summary-stats">
              <span class="summary-pill ok">Сопоставлено: {{ getMappedColumnsCount(target) }}</span>
              <span class="summary-pill" :class="{ warning: getSkippedColumnsCount(target) > 0 }">
                Пропущено: {{ getSkippedColumnsCount(target) }}
              </span>
              <span class="summary-pill" :class="{ warning: getImportTargetIssues(target).length > 0 }">
                Требует внимания: {{ getImportTargetIssues(target).length }}
              </span>
            </div>
          </div>

          <div class="import-target-row">
            <label>Режим</label>
            <select v-model="target.mode" @change="onImportTargetModeChange(target)">
              <option value="existing">В существующую таблицу</option>
              <option value="new">Создать новую таблицу</option>
            </select>
            <button class="small danger" @click="emit('remove-import-target', target.localId)">Удалить цель</button>
          </div>

          <div v-if="target.mode === 'existing'" class="import-target-row">
            <label>Таблица</label>
            <select v-model.number="target.table_id" @change="onImportTargetTableChange(target)">
              <option :value="null">Выберите таблицу</option>
              <option v-for="table in allTableOptions" :key="`imp-target-${target.localId}-${table.id}`" :value="table.id">
                {{ table.name }}
              </option>
            </select>
          </div>

          <div v-else class="import-target-row import-target-grid">
            <div>
              <label>Название новой таблицы</label>
              <input v-model="target.table_name" placeholder="Например: Импорт товаров" />
            </div>
            <div>
              <label>Описание</label>
              <input v-model="target.table_description" placeholder="Описание новой таблицы" />
            </div>
          </div>

          <div class="import-target-row import-target-grid">
            <label class="checkbox-inline">
              <input v-model="target.map_section_to_field" type="checkbox" />
              Добавить отдельный столбец "разделитель" и заполнить его значением разделителя
            </label>
            <div v-if="target.map_section_to_field">
              <label>Имя столбца разделителя</label>
              <input v-model="target.section_field_name" placeholder="Разделитель" />
            </div>
          </div>

        </div>
      </article>

      <article class="import-card import-preview-card" v-if="importScanResult && activeImportTarget">
        <div class="import-preview-head">
          <div>
            <h4>Превью таблицы</h4>
          </div>
        </div>
        <UiStatusText v-if="importSourceKeys.length === 0" as="div">
          Нет колонок для предпросмотра.
        </UiStatusText>
        <div v-else class="data-table-wrap import-preview-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th>#</th>
                <th
                  v-for="sourceKey in importSourceKeys"
                  :key="`preview-head-${sourceKey}`"
                  :class="{ inactive: !isSourceColumnIncluded(activeImportTarget, sourceKey) }"
                >
                  <div class="preview-header-title" :class="{ excluded: !isSourceColumnIncluded(activeImportTarget, sourceKey) }">
                    <strong>{{ sourceKey }}</strong>
                    <span class="muted">Исходный тип: {{ detectedColumnsBySourceKey[sourceKey]?.suggested_type || 'text' }}</span>
                  </div>
                </th>
              </tr>
              <tr class="preview-controls-row">
                <th>Настройки</th>
                <th
                  v-for="sourceKey in importSourceKeys"
                  :key="`preview-controls-${sourceKey}`"
                  :class="{ inactive: !isSourceColumnIncluded(activeImportTarget, sourceKey) }"
                >
                  <div class="preview-column-editor">
                    <button
                      type="button"
                      class="column-toggle-button"
                      :class="{ included: isSourceColumnIncluded(activeImportTarget, sourceKey), excluded: !isSourceColumnIncluded(activeImportTarget, sourceKey) }"
                      @click="toggleSourceColumn(activeImportTarget, sourceKey, !isSourceColumnIncluded(activeImportTarget, sourceKey))"
                    >
                      {{ getColumnToggleLabel(activeImportTarget, sourceKey) }}
                    </button>

                    <template v-if="activeImportTarget.mode === 'existing'">
                      <label class="preview-control-label">Куда сохранить</label>
                      <select v-model="activeImportTarget.column_mappings[sourceKey]">
                        <option :value="null">Не импортировать</option>
                        <option
                          v-for="column in getImportTargetColumns(activeImportTarget)"
                          :key="`preview-map-col-${activeImportTarget.localId}-${sourceKey}-${column.key}`"
                          :value="column.key"
                        >
                          {{ column.name }} ({{ column.key }})
                        </option>
                      </select>
                    </template>

                    <template v-else>
                      <label class="preview-control-label">Название колонки</label>
                      <input
                        :value="getEditableColumnName(activeImportTarget, sourceKey)"
                        placeholder="Название колонки"
                        @input="activeImportTarget.column_names = activeImportTarget.column_names || {}; activeImportTarget.column_names[sourceKey] = ($event.target as HTMLInputElement).value"
                      />
                      <label class="preview-control-label">Тип данных</label>
                      <select
                        :value="activeImportTarget.column_types?.[sourceKey] || detectedColumnsBySourceKey[sourceKey]?.suggested_type || 'text'"
                        @change="activeImportTarget.column_types = activeImportTarget.column_types || {}; activeImportTarget.column_types[sourceKey] = ($event.target as HTMLSelectElement).value"
                      >
                        <option
                          v-for="typeOption in NEW_TABLE_COLUMN_TYPES"
                          :key="`preview-type-${sourceKey}-${typeOption.value}`"
                          :value="typeOption.value"
                        >
                          {{ typeOption.label }}
                        </option>
                      </select>
                      <span class="muted preview-column-key">
                        key: {{ formatMappedKeyPreview(activeImportTarget.column_mappings[sourceKey]) }}
                      </span>
                    </template>
                  </div>
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, rowIndex) in importScanResult.preview_rows.slice(0, 30)" :key="`preview-row-${rowIndex}`">
                <td>{{ rowIndex + 1 }}</td>
                <td
                  v-for="sourceKey in importSourceKeys"
                  :key="`preview-cell-${rowIndex}-${sourceKey}`"
                  :class="{ inactive: !isSourceColumnIncluded(activeImportTarget, sourceKey) }"
                >
                  <span :title="String(row[sourceKey] ?? '—')">
                    {{ row[sourceKey] ?? '—' }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="import-final-actions">
          <UiStatusText as="div">
            Проверьте, какие колонки включены, как они будут называться и куда сохранятся. После этого запускайте импорт.
          </UiStatusText>
          <DashboardTileActions>
            <button class="small" :disabled="!importCanApply || importApplying" @click="emit('apply-import')">
              {{ importApplying ? 'Импорт...' : 'Запустить импорт' }}
            </button>
          </DashboardTileActions>
        </div>
      </article>
    </div>
  </section>
</template>

<style scoped src="../../styles/dashboard/dashboard-import-section.css"></style>
