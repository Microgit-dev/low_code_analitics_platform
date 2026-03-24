<script setup lang="ts">
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
  importPreviewRows: Record<string, unknown>[]
  importDetectedSeparators: string[]
  importVisibleSeparators: string[]
  importShowAllSeparators: boolean
  importError: string
  importSuccess: string
  importKeyMaxLength: number
  getImportTargetColumns: (target: ImportTargetUi) => ImportColumnOption[]
  formatMappedKeyPreview: (key: string | null) => string
  isMappedKeyTruncated: (key: string | null) => boolean
  formatImportValue: (value: unknown) => string
  onImportTargetModeChange: (target: ImportTargetUi) => void
  onImportTargetTableChange: (target: ImportTargetUi) => void
}>()

const emit = defineEmits<{
  (event: 'update:importHeaderRowStart', value: number | null): void
  (event: 'update:importHeaderRowEnd', value: number | null): void
  (event: 'update:importDataRowStart', value: number | null): void
  (event: 'update:importDataRowEnd', value: number | null): void
  (event: 'update:importListDelimiters', value: string): void
  (event: 'import-file-change', eventObj: Event): void
  (event: 'import-scan-options-change'): void
  (event: 'scan-import'): void
  (event: 'apply-import'): void
  (event: 'toggle-separators'): void
  (event: 'add-import-target'): void
  (event: 'remove-import-target', localId: number): void
}>()
</script>

<template>
  <section class="import-section">
    <UiSectionHeader
      title="Импорт"
      description="Загрузите файл, просканируйте структуру, затем сопоставьте колонки и выполните импорт."
    />

    <div class="import-panel">
      <div class="import-flow">
        <span class="flow-step" :class="{ active: !!importScanResult, warning: importRequiresRescan }">
          Шаг 1: Сканирование
        </span>
        <span class="flow-step" :class="{ active: importCanApply }">
          Шаг 2: Загрузка в систему
        </span>
      </div>

      <div class="import-inputs">
        <label>Файл</label>
        <input type="file" accept=".csv,.xls,.xlsx" @change="emit('import-file-change', $event)" />
      </div>

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

      <p class="import-warning" v-if="importScanResult">
        Важно: ключи колонок ограничены {{ importKeyMaxLength }} символами.
        При импорте длинные ключи автоматически сокращаются.
      </p>

      <DashboardTileActions>
        <button class="small" :disabled="!importFile || importLoading" @click="emit('scan-import')">
          {{ importLoading ? 'Сканирование...' : 'Сканировать файл' }}
        </button>
        <button class="small" :disabled="!importCanApply || importApplying" @click="emit('apply-import')">
          {{ importApplying ? 'Импорт...' : 'Запустить импорт' }}
        </button>
      </DashboardTileActions>

      <UiStatusText v-if="importRequiresRescan">
        Параметры сканирования изменены. Выполните шаг 1 повторно перед загрузкой.
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
          <button class="small" @click="emit('add-import-target')">Добавить цель</button>
        </div>

        <UiStatusText v-if="importTargets.length === 0" as="div">Добавьте цель импорта.</UiStatusText>

        <div v-for="target in importTargets" :key="target.localId" class="import-target">
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

          <div class="mapping-grid" v-if="importSourceKeys.length > 0">
            <div v-for="sourceKey in importSourceKeys" :key="`map-${target.localId}-${sourceKey}`" class="mapping-row">
              <strong>{{ sourceKey }}</strong>

              <select v-if="target.mode === 'existing'" v-model="target.column_mappings[sourceKey]">
                <option :value="null">Не импортировать</option>
                <option v-for="column in getImportTargetColumns(target)" :key="`map-col-${target.localId}-${column.key}`" :value="column.key">
                  {{ column.name }} ({{ column.key }})
                </option>
              </select>

              <input
                v-else
                v-model="target.column_mappings[sourceKey]"
                :placeholder="`Ключ колонки (например ${sourceKey})`"
              />

              <p v-if="target.mode === 'new'" class="mapping-hint">
                Итоговый ключ: <strong>{{ formatMappedKeyPreview(target.column_mappings[sourceKey]) }}</strong>
                <span v-if="isMappedKeyTruncated(target.column_mappings[sourceKey])" class="mapping-warning">
                  (будет сокращен до {{ importKeyMaxLength }} символов)
                </span>
              </p>
            </div>
          </div>
        </div>
      </article>

      <article class="import-card import-preview-card" v-if="importPreviewRows.length > 0">
        <h4>Превью данных</h4>
        <div class="data-table-wrap import-preview-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th>#</th>
                <th v-for="sourceKey in importSourceKeys" :key="`preview-head-${sourceKey}`">{{ sourceKey }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, rowIndex) in importPreviewRows" :key="`preview-row-${rowIndex}`">
                <td>{{ rowIndex + 1 }}</td>
                <td v-for="sourceKey in importSourceKeys" :key="`preview-cell-${rowIndex}-${sourceKey}`">
                  <span :title="formatImportValue(row[sourceKey])">
                    {{ formatImportValue(row[sourceKey]) }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </article>
    </div>
  </section>
</template>

<style scoped src="../../styles/dashboard/dashboard-import-section.css"></style>
