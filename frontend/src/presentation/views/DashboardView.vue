<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
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
import UiMultiSelect from '../components/common/UiMultiSelect.vue'
import UiSectionHeader from '../components/common/UiSectionHeader.vue'
import UiStatusText from '../components/common/UiStatusText.vue'
import DashboardDataSection from '../components/dashboard/DashboardDataSection.vue'
import DashboardImportSection from '../components/dashboard/DashboardImportSection.vue'
import DashboardSidebar from '../components/dashboard/DashboardSidebar.vue'
import DashboardTopBar from '../components/dashboard/DashboardTopBar.vue'
import DashboardTemplateModal from '../components/dashboard/DashboardTemplateModal.vue'
import DashboardTileActions from '../components/dashboard/DashboardTileActions.vue'
import DashboardTileCard from '../components/dashboard/DashboardTileCard.vue'
import DashboardUserModal from '../components/dashboard/DashboardUserModal.vue'
import DashboardWorkspaceModal from '../components/dashboard/DashboardWorkspaceModal.vue'

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
type ImportPreviewColumn = {
  id: string
  sourceKey: string
  outputKey: string
  outputName: string
  outputType: string
}
type ReportCreationKind = 'dashboard' | 'table_export'
const TABLE_LAYOUT_STORAGE_KEY = 'dashboard-table-layout'

const workspaces = ref<Workspace[]>([])
const loading = ref(false)
const deleting = ref(false)
const schemaLoading = ref(false)
const schemaError = ref('')
const workspaceTab = ref<WorkspaceTab>('tables')

const workspaceName = ref('')
const workspaceDescription = ref('')
const selectedWorkspaceId = ref<number | null>(null)
const createWorkspaceModalOpen = ref(false)
const workspaceCreateError = ref('')
const userModalOpen = ref(false)
const passwordChangeError = ref('')
const editWorkspaceName = ref('')
const editWorkspaceDescription = ref('')
const savingWorkspaceDetails = ref(false)

const tableStructures = ref<TableStructure[]>([])
const relations = ref<TableRelation[]>([])
const activeTableId = ref<number | null>(null)
const selectedColumnRef = ref<{ tableId: number; columnKey: string } | null>(null)
const tablePositions = ref<Record<number, TablePosition>>({})
const tableDragging = ref<{ tableId: number; offsetX: number; offsetY: number } | null>(null)
const schemaCanvasWrapRef = ref<HTMLElement | null>(null)

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
const importPreviewTargetLocalId = ref<number | null>(null)
const importShowAllSeparators = ref(false)
const importRequiresRescan = ref(false)
const IMPORT_KEY_MAX_LENGTH = 64

// Reports state
const reports = ref<ReportConfiguration[]>([])
const reportsLoading = ref(false)
const reportsError = ref('')
const selectedReportId = ref<number | null>(null)

const reportCreateModalOpen = ref(false)
const reportCreateKind = ref<ReportCreationKind>('dashboard')
const reportCreateSelectedTableIds = ref<number[]>([])
const reportEditorOpen = ref(false)
const reportName = ref('')
const reportDescription = ref('')
const reportType = ref<ReportType>('table_export')
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

const selectedWorkspace = computed(() => {
  if (selectedWorkspaceId.value === null) return null
  return workspaces.value.find((workspace) => workspace.id === selectedWorkspaceId.value) ?? null
})

const tableLayoutStorageKey = computed(() =>
  selectedWorkspace.value ? `${TABLE_LAYOUT_STORAGE_KEY}:${selectedWorkspace.value.id}` : null
)

const loadStoredTablePositions = (): Record<number, TablePosition> => {
  if (typeof window === 'undefined' || !tableLayoutStorageKey.value) return {}

  try {
    const raw = localStorage.getItem(tableLayoutStorageKey.value)
    if (!raw) return {}
    const parsed = JSON.parse(raw) as Record<string, TablePosition>
    return Object.fromEntries(
      Object.entries(parsed).filter(
        ([, position]) =>
          position &&
          typeof position.x === 'number' &&
          Number.isFinite(position.x) &&
          typeof position.y === 'number' &&
          Number.isFinite(position.y)
      )
        .map(([tableId, position]) => [Number(tableId), position])
    )
  } catch {
    return {}
  }
}

const persistTablePositions = () => {
  if (typeof window === 'undefined' || !tableLayoutStorageKey.value) return

  try {
    localStorage.setItem(tableLayoutStorageKey.value, JSON.stringify(tablePositions.value))
  } catch {
    // ignore storage write failures
  }
}

const nextWorkspaceName = computed(() => `WorkSpace ${workspaces.value.length + 1}`)

const workspaceStats = computed(() => {
  const tableCount = tableStructures.value.length
  const columnCount = tableStructures.value.reduce((total, table) => total + table.columns.length, 0)
  const formCount = formConfigurations.value.length
  const reportCount = reports.value.length
  const relationCount = relations.value.length
  return {
    tableCount,
    columnCount,
    formCount,
    reportCount,
    relationCount,
    avgColumnsPerTable: tableCount > 0 ? Math.round((columnCount / tableCount) * 10) / 10 : 0
  }
})

const statsMaxColumns = computed(() => {
  const max = Math.max(...tableStructures.value.map((table) => table.columns.length), 0)
  return max || 1
})

const tableColumnStats = computed(() =>
  tableStructures.value
    .map((table) => ({
      id: table.id,
      name: table.name,
      columns: table.columns.length,
      widthPercent: Math.max(8, Math.round((table.columns.length / statsMaxColumns.value) * 100))
    }))
    .slice(0, 8)
)

const canSaveWorkspaceDetails = computed(() => {
  const workspace = selectedWorkspace.value
  if (!workspace || savingWorkspaceDetails.value) return false

  const nextName = editWorkspaceName.value.trim()
  const nextDescription = editWorkspaceDescription.value.trim()
  const currentDescription = workspace.description ?? ''

  return nextName.length >= 2 && (nextName !== workspace.name || nextDescription !== currentDescription)
})

const activeTable = computed(() => {
  if (activeTableId.value === null) return null
  return tableStructures.value.find((table) => table.id === activeTableId.value) ?? null
})

const tableEditorName = computed({
  get: () => activeTable.value?.name ?? newTableName.value,
  set: (value: string) => {
    if (activeTable.value) {
      activeTable.value.name = value
      return
    }
    newTableName.value = value
  }
})

const tableEditorDescription = computed({
  get: () => activeTable.value?.description ?? newTableDescription.value,
  set: (value: string) => {
    if (activeTable.value) {
      activeTable.value.description = value
      return
    }
    newTableDescription.value = value
  }
})

const selectedDataTable = computed(() => {
  if (selectedDataTableId.value === null) return null
  return tableStructures.value.find((table) => table.id === selectedDataTableId.value) ?? null
})

const selectedReport = computed(() => {
  if (selectedReportId.value === null) return null
  return reports.value.find((report) => report.id === selectedReportId.value) ?? null
})

const reportCreateSelectedTables = computed(() => {
  const selected = new Set(reportCreateSelectedTableIds.value)
  return tableStructures.value.filter((table) => selected.has(table.id))
})

const selectedReportTable = computed(() => {
  if (reportTableId.value === null) return null
  return tableStructures.value.find((table) => table.id === reportTableId.value) ?? null
})

const importSourceKeys = computed(() => importScanResult.value?.detected_columns.map((col) => col.source_key) ?? [])
const importPreviewTarget = computed(() => {
  if (importTargets.value.length === 0) return null
  return (
    importTargets.value.find((target) => target.localId === importPreviewTargetLocalId.value) ??
    importTargets.value[0]
  )
})
const importPreviewTargetOptions = computed(() =>
  importTargets.value.map((target, index) => ({
    localId: target.localId,
    label:
      target.mode === 'existing'
        ? `Цель ${index + 1}: существующая таблица`
        : `Цель ${index + 1}: новая таблица ${target.table_name?.trim() ? `(${target.table_name.trim()})` : ''}`.trim()
  }))
)
const importPreviewColumns = computed<ImportPreviewColumn[]>(() => {
  if (!importScanResult.value || !importPreviewTarget.value) return []

  const target = importPreviewTarget.value
  const columns: ImportPreviewColumn[] = []

  if (target.mode === 'existing') {
    const table = tableStructures.value.find((item) => item.id === target.table_id)
    if (!table) return []

    importSourceKeys.value.forEach((sourceKey, index) => {
      const mappedKey = target.column_mappings[sourceKey]
      if (!mappedKey) return

      const targetColumn = table.columns.find((column) => column.key === mappedKey)
      if (!targetColumn) return

      columns.push({
        id: `${sourceKey}:${mappedKey}:${index}`,
        sourceKey,
        outputKey: targetColumn.key,
        outputName: targetColumn.name,
        outputType: targetColumn.type
      })
    })

    return columns
  }

  importSourceKeys.value.forEach((sourceKey, index) => {
    const mappedValue = target.column_mappings[sourceKey]
    if (!mappedValue) return

    const normalizedKey = normalizeImportKey(mappedValue)
    if (!normalizedKey) return

    const detected = importScanResult.value?.detected_columns.find((column) => column.source_key === sourceKey)
    const outputType = normalizeImportColumnType(target.column_types?.[sourceKey] || detected?.suggested_type)

    columns.push({
      id: `${sourceKey}:${normalizedKey}:${index}`,
      sourceKey,
      outputKey: normalizedKey,
      outputName: detected?.suggested_name || sourceKey,
      outputType
    })
  })

  return columns
})
const importPreviewRows = computed<Record<string, string>[]>(() => {
  if (!importScanResult.value || importPreviewColumns.value.length === 0) return []

  return (importScanResult.value.preview_rows ?? []).slice(0, 30).map((sourceRow) => {
    const row: Record<string, string> = {}
    importPreviewColumns.value.forEach((column) => {
      row[column.id] = formatImportValueByType(sourceRow[column.sourceKey], column.outputType)
    })
    return row
  })
})
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
    const storedPositions = loadStoredTablePositions()
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
      nextPositions[table.id] = storedPositions[table.id] ?? tablePositions.value[table.id] ?? {
        x: 20 + (index % 3) * 300,
        y: 20 + Math.floor(index / 3) * 260
      }
    }
    tablePositions.value = nextPositions
    persistTablePositions()
  } catch {
    schemaError.value = 'Не удалось загрузить low-code структуры.'
  } finally {
    schemaLoading.value = false
  }
}

const createWorkspace = async (): Promise<Workspace | null> => {
  if (!authStore.token || !workspaceName.value.trim()) return null

  workspaceCreateError.value = ''
  try {
    const createdWorkspace = await workspaceUseCase.create(
      authStore.token,
      workspaceName.value.trim(),
      workspaceDescription.value.trim()
    )
    workspaceName.value = ''
    workspaceDescription.value = ''
    await loadWorkspaces()
    selectedWorkspaceId.value = createdWorkspace.id
    workspaceTab.value = 'tables'
    await loadSchema()
    return createdWorkspace
  } catch (error: any) {
    workspaceCreateError.value = error?.response?.data?.detail || 'Не удалось создать workspace'
    return null
  }
}

const openCreateWorkspaceModal = () => {
  workspaceCreateError.value = ''
  createWorkspaceModalOpen.value = true
}

const closeCreateWorkspaceModal = () => {
  workspaceCreateError.value = ''
  createWorkspaceModalOpen.value = false
}

const createWorkspaceAndClose = async () => {
  const created = await createWorkspace()
  if (created) {
    closeCreateWorkspaceModal()
  }
}

const saveWorkspaceDetails = async () => {
  if (!authStore.token || !selectedWorkspace.value || !canSaveWorkspaceDetails.value) return

  savingWorkspaceDetails.value = true
  try {
    const updatedWorkspace = await workspaceUseCase.update(
      authStore.token,
      selectedWorkspace.value.id,
      editWorkspaceName.value.trim(),
      editWorkspaceDescription.value.trim() || undefined
    )

    const targetIndex = workspaces.value.findIndex((workspace) => workspace.id === updatedWorkspace.id)
    if (targetIndex !== -1) {
      workspaces.value[targetIndex] = updatedWorkspace
    }

    editWorkspaceName.value = updatedWorkspace.name
    editWorkspaceDescription.value = updatedWorkspace.description ?? ''
  } finally {
    savingWorkspaceDetails.value = false
  }
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

const deleteWorkspaceById = async (workspaceId: number) => {
  if (!authStore.token || deleting.value) return
  const workspace = workspaces.value.find((item) => item.id === workspaceId)
  if (!workspace) return

  const shouldDelete = window.confirm(
    `Удалить workspace \"${workspace.name}\"? Это действие нельзя отменить.`
  )
  if (!shouldDelete) return

  deleting.value = true
  try {
    await workspaceUseCase.delete(authStore.token, workspaceId)
    await loadWorkspaces()
    await loadSchema()
  } finally {
    deleting.value = false
  }
}

const onSidebarNavClick = async (tab: 'tables' | 'forms' | 'data' | 'reports') => {
  if (tab === 'tables') {
    workspaceTab.value = 'tables'
    return
  }

  if (tab === 'forms') {
    await goToFormsTab()
    return
  }

  if (tab === 'data') {
    await goToDataTab()
    return
  }

  await goToReportsTab()
}

const onTopBarCreateWorkspace = async (payload: { name: string; description: string }) => {
  workspaceName.value = payload.name
  workspaceDescription.value = payload.description
  await createWorkspaceAndClose()
  if (workspaceCreateError.value) {
    alert(workspaceCreateError.value)
  }
}

const goToDetailsTab = async () => {
  workspaceTab.value = 'details'
  if (selectedWorkspace.value) {
    await Promise.all([loadForms(), loadReports()])
  }
}

const openUserModal = () => {
  passwordChangeError.value = ''
  userModalOpen.value = true
}

const closeUserModal = () => {
  userModalOpen.value = false
}

const changePassword = async (payload: { currentPassword: string; newPassword: string }) => {
  passwordChangeError.value = ''
  try {
    await authStore.changePassword(payload.currentPassword, payload.newPassword)
  } catch (error: any) {
    passwordChangeError.value = error?.response?.data?.detail || authStore.error || 'Не удалось сменить пароль.'
  }
}

const onTopBarCreateTable = async () => {
  if (!newTableName.value.trim()) {
    newTableName.value = `Таблица ${tableStructures.value.length + 1}`
  }
  await createTable()
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
  const canvasEl = schemaCanvasWrapRef.value
  if (!drag || !canvasEl) return

  const canvasRect = canvasEl.getBoundingClientRect()
  const nextX = event.clientX - canvasRect.left - drag.offsetX
  const nextY = event.clientY - canvasRect.top - drag.offsetY

  tablePositions.value = {
    ...tablePositions.value,
    [drag.tableId]: {
      x: Math.max(20, nextX),
      y: Math.max(20, nextY)
    }
  }
  persistTablePositions()
}

const stopTableDrag = () => {
  tableDragging.value = null
}

const onTableCardPointerDown = (event: PointerEvent, tableId: number) => {
  const card = event.currentTarget as HTMLElement | null
  if (!card) return

  const cardRect = card.getBoundingClientRect()
  const position = getTablePosition(tableId)
  tableDragging.value = {
    tableId,
    offsetX: event.clientX - cardRect.left,
    offsetY: event.clientY - cardRect.top
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

const IMPORT_COLUMN_TYPES = new Set([
  'text',
  'number',
  'boolean',
  'date',
  'datetime',
  'enum',
  'list',
  'geoPoint',
  'geoPolygon'
])

const normalizeImportColumnType = (value: string | null | undefined): string => {
  const prepared = String(value || '').trim()
  return IMPORT_COLUMN_TYPES.has(prepared) ? prepared : 'text'
}

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
  const nextColumnTypes: Record<string, string | null> = {}
  if (target.mode === 'new') {
    for (const detected of importScanResult.value.detected_columns) {
      const hasSourceKey = Object.prototype.hasOwnProperty.call(target.column_mappings, detected.source_key)
      const current = target.column_mappings[detected.source_key]
      if (hasSourceKey && current === null) {
        nextMappings[detected.source_key] = null
        nextColumnTypes[detected.source_key] = null
        continue
      }

      nextMappings[detected.source_key] =
        typeof current === 'string' && current.trim().length > 0
          ? normalizeImportKey(current)
          : normalizeImportKey(detected.suggested_key || detected.source_key)

      const existingType = target.column_types?.[detected.source_key]
      nextColumnTypes[detected.source_key] = normalizeImportColumnType(existingType || detected.suggested_type)
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
  target.column_types = nextColumnTypes
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
    column_types: {},
    map_section_to_field: false,
    section_field_name: 'Раздел'
  }
  importTargetSeq.value += 1
  if (importScanResult.value) {
    syncImportTargetMappings(target)
  }
  importTargets.value.push(target)
  if (importPreviewTargetLocalId.value === null) {
    importPreviewTargetLocalId.value = target.localId
  }
}

const removeImportTarget = (localId: number) => {
  importTargets.value = importTargets.value.filter((target) => target.localId !== localId)
  if (importPreviewTargetLocalId.value === localId) {
    importPreviewTargetLocalId.value = importTargets.value[0]?.localId ?? null
  }
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
  importPreviewTargetLocalId.value = null
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

    if (!importPreviewTarget.value) {
      importPreviewTargetLocalId.value = importTargets.value[0]?.localId ?? null
    }
  } catch (error) {
    importError.value = 'Не удалось просканировать файл'
    console.error(error)
  } finally {
    importLoading.value = false
  }
}

const refreshImportPreview = async () => {
  if (!importScanResult.value || !importFile.value) return
  await scanImport()
  if (!importError.value) {
    importSuccess.value = 'Превью таблицы обновлено'
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
      column_types: target.mode === 'new'
        ? Object.fromEntries(
            Object.entries(target.column_types || {}).map(([source, selectedType]) => [
              source,
              target.column_mappings[source] ? normalizeImportColumnType(selectedType) : null
            ])
          )
        : {},
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

const parseImportDateCandidate = (value: unknown): Date | null => {
  const excelBase = new Date(Date.UTC(1899, 11, 30))

  const fromExcelSerial = (numeric: number): Date | null => {
    if (!Number.isFinite(numeric) || numeric < 0) return null
    const date = new Date(excelBase.getTime() + numeric * 24 * 60 * 60 * 1000)
    return Number.isNaN(date.getTime()) ? null : date
  }

  const fromUnix = (numeric: number): Date | null => {
    if (!Number.isFinite(numeric)) return null
    if (numeric > 1_000_000_000_000) {
      const msDate = new Date(numeric)
      return Number.isNaN(msDate.getTime()) ? null : msDate
    }
    if (numeric > 1_000_000_000) {
      const secDate = new Date(numeric * 1000)
      return Number.isNaN(secDate.getTime()) ? null : secDate
    }
    return null
  }

  if (value instanceof Date) {
    return Number.isNaN(value.getTime()) ? null : value
  }

  if (typeof value === 'number' && Number.isFinite(value)) {
    const unixDate = fromUnix(value)
    if (unixDate) return unixDate

    const excelDate = fromExcelSerial(value)
    if (excelDate) return excelDate

    return null
  }

  if (typeof value === 'string') {
    const trimmed = value.trim()
    if (!trimmed) return null

    const ruDateTime = trimmed.match(
      /^(\d{1,2})\.(\d{1,2})\.(\d{4})(?:\s+(\d{1,2}):(\d{2})(?::(\d{2}))?)?$/
    )
    if (ruDateTime) {
      const [, day, month, year, hour = '0', minute = '0', second = '0'] = ruDateTime
      const parsed = new Date(
        Number(year),
        Number(month) - 1,
        Number(day),
        Number(hour),
        Number(minute),
        Number(second)
      )
      return Number.isNaN(parsed.getTime()) ? null : parsed
    }

    const timeOnly = trimmed.match(/^(\d{1,2}):(\d{2})(?::(\d{2}))?$/)
    if (timeOnly) {
      const now = new Date()
      const [, hour, minute, second = '0'] = timeOnly
      const parsed = new Date(
        now.getFullYear(),
        now.getMonth(),
        now.getDate(),
        Number(hour),
        Number(minute),
        Number(second)
      )
      return Number.isNaN(parsed.getTime()) ? null : parsed
    }

    const numberLike = /^\d+(?:[\.,]\d+)?$/.test(trimmed)
    if (numberLike) {
      const numeric = Number(trimmed.replace(',', '.'))
      if (Number.isFinite(numeric)) {
        const unixDate = fromUnix(numeric)
        if (unixDate) return unixDate

        const excelDate = fromExcelSerial(numeric)
        if (excelDate) return excelDate
      }
    }

    const parsed = new Date(trimmed)
    return Number.isNaN(parsed.getTime()) ? null : parsed
  }

  return null
}

const formatImportValueByType = (value: unknown, targetType: string): string => {
  if (value === null || value === undefined || value === '') return '—'

  if (targetType === 'number') {
    const numeric = typeof value === 'number' ? value : Number(String(value).replace(',', '.'))
    return Number.isFinite(numeric) ? String(numeric) : '—'
  }

  if (targetType === 'boolean') {
    if (typeof value === 'boolean') return value ? 'Да' : 'Нет'
    const lowered = String(value).trim().toLowerCase()
    if (['true', '1', 'yes', 'да'].includes(lowered)) return 'Да'
    if (['false', '0', 'no', 'нет'].includes(lowered)) return 'Нет'
    return '—'
  }

  if (targetType === 'date' || targetType === 'datetime') {
    const parsed = parseImportDateCandidate(value)
    if (!parsed) return '—'

    if (targetType === 'date') {
      return new Intl.DateTimeFormat('ru-RU', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric'
      }).format(parsed)
    }

    return new Intl.DateTimeFormat('ru-RU', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    }).format(parsed)
  }

  return formatImportValue(value)
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
  if (type === 'table_export') return 'Табличная выгрузка'
  return 'Публичный дашборд'
}

const getReportCardTypeLabel = (report: ReportConfiguration) => {
  if (report.report_type !== 'table_export') {
    return 'Публичный дашборд'
  }

  return 'Табличная выгрузка'
}

const syncReportCreateSelectedTablesWithSchema = () => {
  const allowed = new Set(tableStructures.value.map((table) => table.id))
  reportCreateSelectedTableIds.value = reportCreateSelectedTableIds.value.filter((id) => allowed.has(id))
}

const openCreateReportModal = () => {
  if (!selectedWorkspace.value) return

  reportCreateKind.value = 'dashboard'
  reportName.value = ''
  reportDescription.value = ''
  reportIsPublished.value = false
  syncReportCreateSelectedTablesWithSchema()
  reportCreateSelectedTableIds.value = tableStructures.value[0]?.id ? [tableStructures.value[0].id] : []

  reportCreateModalOpen.value = true
}

const closeCreateReportModal = () => {
  reportCreateModalOpen.value = false
}

const onReportCreateTypeChange = () => {
  if (reportCreateSelectedTableIds.value.length === 0 && tableStructures.value.length > 0) {
    reportCreateSelectedTableIds.value = [tableStructures.value[0].id]
  }
}

const createReportFromModal = async () => {
  if (!selectedWorkspace.value || !reportName.value.trim()) return
  if (reportCreateSelectedTables.value.length === 0) {
    alert('Выберите хотя бы одну таблицу.')
    return
  }

  const reportTitle = reportName.value.trim()
  const reportDesc = reportDescription.value.trim()

  try {
    if (reportCreateKind.value === 'dashboard') {
      // Redirect to new dashboard editor
      reportCreateModalOpen.value = false
      await router.push({
        name: 'dashboard-create',
        params: { workspaceId: selectedWorkspace.value.id }
      })
    } else {
      const datasets = reportCreateSelectedTables.value
        .map((dataset, index) => ({
          id: `dataset_${index + 1}`,
          title: dataset.name,
          sheet_name: dataset.name.slice(0, 31) || `Sheet${index + 1}`,
          table_id: dataset.id,
          columns: [],
          aggregated_columns: [],
          group_by_columns: [],
          sorting: [],
          filters: []
        }))

      const settings: Record<string, unknown> = {
        datasets
      }

      const created = await reportUseCase.createReport(
        selectedWorkspace.value.id,
        reportTitle,
        reportDesc,
        'table_export',
        settings,
        reportIsPublished.value
      )

      reportCreateModalOpen.value = false
      await loadReports()
      await router.push({
        name: 'table-report-detail',
        params: { workspaceId: selectedWorkspace.value.id, reportId: created.id }
      })
    }
  } catch (error) {
    console.error(error)
    alert('Не удалось создать отчет')
  }
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
  reportType.value = 'table_export'
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
  syncReportCreateSelectedTablesWithSchema()
  await loadReports()
}

const createReport = () => {
  openCreateReportModal()
}

const editReport = (report: ReportConfiguration) => {
  if (!selectedWorkspace.value) return
  if (report.report_type === 'dashboard') {
    router.push({
      name: 'dashboard-detail',
      params: { workspaceId: selectedWorkspace.value.id, reportId: report.id }
    })
    return
  }
  router.push({
    name: 'table-report-detail',
    params: { workspaceId: selectedWorkspace.value.id, reportId: report.id }
  })
}

const onReportTableChange = () => {
  syncReportColumnsWithSelectedTable()
}

const saveReport = async () => {
  if (!selectedWorkspace.value || !reportName.value.trim() || !reportTableId.value) return

  const excelColumns = reportExcelColumns.value
    .filter((column) => column.enabled)
    .map((column) => ({ key: column.key, label: column.label || column.key }))

  const settings: Record<string, unknown> = { table_id: reportTableId.value }
  if (reportType.value === 'table_export') {
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

const openTableReportView = (reportId: number) => {
  if (!selectedWorkspace.value) return
  router.push({
    name: 'table-report-view',
    params: { workspaceId: selectedWorkspace.value.id, reportId }
  })
}

const downloadReport = async (reportId: number, format: 'xlsx' | 'csv' = 'xlsx') => {
  if (!selectedWorkspace.value) return

  const blob = await reportUseCase.downloadExcelReport(selectedWorkspace.value.id, reportId, format)
  const url = window.URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = format === 'xlsx' ? `report_${reportId}.xlsx` : `report_${reportId}.zip`
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

const saveDataRecord = async (payload: { recordId: number; data: Record<string, unknown> }) => {
  if (!authStore.token || !selectedWorkspace.value || !selectedDataTable.value) return

  try {
    await formBuilderUseCase.updateTableDataRecord(
      selectedWorkspace.value.id,
      selectedDataTable.value.id,
      payload.recordId,
      payload.data
    )
    await loadTableData()
  } catch (error) {
    console.error(error)
    alert('Ошибка при сохранении записи')
  }
}

const normalizeDateValue = (input: unknown): Date | null => {
  if (input instanceof Date) {
    return Number.isNaN(input.getTime()) ? null : input
  }

  if (typeof input === 'number' && Number.isFinite(input)) {
    const millis = input < 1_000_000_000_000 ? input * 1000 : input
    const date = new Date(millis)
    return Number.isNaN(date.getTime()) ? null : date
  }

  if (typeof input === 'string') {
    const trimmed = input.trim()
    if (!trimmed) return null

    if (/^\d+$/.test(trimmed)) {
      const numeric = Number(trimmed)
      if (Number.isFinite(numeric)) {
        const millis = numeric < 1_000_000_000_000 ? numeric * 1000 : numeric
        const dateFromNumeric = new Date(millis)
        if (!Number.isNaN(dateFromNumeric.getTime())) {
          return dateFromNumeric
        }
      }
    }

    const dateFromString = new Date(trimmed)
    return Number.isNaN(dateFromString.getTime()) ? null : dateFromString
  }

  return null
}

const formatDateOnly = (date: Date): string =>
  new Intl.DateTimeFormat('ru-RU', {
    day: '2-digit',
    month: 'long',
    year: 'numeric'
  }).format(date)

const formatDateTime = (date: Date): string =>
  new Intl.DateTimeFormat('ru-RU', {
    day: '2-digit',
    month: 'long',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  }).format(date)

const formatDataValue = (value: unknown, columnType: ColumnType): string => {
  if (value === null || value === undefined) return '—'

  if (columnType === 'date' || columnType === 'datetime') {
    const parsedDate = normalizeDateValue(value)
    if (parsedDate) {
      return columnType === 'date' ? formatDateOnly(parsedDate) : formatDateTime(parsedDate)
    }
  }

  if (typeof value === 'boolean') return value ? 'Да' : 'Нет'
  if (typeof value === 'object') return JSON.stringify(value).substring(0, 50) + '...'
  return String(value).substring(0, 80)
}

const formatDate = (value: unknown): string => {
  const date = normalizeDateValue(value)
  if (!date) return typeof value === 'string' ? value : String(value ?? '')
  return formatDateTime(date)
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

watch(
  () => selectedWorkspace.value,
  (workspace) => {
    if (!workspace) {
      editWorkspaceName.value = ''
      editWorkspaceDescription.value = ''
      return
    }

    editWorkspaceName.value = workspace.name
    editWorkspaceDescription.value = workspace.description ?? ''
  },
  { immediate: true }
)

onBeforeUnmount(() => {
  window.removeEventListener('pointermove', onCanvasPointerMove)
  window.removeEventListener('pointerup', stopTableDrag)
})
</script>

<template>
  <main class="dashboard">
    <DashboardSidebar
      :active-tab="workspaceTab"
      @nav-click="onSidebarNavClick"
      @open-profile="openUserModal"
      @logout="logout"
    />

    <section class="content">
      <article v-if="selectedWorkspace" class="workspace-content">
        <DashboardTopBar
          :workspaces="workspaces"
          :active-workspace-id="selectedWorkspaceId"
          :active-tab="workspaceTab"
          @select-workspace="selectWorkspace"
          @open-modal="openCreateWorkspaceModal"
          @delete-workspace="deleteWorkspaceById"
          @go-details="goToDetailsTab"
          @go-import="goToImportTab"
          @refresh-workspaces="loadWorkspaces"
          @create-table="onTopBarCreateTable"
          @create-form="createNewForm"
          @create-report="createReport"
        />

        <header class="workspace-header">
          <div class="workspace-title-group">
            <h2>{{ selectedWorkspace.name }}</h2>
            <p>{{ selectedWorkspace.description || 'Описание пока не добавлено' }}</p>
          </div>
        </header>

        <DashboardTileActions v-if="workspaceTab === 'details'" class="actions-row">
          <button class="danger" :disabled="deleting" @click="deleteWorkspace">
            {{ deleting ? 'Удаляем...' : 'Удалить workspace' }}
          </button>
        </DashboardTileActions>

        <section v-if="workspaceTab === 'tables'" class="designer">
          <div class="table-workspace">
            <aside class="table-editor-pane">
              <section class="object-card table-editor-card">
                <h3>{{ activeTable ? activeTable.name : 'Создать таблицу' }}</h3>
                <p class="muted">
                  {{ activeTable ? 'Редактируйте таблицу и её описание.' : 'Добавьте новую таблицу в workspace.' }}
                </p>
                <input
                  v-model="tableEditorName"
                  :placeholder="activeTable ? 'Имя таблицы' : 'Новая таблица: название'"
                  maxlength="255"
                />
                <textarea
                  v-model="tableEditorDescription"
                  :placeholder="activeTable ? 'Описание таблицы' : 'Описание таблицы'"
                  rows="4"
                  maxlength="255"
                />
                <DashboardTileActions>
                  <button v-if="activeTable" class="small" @click="saveTable(activeTable)">Сохранить таблицу</button>
                  <button v-else class="small" @click="createTable">Добавить таблицу</button>
                  <button v-if="activeTable" class="small danger" @click="deleteActiveTable">Удалить таблицу</button>
                </DashboardTileActions>
              </section>

              <section class="object-card table-editor-card" v-if="activeTable">
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
            </aside>

            <div class="table-canvas-shell">
              <div class="designer-header">
                <h3>Low-code структуры таблиц</h3>
                <p>Перемещайте таблицы по полю и переносите колонки drag-and-drop между таблицами.</p>
              </div>

              <UiStatusText v-if="schemaLoading">Загрузка структуры...</UiStatusText>
              <UiStatusText v-if="schemaError" variant="error">{{ schemaError }}</UiStatusText>

              <div ref="schemaCanvasWrapRef" class="schema-canvas-wrap">
                <div class="schema-canvas">
                  <article
                    v-for="table in tableStructures"
                    :key="table.id"
                    class="table-card"
                    :class="{ active: activeTableId === table.id }"
                    :style="{ left: `${getTablePosition(table.id).x}px`, top: `${getTablePosition(table.id).y}px` }"
                    @pointerdown.left="onTableCardPointerDown($event, table.id)"
                    @dragover.prevent
                    @drop="onDropColumnToTable(table.id)"
                  >
                    <div class="table-head" @click="selectTable(table.id)">
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
            </div>
          </div>
        </section>

        <section v-if="workspaceTab === 'forms'" class="forms-section">
          <UiSectionHeader
            title="Конструктор форм"
            description="Создавайте несколько форм для одной таблицы или для набора таблиц."
          >
            <template #actions>
              <button class="small" @click="createNewForm">Новая форма</button>
            </template>
          </UiSectionHeader>

          <UiStatusText v-if="formLoading" as="div">Загрузка форм...</UiStatusText>
          <UiStatusText v-if="formError" as="div" variant="error">{{ formError }}</UiStatusText>

          <div class="reports-grid" v-if="formConfigurations.length > 0">
            <DashboardTileCard
              v-for="form in formConfigurations"
              :key="form.id"
              :active="selectedFormId === form.id"
            >
              <template #title>
                <h4>{{ form.name }}</h4>
              </template>
              <template #badge>
                <span class="report-type">{{ form.is_published ? 'Публичная' : 'Черновик' }}</span>
              </template>
              <p>{{ form.description || 'Без описания' }}</p>
              <p class="muted">Поля: {{ form.fields.length }}</p>
              <p class="muted">Таблицы: {{ getFormUsedTableNames(form) }}</p>
              <template #actions>
                <DashboardTileActions>
                  <button
                    class="small"
                    :disabled="!form.is_published"
                    @click="openFormPublicLink(form.id)"
                  >
                    Ссылка
                  </button>
                  <button class="small" @click="selectForm(form.id)">Редактировать</button>
                  <button class="small danger" @click="deleteForm(form.id)">Удалить</button>
                </DashboardTileActions>
              </template>
            </DashboardTileCard>
          </div>
          <UiStatusText v-else-if="!formLoading">Пока нет форм. Создайте первую.</UiStatusText>

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

        <DashboardDataSection
          v-if="workspaceTab === 'data'"
          :selected-data-table="selectedDataTable"
          :table-data-records="tableDataRecords"
          :data-pagination="dataPagination"
          :data-loading="dataLoading"
          :data-error="dataError"
          :total-pages="totalPages"
          :current-page="currentPage"
          :all-table-options="allTableOptions"
          :selected-data-table-id="selectedDataTableId"
          :format-data-value="formatDataValue"
          :format-date="formatDate"
          @update:selected-data-table-id="selectedDataTableId = $event"
          @update:data-limit="dataPagination.limit = $event"
          @data-table-change="onDataTableChange"
          @data-limit-change="onDataLimitChange"
          @delete-record="deleteDataRecord"
          @save-record="saveDataRecord"
          @go-to-page="goToPage"
        />

        <DashboardImportSection
          v-if="workspaceTab === 'import'"
          :import-scan-result="importScanResult"
          :import-requires-rescan="importRequiresRescan"
          :import-can-apply="importCanApply"
          :import-file="importFile"
          :import-loading="importLoading"
          :import-applying="importApplying"
          :import-header-row-start="importHeaderRowStart"
          :import-header-row-end="importHeaderRowEnd"
          :import-data-row-start="importDataRowStart"
          :import-data-row-end="importDataRowEnd"
          :import-list-delimiters="importListDelimiters"
          :import-targets="importTargets"
          :all-table-options="allTableOptions"
          :import-source-keys="importSourceKeys"
          :import-preview-columns="importPreviewColumns"
          :import-preview-rows="importPreviewRows"
          :import-preview-target-local-id="importPreviewTargetLocalId"
          :import-preview-target-options="importPreviewTargetOptions"
          :import-detected-separators="importDetectedSeparators"
          :import-visible-separators="importVisibleSeparators"
          :import-show-all-separators="importShowAllSeparators"
          :import-error="importError"
          :import-success="importSuccess"
          :import-key-max-length="IMPORT_KEY_MAX_LENGTH"
          :get-import-target-columns="getImportTargetColumns"
          :format-mapped-key-preview="formatMappedKeyPreview"
          :is-mapped-key-truncated="isMappedKeyTruncated"
          :on-import-target-mode-change="onImportTargetModeChange"
          :on-import-target-table-change="onImportTargetTableChange"
          @update:import-header-row-start="importHeaderRowStart = $event"
          @update:import-header-row-end="importHeaderRowEnd = $event"
          @update:import-data-row-start="importDataRowStart = $event"
          @update:import-data-row-end="importDataRowEnd = $event"
          @update:import-list-delimiters="importListDelimiters = $event"
          @update:import-preview-target-local-id="importPreviewTargetLocalId = $event"
          @import-file-change="onImportFileChange"
          @import-scan-options-change="onImportScanOptionsChanged"
          @scan-import="scanImport"
          @refresh-import-preview="refreshImportPreview"
          @apply-import="applyImport"
          @toggle-separators="toggleAllSeparators"
          @add-import-target="addImportTarget"
          @remove-import-target="removeImportTarget"
        />

        <section v-if="workspaceTab === 'reports'" class="reports-section">
          <UiSectionHeader
            title="Отчеты"
            description="Создавайте Excel-выгрузки и публичные дашборды с настройками."
          >
            <template #actions>
              <DashboardTileActions>
                <button class="small ghost" @click="openTemplateModal">Посчитать по шаблону</button>
                <button class="small" @click="createReport">Новый отчет</button>
              </DashboardTileActions>
            </template>
          </UiSectionHeader>

          <UiStatusText v-if="reportsLoading" as="div">Загрузка отчетов...</UiStatusText>
          <UiStatusText v-if="reportsError" as="div" variant="error">{{ reportsError }}</UiStatusText>

          <div class="reports-grid" v-if="reports.length > 0">
            <DashboardTileCard v-for="report in reports" :key="report.id">
              <template #title>
                <h4>{{ report.name }}</h4>
              </template>
              <template #badge>
                <span class="report-type">{{ getReportCardTypeLabel(report) }}</span>
              </template>
              <p>{{ report.description || 'Без описания' }}</p>
              <p class="muted">Статус: {{ report.is_published ? 'опубликован' : 'черновик' }}</p>
              <template #actions>
                <DashboardTileActions>
                  <button
                    v-if="report.report_type === 'table_export'"
                    class="small"
                    @click="openTableReportView(report.id)"
                  >
                    Открыть
                  </button>
                  <button
                    v-if="report.report_type === 'table_export'"
                    class="small"
                    @click="downloadReport(report.id, 'csv')"
                  >
                    CSV
                  </button>
                  <button
                    v-if="report.report_type === 'table_export'"
                    class="small"
                    @click="downloadReport(report.id, 'xlsx')"
                  >
                    Excel
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
                </DashboardTileActions>
              </template>
            </DashboardTileCard>
          </div>
          <UiStatusText v-else-if="!reportsLoading">Пока нет отчетов. Создайте первый.</UiStatusText>

          <div v-if="reportCreateModalOpen" class="report-create-modal-backdrop" @click.self="closeCreateReportModal">
            <article class="report-create-modal">
              <header class="report-create-head">
                <h4>Новый отчет</h4>
                <button class="small ghost" @click="closeCreateReportModal">Закрыть</button>
              </header>

              <div class="report-create-grid">
                <div>
                  <label>Название</label>
                  <input v-model="reportName" placeholder="Например: Сводка по продажам" />
                </div>
                <div>
                  <label>Тип отчета</label>
                  <select v-model="reportCreateKind" @change="onReportCreateTypeChange">
                    <option value="dashboard">Дашборд</option>
                    <option value="table_export">Табличная выгрузка (Excel/CSV)</option>
                  </select>
                </div>
                <div class="report-create-full">
                  <label>Описание</label>
                  <input v-model="reportDescription" placeholder="Коротко про назначение отчета" />
                </div>
              </div>

              <label class="checkbox-inline">
                <input v-model="reportIsPublished" type="checkbox" /> Опубликовать сразу
              </label>

              <section v-if="reportCreateKind === 'dashboard'" class="report-create-section">
                <h5>Таблицы для дашборда</h5>
                <p class="muted">Выберите одну или несколько таблиц. Базовая конфигурация будет создана автоматически.</p>

                <div class="report-create-grid">
                  <div class="report-create-full">
                    <label>Таблицы</label>
                    <UiMultiSelect
                      v-model="reportCreateSelectedTableIds"
                      :options="allTableOptions"
                      placeholder="Выберите таблицы для дашборда"
                      @change="onReportCreateTypeChange"
                    />
                  </div>
                </div>
              </section>

              <section v-else class="report-create-section">
                <h5>Таблицы для табличного отчета</h5>
                <p class="muted">Выберите таблицы через мультиселект. Столбцы, порядок и листы настраиваются в детальном редакторе.</p>

                <div class="report-create-grid">
                  <div class="report-create-full">
                    <label>Таблицы</label>
                    <UiMultiSelect
                      v-model="reportCreateSelectedTableIds"
                      :options="allTableOptions"
                      placeholder="Выберите таблицы для табличного отчета"
                      @change="onReportCreateTypeChange"
                    />
                  </div>
                </div>
              </section>

              <DashboardTileActions>
                <button class="small" @click="createReportFromModal">Создать отчет</button>
                <button class="small ghost" @click="closeCreateReportModal">Отмена</button>
              </DashboardTileActions>
            </article>
          </div>

          <DashboardTemplateModal
            :open="templateModalOpen"
            :uploading="templateUploading"
            :drag-active="templateDragActive"
            :error="templateError"
            :file-name="templateFileName"
            :table-id="templateTableId"
            :table-options="allTableOptions"
            @close="closeTemplateModal"
            @update:table-id="templateTableId = $event"
            @drag-over="onTemplateDragOver"
            @drag-leave="onTemplateDragLeave"
            @drop="onTemplateDrop"
            @file-selected="processTemplateFile"
          />
        </section>

        <section class="info-grid" v-if="workspaceTab === 'details'">
          <section class="info-card workspace-stats-card">
            <h3>Статистика workspace</h3>
            <div class="stats-kpi-grid">
              <article class="stats-kpi">
                <span>Таблиц</span>
                <strong>{{ workspaceStats.tableCount }}</strong>
              </article>
              <article class="stats-kpi">
                <span>Колонок</span>
                <strong>{{ workspaceStats.columnCount }}</strong>
              </article>
              <article class="stats-kpi">
                <span>Форм</span>
                <strong>{{ workspaceStats.formCount }}</strong>
              </article>
              <article class="stats-kpi">
                <span>Отчетов</span>
                <strong>{{ workspaceStats.reportCount }}</strong>
              </article>
              <article class="stats-kpi">
                <span>Связей</span>
                <strong>{{ workspaceStats.relationCount }}</strong>
              </article>
              <article class="stats-kpi">
                <span>Ср. колонок/таблица</span>
                <strong>{{ workspaceStats.avgColumnsPerTable }}</strong>
              </article>
            </div>

            <div class="stats-bars">
              <h4>Насыщенность таблиц полями</h4>
              <div v-if="tableColumnStats.length" class="stats-bar-list">
                <div v-for="item in tableColumnStats" :key="item.id" class="stats-bar-row">
                  <span class="stats-bar-label" :title="item.name">{{ item.name }}</span>
                  <div class="stats-bar-track">
                    <div class="stats-bar-fill" :style="{ width: `${item.widthPercent}%` }" />
                  </div>
                  <strong class="stats-bar-value">{{ item.columns }}</strong>
                </div>
              </div>
              <p v-else class="muted">Таблицы еще не созданы.</p>
            </div>
          </section>

          <section class="info-card">
            <h3>Редактировать workspace</h3>
            <div class="workspace-edit-form">
              <input v-model="editWorkspaceName" type="text" placeholder="Название" maxlength="255" />
              <textarea v-model="editWorkspaceDescription" rows="4" placeholder="Описание (опционально)" maxlength="2000" />
              <DashboardTileActions>
                <button class="small" :disabled="!canSaveWorkspaceDetails" @click="saveWorkspaceDetails">
                  {{ savingWorkspaceDetails ? 'Сохраняем...' : 'Сохранить изменения' }}
                </button>
              </DashboardTileActions>
            </div>
          </section>

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

      <DashboardWorkspaceModal
        v-if="createWorkspaceModalOpen"
        :default-name="nextWorkspaceName"
        @create="onTopBarCreateWorkspace"
        @close="closeCreateWorkspaceModal"
      />

      <DashboardUserModal
        v-if="userModalOpen"
        :email="authStore.me?.email || 'unknown@local'"
        :user-id="authStore.me?.id ?? null"
        :loading="authStore.loading"
        :error="passwordChangeError"
        @close="closeUserModal"
        @change-password="changePassword"
      />

      <article v-if="!selectedWorkspace" class="empty-content">
        <h2>У вас пока нет workspace</h2>
        <p>Создайте первое пространство, чтобы начать работу с таблицами, формами, импортом и отчетами.</p>
        <div class="empty-content-actions">
          <button @click="openCreateWorkspaceModal">Создать workspace</button>
        </div>
      </article>
    </section>
  </main>
</template>

<style scoped src="../styles/dashboard/dashboard-view.css"></style>
