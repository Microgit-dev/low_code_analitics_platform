<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { FormBuilderUseCase } from '../../application/usecases/FormBuilderUseCase'
import { ImportUseCase } from '../../application/usecases/ImportUseCase'
import { ReportUseCase } from '../../application/usecases/ReportUseCase'
import { TableSchemaUseCase } from '../../application/usecases/TableSchemaUseCase'
import { WorkspaceUseCase } from '../../application/usecases/WorkspaceUseCase'
import type { Workspace } from '../../domain/entities/Auth'
import type { ImportApplyConfig, ImportScanResult, ImportTargetConfig } from '../../domain/entities/Import'
import type { ColumnType, TableRelation, TableStructure } from '../../domain/entities/TableSchema'
import type { FormConfiguration, FormField, WidgetType } from '../../domain/entities/FormBuilder'
import type { DashboardChartConfig, DashboardMetricConfig, ReportConfiguration, ReportType } from '../../domain/entities/Report'
import { useAuthStore } from '../stores/authStore'

const authStore = useAuthStore()
const router = useRouter()
const workspaceUseCase = new WorkspaceUseCase()
const tableSchemaUseCase = new TableSchemaUseCase()
const formBuilderUseCase = new FormBuilderUseCase(authStore.token || '')
const importUseCase = new ImportUseCase()
const reportUseCase = new ReportUseCase(authStore.token || '')

type WorkspaceTab = 'details' | 'tables' | 'forms' | 'data' | 'import' | 'reports'
type TablePosition = { x: number; y: number }
type ImportTargetUi = ImportTargetConfig & { localId: number }

const workspaces = ref<Workspace[]>([])
const loading = ref(false)
const deleting = ref(false)
const schemaLoading = ref(false)
const schemaError = ref('')
const workspaceTab = ref<WorkspaceTab>('tables')

const workspaceName = ref('')
const workspaceDescription = ref('')
const selectedWorkspaceId = ref<number | null>(null)

const tableStructures = ref<TableStructure[]>([])
const relations = ref<TableRelation[]>([])
const activeTableId = ref<number | null>(null)
const selectedColumnRef = ref<{ tableId: number; columnKey: string } | null>(null)
const tablePositions = ref<Record<number, TablePosition>>({})
const tableDragging = ref<{ tableId: number; offsetX: number; offsetY: number } | null>(null)

const newTableName = ref('')
const newTableDescription = ref('')

const newColumnName = ref('')
const newColumnType = ref<ColumnType>('text')
const newColumnRequired = ref(false)
const newColumnEnumOptions = ref('')
const newColumnListItemType = ref<'text' | 'number' | 'boolean' | 'enum'>('text')
const newColumnNumberIsId = ref(false)
const newColumnNumberAutoIncrement = ref(false)
const newColumnNumberStart = ref(1)
const newColumnNumberStep = ref(1)
const newColumnGeoSrid = ref(4326)
const newColumnGeoAllowHoles = ref(false)

const relationName = ref('')
const relationSourceTableId = ref('')
const relationTargetTableId = ref('')
const relationType = ref<'one_to_one' | 'one_to_many' | 'many_to_many'>('one_to_many')
const relationSourceColumn = ref('')
const relationTargetColumn = ref('')

const dragState = ref<{ sourceTableId: number; columnKey: string } | null>(null)

// Form Builder state
const formConfigurations = ref<FormConfiguration[]>([])
const selectedFormId = ref<number | null>(null)
const formEditorOpen = ref(false)
const formLoading = ref(false)
const formError = ref('')
const formFieldDragIndex = ref<number | null>(null)
const selectedFormFieldIndex = ref<number | null>(null)
const formTableSelection = ref<number[]>([])
const addFieldTableId = ref('')
const addFieldColumnKey = ref('')
const newWidgetOption = ref('')

// Data Viewer state
const tableDataRecords = ref<any[]>([])
const dataLoading = ref(false)
const dataError = ref('')
const dataPagination = ref({ skip: 0, limit: 50, total: 0 })
const selectedDataTableId = ref<number | null>(null)

// Import state
const importFile = ref<File | null>(null)
const importLoading = ref(false)
const importApplying = ref(false)
const importError = ref('')
const importSuccess = ref('')
const importScanResult = ref<ImportScanResult | null>(null)
const importHeaderRowStart = ref<number | null>(null)
const importHeaderRowEnd = ref<number | null>(null)
const importDataRowStart = ref<number | null>(null)
const importDataRowEnd = ref<number | null>(null)
const importListDelimiters = ref(',;|\\n')
const importTargets = ref<ImportTargetUi[]>([])
const importTargetSeq = ref(1)
const importShowAllSeparators = ref(false)
const importRequiresRescan = ref(false)
const IMPORT_KEY_MAX_LENGTH = 64

// Reports state
const reports = ref<ReportConfiguration[]>([])
const reportsLoading = ref(false)
const reportsError = ref('')
const selectedReportId = ref<number | null>(null)

const reportEditorOpen = ref(false)
const reportName = ref('')
const reportDescription = ref('')
const reportType = ref<ReportType>('excel_export')
const reportIsPublished = ref(false)
const reportTableId = ref<number | null>(null)
const reportRecentLimit = ref(10)
const reportExcelColumns = ref<Array<{ key: string; label: string; enabled: boolean }>>([])
const reportMetrics = ref<DashboardMetricConfig[]>([])
const reportCharts = ref<DashboardChartConfig[]>([])
const templateModalOpen = ref(false)
const templateTableId = ref<number | null>(null)
const templateDragActive = ref(false)
const templateUploading = ref(false)
const templateError = ref('')
const templateFileName = ref('')
const templateFileInput = ref<HTMLInputElement | null>(null)

const selectedWorkspace = computed(() => {
  if (selectedWorkspaceId.value === null) return null
  return workspaces.value.find((workspace) => workspace.id === selectedWorkspaceId.value) ?? null
})

const activeTable = computed(() => {
  if (activeTableId.value === null) return null
  return tableStructures.value.find((table) => table.id === activeTableId.value) ?? null
})

const selectedDataTable = computed(() => {
  if (selectedDataTableId.value === null) return null
  return tableStructures.value.find((table) => table.id === selectedDataTableId.value) ?? null
})

const selectedReport = computed(() => {
  if (selectedReportId.value === null) return null
  return reports.value.find((report) => report.id === selectedReportId.value) ?? null
})

const selectedReportTable = computed(() => {
  if (reportTableId.value === null) return null
  return tableStructures.value.find((table) => table.id === reportTableId.value) ?? null
})

const importSourceKeys = computed(() => importScanResult.value?.detected_columns.map((col) => col.source_key) ?? [])
const importPreviewRows = computed(() => (importScanResult.value?.preview_rows ?? []).slice(0, 30))
const importDetectedSeparators = computed(() => importScanResult.value?.artifacts.detected_sections ?? [])
const importVisibleSeparators = computed(() =>
  importShowAllSeparators.value ? importDetectedSeparators.value : importDetectedSeparators.value.slice(0, 3)
)
const importCanApply = computed(
  () => Boolean(importFile.value) && Boolean(importScanResult.value) && !importRequiresRescan.value
)

const selectedColumnParent = computed(() => {
  if (selectedColumnRef.value === null) return null
  return tableStructures.value.find((table) => table.id === selectedColumnRef.value?.tableId) ?? null
})

const selectedColumn = computed(() => {
  if (selectedColumnRef.value === null) return null
  const parent = selectedColumnParent.value
  if (!parent) return null
  return parent.columns.find((column) => column.key === selectedColumnRef.value?.columnKey) ?? null
})

const allTableOptions = computed(() => tableStructures.value.map((table) => ({ id: table.id, name: table.name })))

const allWorkspaceColumns = computed(() =>
  tableStructures.value.flatMap((table) =>
    table.columns.map((column) => ({
      tableId: table.id,
      tableName: table.name,
      column
    }))
  )
)

const selectedFormField = computed(() => {
  if (!selectedForm.value || selectedFormFieldIndex.value === null) return null
  return selectedForm.value.fields[selectedFormFieldIndex.value] ?? null
})

const addFieldCandidates = computed(() => {
  const tableId = Number(addFieldTableId.value)
  if (!tableId || !selectedForm.value) return []
  if (!formTableSelection.value.includes(tableId)) return []

  const existing = new Set(
    selectedForm.value.fields.map((field) => `${field.table_id ?? activeTable.value?.id ?? 0}:${field.column_key}`)
  )

  const table = tableStructures.value.find((item) => item.id === tableId)
  if (!table) return []

  return table.columns.filter((column) => !existing.has(`${tableId}:${column.key}`))
})

const relationSourceColumns = computed(() => {
  const sourceId = Number(relationSourceTableId.value)
  if (!sourceId) return []
  return tableStructures.value.find((table) => table.id === sourceId)?.columns ?? []
})

const relationTargetColumns = computed(() => {
  const targetId = Number(relationTargetTableId.value)
  if (!targetId) return []
  return tableStructures.value.find((table) => table.id === targetId)?.columns ?? []
})

const loadWorkspaces = async () => {
  if (!authStore.token) return
  loading.value = true
  try {
    await authStore.fetchMe()
    workspaces.value = await workspaceUseCase.list(authStore.token)
    if (workspaces.value.length > 0) {
      const selectedExists = workspaces.value.some((workspace) => workspace.id === selectedWorkspaceId.value)
      selectedWorkspaceId.value = selectedExists ? selectedWorkspaceId.value : workspaces.value[0].id
    } else {
      selectedWorkspaceId.value = null
    }
  } finally {
    loading.value = false
  }
}

const loadSchema = async () => {
  if (!authStore.token || !selectedWorkspace.value) {
    tableStructures.value = []
    relations.value = []
    activeTableId.value = null
    selectedColumnRef.value = null
    tablePositions.value = {}
    return
  }

  schemaLoading.value = true
  schemaError.value = ''
  try {
    tableStructures.value = await tableSchemaUseCase.listTables(authStore.token, selectedWorkspace.value.id)
    relations.value = await tableSchemaUseCase.listRelations(authStore.token, selectedWorkspace.value.id)
    if (tableStructures.value.length > 0) {
      const hasActive = tableStructures.value.some((table) => table.id === activeTableId.value)
      activeTableId.value = hasActive ? activeTableId.value : tableStructures.value[0].id
    } else {
      activeTableId.value = null
    }

    if (selectedColumnRef.value) {
      const parent = tableStructures.value.find((table) => table.id === selectedColumnRef.value?.tableId)
      const hasColumn = parent?.columns.some((column) => column.key === selectedColumnRef.value?.columnKey)
      if (!hasColumn) {
        selectedColumnRef.value = null
      }
    }

    if (selectedDataTableId.value !== null) {
      const hasDataTable = tableStructures.value.some((table) => table.id === selectedDataTableId.value)
      if (!hasDataTable) {
        selectedDataTableId.value = activeTableId.value
      }
    }

    if (reportTableId.value !== null) {
      const hasReportTable = tableStructures.value.some((table) => table.id === reportTableId.value)
      if (!hasReportTable) {
        reportTableId.value = activeTableId.value
        syncReportColumnsWithSelectedTable()
      }
    }

    const nextPositions: Record<number, TablePosition> = {}
    for (const [index, table] of tableStructures.value.entries()) {
      nextPositions[table.id] = tablePositions.value[table.id] ?? {
        x: 36 + (index % 3) * 310,
        y: 36 + Math.floor(index / 3) * 260
      }
    }
    tablePositions.value = nextPositions
  } catch {
    schemaError.value = 'Не удалось загрузить low-code структуры.'
  } finally {
    schemaLoading.value = false
  }
}

const createWorkspace = async () => {
  if (!authStore.token || !workspaceName.value.trim()) return

  await workspaceUseCase.create(authStore.token, workspaceName.value.trim(), workspaceDescription.value.trim())
  workspaceName.value = ''
  workspaceDescription.value = ''
  await loadWorkspaces()
  await loadSchema()
}

const deleteWorkspace = async () => {
  if (!authStore.token || !selectedWorkspace.value || deleting.value) return

  const shouldDelete = window.confirm(
    `Удалить workspace \"${selectedWorkspace.value.name}\"? Это действие нельзя отменить.`
  )
  if (!shouldDelete) return

  deleting.value = true
  try {
    await workspaceUseCase.delete(authStore.token, selectedWorkspace.value.id)
    await loadWorkspaces()
    await loadSchema()
  } finally {
    deleting.value = false
  }
}

const selectWorkspace = async (workspaceId: number) => {
  selectedWorkspaceId.value = workspaceId
  workspaceTab.value = 'tables'
  importFile.value = null
  importScanResult.value = null
  importTargets.value = []
  importError.value = ''
  importSuccess.value = ''
  await loadSchema()
}

const selectTable = (tableId: number) => {
  activeTableId.value = tableId
  selectedColumnRef.value = null
  if (workspaceTab.value === 'forms') {
    void loadForms()
  }
}

const selectColumn = (tableId: number, columnKey: string) => {
  activeTableId.value = tableId
  selectedColumnRef.value = { tableId, columnKey }
}

const getTablePosition = (tableId: number): TablePosition => {
  const fallback = { x: 40, y: 40 }
  if (!tablePositions.value[tableId]) {
    tablePositions.value[tableId] = fallback
  }
  return tablePositions.value[tableId] ?? fallback
}

const onCanvasPointerMove = (event: PointerEvent) => {
  const drag = tableDragging.value
  if (!drag) return

  tablePositions.value = {
    ...tablePositions.value,
    [drag.tableId]: {
      x: Math.max(16, event.clientX - drag.offsetX),
      y: Math.max(16, event.clientY - drag.offsetY)
    }
  }
}

const stopTableDrag = () => {
  tableDragging.value = null
}

const onTableGripPointerDown = (event: PointerEvent, tableId: number) => {
  const position = getTablePosition(tableId)
  tableDragging.value = {
    tableId,
    offsetX: event.clientX - position.x,
    offsetY: event.clientY - position.y
  }
  selectTable(tableId)
}

const saveSelectedColumn = async () => {
  const parent = selectedColumnParent.value
  if (!parent) return
  await saveTable(parent)
}

const createTable = async () => {
  if (!authStore.token || !selectedWorkspace.value || !newTableName.value.trim()) return

  await tableSchemaUseCase.createTable(authStore.token, selectedWorkspace.value.id, {
    name: newTableName.value.trim(),
    description: newTableDescription.value.trim() || null,
    columns: []
  })
  newTableName.value = ''
  newTableDescription.value = ''
  await loadSchema()
}

const saveTable = async (table: TableStructure) => {
  if (!authStore.token || !selectedWorkspace.value) return
  await tableSchemaUseCase.updateTable(authStore.token, selectedWorkspace.value.id, table.id, {
    name: table.name,
    description: table.description,
    columns: table.columns
  })
  await loadSchema()
}

const deleteActiveTable = async () => {
  if (!authStore.token || !selectedWorkspace.value || !activeTable.value) return

  const shouldDelete = window.confirm(
    `Удалить таблицу "${activeTable.value.name}"? Это действие удалит связанные данные.`
  )
  if (!shouldDelete) return

  await tableSchemaUseCase.deleteTable(authStore.token, selectedWorkspace.value.id, activeTable.value.id)
  selectedColumnRef.value = null
  await loadSchema()
}

const slugify = (value: string): string =>
  value
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9а-я]+/gi, '_')
    .replace(/^_+|_+$/g, '')
    .slice(0, 60)

const buildColumnSettings = (): Record<string, unknown> => {
  if (newColumnType.value === 'number') {
    const settings: Record<string, unknown> = {
      autoIncrement: newColumnNumberAutoIncrement.value,
      autoIncrementStart: Math.max(1, Number(newColumnNumberStart.value) || 1),
      autoIncrementStep: Math.max(1, Number(newColumnNumberStep.value) || 1)
    }
    if (newColumnNumberIsId.value) {
      settings.isId = true
    }
    return settings
  }

  if (newColumnType.value === 'enum') {
    return {
      options: newColumnEnumOptions.value
        .split(',')
        .map((item) => item.trim())
        .filter(Boolean)
    }
  }

  if (newColumnType.value === 'list') {
    const settings: Record<string, unknown> = {
      itemType: newColumnListItemType.value
    }
    if (newColumnListItemType.value === 'enum') {
      settings.options = newColumnEnumOptions.value
        .split(',')
        .map((item) => item.trim())
        .filter(Boolean)
    }
    return settings
  }

  if (newColumnType.value === 'geoPoint') {
    return { srid: Number(newColumnGeoSrid.value) || 4326 }
  }

  if (newColumnType.value === 'geoPolygon') {
    return {
      srid: Number(newColumnGeoSrid.value) || 4326,
      allowHoles: newColumnGeoAllowHoles.value
    }
  }

  return {}
}

const addColumnToActiveTable = async () => {
  if (!activeTable.value || !newColumnName.value.trim()) return

  const baseKey = slugify(newColumnName.value)
  const fallbackKey = baseKey || `column_${Date.now()}`
  let key = fallbackKey
  let index = 2
  while (activeTable.value.columns.some((col) => col.key === key)) {
    key = `${fallbackKey}_${index}`
    index += 1
  }

  activeTable.value.columns.push({
    key,
    name: newColumnName.value.trim(),
    type: newColumnType.value,
    required: newColumnRequired.value,
    settings: buildColumnSettings()
  })

  newColumnName.value = ''
  newColumnType.value = 'text'
  newColumnRequired.value = false
  newColumnEnumOptions.value = ''
  newColumnListItemType.value = 'text'
  newColumnNumberIsId.value = false
  newColumnNumberAutoIncrement.value = false
  newColumnNumberStart.value = 1
  newColumnNumberStep.value = 1
  newColumnGeoSrid.value = 4326
  newColumnGeoAllowHoles.value = false

  await saveTable(activeTable.value)
}

const removeColumnFromActiveTable = async (columnKey: string) => {
  if (!activeTable.value) return
  activeTable.value.columns = activeTable.value.columns.filter((column) => column.key !== columnKey)
  if (selectedColumnRef.value?.columnKey === columnKey && selectedColumnRef.value.tableId === activeTable.value.id) {
    selectedColumnRef.value = null
  }
  await saveTable(activeTable.value)
}

const getSelectedNumberSetting = <T,>(key: string, fallback: T): T => {
  if (!selectedColumn.value || selectedColumn.value.type !== 'number') return fallback
  const raw = selectedColumn.value.settings?.[key]
  if (typeof fallback === 'boolean') {
    return (Boolean(raw) as T)
  }
  if (typeof fallback === 'number') {
    return ((typeof raw === 'number' ? raw : fallback) as T)
  }
  return fallback
}

const setSelectedNumberSetting = (key: string, value: unknown) => {
  if (!selectedColumn.value || selectedColumn.value.type !== 'number') return
  selectedColumn.value.settings = {
    ...(selectedColumn.value.settings ?? {}),
    [key]: value
  }
}

const onNewColumnNumberIsIdChange = (checked: boolean) => {
  newColumnNumberIsId.value = checked
  if (checked) {
    newColumnNumberAutoIncrement.value = true
    newColumnRequired.value = true
  }
}

const onSelectedColumnIsIdChange = (checked: boolean) => {
  setSelectedNumberSetting('isId', checked)
  if (checked) {
    setSelectedNumberSetting('autoIncrement', true)
    if (selectedColumn.value) {
      selectedColumn.value.required = true
    }
  }
}

const startDraggingColumn = (sourceTableId: number, columnKey: string) => {
  dragState.value = { sourceTableId, columnKey }
}

const onDropColumnToTable = async (targetTableId: number) => {
  if (!authStore.token || !selectedWorkspace.value || dragState.value === null) return

  const sourceTableId = dragState.value.sourceTableId
  const columnKey = dragState.value.columnKey
  dragState.value = null

  if (sourceTableId === targetTableId) return

  await tableSchemaUseCase.moveColumn(authStore.token, selectedWorkspace.value.id, sourceTableId, targetTableId, columnKey)
  await loadSchema()
}

const createRelation = async () => {
  if (!authStore.token || !selectedWorkspace.value) return
  const sourceTableId = Number(relationSourceTableId.value)
  const targetTableId = Number(relationTargetTableId.value)

  if (!relationName.value.trim() || !sourceTableId || !targetTableId) return
  if (!relationSourceColumn.value.trim() || !relationTargetColumn.value.trim()) return

  await tableSchemaUseCase.createRelation(authStore.token, selectedWorkspace.value.id, {
    name: relationName.value.trim(),
    source_table_id: sourceTableId,
    target_table_id: targetTableId,
    relation_type: relationType.value,
    mapping: { [relationSourceColumn.value.trim()]: relationTargetColumn.value.trim() },
    properties: {}
  })

  relationName.value = ''
  relationSourceTableId.value = ''
  relationTargetTableId.value = ''
  relationSourceColumn.value = ''
  relationTargetColumn.value = ''
  await loadSchema()
}

const deleteRelation = async (relationId: number) => {
  if (!authStore.token || !selectedWorkspace.value) return
  await tableSchemaUseCase.deleteRelation(authStore.token, selectedWorkspace.value.id, relationId)
  await loadSchema()
}

const loadForms = async () => {
  if (!authStore.token || !selectedWorkspace.value) {
    formConfigurations.value = []
    selectedFormId.value = null
    selectedFormFieldIndex.value = null
    formTableSelection.value = []
    return
  }

  formLoading.value = true
  formError.value = ''
  try {
    formConfigurations.value = await formBuilderUseCase.listForms(selectedWorkspace.value.id)

    if (formConfigurations.value.length === 0) {
      selectedFormId.value = null
      selectedFormFieldIndex.value = null
      formTableSelection.value = []
      formEditorOpen.value = false
      return
    }

    const selectedExists = formConfigurations.value.some((form) => form.id === selectedFormId.value)
    selectedFormId.value = selectedExists ? selectedFormId.value : formConfigurations.value[0].id
    syncFormTableSelectionFromSelected()
    selectedFormFieldIndex.value = selectedForm.value?.fields.length ? 0 : null
  } catch (error) {
    formError.value = 'Не удалось загрузить формы'
    console.error(error)
  } finally {
    formLoading.value = false
  }
}

const selectedForm = computed(() => {
  if (!selectedFormId.value) return null
  return formConfigurations.value.find((f) => f.id === selectedFormId.value) ?? null
})

const getFormUsedTableIds = (form: FormConfiguration): number[] => {
  const ids = new Set<number>()
  if (typeof form.table_id === 'number') {
    ids.add(form.table_id)
  }
  for (const field of form.fields) {
    if (typeof field.table_id === 'number') {
      ids.add(field.table_id)
    }
  }
  return [...ids]
}

const getFormUsedTableNames = (form: FormConfiguration): string => {
  const names = getFormUsedTableIds(form)
    .map((tableId) => tableStructures.value.find((table) => table.id === tableId)?.name)
    .filter((name): name is string => Boolean(name))

  if (names.length === 0) return 'Таблицы не выбраны'
  return names.join(', ')
}

const syncFormTableSelectionFromSelected = () => {
  if (!selectedForm.value) {
    formTableSelection.value = []
    return
  }

  const ids = getFormUsedTableIds(selectedForm.value)
  if (ids.length > 0) {
    formTableSelection.value = ids
    return
  }

  const fallback = activeTable.value?.id ?? tableStructures.value[0]?.id
  formTableSelection.value = typeof fallback === 'number' ? [fallback] : []
}

const selectForm = (formId: number) => {
  selectedFormId.value = formId
  selectedFormFieldIndex.value = selectedForm.value?.fields.length ? 0 : null
  syncFormTableSelectionFromSelected()
  formEditorOpen.value = true
}

const getWidgetTypeLabel = (type: string): string => {
  const labels: Record<string, string> = {
    text_input: 'Текстовое поле',
    textarea: 'Многострочный текст',
    number_input: 'Числовое поле',
    date_input: 'Дата',
    datetime_input: 'Дата и время',
    select: 'Выпадающий список',
    multiselect: 'Множественный выбор',
    list_input: 'Список значений',
    checkbox: 'Чекбокс',
    radio: 'Радио'
  }
  return labels[type] || type
}

const getFieldTableName = (field: FormField): string => {
  const fallback = activeTable.value?.name ?? 'Таблица по умолчанию'
  if (!field.table_id) return fallback
  return tableStructures.value.find((table) => table.id === field.table_id)?.name ?? fallback
}

const getFieldInputType = (widgetType: string): string => {
  const typeMap: Record<string, string> = {
    number_input: 'number',
    date_input: 'date',
    datetime_input: 'datetime-local'
  }
  return typeMap[widgetType] || 'text'
}

const mapWidgetTypeFromColumn = (
  columnType: ColumnType,
  settings?: Record<string, unknown>
): WidgetType => {
  if (columnType === 'number') return 'number_input'
  if (columnType === 'date') return 'date_input'
  if (columnType === 'datetime') return 'datetime_input'
  if (columnType === 'enum') return 'select'
  if (columnType === 'boolean') return 'checkbox'
  if (columnType === 'list') {
    const itemType = settings?.itemType
    if (itemType === 'enum') return 'multiselect'
    return 'list_input'
  }
  return 'text_input'
}

const supportsWidgetOptions = (field: FormField): boolean =>
  ['select', 'multiselect', 'checkbox', 'radio'].includes(field.widget_type)

const getFieldOptions = (field: FormField): string[] => {
  const options = field.widget_settings?.options
  if (!Array.isArray(options)) return []
  return options.map((item) => String(item)).filter(Boolean)
}

const setFieldOptions = (field: FormField, options: string[]) => {
  field.widget_settings = {
    ...(field.widget_settings ?? {}),
    options
  }
}

const addOptionToSelectedField = () => {
  if (!selectedFormField.value || !supportsWidgetOptions(selectedFormField.value)) return

  const next = newWidgetOption.value.trim()
  if (!next) return

  const existing = getFieldOptions(selectedFormField.value)
  if (existing.includes(next)) {
    newWidgetOption.value = ''
    return
  }

  setFieldOptions(selectedFormField.value, [...existing, next])
  newWidgetOption.value = ''
}

const updateFieldOptionAt = (field: FormField, index: number, value: string) => {
  const normalized = value.trim()
  const options = [...getFieldOptions(field)]
  if (index < 0 || index >= options.length) return

  if (!normalized) {
    options.splice(index, 1)
    setFieldOptions(field, options)
    return
  }

  options[index] = normalized
  setFieldOptions(field, options)
}

const removeFieldOptionAt = (field: FormField, index: number) => {
  const options = [...getFieldOptions(field)]
  if (index < 0 || index >= options.length) return
  options.splice(index, 1)
  setFieldOptions(field, options)
}

const startFieldDrag = (index: number) => {
  formFieldDragIndex.value = index
}

const dropFieldAt = (targetIndex: number) => {
  if (!selectedForm.value || formFieldDragIndex.value === null) return

  const sourceIndex = formFieldDragIndex.value
  formFieldDragIndex.value = null
  if (sourceIndex === targetIndex) return

  const fields = [...selectedForm.value.fields]
  const [moved] = fields.splice(sourceIndex, 1)
  fields.splice(targetIndex, 0, moved)
  selectedForm.value.fields = fields

  if (selectedFormFieldIndex.value === sourceIndex) {
    selectedFormFieldIndex.value = targetIndex
  } else if (selectedFormFieldIndex.value !== null) {
    const selectedIndex = selectedFormFieldIndex.value
    if (sourceIndex < selectedIndex && targetIndex >= selectedIndex) {
      selectedFormFieldIndex.value = selectedIndex - 1
    } else if (sourceIndex > selectedIndex && targetIndex <= selectedIndex) {
      selectedFormFieldIndex.value = selectedIndex + 1
    }
  }
}

const selectFormField = (index: number) => {
  selectedFormFieldIndex.value = index
}

const removeFormField = (index: number) => {
  if (!selectedForm.value || index < 0 || index >= selectedForm.value.fields.length) return

  const fields = [...selectedForm.value.fields]
  fields.splice(index, 1)
  selectedForm.value.fields = fields

  if (fields.length === 0) {
    selectedFormFieldIndex.value = null
    return
  }

  if (selectedFormFieldIndex.value === null) return

  if (selectedFormFieldIndex.value === index) {
    selectedFormFieldIndex.value = Math.min(index, fields.length - 1)
  } else if (selectedFormFieldIndex.value > index) {
    selectedFormFieldIndex.value -= 1
  }
}

const removeSelectedFormField = () => {
  if (selectedFormFieldIndex.value === null) return
  removeFormField(selectedFormFieldIndex.value)
}

const syncMissingFieldsFromWorkspace = () => {
  if (!selectedForm.value) return

  const existing = new Set(
    selectedForm.value.fields.map((field) => `${field.table_id ?? activeTable.value?.id ?? 0}:${field.column_key}`)
  )

  const missingFields: FormField[] = allWorkspaceColumns.value
    .filter((item) => formTableSelection.value.includes(item.tableId))
    .filter((item) => !existing.has(`${item.tableId}:${item.column.key}`))
    .map((item) => ({
      table_id: item.tableId,
      column_key: item.column.key,
      column_name: item.column.name,
      field_label: item.column.name,
      widget_type: mapWidgetTypeFromColumn(item.column.type, item.column.settings),
      required: item.column.required,
      placeholder: '',
      help_text: '',
      widget_settings: { ...(item.column.settings ?? {}) }
    }))

  if (missingFields.length === 0) return
  selectedForm.value.fields = [...selectedForm.value.fields, ...missingFields]
}

const addSelectedFieldToForm = () => {
  if (!selectedForm.value) return

  const tableId = Number(addFieldTableId.value)
  if (!tableId || !addFieldColumnKey.value) return

  const table = tableStructures.value.find((item) => item.id === tableId)
  const column = table?.columns.find((item) => item.key === addFieldColumnKey.value)
  if (!table || !column) return

  selectedForm.value.fields = [
    ...selectedForm.value.fields,
    {
      table_id: tableId,
      column_key: column.key,
      column_name: column.name,
      field_label: column.name,
      widget_type: mapWidgetTypeFromColumn(column.type, column.settings),
      required: column.required,
      placeholder: '',
      help_text: '',
      widget_settings: { ...(column.settings ?? {}) }
    }
  ]

  selectedFormFieldIndex.value = selectedForm.value.fields.length - 1
  addFieldColumnKey.value = ''
}

const copyToClipboard = () => {
  if (!selectedForm.value) return
  const text = `${window.location.origin}/form/${selectedForm.value.id}`
  navigator.clipboard.writeText(text).then(() => {
    alert('Ссылка скопирована!')
  })
}

const openFormPublicLink = (formId: number) => {
  window.open(`/form/${formId}`, '_blank')
}

const goToFormsTab = async () => {
  workspaceTab.value = 'forms'
  formEditorOpen.value = false
  await loadForms()
}

const createNewForm = async () => {
  if (!selectedWorkspace.value) return

  const baseTableId = activeTable.value?.id ?? tableStructures.value[0]?.id
  if (!baseTableId) {
    alert('Сначала создайте хотя бы одну таблицу.')
    return
  }

  const baseTable = tableStructures.value.find((table) => table.id === baseTableId)
  const defaultFields: FormField[] = (baseTable?.columns || []).map((column) => ({
    table_id: baseTableId,
    column_key: column.key,
    column_name: column.name,
    field_label: column.name,
    widget_type: mapWidgetTypeFromColumn(column.type, column.settings),
    required: column.required,
    placeholder: '',
    help_text: '',
    widget_settings: { ...(column.settings ?? {}) }
  }))

  const created = await formBuilderUseCase.createForm(
    selectedWorkspace.value.id,
    baseTableId,
    `Форма ${formConfigurations.value.length + 1}`,
    '',
    defaultFields,
    false
  )

  await loadForms()
  selectForm(created.id)
}

const onFormTablesChange = () => {
  if (!selectedForm.value) return

  if (formTableSelection.value.length === 0) {
    const fallback = selectedForm.value.table_id ?? activeTable.value?.id ?? tableStructures.value[0]?.id
    formTableSelection.value = typeof fallback === 'number' ? [fallback] : []
  }

  if (!formTableSelection.value.includes(Number(addFieldTableId.value))) {
    addFieldTableId.value = String(formTableSelection.value[0] ?? '')
    addFieldColumnKey.value = ''
  }
}

const saveSingleForm = async () => {
  if (!selectedForm.value || !selectedWorkspace.value || formTableSelection.value.length === 0) return

  const primaryTableId = formTableSelection.value[0]

  // Keep form fields mapped to selected tables only.
  selectedForm.value.fields = selectedForm.value.fields.filter((field) => {
    const fieldTableId = Number(field.table_id ?? primaryTableId)
    return formTableSelection.value.includes(fieldTableId)
  })

  selectedForm.value.table_id = primaryTableId

  await formBuilderUseCase.updateForm(
    selectedWorkspace.value.id,
    selectedForm.value.id,
    selectedForm.value.name,
    selectedForm.value.description,
    selectedForm.value.fields,
    selectedForm.value.is_published,
    selectedForm.value.collect_email
  )

  await loadForms()
}

const deleteForm = async (formId: number) => {
  if (!selectedWorkspace.value) return
  if (!window.confirm('Удалить эту форму?')) return

  await formBuilderUseCase.deleteForm(selectedWorkspace.value.id, formId)
  if (selectedFormId.value === formId) {
    selectedFormId.value = null
    selectedFormFieldIndex.value = null
    formEditorOpen.value = false
  }
  await loadForms()
}

const loadTableData = async () => {
  if (!authStore.token || !selectedWorkspace.value || !selectedDataTable.value) {
    tableDataRecords.value = []
    return
  }

  dataLoading.value = true
  dataError.value = ''
  try {
    const result = await formBuilderUseCase.listTableData(
      selectedWorkspace.value.id,
      selectedDataTable.value.id,
      dataPagination.value.skip,
      dataPagination.value.limit
    )
    tableDataRecords.value = result.items
    dataPagination.value = {
      skip: result.skip,
      limit: result.limit,
      total: result.total
    }
  } catch (error) {
    dataError.value = 'Не удалось загрузить данные'
    console.error(error)
  } finally {
    dataLoading.value = false
  }
}

const currentPage = computed(() => Math.floor(dataPagination.value.skip / dataPagination.value.limit) + 1)
const totalPages = computed(() => Math.ceil(dataPagination.value.total / dataPagination.value.limit) || 1)

const goToPage = async (page: number) => {
  dataPagination.value.skip = (page - 1) * dataPagination.value.limit
  await loadTableData()
}

const goToDataTab = async () => {
  workspaceTab.value = 'data'
  if (!selectedDataTableId.value) {
    selectedDataTableId.value = activeTable.value?.id ?? tableStructures.value[0]?.id ?? null
  }
  dataPagination.value.skip = 0
  await loadTableData()
}

const toNullableNumber = (value: string | number | null | undefined): number | null => {
  if (value === '' || value === null || value === undefined) return null
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : null
}

const normalizeImportKey = (value: string): string =>
  value
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9а-я]+/gi, '_')
    .replace(/^_+|_+$/g, '')
    .slice(0, IMPORT_KEY_MAX_LENGTH) || 'column'

const formatMappedKeyPreview = (value: string | null | undefined): string => {
  const normalized = normalizeImportKey(String(value || ''))
  return normalized || 'column'
}

const isMappedKeyTruncated = (value: string | null | undefined): boolean => {
  const raw = String(value || '').trim()
  return raw.length > IMPORT_KEY_MAX_LENGTH
}

const getImportTargetColumns = (target: ImportTargetUi) => {
  if (target.mode !== 'existing' || !target.table_id) return []
  const table = tableStructures.value.find((item) => item.id === target.table_id)
  return table?.columns ?? []
}

const syncImportTargetMappings = (target: ImportTargetUi) => {
  if (!importScanResult.value) return

  const nextMappings: Record<string, string | null> = {}
  if (target.mode === 'new') {
    for (const detected of importScanResult.value.detected_columns) {
      const current = target.column_mappings[detected.source_key]
      nextMappings[detected.source_key] =
        typeof current === 'string' && current.trim().length > 0
          ? normalizeImportKey(current)
          : normalizeImportKey(detected.suggested_key || detected.source_key)
    }
  } else {
    const columns = getImportTargetColumns(target)
    for (const detected of importScanResult.value.detected_columns) {
      const current = target.column_mappings[detected.source_key]
      if (current && columns.some((column) => column.key === current)) {
        nextMappings[detected.source_key] = current
        continue
      }

      const exactByKey = columns.find((column) => column.key === detected.suggested_key)
      const exactByName = columns.find((column) => column.name === detected.suggested_name)
      nextMappings[detected.source_key] = exactByKey?.key || exactByName?.key || null
    }
  }

  target.column_mappings = nextMappings
}

const addImportTarget = () => {
  const fallbackTableId = activeTable.value?.id ?? tableStructures.value[0]?.id ?? null
  const target: ImportTargetUi = {
    localId: importTargetSeq.value,
    mode: 'existing',
    table_id: fallbackTableId,
    table_name: '',
    table_description: '',
    column_mappings: {},
    map_section_to_field: false,
    section_field_name: 'Раздел'
  }
  importTargetSeq.value += 1
  if (importScanResult.value) {
    syncImportTargetMappings(target)
  }
  importTargets.value.push(target)
}

const removeImportTarget = (localId: number) => {
  importTargets.value = importTargets.value.filter((target) => target.localId !== localId)
}

const onImportTargetModeChange = (target: ImportTargetUi) => {
  if (target.mode === 'existing') {
    target.table_name = ''
    target.table_description = ''
    target.table_id = target.table_id ?? activeTable.value?.id ?? tableStructures.value[0]?.id ?? null
  } else {
    target.table_id = null
    target.table_name = target.table_name || `Импорт ${importTargets.value.length}`
  }
  syncImportTargetMappings(target)
}

const onImportTargetTableChange = (target: ImportTargetUi) => {
  syncImportTargetMappings(target)
}

const onImportFileChange = (event: Event) => {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0] ?? null
  importFile.value = file
  importError.value = ''
  importSuccess.value = ''
  importScanResult.value = null
  importShowAllSeparators.value = false
  importRequiresRescan.value = false
}

const onImportScanOptionsChanged = () => {
  if (!importScanResult.value) return
  importRequiresRescan.value = true
  importSuccess.value = ''
}

const scanImport = async () => {
  if (!authStore.token || !selectedWorkspace.value || !importFile.value) return

  importLoading.value = true
  importError.value = ''
  importSuccess.value = ''
  try {
    const delimiters = importListDelimiters.value
      .split(';')
      .map((item) => item.replace(/\\n/g, '\n').trim())
      .filter(Boolean)

    const result = await importUseCase.scanFile(authStore.token, selectedWorkspace.value.id, importFile.value, {
      sheet_name: null,
      header_row_start: toNullableNumber(importHeaderRowStart.value),
      header_row_end: toNullableNumber(importHeaderRowEnd.value),
      data_row_start: toNullableNumber(importDataRowStart.value),
      data_row_end: toNullableNumber(importDataRowEnd.value),
      list_split_delimiters: delimiters.length > 0 ? delimiters : [',', ';', '|', '\n']
    })

    importScanResult.value = result
    importHeaderRowStart.value = toNullableNumber(result.structure.header_row_start)
    importHeaderRowEnd.value = toNullableNumber(result.structure.header_row_end)
    importDataRowStart.value = toNullableNumber(result.structure.data_row_start)
    importDataRowEnd.value = null
    importShowAllSeparators.value = false
    importRequiresRescan.value = false

    if (importTargets.value.length === 0) {
      addImportTarget()
    } else {
      importTargets.value.forEach(syncImportTargetMappings)
    }
  } catch (error) {
    importError.value = 'Не удалось просканировать файл'
    console.error(error)
  } finally {
    importLoading.value = false
  }
}

const buildImportApplyConfig = (): ImportApplyConfig => {
  const delimiters = importListDelimiters.value
    .split(';')
    .map((item) => item.replace(/\\n/g, '\n').trim())
    .filter(Boolean)

  return {
    scan: {
      sheet_name: null,
      header_row_start: toNullableNumber(importHeaderRowStart.value),
      header_row_end: toNullableNumber(importHeaderRowEnd.value),
      data_row_start: toNullableNumber(importDataRowStart.value),
      data_row_end: toNullableNumber(importDataRowEnd.value),
      list_split_delimiters: delimiters.length > 0 ? delimiters : [',', ';', '|', '\n']
    },
    targets: importTargets.value.map((target) => ({
      mode: target.mode,
      table_id: target.mode === 'existing' ? toNullableNumber(target.table_id) : null,
      table_name: target.mode === 'new' ? (target.table_name || '').trim() : undefined,
      table_description: target.mode === 'new' ? (target.table_description || '').trim() : undefined,
      column_mappings: Object.fromEntries(
        Object.entries(target.column_mappings).map(([source, mapped]) => [source, mapped && mapped.trim() ? mapped.trim() : null])
      ),
      map_section_to_field: Boolean(target.map_section_to_field),
      section_field_name: (target.section_field_name || 'Раздел').trim() || 'Раздел'
    }))
  }
}

const applyImport = async () => {
  if (!authStore.token || !selectedWorkspace.value || !importFile.value || !importScanResult.value) return

  if (importRequiresRescan.value) {
    importError.value = 'Изменились параметры сканирования. Сначала выполните сканирование заново.'
    return
  }

  if (importTargets.value.length === 0) {
    importError.value = 'Добавьте хотя бы одну цель импорта'
    return
  }

  importApplying.value = true
  importError.value = ''
  importSuccess.value = ''
  try {
    const config = buildImportApplyConfig()
    const result = await importUseCase.applyImport(authStore.token, selectedWorkspace.value.id, importFile.value, config)
    importSuccess.value = result.imported_tables
      .map((item) => `${item.table_name}: ${item.created_records} записей`)
      .join(' | ')
    await loadSchema()
    await loadTableData()
  } catch (error) {
    importError.value = 'Ошибка при импорте данных'
    console.error(error)
  } finally {
    importApplying.value = false
  }
}

const goToImportTab = () => {
  workspaceTab.value = 'import'
  importError.value = ''
  importSuccess.value = ''
}

const toggleAllSeparators = () => {
  importShowAllSeparators.value = !importShowAllSeparators.value
}

const formatImportValue = (value: unknown): string => {
  if (value === null || value === undefined || value === '') return '—'
  if (Array.isArray(value)) return value.join(', ')
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

const onDataTableChange = async () => {
  dataPagination.value.skip = 0
  await loadTableData()
}

const onDataLimitChange = async () => {
  dataPagination.value.skip = 0
  await loadTableData()
}

const getReportTypeLabel = (type: ReportType) => {
  if (type === 'excel_export') return 'Excel выгрузка'
  return 'Публичный дашборд'
}

const syncReportColumnsWithSelectedTable = () => {
  const table = selectedReportTable.value
  if (!table) {
    reportExcelColumns.value = []
    return
  }

  const existing = new Map(reportExcelColumns.value.map((item) => [item.key, item]))
  reportExcelColumns.value = table.columns.map((column) => {
    const prev = existing.get(column.key)
    return {
      key: column.key,
      label: prev?.label || column.name,
      enabled: prev?.enabled ?? true
    }
  })
}

const resetReportEditor = () => {
  selectedReportId.value = null
  reportName.value = ''
  reportDescription.value = ''
  reportType.value = 'excel_export'
  reportIsPublished.value = false
  reportTableId.value = activeTable.value?.id ?? tableStructures.value[0]?.id ?? null
  reportRecentLimit.value = 10
  reportMetrics.value = [{ label: 'Количество записей', aggregation: 'count' }]
  reportCharts.value = []
  syncReportColumnsWithSelectedTable()
}

const loadReports = async () => {
  if (!selectedWorkspace.value) {
    reports.value = []
    return
  }

  reportsLoading.value = true
  reportsError.value = ''
  try {
    reports.value = await reportUseCase.listReports(selectedWorkspace.value.id)
  } catch (error) {
    reportsError.value = 'Не удалось загрузить отчеты'
    console.error(error)
  } finally {
    reportsLoading.value = false
  }
}

const goToReportsTab = async () => {
  workspaceTab.value = 'reports'
  reportEditorOpen.value = false
  templateModalOpen.value = false
  await loadReports()
}

const createReport = () => {
  reportEditorOpen.value = true
  resetReportEditor()
}

const editReport = (report: ReportConfiguration) => {
  selectedReportId.value = report.id
  reportName.value = report.name
  reportDescription.value = report.description || ''
  reportType.value = report.report_type
  reportIsPublished.value = report.is_published

  const settings = report.settings || {}
  reportTableId.value = Number(settings.table_id) || activeTable.value?.id || tableStructures.value[0]?.id || null

  syncReportColumnsWithSelectedTable()
  if (report.report_type === 'excel_export') {
    const configuredColumns = Array.isArray(settings.columns) ? settings.columns : []
    if (configuredColumns.length > 0) {
      const enabled = new Map(
        configuredColumns
          .filter((item): item is { key: string; label?: string } => !!item && typeof item === 'object' && 'key' in item)
          .map((item) => [item.key, item.label])
      )
      reportExcelColumns.value = reportExcelColumns.value.map((column) => ({
        ...column,
        enabled: enabled.has(column.key),
        label: String(enabled.get(column.key) || column.label)
      }))
    }
  }

  if (report.report_type === 'dashboard') {
    reportRecentLimit.value = Number(settings.recent_limit) || 10
    const metrics = Array.isArray(settings.metrics) ? settings.metrics : []
    reportMetrics.value = metrics
      .filter((metric): metric is DashboardMetricConfig => !!metric && typeof metric === 'object')
      .map((metric) => ({
        label: String(metric.label || 'Метрика'),
        aggregation: (metric.aggregation as DashboardMetricConfig['aggregation']) || 'count',
        field_key: metric.field_key ? String(metric.field_key) : undefined
      }))

    if (reportMetrics.value.length === 0) {
      reportMetrics.value = [{ label: 'Количество записей', aggregation: 'count' }]
    }

    const charts = Array.isArray(settings.charts) ? settings.charts : []
    reportCharts.value = charts
      .filter((chart): chart is DashboardChartConfig => !!chart && typeof chart === 'object')
      .map((chart) => ({
        title: String(chart.title || 'График'),
        chart_type: 'bar',
        group_by_key: String(chart.group_by_key || ''),
        aggregation: chart.aggregation || 'count',
        value_key: chart.value_key ? String(chart.value_key) : undefined,
        limit: Number(chart.limit) || 10
      }))
  }

  reportEditorOpen.value = true
}

const onReportTableChange = () => {
  syncReportColumnsWithSelectedTable()
}

const addDashboardMetric = () => {
  reportMetrics.value.push({ label: 'Новая метрика', aggregation: 'count' })
}

const addDashboardChart = () => {
  reportCharts.value.push({
    title: 'Новый график',
    chart_type: 'bar',
    group_by_key: '',
    aggregation: 'count',
    limit: 10
  })
}

const removeDashboardMetric = (index: number) => {
  reportMetrics.value.splice(index, 1)
  if (reportMetrics.value.length === 0) {
    reportMetrics.value.push({ label: 'Количество записей', aggregation: 'count' })
  }
}

const removeDashboardChart = (index: number) => {
  reportCharts.value.splice(index, 1)
}

const saveReport = async () => {
  if (!selectedWorkspace.value || !reportName.value.trim() || !reportTableId.value) return

  const excelColumns = reportExcelColumns.value
    .filter((column) => column.enabled)
    .map((column) => ({ key: column.key, label: column.label || column.key }))

  const settings: Record<string, unknown> = { table_id: reportTableId.value }
  if (reportType.value === 'excel_export') {
    settings.columns = excelColumns
  } else {
    settings.metrics = reportMetrics.value
    settings.charts = reportCharts.value
    settings.recent_limit = Math.max(1, Number(reportRecentLimit.value) || 10)
  }

  if (selectedReportId.value) {
    await reportUseCase.updateReport(
      selectedWorkspace.value.id,
      selectedReportId.value,
      reportName.value.trim(),
      reportDescription.value.trim(),
      reportType.value,
      settings as {
        table_id: number
      },
      reportIsPublished.value
    )
  } else {
    await reportUseCase.createReport(
      selectedWorkspace.value.id,
      reportName.value.trim(),
      reportDescription.value.trim(),
      reportType.value,
      settings as {
        table_id: number
      },
      reportIsPublished.value
    )
  }

  reportEditorOpen.value = false
  await loadReports()
}

const deleteReport = async (reportId: number) => {
  if (!selectedWorkspace.value) return
  if (!window.confirm('Удалить этот отчет?')) return

  await reportUseCase.deleteReport(selectedWorkspace.value.id, reportId)
  if (selectedReportId.value === reportId) {
    reportEditorOpen.value = false
    resetReportEditor()
  }
  await loadReports()
}

const openReportPublicLink = (reportId: number) => {
  window.open(`/report/${reportId}`, '_blank')
}

const downloadReport = async (reportId: number) => {
  if (!selectedWorkspace.value) return

  const blob = await reportUseCase.downloadExcelReport(selectedWorkspace.value.id, reportId)
  const url = window.URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = `report_${reportId}.xlsx`
  document.body.appendChild(anchor)
  anchor.click()
  document.body.removeChild(anchor)
  window.URL.revokeObjectURL(url)
}

const resetTemplateModalState = () => {
  templateDragActive.value = false
  templateUploading.value = false
  templateError.value = ''
  templateFileName.value = ''
}

const openTemplateModal = () => {
  templateModalOpen.value = true
  resetTemplateModalState()
  templateTableId.value = activeTable.value?.id ?? tableStructures.value[0]?.id ?? null
}

const closeTemplateModal = () => {
  if (templateUploading.value) return
  templateModalOpen.value = false
  resetTemplateModalState()
}

const isOdtFile = (file: File): boolean =>
  file.name.toLowerCase().endsWith('.odt') || file.type === 'application/vnd.oasis.opendocument.text'

const saveBlob = (blob: Blob, filename: string) => {
  const url = window.URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  document.body.appendChild(anchor)
  anchor.click()
  document.body.removeChild(anchor)
  window.URL.revokeObjectURL(url)
}

const extractTemplateApiError = (error: any): string => {
  const data = error?.response?.data
  if (typeof data === 'string' && data.trim()) return data

  const detail = data?.detail
  if (typeof detail === 'string' && detail.trim()) return detail

  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0]
    if (typeof first === 'string') return first
    if (first && typeof first === 'object') {
      const location = Array.isArray(first.loc) ? first.loc.join('.') : 'request'
      const message = typeof first.msg === 'string' ? first.msg : 'Validation error'
      return `${location}: ${message}`
    }
    return 'Validation error'
  }

  if (typeof error?.message === 'string' && error.message.trim()) return error.message
  return 'Не удалось обработать шаблон. Проверьте формат {{ aggregation_func(key) }}.'
}

const processTemplateFile = async (file: File) => {
  if (!selectedWorkspace.value || !templateTableId.value) {
    templateError.value = 'Выберите таблицу, по которой нужно считать агрегаты.'
    return
  }
  if (!isOdtFile(file)) {
    templateError.value = 'Нужен файл в формате .odt'
    return
  }

  templateUploading.value = true
  templateError.value = ''
  templateFileName.value = file.name

  let completed = false
  try {
    const result = await reportUseCase.calculateByTemplate(selectedWorkspace.value.id, templateTableId.value, file)
    const normalizedName = file.name.toLowerCase().endsWith('.odt')
      ? file.name.slice(0, -4)
      : file.name
    saveBlob(result, `${normalizedName}_calculated.odt`)
    completed = true
  } catch (error: any) {
    console.error('Template processing request failed', {
      status: error?.response?.status,
      data: error?.response?.data
    })
    templateError.value = extractTemplateApiError(error)
  } finally {
    templateUploading.value = false
  }

  if (completed) {
    closeTemplateModal()
  }
}

const onTemplateDragOver = (event: DragEvent) => {
  event.preventDefault()
  if (templateUploading.value) return
  templateDragActive.value = true
}

const onTemplateDragLeave = (event: DragEvent) => {
  event.preventDefault()
  templateDragActive.value = false
}

const onTemplateDrop = async (event: DragEvent) => {
  event.preventDefault()
  templateDragActive.value = false
  if (templateUploading.value) return

  const file = event.dataTransfer?.files?.[0]
  if (!file) return
  await processTemplateFile(file)
}

const openTemplateFilePicker = () => {
  if (templateUploading.value) return
  templateFileInput.value?.click()
}

const onTemplateFileChange = async (event: Event) => {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return
  await processTemplateFile(file)
}

const deleteDataRecord = async (recordId: number) => {
  if (!authStore.token || !selectedWorkspace.value || !selectedDataTable.value) return
  if (!window.confirm('Удалить эту запись?')) return

  try {
    await formBuilderUseCase.deleteTableDataRecord(
      selectedWorkspace.value.id,
      selectedDataTable.value.id,
      recordId
    )
    await loadTableData()
  } catch (error) {
    alert('Ошибка при удалении записи')
  }
}

const formatDataValue = (value: unknown, columnType: ColumnType): string => {
  if (value === null || value === undefined) return '—'
  if (typeof value === 'boolean') return value ? 'Да' : 'Нет'
  if (typeof value === 'object') return JSON.stringify(value).substring(0, 50) + '...'
  return String(value).substring(0, 80)
}

const formatDate = (value: string): string => {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat('ru-RU', {
    day: '2-digit',
    month: 'long',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  }).format(date)
}

const logout = () => {
  authStore.logout()
  router.push({ name: 'login' })
}

onMounted(async () => {
  window.addEventListener('pointermove', onCanvasPointerMove)
  window.addEventListener('pointerup', stopTableDrag)
  await loadWorkspaces()
  await loadSchema()
})

onBeforeUnmount(() => {
  window.removeEventListener('pointermove', onCanvasPointerMove)
  window.removeEventListener('pointerup', stopTableDrag)
})
</script>

<template>
  <main class="dashboard">
    <aside class="sidebar">
      <header class="sidebar-header">
        <h1>Workspace</h1>
        <p>{{ authStore.me?.email }}</p>
      </header>

      <section class="create-widget">
        <h2>Новый workspace</h2>
        <div class="fields">
          <input v-model="workspaceName" type="text" placeholder="Название" maxlength="255" />
          <textarea v-model="workspaceDescription" rows="3" placeholder="Описание (опционально)" maxlength="2000" />
          <button @click="createWorkspace">Создать</button>
        </div>
      </section>

      <section class="workspace-nav">
        <div class="nav-title">
          <h2>Список</h2>
          <span>{{ workspaces.length }}</span>
        </div>
        <p v-if="loading" class="muted">Загрузка...</p>
        <p v-else-if="workspaces.length === 0" class="muted">Пока нет workspace</p>

        <ul v-else>
          <li v-for="workspace in workspaces" :key="workspace.id">
            <button class="workspace-link" :class="{ active: selectedWorkspaceId === workspace.id }" @click="selectWorkspace(workspace.id)">
              <strong>{{ workspace.name }}</strong>
              <span>{{ workspace.description || 'Без описания' }}</span>
            </button>
          </li>
        </ul>
      </section>

      <button class="ghost" @click="logout">Выйти</button>
    </aside>

    <section class="content">
      <article v-if="selectedWorkspace" class="workspace-content">
        <header>
          <h2>{{ selectedWorkspace.name }}</h2>
          <p>{{ selectedWorkspace.description || 'Описание пока не добавлено' }}</p>
        </header>

        <div class="workspace-tabs">
          <button class="tab" :class="{ active: workspaceTab === 'details' }" @click="workspaceTab = 'details'">Детали</button>
          <button class="tab" :class="{ active: workspaceTab === 'tables' }" @click="workspaceTab = 'tables'">Таблицы</button>
          <button class="tab" :class="{ active: workspaceTab === 'forms' }" @click="goToFormsTab">Формы</button>
          <button class="tab" :class="{ active: workspaceTab === 'data' }" @click="goToDataTab">Данные</button>
          <button class="tab" :class="{ active: workspaceTab === 'import' }" @click="goToImportTab">Импорт</button>
          <button class="tab" :class="{ active: workspaceTab === 'reports' }" @click="goToReportsTab">Отчеты</button>
        </div>

        <div class="actions-row" v-if="workspaceTab === 'details'">
          <button class="danger" :disabled="deleting" @click="deleteWorkspace">
            {{ deleting ? 'Удаляем...' : 'Удалить workspace' }}
          </button>
        </div>

        <section v-if="workspaceTab === 'tables'" class="designer">
          <div class="designer-header">
            <h3>Low-code структуры таблиц</h3>
            <p>SQL Canvas: перемещайте таблицы по полю и переносите колонки drag-and-drop между таблицами.</p>
          </div>

          <div class="create-table">
            <input v-model="newTableName" type="text" placeholder="Новая таблица: название" maxlength="255" />
            <input v-model="newTableDescription" type="text" placeholder="Описание таблицы" maxlength="255" />
            <button @click="createTable">Добавить таблицу</button>
          </div>

          <p v-if="schemaLoading" class="muted">Загрузка структуры...</p>
          <p v-if="schemaError" class="error">{{ schemaError }}</p>

          <div class="schema-layout">
            <div class="schema-canvas-wrap">
              <div class="schema-canvas">
                <article
                  v-for="table in tableStructures"
                  :key="table.id"
                  class="table-card"
                  :class="{ active: activeTableId === table.id }"
                  :style="{ left: `${getTablePosition(table.id).x}px`, top: `${getTablePosition(table.id).y}px` }"
                  @dragover.prevent
                  @drop="onDropColumnToTable(table.id)"
                >
                  <div class="table-head" @click="selectTable(table.id)">
                    <button class="table-grip" @pointerdown.prevent="onTableGripPointerDown($event, table.id)">::: </button>
                    <strong>{{ table.name }}</strong>
                  </div>
                  <p class="table-sub">{{ table.description || 'Без описания' }}</p>

                  <ul class="column-list">
                    <li
                      v-for="column in table.columns"
                      :key="column.key"
                      class="column-item"
                      draggable="true"
                      @dragstart="startDraggingColumn(table.id, column.key)"
                      @dragend="dragState = null"
                      @click="selectColumn(table.id, column.key)"
                    >
                      <div>
                        <strong>{{ column.name }}</strong>
                        <span>{{ column.key }}</span>
                      </div>
                      <em>{{ column.type }}</em>
                    </li>
                  </ul>
                </article>
              </div>
            </div>

            <aside class="object-sidebar">
              <section v-if="activeTable" class="object-card">
                <h4>Выделенная таблица</h4>
                <input v-model="activeTable.name" placeholder="Имя таблицы" />
                <input v-model="activeTable.description" placeholder="Описание таблицы" />
                <div class="row-actions">
                  <button class="small" @click="saveTable(activeTable)">Сохранить таблицу</button>
                  <button class="small danger" @click="deleteActiveTable">Удалить таблицу</button>
                </div>
              </section>

              <section class="object-card" v-if="activeTable">
                <h4>Добавить колонку</h4>
                <div class="new-column-form">
                  <input v-model="newColumnName" placeholder="Название колонки" />
                  <select v-model="newColumnType">
                    <option value="text">text</option>
                    <option value="number">number</option>
                    <option value="boolean">boolean</option>
                    <option value="date">date</option>
                    <option value="datetime">datetime</option>
                    <option value="enum">enum</option>
                    <option value="list">list</option>
                    <option value="geoPoint">geoPoint</option>
                    <option value="geoPolygon">geoPolygon</option>
                  </select>
                  <label class="checkbox-inline"><input v-model="newColumnRequired" type="checkbox" />required</label>
                </div>

                <div v-if="newColumnType === 'enum'" class="type-settings">
                  <input v-model="newColumnEnumOptions" placeholder="Enum options через запятую" />
                </div>

                <div v-if="newColumnType === 'list'" class="type-settings">
                  <select v-model="newColumnListItemType">
                    <option value="text">text</option>
                    <option value="number">number</option>
                    <option value="boolean">boolean</option>
                    <option value="enum">enum</option>
                  </select>
                  <input v-if="newColumnListItemType === 'enum'" v-model="newColumnEnumOptions" placeholder="List enum options" />
                </div>

                <div v-if="newColumnType === 'number'" class="type-settings">
                  <label class="checkbox-inline">
                    <input
                      :checked="newColumnNumberIsId"
                      type="checkbox"
                      @change="onNewColumnNumberIsIdChange(($event.target as HTMLInputElement).checked)"
                    />
                    Использовать как ID
                  </label>
                  <label class="checkbox-inline">
                    <input v-model="newColumnNumberAutoIncrement" type="checkbox" /> Автоинкремент
                  </label>
                  <label class="setting-label">Стартовое значение</label>
                  <input
                    v-model.number="newColumnNumberStart"
                    type="number"
                    min="1"
                    placeholder="Стартовое значение"
                    :disabled="!newColumnNumberAutoIncrement"
                  />
                  <label class="setting-label">Шаг инкремента</label>
                  <input
                    v-model.number="newColumnNumberStep"
                    type="number"
                    min="1"
                    placeholder="Шаг"
                    :disabled="!newColumnNumberAutoIncrement"
                  />
                </div>

                <div v-if="newColumnType === 'geoPoint' || newColumnType === 'geoPolygon'" class="type-settings">
                  <input v-model.number="newColumnGeoSrid" type="number" min="1" placeholder="SRID" />
                  <label v-if="newColumnType === 'geoPolygon'" class="checkbox-inline">
                    <input v-model="newColumnGeoAllowHoles" type="checkbox" />allow holes
                  </label>
                </div>

                <button class="small" @click="addColumnToActiveTable">Добавить в таблицу</button>
              </section>

              <section v-if="selectedColumn && selectedColumnParent" class="object-card">
                <h4>Выделенная колонка</h4>
                <p class="muted">Таблица: {{ selectedColumnParent.name }}</p>
                <input v-model="selectedColumn.name" placeholder="Название" />
                <input v-model="selectedColumn.key" placeholder="Ключ" />
                <select v-model="selectedColumn.type">
                  <option value="text">text</option>
                  <option value="number">number</option>
                  <option value="boolean">boolean</option>
                  <option value="date">date</option>
                  <option value="datetime">datetime</option>
                  <option value="enum">enum</option>
                  <option value="list">list</option>
                  <option value="geoPoint">geoPoint</option>
                  <option value="geoPolygon">geoPolygon</option>
                </select>
                <label class="checkbox-inline"><input v-model="selectedColumn.required" type="checkbox" />required</label>
                <div v-if="selectedColumn.type === 'number'" class="type-settings">
                  <label class="checkbox-inline">
                    <input
                      :checked="getSelectedNumberSetting('isId', false)"
                      type="checkbox"
                      @change="onSelectedColumnIsIdChange(($event.target as HTMLInputElement).checked)"
                    />
                    Использовать как ID
                  </label>
                  <label class="checkbox-inline">
                    <input
                      :checked="getSelectedNumberSetting('autoIncrement', false)"
                      type="checkbox"
                      @change="setSelectedNumberSetting('autoIncrement', ($event.target as HTMLInputElement).checked)"
                    />
                    Автоинкремент
                  </label>
                  <label class="setting-label">Стартовое значение</label>
                  <input
                    :value="getSelectedNumberSetting('autoIncrementStart', 1)"
                    type="number"
                    min="1"
                    placeholder="Стартовое значение"
                    :disabled="!getSelectedNumberSetting('autoIncrement', false)"
                    @input="setSelectedNumberSetting('autoIncrementStart', Math.max(1, Number(($event.target as HTMLInputElement).value) || 1))"
                  />
                  <label class="setting-label">Шаг инкремента</label>
                  <input
                    :value="getSelectedNumberSetting('autoIncrementStep', 1)"
                    type="number"
                    min="1"
                    placeholder="Шаг"
                    :disabled="!getSelectedNumberSetting('autoIncrement', false)"
                    @input="setSelectedNumberSetting('autoIncrementStep', Math.max(1, Number(($event.target as HTMLInputElement).value) || 1))"
                  />
                </div>
                <div class="row-actions">
                  <button class="small" @click="saveSelectedColumn">Сохранить</button>
                  <button class="small danger" @click="removeColumnFromActiveTable(selectedColumn.key)">Удалить</button>
                </div>
              </section>

              <section class="object-card relations">
                <h4>Связи таблиц</h4>
                <div class="relation-form">
                  <input v-model="relationName" placeholder="Название связи" />
                  <select v-model="relationSourceTableId">
                    <option value="">Источник</option>
                    <option v-for="table in allTableOptions" :key="`s-${table.id}`" :value="String(table.id)">{{ table.name }}</option>
                  </select>
                  <select v-model="relationSourceColumn">
                    <option value="">Колонка источника</option>
                    <option v-for="column in relationSourceColumns" :key="`sc-${column.key}`" :value="column.key">{{ column.name }}</option>
                  </select>
                  <select v-model="relationTargetTableId">
                    <option value="">Цель</option>
                    <option v-for="table in allTableOptions" :key="`t-${table.id}`" :value="String(table.id)">{{ table.name }}</option>
                  </select>
                  <select v-model="relationTargetColumn">
                    <option value="">Колонка цели</option>
                    <option v-for="column in relationTargetColumns" :key="`tc-${column.key}`" :value="column.key">{{ column.name }}</option>
                  </select>
                  <select v-model="relationType">
                    <option value="one_to_one">one_to_one</option>
                    <option value="one_to_many">one_to_many</option>
                    <option value="many_to_many">many_to_many</option>
                  </select>
                  <button @click="createRelation">Добавить связь</button>
                </div>

                <ul class="relation-list">
                  <li v-for="relation in relations" :key="relation.id">
                    <div>
                      <strong>{{ relation.name }}</strong>
                      <span>{{ relation.relation_type }}: {{ relation.source_table_id }} -> {{ relation.target_table_id }}</span>
                    </div>
                    <button class="small danger" @click="deleteRelation(relation.id)">Удалить</button>
                  </li>
                </ul>
              </section>
            </aside>
          </div>
        </section>

        <section v-if="workspaceTab === 'forms'" class="forms-section">
          <div class="forms-header">
            <div>
              <h3>Конструктор форм</h3>
              <p>Создавайте несколько форм для одной таблицы или для набора таблиц.</p>
            </div>
            <button class="small" @click="createNewForm">Новая форма</button>
          </div>

          <div v-if="formLoading" class="muted">Загрузка форм...</div>
          <div v-if="formError" class="error">{{ formError }}</div>

          <div class="reports-grid" v-if="formConfigurations.length > 0">
            <article
              v-for="form in formConfigurations"
              :key="form.id"
              class="report-tile"
              :class="{ active: selectedFormId === form.id }"
            >
              <header>
                <h4>{{ form.name }}</h4>
                <span class="report-type">{{ form.is_published ? 'Публичная' : 'Черновик' }}</span>
              </header>
              <p>{{ form.description || 'Без описания' }}</p>
              <p class="muted">Поля: {{ form.fields.length }}</p>
              <p class="muted">Таблицы: {{ getFormUsedTableNames(form) }}</p>
              <div class="report-actions">
                <button
                  class="small"
                  :disabled="!form.is_published"
                  @click="openFormPublicLink(form.id)"
                >
                  Ссылка
                </button>
                <button class="small" @click="selectForm(form.id)">Редактировать</button>
                <button class="small danger" @click="deleteForm(form.id)">Удалить</button>
              </div>
            </article>
          </div>
          <p v-else-if="!formLoading" class="muted">Пока нет форм. Создайте первую.</p>

          <div v-if="formEditorOpen && selectedForm" class="form-editor">
            <article class="form-preview">
              <header class="form-header">
                <h4>{{ selectedForm.name }}</h4>
                <p>{{ selectedForm.description }}</p>
              </header>

              <form @submit.prevent>
                <div
                  v-for="(field, index) in selectedForm.fields"
                  :key="`${field.table_id ?? 'default'}-${field.column_key}`"
                  class="form-field-preview"
                  :class="{ active: selectedFormFieldIndex === index }"
                  draggable="true"
                  @dragstart="startFieldDrag(index)"
                  @dragover.prevent
                  @drop.prevent="dropFieldAt(index)"
                  @click="selectFormField(index)"
                >
                  <label :for="`field-${field.column_key}`">
                    {{ field.field_label }}
                    <span v-if="field.required" class="required">*</span>
                  </label>
                  <p class="field-table-label">Таблица: {{ getFieldTableName(field) }}</p>
                  <input
                    v-if="['text_input', 'number_input', 'date_input', 'datetime_input'].includes(field.widget_type)"
                    :id="`field-${field.column_key}`"
                    :type="getFieldInputType(field.widget_type)"
                    :placeholder="field.placeholder"
                    :required="field.required"
                  />
                  <textarea
                    v-else-if="field.widget_type === 'textarea'"
                    :id="`field-${field.column_key}`"
                    :placeholder="field.placeholder"
                    :required="field.required"
                  />
                  <select
                    v-else-if="field.widget_type === 'select' && field.widget_settings.options"
                    :id="`field-${field.column_key}`"
                    :required="field.required"
                  >
                    <option value="">{{ field.placeholder || 'Выберите...' }}</option>
                    <option v-for="opt in field.widget_settings.options" :key="opt" :value="opt">{{ opt }}</option>
                  </select>
                  <select
                    v-else-if="field.widget_type === 'multiselect' && field.widget_settings.options"
                    :id="`field-${field.column_key}`"
                    multiple
                    :required="field.required"
                  >
                    <option v-for="opt in field.widget_settings.options" :key="`multi-${opt}`" :value="opt">{{ opt }}</option>
                  </select>
                  <div v-else-if="field.widget_type === 'list_input'" class="list-input-preview">
                    <input :placeholder="field.placeholder || 'Добавить элемент списка'" />
                    <button type="button" class="small">Добавить</button>
                  </div>
                  <div v-else-if="field.widget_type === 'checkbox'" class="checkbox-wrapper">
                    <template v-if="getFieldOptions(field).length > 0">
                      <label v-for="(opt, idx) in getFieldOptions(field)" :key="`preview-checkbox-${idx}-${opt}`">
                        <input type="checkbox" :name="`field-${field.column_key}`" :value="opt" />
                        {{ opt }}
                      </label>
                    </template>
                    <input v-else :id="`field-${field.column_key}`" type="checkbox" :required="field.required" />
                  </div>
                  <div v-else-if="field.widget_type === 'radio' && field.widget_settings.options" class="radio-wrapper">
                    <label v-for="opt in field.widget_settings.options" :key="opt">
                      <input type="radio" :name="`field-${field.column_key}`" :value="opt" :required="field.required" />
                      {{ opt }}
                    </label>
                  </div>
                  <p v-if="field.help_text" class="help-text">{{ field.help_text }}</p>
                </div>
              </form>
            </article>

            <aside class="form-config">
              <section class="object-card">
                <h4>Настройки формы</h4>
                <div>
                  <label>Название</label>
                  <input v-model="selectedForm.name" />
                </div>
                <div>
                  <label>Описание</label>
                  <input v-model="selectedForm.description" />
                </div>
                <div>
                  <label>Таблицы формы (можно несколько)</label>
                  <select v-model="formTableSelection" multiple @change="onFormTablesChange">
                    <option v-for="table in allTableOptions" :key="`ft-t-${table.id}`" :value="table.id">
                      {{ table.name }}
                    </option>
                  </select>
                </div>
                <label class="checkbox-inline">
                  <input v-model="selectedForm.is_published" type="checkbox" /> Опубликована
                </label>
                <label class="checkbox-inline">
                  <input v-model="selectedForm.collect_email" type="checkbox" /> Собирать email
                </label>
                <button class="small" @click="saveSingleForm">Сохранить форму</button>
              </section>

              <section class="object-card">
                <h4>Поля ({{ selectedForm.fields.length }})</h4>
                <button class="small" @click="syncMissingFieldsFromWorkspace">Добавить все недостающие</button>
                <div class="field-settings-row">
                  <select v-model="addFieldTableId">
                    <option value="">Таблица для добавления</option>
                    <option
                      v-for="table in allTableOptions.filter((item) => formTableSelection.includes(item.id))"
                      :key="`add-t-${table.id}`"
                      :value="String(table.id)"
                    >
                      {{ table.name }}
                    </option>
                  </select>
                  <select v-model="addFieldColumnKey" :disabled="!addFieldTableId">
                    <option value="">Поле таблицы</option>
                    <option v-for="column in addFieldCandidates" :key="`add-c-${column.key}`" :value="column.key">
                      {{ column.name }}
                    </option>
                  </select>
                  <button class="small" @click="addSelectedFieldToForm">Добавить поле в конец формы</button>
                </div>
                <ul v-if="selectedForm.fields.length > 0" class="form-fields-list">
                  <li
                    v-for="(field, index) in selectedForm.fields"
                    :key="`${field.table_id ?? 'default'}-${field.column_key}`"
                    :class="{ active: selectedFormFieldIndex === index }"
                    @click="selectFormField(index)"
                  >
                    <div>
                      <strong>{{ field.field_label }}</strong>
                      <span>{{ getWidgetTypeLabel(field.widget_type) }} · {{ field.column_key }} · {{ getFieldTableName(field) }}</span>
                    </div>
                    <button class="small danger" @click.stop="removeFormField(index)">Удалить</button>
                  </li>
                </ul>
                <p v-else class="muted">Нет полей</p>
              </section>

              <section v-if="selectedFormField" class="object-card">
                <h4>Настройки выбранного поля</h4>
                <p class="muted">Текущая таблица: {{ getFieldTableName(selectedFormField) }}</p>
                <input v-model="selectedFormField.field_label" placeholder="Заголовок поля" />
                <select v-model="selectedFormField.widget_type">
                  <option value="text_input">text_input</option>
                  <option value="textarea">textarea</option>
                  <option value="number_input">number_input</option>
                  <option value="date_input">date_input</option>
                  <option value="datetime_input">datetime_input</option>
                  <option value="select">select</option>
                  <option value="multiselect">multiselect</option>
                  <option value="list_input">list_input</option>
                  <option value="checkbox">checkbox</option>
                  <option value="radio">radio</option>
                </select>
                <select v-model.number="selectedFormField.table_id">
                  <option v-for="table in allTableOptions.filter((item) => formTableSelection.includes(item.id))" :key="`sf-t-${table.id}`" :value="table.id">
                    {{ table.name }}
                  </option>
                </select>
                <input v-model="selectedFormField.placeholder" placeholder="Placeholder" />
                <input v-model="selectedFormField.help_text" placeholder="Подсказка" />
                <div v-if="supportsWidgetOptions(selectedFormField)" class="options-editor">
                  <label>Варианты</label>
                  <div class="option-row" v-for="(opt, optIndex) in getFieldOptions(selectedFormField)" :key="`opt-${optIndex}`">
                    <input
                      :value="opt"
                      placeholder="Вариант"
                      @input="updateFieldOptionAt(selectedFormField, optIndex, ($event.target as HTMLInputElement).value)"
                    />
                    <button class="small danger" @click="removeFieldOptionAt(selectedFormField, optIndex)">Удалить</button>
                  </div>
                  <div class="option-add-row">
                    <input
                      v-model="newWidgetOption"
                      placeholder="Новый вариант"
                      @keydown.enter.prevent="addOptionToSelectedField"
                    />
                    <button class="small" @click="addOptionToSelectedField">Добавить вариант</button>
                  </div>
                </div>
                <label class="checkbox-inline">
                  <input v-model="selectedFormField.required" type="checkbox" /> Обязательное
                </label>
                <button class="small danger" @click="removeSelectedFormField">Удалить поле</button>
              </section>

              <section class="object-card">
                <h4>Поделиться</h4>
                <p class="muted">Скопируйте ссылку для отправки пользователям:</p>
                <div class="share-link">
                  <code>/form/{{ selectedForm.id }}</code>
                  <button class="small" @click="copyToClipboard">Копировать</button>
                </div>
              </section>
            </aside>
          </div>
        </section>

        <section v-if="workspaceTab === 'data'" class="data-section">
          <div class="data-header">
            <h3>{{ selectedDataTable ? selectedDataTable.name : 'Таблица' }}: Данные</h3>
            <p v-if="selectedDataTable">Показано {{ tableDataRecords.length }} из {{ dataPagination.total }} записей</p>
          </div>

          <div class="field-settings-row">
            <select v-model.number="selectedDataTableId" @change="onDataTableChange">
              <option :value="null">Выберите таблицу</option>
              <option v-for="table in allTableOptions" :key="`data-t-${table.id}`" :value="table.id">
                {{ table.name }}
              </option>
            </select>
            <select v-model.number="dataPagination.limit" @change="onDataLimitChange">
              <option :value="10">10 записей</option>
              <option :value="25">25 записей</option>
              <option :value="50">50 записей</option>
              <option :value="100">100 записей</option>
            </select>
          </div>

          <div v-if="dataLoading" class="muted">Загрузка данных...</div>
          <div v-if="dataError" class="error">{{ dataError }}</div>

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
                    <span :title="JSON.stringify(record.data[column.key])">
                      {{ formatDataValue(record.data[column.key], column.type) }}
                    </span>
                  </td>
                  <td>{{ formatDate(record.submitted_at || record.created_at) }}</td>
                  <td>{{ record.submitter_email || '—' }}</td>
                  <td>
                    <button class="small danger" @click="deleteDataRecord(record.id)">Удалить</button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <div v-else-if="!dataLoading && selectedDataTable" class="muted" style="text-align: center; padding: 20px;">
            Нет записей в этой таблице
          </div>

          <div v-if="totalPages > 1" class="pagination">
            <button @click="goToPage(currentPage - 1)" :disabled="currentPage === 1">← Назад</button>
            <span>Страница {{ currentPage }} из {{ totalPages }}</span>
            <button @click="goToPage(currentPage + 1)" :disabled="currentPage === totalPages">Вперёд →</button>
          </div>
        </section>

        <section v-if="workspaceTab === 'import'" class="import-section">
          <div class="import-header">
            <div>
              <h3>Импорт</h3>
              <p>Загрузите файл, просканируйте структуру, затем сопоставьте колонки и выполните импорт.</p>
            </div>
          </div>

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
              <input type="file" accept=".csv,.xls,.xlsx" @change="onImportFileChange" />
            </div>

            <div class="import-zones">
              <h4>Зоны поиска</h4>
              <div class="zones-grid">
                <div>
                  <label>Header start</label>
                  <input v-model.number="importHeaderRowStart" type="number" min="0" placeholder="auto" @input="onImportScanOptionsChanged" />
                </div>
                <div>
                  <label>Header end</label>
                  <input v-model.number="importHeaderRowEnd" type="number" min="0" placeholder="auto" @input="onImportScanOptionsChanged" />
                </div>
                <div>
                  <label>Data start</label>
                  <input v-model.number="importDataRowStart" type="number" min="0" placeholder="auto" @input="onImportScanOptionsChanged" />
                </div>
                <div>
                  <label>Data end</label>
                  <input v-model.number="importDataRowEnd" type="number" min="0" placeholder="до конца" @input="onImportScanOptionsChanged" />
                </div>
              </div>
            </div>

            <div class="import-zones">
              <h4>Списки</h4>
              <label>Разделители списка (через ;, используйте \n для новой строки)</label>
              <input v-model="importListDelimiters" placeholder=",;|;\\n" @input="onImportScanOptionsChanged" />
            </div>

            <p class="import-warning" v-if="importScanResult">
              Важно: ключи колонок ограничены {{ IMPORT_KEY_MAX_LENGTH }} символами.
              При импорте длинные ключи автоматически сокращаются.
            </p>

            <div class="row-actions">
              <button class="small" :disabled="!importFile || importLoading" @click="scanImport">
                {{ importLoading ? 'Сканирование...' : 'Сканировать файл' }}
              </button>
              <button
                class="small"
                :disabled="!importCanApply || importApplying"
                @click="applyImport"
              >
                {{ importApplying ? 'Импорт...' : 'Запустить импорт' }}
              </button>
            </div>

            <p v-if="importRequiresRescan" class="muted">
              Параметры сканирования изменены. Выполните шаг 1 повторно перед загрузкой.
            </p>

            <p v-if="importError" class="error">{{ importError }}</p>
            <p v-if="importSuccess" class="success-text">{{ importSuccess }}</p>
          </div>

          <div v-if="importScanResult" class="import-results">
            <article class="import-card">
              <h4>Результат сканирования</h4>
              <p class="muted">Лист: {{ importScanResult.sheet_name }} ({{ importScanResult.source_format }})</p>
              <p class="muted">
                Артефакты: merged cells {{ importScanResult.artifacts.merged_cells_count }},
                разделители {{ importScanResult.artifacts.sections_count }}
              </p>
              <div v-if="importDetectedSeparators.length > 0" class="separator-artifacts">
                <p class="muted">Найденные разделители:</p>
                <div class="separator-list">
                  <span v-for="(separator, index) in importVisibleSeparators" :key="`separator-${index}`" class="separator-pill" :title="separator">
                    {{ separator }}
                  </span>
                </div>
                <button v-if="importDetectedSeparators.length > 3" class="small ghost" @click="toggleAllSeparators">
                  {{ importShowAllSeparators ? 'Свернуть список' : `Показать все (${importDetectedSeparators.length})` }}
                </button>
              </div>
            </article>

            <article class="import-card">
              <div class="import-targets-head">
                <h4>Цели импорта</h4>
                <button class="small" @click="addImportTarget">Добавить цель</button>
              </div>

              <div v-if="importTargets.length === 0" class="muted">Добавьте цель импорта.</div>

              <div v-for="target in importTargets" :key="target.localId" class="import-target">
                <div class="import-target-row">
                  <label>Режим</label>
                  <select v-model="target.mode" @change="onImportTargetModeChange(target)">
                    <option value="existing">В существующую таблицу</option>
                    <option value="new">Создать новую таблицу</option>
                  </select>
                  <button class="small danger" @click="removeImportTarget(target.localId)">Удалить цель</button>
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

                    <select
                      v-if="target.mode === 'existing'"
                      v-model="target.column_mappings[sourceKey]"
                    >
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
                        (будет сокращен до {{ IMPORT_KEY_MAX_LENGTH }} символов)
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

        <section v-if="workspaceTab === 'reports'" class="reports-section">
          <div class="reports-header">
            <div>
              <h3>Отчеты</h3>
              <p>Создавайте Excel-выгрузки и публичные дашборды с настройками.</p>
            </div>
            <div class="reports-header-actions">
              <button class="small ghost" @click="openTemplateModal">Посчитать по шаблону</button>
              <button class="small" @click="createReport">Новый отчет</button>
            </div>
          </div>

          <div v-if="reportsLoading" class="muted">Загрузка отчетов...</div>
          <div v-if="reportsError" class="error">{{ reportsError }}</div>

          <div class="reports-grid" v-if="reports.length > 0">
            <article v-for="report in reports" :key="report.id" class="report-tile">
              <header>
                <h4>{{ report.name }}</h4>
                <span class="report-type">{{ getReportTypeLabel(report.report_type) }}</span>
              </header>
              <p>{{ report.description || 'Без описания' }}</p>
              <p class="muted">Статус: {{ report.is_published ? 'опубликован' : 'черновик' }}</p>
              <div class="report-actions">
                <button
                  v-if="report.report_type === 'excel_export'"
                  class="small"
                  @click="downloadReport(report.id)"
                >
                  Скачать
                </button>
                <button
                  v-else
                  class="small"
                  :disabled="!report.is_published"
                  @click="openReportPublicLink(report.id)"
                >
                  Ссылка
                </button>
                <button class="small" @click="editReport(report)">Редактировать</button>
                <button class="small danger" @click="deleteReport(report.id)">Удалить</button>
              </div>
            </article>
          </div>
          <p v-else-if="!reportsLoading" class="muted">Пока нет отчетов. Создайте первый.</p>

          <article v-if="reportEditorOpen" class="report-editor">
            <header>
              <h4>{{ selectedReport ? 'Редактирование отчета' : 'Новый отчет' }}</h4>
            </header>

            <div class="report-editor-grid">
              <div>
                <label>Название</label>
                <input v-model="reportName" placeholder="Например: Продажи за неделю" />
              </div>
              <div>
                <label>Тип отчета</label>
                <select v-model="reportType">
                  <option value="excel_export">Excel выгрузка</option>
                  <option value="dashboard">Публичный дашборд</option>
                </select>
              </div>
              <div>
                <label>Таблица источника</label>
                <select v-model.number="reportTableId" @change="onReportTableChange">
                  <option :value="null">Выберите таблицу</option>
                  <option v-for="table in allTableOptions" :key="`r-t-${table.id}`" :value="table.id">
                    {{ table.name }}
                  </option>
                </select>
              </div>
              <div>
                <label>Описание</label>
                <input v-model="reportDescription" placeholder="Коротко про назначение" />
              </div>
            </div>

            <label class="checkbox-inline">
              <input v-model="reportIsPublished" type="checkbox" /> Опубликовать
            </label>

            <section v-if="reportType === 'excel_export'" class="report-settings">
              <h5>Структура Excel</h5>
              <p class="muted">Выберите столбцы и подписи в выгрузке.</p>
              <div class="excel-columns" v-if="reportExcelColumns.length > 0">
                <div v-for="column in reportExcelColumns" :key="`excel-${column.key}`" class="excel-column-row">
                  <label class="checkbox-inline">
                    <input v-model="column.enabled" type="checkbox" /> {{ column.key }}
                  </label>
                  <input v-model="column.label" placeholder="Заголовок в Excel" />
                </div>
              </div>
              <p v-else class="muted">Сначала выберите таблицу.</p>
            </section>

            <section v-else class="report-settings">
              <h5>Настройки дашборда</h5>
              <div class="report-editor-grid compact">
                <div>
                  <label>Количество последних записей</label>
                  <input v-model.number="reportRecentLimit" type="number" min="1" max="100" />
                </div>
              </div>

              <div class="metrics-settings">
                <div class="metrics-header">
                  <strong>Метрики</strong>
                  <button class="small" @click="addDashboardMetric">Добавить метрику</button>
                </div>
                <div v-for="(metric, index) in reportMetrics" :key="`m-${index}`" class="metric-row">
                  <input v-model="metric.label" placeholder="Название метрики" />
                  <select v-model="metric.aggregation">
                    <option value="count">count</option>
                    <option value="sum">sum</option>
                    <option value="avg">avg</option>
                    <option value="min">min</option>
                    <option value="max">max</option>
                  </select>
                  <select v-model="metric.field_key" :disabled="metric.aggregation === 'count'">
                    <option value="">Поле</option>
                    <option
                      v-for="column in selectedReportTable?.columns || []"
                      :key="`mc-${column.key}`"
                      :value="column.key"
                    >
                      {{ column.name }}
                    </option>
                  </select>
                  <button class="small danger" @click="removeDashboardMetric(index)">Удалить</button>
                </div>
              </div>

              <div class="metrics-settings">
                <div class="metrics-header">
                  <strong>Графики (bar)</strong>
                  <button class="small" @click="addDashboardChart">Добавить график</button>
                </div>
                <div v-for="(chart, index) in reportCharts" :key="`c-${index}`" class="chart-row">
                  <input v-model="chart.title" placeholder="Название графика" />
                  <select v-model="chart.group_by_key">
                    <option value="">Группировать по полю</option>
                    <option
                      v-for="column in selectedReportTable?.columns || []"
                      :key="`cg-${column.key}`"
                      :value="column.key"
                    >
                      {{ column.name }}
                    </option>
                  </select>
                  <select v-model="chart.aggregation">
                    <option value="count">count</option>
                    <option value="sum">sum</option>
                    <option value="avg">avg</option>
                    <option value="min">min</option>
                    <option value="max">max</option>
                  </select>
                  <select v-model="chart.value_key" :disabled="chart.aggregation === 'count'">
                    <option value="">Поле значения</option>
                    <option
                      v-for="column in selectedReportTable?.columns || []"
                      :key="`cv-${column.key}`"
                      :value="column.key"
                    >
                      {{ column.name }}
                    </option>
                  </select>
                  <input v-model.number="chart.limit" type="number" min="1" max="30" placeholder="Top N" />
                  <button class="small danger" @click="removeDashboardChart(index)">Удалить</button>
                </div>
              </div>
            </section>

            <div class="report-editor-actions">
              <button class="small" @click="saveReport">Сохранить отчет</button>
              <button class="small ghost" @click="reportEditorOpen = false">Закрыть</button>
            </div>
          </article>

          <div v-if="templateModalOpen" class="template-modal-backdrop" @click.self="closeTemplateModal">
            <article class="template-modal">
              <header class="template-modal-header">
                <h4>Посчитать по шаблону</h4>
                <button class="small ghost" :disabled="templateUploading" @click="closeTemplateModal">Закрыть</button>
              </header>

              <p class="muted" v-pre>
                Поддерживаемые выражения в `.odt`: {{ count(key) }}, {{ sum(key) }}, {{ avg(key) }}, {{ min(key) }},
                {{ max(key) }}.
              </p>

              <label>Таблица источника</label>
              <select v-model.number="templateTableId" :disabled="templateUploading">
                <option :value="null">Выберите таблицу</option>
                <option v-for="table in allTableOptions" :key="`template-table-${table.id}`" :value="table.id">
                  {{ table.name }}
                </option>
              </select>

              <div
                class="template-dropzone"
                :class="{ active: templateDragActive, disabled: templateUploading }"
                @dragover="onTemplateDragOver"
                @dragleave="onTemplateDragLeave"
                @drop="onTemplateDrop"
              >
                <p>{{ templateUploading ? 'Обрабатываем шаблон...' : 'Перетащите сюда .odt файл' }}</p>
                <p class="muted">или</p>
                <button class="small" :disabled="templateUploading" @click="openTemplateFilePicker">
                  Выбрать файл
                </button>
                <p v-if="templateFileName" class="muted">Текущий файл: {{ templateFileName }}</p>
              </div>

              <input
                ref="templateFileInput"
                class="template-file-input"
                type="file"
                accept=".odt,application/vnd.oasis.opendocument.text"
                @change="onTemplateFileChange"
              />

              <p v-if="templateError" class="error">{{ templateError }}</p>
            </article>
          </div>
        </section>

        <section class="info-grid" v-if="workspaceTab === 'details'">
          <section class="info-card">
            <h3>Детали workspace</h3>
            <dl>
              <div>
                <dt>ID</dt>
                <dd>#{{ selectedWorkspace.id }}</dd>
              </div>
              <div>
                <dt>Владелец</dt>
                <dd>{{ authStore.me?.email }}</dd>
              </div>
              <div>
                <dt>Создан</dt>
                <dd>{{ formatDate(selectedWorkspace.created_at) }}</dd>
              </div>
            </dl>
          </section>
        </section>
      </article>

      <article v-else class="empty-content">
        <h2>Выберите workspace</h2>
        <p>Создайте новое пространство в боковой панели или выберите существующее из списка.</p>
      </article>
    </section>
  </main>
</template>

<style scoped>
.dashboard {
  min-height: 100vh;
  padding: 18px;
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: 16px;
}

.sidebar {
  background: var(--bg-panel);
  border-radius: 18px;
  border: 1px solid var(--line);
  padding: 16px;
  display: grid;
  gap: 14px;
  align-content: start;
}

.sidebar-header h1 {
  margin: 0;
  letter-spacing: 0.02em;
}

.sidebar-header p {
  margin: 6px 0 0;
  color: var(--text-muted);
}

h2,
h3,
h4 {
  margin: 0;
}

.create-widget,
.workspace-nav {
  border: 1px solid var(--line);
  border-radius: 14px;
  background: var(--bg-soft);
  padding: 12px;
}

.fields {
  display: grid;
  gap: 10px;
  margin-top: 10px;
}

input,
textarea,
select {
  border: 1px solid var(--line);
  background: #edf4f5;
  padding: 10px 12px;
  border-radius: 10px;
  color: var(--text-main);
  font: inherit;
}

textarea {
  resize: vertical;
}

button {
  border: none;
  background: var(--accent);
  color: #e8fbff;
  border-radius: 10px;
  padding: 10px 16px;
  font-weight: 700;
}

button.small {
  padding: 7px 10px;
  font-size: 0.84rem;
}

button.ghost {
  background: #d9e3e5;
  color: #1f353b;
}

button.danger {
  background: var(--danger);
  color: #fff;
}

ul {
  list-style: none;
  padding: 0;
  margin: 0;
}

.workspace-nav ul {
  display: grid;
  gap: 8px;
  margin-top: 10px;
}

.workspace-link {
  width: 100%;
  text-align: left;
  background: #dbe8ea;
  color: var(--text-main);
  border: 1px solid transparent;
  padding: 10px;
  border-radius: 10px;
  display: grid;
  gap: 4px;
}

.workspace-link.active {
  background: linear-gradient(135deg, #3c6f7f, #2b8f86);
  color: #f0fffd;
  border-color: #70ada5;
}

.workspace-link span,
.muted {
  color: var(--text-muted);
}

.workspace-link.active span {
  color: #c6f7f0;
}

.nav-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.nav-title span {
  border: 1px solid var(--line);
  border-radius: 999px;
  font-size: 0.82rem;
  padding: 2px 9px;
  color: var(--text-muted);
}

.content {
  border-radius: 18px;
  border: 1px solid var(--line);
  background: var(--bg-panel);
  padding: 20px;
}

.workspace-content header p {
  color: var(--text-muted);
  margin: 8px 0 0;
}

.workspace-tabs {
  margin-top: 14px;
  display: inline-flex;
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 4px;
  background: #e9f1f3;
}

.workspace-tabs .tab {
  background: transparent;
  color: var(--text-main);
  padding: 8px 14px;
  border-radius: 8px;
}

.workspace-tabs .tab.active {
  background: linear-gradient(135deg, #3d6f7d, #2b8e84);
  color: #effffd;
}

.actions-row {
  margin: 12px 0;
}

.designer {
  margin-top: 8px;
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 14px;
  background: var(--bg-soft);
  display: grid;
  gap: 14px;
}

.designer-header p {
  margin: 6px 0 0;
  color: var(--text-muted);
}

.create-table {
  display: grid;
  grid-template-columns: 1fr 1fr auto;
  gap: 8px;
}

.schema-layout {
  display: grid;
  grid-template-columns: minmax(620px, 1fr) 360px;
  gap: 12px;
}

.schema-canvas-wrap {
  border: 1px dashed var(--line);
  border-radius: 12px;
  background: linear-gradient(180deg, #ebf2f3 0%, #e4edf0 100%);
  overflow: auto;
}

.schema-canvas {
  position: relative;
  min-height: 640px;
  min-width: 940px;
}

.table-card {
  position: absolute;
  width: 280px;
  max-width: 280px;
  border: 1px solid #8ca8b1;
  border-radius: 12px;
  padding: 10px;
  background: #f3f8f9;
  display: grid;
  gap: 8px;
  box-shadow: 0 6px 14px rgba(38, 74, 85, 0.12);
  overflow: hidden;
}

.table-card.active {
  border-color: #2b8f86;
  box-shadow: inset 0 0 0 1px #2b8f86;
}

.table-head {
  display: flex;
  gap: 8px;
  align-items: center;
  cursor: pointer;
  min-width: 0;
}

.table-head strong {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.table-grip {
  background: #dce8ea;
  color: #45676f;
  border-radius: 6px;
  padding: 4px 6px;
  font-size: 0.74rem;
}

.table-sub {
  margin: 0;
  font-size: 0.83rem;
  color: var(--text-muted);
  overflow-wrap: anywhere;
}

.table-name-input,
.table-description-input {
  width: 100%;
}

.column-list {
  display: grid;
  gap: 6px;
}

.column-item {
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 8px;
  background: #f4f9fa;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  cursor: grab;
  min-width: 0;
}

.column-item div {
  display: grid;
  gap: 2px;
  min-width: 0;
  flex: 1;
}

.column-item strong,
.column-item span {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.column-item span {
  color: var(--text-muted);
  font-size: 0.82rem;
}

.column-item em {
  flex-shrink: 0;
  white-space: nowrap;
}

.column-item:hover {
  border-color: #7ea4ad;
}

.object-sidebar {
  border: 1px solid var(--line);
  border-radius: 12px;
  background: #eef5f7;
  padding: 10px;
  display: grid;
  gap: 10px;
  align-content: start;
  max-height: 640px;
  overflow: auto;
}

.object-card {
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 12px;
  background: #f7fbfc;
  display: grid;
  gap: 10px;
}

.new-column-form,
.type-settings,
.relation-form {
  display: grid;
  grid-template-columns: 1fr;
  gap: 8px;
  align-items: center;
}

.checkbox-inline {
  display: inline-flex;
  gap: 6px;
  align-items: center;
  color: var(--text-muted);
}

.setting-label {
  font-size: 0.84rem;
  color: var(--text-muted);
}

.add-column {
  width: fit-content;
}

.row-actions {
  display: flex;
  gap: 8px;
}

.relations {
  background: #edf5f7;
  display: grid;
  gap: 10px;
}

.relation-list {
  display: grid;
  gap: 8px;
}

.relation-list li {
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 9px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  background: #f7fbfb;
}

.relation-list span {
  color: var(--text-muted);
  font-size: 0.85rem;
}

.info-grid {
  margin-top: 14px;
}

.info-card {
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 14px;
  background: var(--bg-soft);
}

dl {
  margin: 0;
  display: grid;
  gap: 10px;
}

dt {
  font-size: 0.85rem;
  color: var(--text-muted);
}

dd {
  margin: 0;
  font-weight: 600;
}

.empty-content {
  min-height: 320px;
  display: grid;
  place-content: center;
  text-align: center;
  gap: 6px;
}

.error {
  color: var(--danger);
}

/* Form Builder Styles */
.forms-section {
  margin-top: 8px;
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 14px;
  background: var(--bg-soft);
  display: grid;
  gap: 14px;
}

.forms-header p {
  margin: 6px 0 0;
  color: var(--text-muted);
}

.forms-list ul {
  display: grid;
  gap: 6px;
}

.form-link {
  width: 100%;
  text-align: left;
  background: #dbe8ea;
  color: var(--text-main);
  border: 1px solid transparent;
  padding: 10px;
  border-radius: 10px;
  display: grid;
  gap: 4px;
}

.form-link.active {
  background: linear-gradient(135deg, #3c6f7f, #2b8f86);
  color: #f0fffd;
  border-color: #70ada5;
}

.form-link span {
  color: var(--text-muted);
  font-size: 0.82rem;
}

.form-link.active span {
  color: #c6f7f0;
}

.form-editor {
  display: grid;
  grid-template-columns: 1fr 340px;
  gap: 12px;
  margin-top: 8px;
}

.form-preview {
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 20px;
  background: #fafbfc;
}

.form-header {
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--line);
}

.form-header h4 {
  margin: 0 0 4px;
}

.form-header p {
  margin: 0;
  color: var(--text-muted);
  font-size: 0.9rem;
}

form {
  display: grid;
  gap: 14px;
}

.form-field-preview {
  display: grid;
  gap: 6px;
  border: 1px solid transparent;
  border-radius: 10px;
  padding: 8px;
  cursor: pointer;
}

.form-field-preview.active {
  border-color: #7ea4ad;
  background: #f2f8f9;
}

.form-field-preview label {
  font-weight: 600;
  font-size: 0.95rem;
  color: var(--text-main);
}

.required {
  color: var(--danger);
}

.form-field-preview input,
.form-field-preview textarea,
.form-field-preview select {
  width: 100%;
  border: 1px solid var(--line);
  background: #fff;
  padding: 10px 12px;
  border-radius: 8px;
  color: var(--text-main);
  font: inherit;
}

.form-field-preview input:focus,
.form-field-preview textarea:focus,
.form-field-preview select:focus {
  outline: 2px solid var(--accent);
  outline-offset: -1px;
}

.checkbox-wrapper,
.radio-wrapper {
  display: flex;
  gap: 8px;
  flex-direction: column;
}

.list-input-preview {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 8px;
}

.radio-wrapper label {
  display: flex;
  gap: 6px;
  align-items: center;
  font-weight: normal;
}

.checkbox-wrapper label {
  display: flex;
  gap: 6px;
  align-items: center;
  font-weight: normal;
}

.help-text {
  margin: 0;
  font-size: 0.85rem;
  color: var(--text-muted);
}

.field-table-label {
  margin: 0;
  font-size: 0.78rem;
  color: var(--text-muted);
}

.form-config {
  display: grid;
  gap: 10px;
  align-content: start;
}

.form-fields-list {
  display: grid;
  gap: 6px;
}

.form-fields-list li {
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 8px;
  background: #f7fbfc;
  display: grid;
  gap: 2px;
  cursor: grab;
}

.form-fields-list li.active {
  border-color: #7ea4ad;
  background: #eef6f8;
}

.form-fields-list li:active {
  cursor: grabbing;
}

.form-fields-list li:hover {
  border-color: #7ea4ad;
}

.form-fields-list div {
  display: grid;
}

.field-settings-row {
  display: grid;
  gap: 8px;
  margin-top: 8px;
}

.form-fields-list strong {
  font-size: 0.9rem;
}

.form-fields-list span {
  font-size: 0.8rem;
  color: var(--text-muted);
}

.share-link {
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 10px;
  background: #f7fbfc;
  display: flex;
  gap: 8px;
  align-items: center;
}

.share-link code {
  flex: 1;
  font-size: 0.85rem;
  color: var(--text-muted);
  word-break: break-all;
}

.form-config select[multiple] {
  min-height: 118px;
  background: #fff;
}

.options-editor {
  display: grid;
  gap: 8px;
}

.option-row,
.option-add-row {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 8px;
  align-items: center;
}

/* Data Viewer Styles */
.data-section {
  margin-top: 8px;
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 14px;
  background: var(--bg-soft);
  display: grid;
  gap: 14px;
}

.data-header p {
  margin: 6px 0 0;
  color: var(--text-muted);
}

.data-table-wrap {
  overflow-x: auto;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: #fafbfc;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9rem;
}

.data-table thead {
  background: #f0f4f5;
  border-bottom: 1px solid var(--line);
}

.data-table th {
  text-align: left;
  padding: 10px 12px;
  font-weight: 600;
  color: var(--text-main);
  white-space: nowrap;
}

.data-table td {
  padding: 10px 12px;
  border-bottom: 1px solid var(--line);
  color: var(--text-main);
}

.data-table tbody tr:hover {
  background-color: #f7fbfc;
}

.data-table td span {
  display: inline-block;
  max-width: 150px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.pagination {
  display: flex;
  gap: 12px;
  align-items: center;
  justify-content: center;
  padding: 12px;
  background: #f0f4f5;
  border-radius: 10px;
}

.pagination button {
  padding: 8px 12px;
  font-size: 0.9rem;
}

.pagination button:disabled {
  background: #d9e3e5;
  color: #7a8c92;
  cursor: not-allowed;
}

.pagination span {
  color: var(--text-muted);
  font-size: 0.9rem;
}

/* Import Styles */
.import-section {
  margin-top: 8px;
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 14px;
  background: var(--bg-soft);
  display: grid;
  gap: 14px;
}

.import-header p {
  margin: 6px 0 0;
  color: var(--text-muted);
}

.import-panel,
.import-card,
.import-target {
  border: 1px solid var(--line);
  border-radius: 10px;
  background: #f7fbfc;
  padding: 10px;
}

.import-panel,
.import-results,
.import-inputs,
.import-zones,
.mapping-grid {
  display: grid;
  gap: 10px;
}

.import-results,
.import-card,
.import-preview-card {
  min-width: 0;
}

.import-flow {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.flow-step {
  border: 1px solid var(--line);
  border-radius: 999px;
  padding: 4px 10px;
  font-size: 0.82rem;
  color: var(--text-muted);
  background: #edf4f6;
}

.flow-step.active {
  border-color: #2b8f86;
  color: #1f5a54;
  background: #e2f3ef;
}

.flow-step.warning {
  border-color: #d49f3f;
  color: #8b621f;
  background: #fff5df;
}

.zones-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(120px, 1fr));
  gap: 8px;
}

.import-targets-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.import-target-row {
  display: grid;
  grid-template-columns: 180px 1fr auto;
  gap: 8px;
  align-items: center;
  margin-bottom: 8px;
}

.import-target-grid {
  grid-template-columns: 1fr 1fr;
}

.mapping-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  align-items: center;
}

.mapping-hint {
  margin: 0;
  font-size: 0.78rem;
  color: var(--text-muted);
  grid-column: 1 / -1;
}

.mapping-warning,
.import-warning {
  color: #8b621f;
  font-size: 0.84rem;
}

.success-text {
  color: #276f45;
  font-weight: 600;
}

.import-preview-wrap {
  width: 100%;
  max-width: 100%;
  max-height: 360px;
  overflow-x: auto;
  overflow-y: auto;
}

.import-preview-card {
  overflow: hidden;
}

.import-preview-wrap .data-table {
  width: max-content;
  min-width: 100%;
  table-layout: fixed;
}

.import-preview-wrap .data-table th,
.import-preview-wrap .data-table td {
  min-width: 150px;
  max-width: 240px;
  white-space: normal;
  word-break: break-word;
  overflow-wrap: anywhere;
  vertical-align: top;
}

.import-preview-wrap .data-table td span {
  max-width: none;
  white-space: normal;
  overflow: visible;
  text-overflow: clip;
  display: block;
}

.separator-artifacts {
  display: grid;
  gap: 8px;
}

.separator-list {
  display: grid;
  gap: 6px;
  max-height: 190px;
  overflow: auto;
  padding-right: 4px;
}

.separator-pill {
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #eef6f8;
  color: var(--text-main);
  padding: 6px 8px;
  font-size: 0.84rem;
  line-height: 1.35;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Reports Styles */
.reports-section {
  margin-top: 8px;
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 14px;
  background: var(--bg-soft);
  display: grid;
  gap: 14px;
}

.reports-header {
  display: flex;
  justify-content: space-between;
  align-items: start;
  gap: 12px;
}

.reports-header p {
  margin: 6px 0 0;
  color: var(--text-muted);
}

.reports-header-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.reports-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 10px;
}

.report-tile {
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 12px;
  background: #f7fbfc;
  display: grid;
  gap: 8px;
}

.report-tile.active {
  border-color: #2b8f86;
  box-shadow: inset 0 0 0 1px #2b8f86;
}

.report-tile header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.report-tile h4 {
  margin: 0;
}

.report-type {
  font-size: 0.75rem;
  border: 1px solid #9fb8bf;
  border-radius: 999px;
  padding: 2px 8px;
  color: #355f6b;
  background: #ecf4f6;
}

.report-tile p {
  margin: 0;
}

.report-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.report-editor {
  border: 1px solid var(--line);
  border-radius: 12px;
  background: #f8fcfc;
  padding: 12px;
  display: grid;
  gap: 12px;
}

.report-editor-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(220px, 1fr));
  gap: 10px;
}

.report-editor-grid.compact {
  grid-template-columns: minmax(220px, 320px);
}

.report-editor-grid label,
.report-settings h5 {
  font-size: 0.9rem;
  color: var(--text-main);
}

.report-settings {
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 10px;
  background: #f3f9fa;
  display: grid;
  gap: 8px;
}

.report-settings h5 {
  margin: 0;
}

.excel-columns {
  display: grid;
  gap: 8px;
}

.excel-column-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  align-items: center;
}

.metrics-settings {
  display: grid;
  gap: 8px;
}

.metrics-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.metric-row {
  display: grid;
  grid-template-columns: 1fr 160px 1fr auto;
  gap: 8px;
  align-items: center;
}

.chart-row {
  display: grid;
  grid-template-columns: 1fr 1fr 140px 1fr 120px auto;
  gap: 8px;
  align-items: center;
}

.report-editor-actions {
  display: flex;
  gap: 8px;
}

.template-modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(25, 48, 57, 0.4);
  display: grid;
  place-items: center;
  z-index: 30;
  padding: 16px;
}

.template-modal {
  width: min(560px, 100%);
  border: 1px solid var(--line);
  border-radius: 14px;
  background: #f8fcfc;
  padding: 14px;
  display: grid;
  gap: 12px;
}

.template-modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.template-dropzone {
  border: 2px dashed #84a7ae;
  border-radius: 12px;
  background: #eef6f8;
  padding: 18px;
  display: grid;
  gap: 8px;
  justify-items: center;
  text-align: center;
}

.template-dropzone.active {
  border-color: #2b8f86;
  background: #e4f6f1;
}

.template-dropzone.disabled {
  opacity: 0.7;
}

.template-dropzone p {
  margin: 0;
}

.template-file-input {
  display: none;
}

@media (max-width: 1100px) {
  .create-table {
    grid-template-columns: 1fr;
  }

  .schema-layout {
    grid-template-columns: 1fr;
  }

  .schema-canvas {
    min-width: 100%;
  }

  .form-editor {
    grid-template-columns: 1fr;
  }

  .report-editor-grid,
  .metric-row,
  .chart-row,
  .excel-column-row,
  .zones-grid,
  .import-target-row,
  .mapping-row,
  .import-target-grid {
    grid-template-columns: 1fr;
  }

  .reports-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .reports-header-actions {
    justify-content: flex-start;
  }
}

@media (max-width: 760px) {
  .dashboard {
    grid-template-columns: 1fr;
  }

  .content {
    padding: 16px;
  }
}
</style>
