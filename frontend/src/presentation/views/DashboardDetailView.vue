<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { FormBuilderUseCase } from '../../application/usecases/FormBuilderUseCase'
import { ReportUseCase } from '../../application/usecases/ReportUseCase'
import { TableSchemaUseCase } from '../../application/usecases/TableSchemaUseCase'
import type { TableDataRecord } from '../../domain/entities/FormBuilder'
import type { ReportConfiguration } from '../../domain/entities/Report'
import type { ColumnDefinition, TableStructure } from '../../domain/entities/TableSchema'
import { useAuthStore } from '../stores/authStore'

type WidgetType = 'metric' | 'chart' | 'table' | 'gauge' | 'text' | 'map'
type AggregationType = 'count' | 'sum' | 'avg' | 'min' | 'max'
type ChartType = 'bar' | 'line' | 'pie' | 'area' | 'histogram'
type WidgetInteraction = 'none' | 'highlight' | 'filter' | 'drilldown'

interface DashboardWidget {
  id: string
  type: WidgetType
  title: string
  description?: string
  gridX: number
  gridY: number
  gridWidth: number
  gridHeight: number
  sourceTableId: number | null
  fieldKey?: string
  aggregation?: AggregationType
  groupByKey?: string | null
  chartType?: ChartType
  colorScheme?: string
  interaction?: WidgetInteraction
  contentScale?: number
  tableColumns?: string[]
  filterColumnKey?: string | null
  filterValue?: string
  pageSize?: number
  geoLatKey?: string | null
  geoLngKey?: string | null
}

interface TablePreviewState {
  rows: TableDataRecord[]
  filteredTotal: number
  page: number
  loading: boolean
  error: string
}

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const workspaceId = computed(() => Number(route.params.workspaceId))
const reportId = computed(() => (route.params.reportId ? Number(route.params.reportId) : null))
const isCreateMode = computed(() => route.name === 'dashboard-create')

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
const widgets = ref<DashboardWidget[]>([])

const selectedWidgetId = ref<string | null>(null)
const previewModalOpen = ref(false)
const dashboardPreviewOpen = ref(false)
const editingWidgetId = ref<string | null>(null)
const draggedWidget = ref<DashboardWidget | null>(null)

const tablePreviewState = ref<Record<string, TablePreviewState>>({})

const gridCols = ref(12)
const gridRows = ref(20)
const cellSize = ref(64)

const canvasStyle = computed(() => ({
  gridTemplateColumns: `repeat(${gridCols.value}, ${cellSize.value}px)`,
  gridTemplateRows: `repeat(${gridRows.value}, ${cellSize.value}px)`,
  width: `${gridCols.value * cellSize.value}px`,
  minHeight: `${gridRows.value * cellSize.value}px`,
  '--cell-size': `${cellSize.value}px`,
}))

const WIDGET_TYPES: Array<{ id: WidgetType; name: string; icon: string; description: string }> = [
  { id: 'metric', name: 'Счетчик', icon: '01', description: 'Count, Sum, Avg, Min, Max' },
  { id: 'chart', name: 'График', icon: '02', description: 'Line, Bar, Pie, Area, Histogram' },
  { id: 'table', name: 'Таблица', icon: '03', description: 'Данные таблицы + фильтр + пагинация' },
  { id: 'gauge', name: 'Индикатор', icon: '04', description: 'Процентный или KPI индикатор' },
  { id: 'text', name: 'Текст', icon: '05', description: 'Текстовый блок с описанием' },
  { id: 'map', name: 'Карта', icon: '06', description: 'Карта по полям координат' },
]

const selectedWidget = computed(() => widgets.value.find((w) => w.id === selectedWidgetId.value) ?? null)
const editingWidget = computed(() => widgets.value.find((w) => w.id === editingWidgetId.value) ?? null)

const selectedWidgetTable = computed(() => {
  if (!selectedWidget.value?.sourceTableId) return null
  return tables.value.find((table) => table.id === selectedWidget.value?.sourceTableId) ?? null
})

const selectedWidgetColumns = computed(() => selectedWidgetTable.value?.columns ?? [])

const selectedTablePreview = computed(() => {
  if (!selectedWidget.value) return null
  return tablePreviewState.value[selectedWidget.value.id] ?? null
})

const modalTablePreview = computed(() => {
  if (!editingWidget.value) return null
  return tablePreviewState.value[editingWidget.value.id] ?? null
})

const modalPreviewColumns = computed(() => {
  if (!editingWidget.value) return []
  if (editingWidget.value.type === 'table') return displayedColumns(editingWidget.value)

  const preferred = [editingWidget.value.groupByKey, editingWidget.value.fieldKey, editingWidget.value.filterColumnKey]
    .filter((value): value is string => Boolean(value && value.trim()))
  const available = getColumnsByTableId(editingWidget.value.sourceTableId).map((column) => column.key)
  return Array.from(new Set([...preferred, ...available])).slice(0, 5)
})

const modalPreviewRows = computed(() => {
  if (!editingWidget.value) return []
  const state = tablePreviewState.value[editingWidget.value.id]
  if (!state) return []
  return state.rows.slice(0, 8)
})

function createWidget(type: WidgetType): DashboardWidget {
  const index = widgets.value.length
  const baseX = (index * 3) % gridCols.value
  const baseY = Math.floor(index / 3) * 3

  const defaultSize: Record<WidgetType, { w: number; h: number }> = {
    metric: { w: 3, h: 2 },
    chart: { w: 6, h: 4 },
    table: { w: 8, h: 5 },
    gauge: { w: 3, h: 3 },
    text: { w: 4, h: 2 },
    map: { w: 6, h: 5 },
  }

  const size = defaultSize[type]

  return {
    id: `widget_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`,
    type,
    title: `${WIDGET_TYPES.find((w) => w.id === type)?.name || 'Widget'} ${index + 1}`,
    description: '',
    gridX: Math.max(0, Math.min(gridCols.value - size.w, baseX)),
    gridY: Math.max(0, baseY),
    gridWidth: size.w,
    gridHeight: size.h,
    sourceTableId: null,
    fieldKey: '',
    aggregation: 'count',
    groupByKey: null,
    chartType: 'bar',
    colorScheme: 'default',
    interaction: 'none',
    contentScale: 1,
    tableColumns: [],
    filterColumnKey: null,
    filterValue: '',
    pageSize: 10,
    geoLatKey: null,
    geoLngKey: null,
  }
}

function addWidget(type: WidgetType) {
  const widget = createWidget(type)
  widgets.value.push(widget)
  selectedWidgetId.value = widget.id
  ensureTablePreviewState(widget.id)
}

async function openPreviewModal(widgetId?: string) {
  const nextId = widgetId || selectedWidgetId.value || widgets.value[0]?.id || null
  if (!nextId) return

  editingWidgetId.value = nextId
  previewModalOpen.value = true

  const widget = widgets.value.find((item) => item.id === nextId)
  if (!widget) return

  ensureTablePreviewState(widget.id)
  if (widget.type === 'table' || widget.type === 'chart' || widget.type === 'metric' || widget.type === 'gauge') {
    await loadTablePreview(widget)
  }
}

async function openDashboardPreview() {
  dashboardPreviewOpen.value = true
  for (const widget of widgets.value) {
    ensureTablePreviewState(widget.id)
    if (widget.type === 'table' || widget.type === 'chart' || widget.type === 'metric' || widget.type === 'gauge') {
      await loadTablePreview(widget)
    }
  }
}

function removeWidget(widgetId: string) {
  widgets.value = widgets.value.filter((widget) => widget.id !== widgetId)
  delete tablePreviewState.value[widgetId]

  if (selectedWidgetId.value === widgetId) {
    selectedWidgetId.value = widgets.value[0]?.id ?? null
  }

  if (editingWidgetId.value === widgetId) {
    editingWidgetId.value = null
    previewModalOpen.value = false
  }
}

function ensureTablePreviewState(widgetId: string): TablePreviewState {
  if (!tablePreviewState.value[widgetId]) {
    tablePreviewState.value[widgetId] = {
      rows: [],
      filteredTotal: 0,
      page: 1,
      loading: false,
      error: '',
    }
  }

  return tablePreviewState.value[widgetId]
}

function updateWidget(widgetId: string, updates: Partial<DashboardWidget>) {
  widgets.value = widgets.value.map((widget) => (widget.id === widgetId ? { ...widget, ...updates } : widget))
}

function updateWidgetSize(widgetId: string, width: number, height: number) {
  const widget = widgets.value.find((w) => w.id === widgetId)
  if (!widget) return

  const nextWidth = Math.max(1, Math.min(gridCols.value, width))
  const nextHeight = Math.max(1, Math.min(gridRows.value, height))
  const nextX = Math.max(0, Math.min(gridCols.value - nextWidth, widget.gridX))

  updateWidget(widgetId, {
    gridX: nextX,
    gridWidth: nextWidth,
    gridHeight: nextHeight,
  })
}

function moveWidget(widgetId: string, direction: 'up' | 'down' | 'left' | 'right') {
  const widget = widgets.value.find((w) => w.id === widgetId)
  if (!widget) return

  const delta = {
    up: { x: 0, y: -1 },
    down: { x: 0, y: 1 },
    left: { x: -1, y: 0 },
    right: { x: 1, y: 0 },
  }[direction]

  const nextX = Math.max(0, Math.min(gridCols.value - widget.gridWidth, widget.gridX + delta.x))
  const nextY = Math.max(0, Math.min(gridRows.value - widget.gridHeight, widget.gridY + delta.y))

  updateWidget(widgetId, { gridX: nextX, gridY: nextY })
}

function onSourceTableChange(widgetId: string, tableIdRaw: string) {
  const tableId = Number(tableIdRaw)
  const table = tables.value.find((item) => item.id === tableId)
  const firstColumn = table?.columns[0]?.key ?? ''

  updateWidget(widgetId, {
    sourceTableId: Number.isFinite(tableId) ? tableId : null,
    fieldKey: firstColumn,
    groupByKey: firstColumn || null,
    tableColumns: table?.columns.slice(0, 5).map((column) => column.key) ?? [],
    filterColumnKey: firstColumn || null,
    filterValue: '',
    geoLatKey: null,
    geoLngKey: null,
  })

  resetTablePreviewPage(widgetId)
}

function toggleTableColumn(widgetId: string, columnKey: string, enabled: boolean) {
  const widget = widgets.value.find((w) => w.id === widgetId)
  if (!widget) return

  const current = widget.tableColumns ?? []
  const next = enabled ? Array.from(new Set([...current, columnKey])) : current.filter((key) => key !== columnKey)
  updateWidget(widgetId, { tableColumns: next })
}

function setAllTableColumns(widgetId: string, selectAll: boolean) {
  const widget = widgets.value.find((w) => w.id === widgetId)
  if (!widget || !widget.sourceTableId) return

  const columns = getColumnsByTableId(widget.sourceTableId)
  updateWidget(widgetId, { tableColumns: selectAll ? columns.map((column) => column.key) : [] })
}

function getColumnsByTableId(tableId: number | null): ColumnDefinition[] {
  if (!tableId) return []
  return tables.value.find((table) => table.id === tableId)?.columns ?? []
}

function getTableName(tableId: number | null): string {
  if (!tableId) return 'Таблица не выбрана'
  return tables.value.find((table) => table.id === tableId)?.name ?? 'Неизвестная таблица'
}

function chartBars(widget: DashboardWidget): number[] {
  if (!widget.sourceTableId) return [30, 55, 42, 80, 46, 62]
  const state = tablePreviewState.value[widget.id]
  const rows = state?.rows ?? []
  const field = widget.fieldKey
  if (!field || rows.length === 0) return [28, 40, 52, 34, 66, 49]

  const values = rows
    .map((row) => Number(row.data[field]))
    .filter((value) => Number.isFinite(value) && value >= 0)
    .slice(0, 8)

  if (values.length === 0) return [22, 58, 33, 64, 41, 76]

  const maxValue = Math.max(...values, 1)
  return values.map((value) => Math.max(8, Math.round((value / maxValue) * 100)))
}

function widgetNumericValues(widget: DashboardWidget): number[] {
  const rows = tablePreviewState.value[widget.id]?.rows ?? []
  if (!widget.fieldKey) return []
  return rows
    .map((row) => Number(row.data[widget.fieldKey as string]))
    .filter((value) => Number.isFinite(value))
}

function widgetAggregateValue(widget: DashboardWidget): number | null {
  const rows = tablePreviewState.value[widget.id]?.rows ?? []
  const aggregation = widget.aggregation || 'count'

  if (aggregation === 'count') {
    return rows.length
  }

  const values = widgetNumericValues(widget)
  if (values.length === 0) return null

  if (aggregation === 'sum') return values.reduce((acc, value) => acc + value, 0)
  if (aggregation === 'avg') return values.reduce((acc, value) => acc + value, 0) / values.length
  if (aggregation === 'min') return Math.min(...values)
  if (aggregation === 'max') return Math.max(...values)
  return null
}

function gaugePercent(widget: DashboardWidget): number {
  const value = widgetAggregateValue(widget)
  if (value === null) return 0
  const normalized = value <= 1 ? value * 100 : value
  return Math.max(0, Math.min(100, Math.round(normalized)))
}

function displayedColumns(widget: DashboardWidget): string[] {
  const fromWidget = widget.tableColumns ?? []
  if (fromWidget.length > 0) return fromWidget

  const columns = getColumnsByTableId(widget.sourceTableId)
  return columns.slice(0, 5).map((column) => column.key)
}

function applyWidgetFilter(rows: TableDataRecord[], widget: DashboardWidget): TableDataRecord[] {
  const filterColumn = widget.filterColumnKey?.trim()
  const filterValue = widget.filterValue?.trim().toLowerCase()

  if (!filterColumn || !filterValue) return rows

  return rows.filter((row) => {
    const raw = row.data[filterColumn]
    if (raw === undefined || raw === null) return false
    return String(raw).toLowerCase().includes(filterValue)
  })
}

function resetTablePreviewPage(widgetId: string) {
  const state = ensureTablePreviewState(widgetId)
  state.page = 1
}

function tableTotalPages(widget: DashboardWidget): number {
  const state = tablePreviewState.value[widget.id]
  const total = state?.filteredTotal ?? 0
  const pageSize = widget.pageSize ?? 10
  return Math.max(1, Math.ceil(total / pageSize))
}

function tablePageRows(widget: DashboardWidget): TableDataRecord[] {
  const state = tablePreviewState.value[widget.id]
  if (!state) return []

  const pageSize = widget.pageSize ?? 10
  const start = (state.page - 1) * pageSize
  return state.rows.slice(start, start + pageSize)
}

function tableCanPrev(widget: DashboardWidget): boolean {
  const state = tablePreviewState.value[widget.id]
  return Boolean(state && state.page > 1)
}

function tableCanNext(widget: DashboardWidget): boolean {
  const state = tablePreviewState.value[widget.id]
  if (!state) return false
  return state.page < tableTotalPages(widget)
}

function tablePrevPage(widget: DashboardWidget) {
  const state = ensureTablePreviewState(widget.id)
  if (state.page <= 1) return
  state.page -= 1
}

function tableNextPage(widget: DashboardWidget) {
  const state = ensureTablePreviewState(widget.id)
  const pages = tableTotalPages(widget)
  if (state.page >= pages) return
  state.page += 1
}

async function loadTablePreview(widget: DashboardWidget) {
  if (!workspaceId.value || !widget.sourceTableId) {
    const state = ensureTablePreviewState(widget.id)
    state.rows = []
    state.filteredTotal = 0
    state.error = ''
    return
  }

  const state = ensureTablePreviewState(widget.id)
  state.loading = true
  state.error = ''

  try {
    const response = await formBuilderUseCase.listTableData(workspaceId.value, widget.sourceTableId, 0, 200)
    const filtered = applyWidgetFilter(response.items, widget)

    state.rows = filtered
    state.filteredTotal = filtered.length

    const pages = tableTotalPages(widget)
    if (state.page > pages) {
      state.page = pages
    }
  } catch (error) {
    state.rows = []
    state.filteredTotal = 0
    state.error = 'Не удалось загрузить preview данных'
    console.error(error)
  } finally {
    state.loading = false
  }
}

async function loadDashboard() {
  if (!authStore.token || !workspaceId.value) return
  loading.value = true
  pageError.value = ''

  try {
    tables.value = await tableSchemaUseCase.listTables(authStore.token, workspaceId.value)

    if (isCreateMode.value) {
      reportName.value = ''
      reportDescription.value = ''
      reportIsPublished.value = false
      widgets.value = []
      selectedWidgetId.value = null
      return
    }

    if (!reportId.value) throw new Error('Missing report id')
    const report: ReportConfiguration = await reportUseCase.getReport(workspaceId.value, reportId.value)

    if (report.report_type !== 'dashboard') {
      throw new Error('Wrong report type')
    }

    reportName.value = report.name
    reportDescription.value = report.description || ''
    reportIsPublished.value = report.is_published

    const rawSettings = (report.settings || {}) as Record<string, unknown>
    const grid = rawSettings.grid && typeof rawSettings.grid === 'object'
      ? (rawSettings.grid as Record<string, unknown>)
      : null

    if (typeof grid?.cols === 'number' && grid.cols > 0) {
      gridCols.value = Math.max(4, Math.min(24, Math.floor(grid.cols)))
    }
    if (typeof grid?.rows === 'number' && grid.rows > 0) {
      gridRows.value = Math.max(6, Math.min(40, Math.floor(grid.rows)))
    }
    if (typeof grid?.cell_size === 'number' && grid.cell_size > 0) {
      cellSize.value = Math.max(40, Math.min(120, Math.floor(grid.cell_size)))
    }

    widgets.value = normalizeDashboardSettings(rawSettings)
    selectedWidgetId.value = widgets.value[0]?.id ?? null

    for (const widget of widgets.value) {
      ensureTablePreviewState(widget.id)
      if (widget.type === 'table' || widget.type === 'chart' || widget.type === 'metric' || widget.type === 'gauge') {
        await loadTablePreview(widget)
      }
    }
  } catch (error) {
    pageError.value = 'Не удалось загрузить дашборд'
    console.error(error)
  } finally {
    loading.value = false
  }
}

function normalizeDashboardSettings(raw: Record<string, unknown>): DashboardWidget[] {
  const rawWidgets = Array.isArray(raw.widgets_editor)
    ? raw.widgets_editor
    : Array.isArray(raw.widgets)
      ? raw.widgets
      : []

  return rawWidgets
    .filter((item): item is Record<string, unknown> => Boolean(item) && typeof item === 'object')
    .map((item, index) => {
      const source = item.source && typeof item.source === 'object' ? (item.source as Record<string, unknown>) : null
      const query = item.query && typeof item.query === 'object' ? (item.query as Record<string, unknown>) : null
      const presentation = item.presentation && typeof item.presentation === 'object'
        ? (item.presentation as Record<string, unknown>)
        : null
      const config = item.config && typeof item.config === 'object' ? (item.config as Record<string, unknown>) : null

      return {
        id: String(item.id || `widget_${Date.now()}_${index}`),
        type: (item.type as WidgetType) || 'metric',
        title: String(item.title || `Widget ${index + 1}`),
        description: String(item.description || ''),
        gridX: typeof item.gridX === 'number' ? item.gridX : 0,
        gridY: typeof item.gridY === 'number' ? item.gridY : 0,
        gridWidth: typeof item.gridWidth === 'number' ? item.gridWidth : 3,
        gridHeight: typeof item.gridHeight === 'number' ? item.gridHeight : 2,
        sourceTableId:
          typeof item.sourceTableId === 'number'
            ? item.sourceTableId
            : typeof source?.table_id === 'number'
              ? (source.table_id as number)
              : null,
        fieldKey:
          typeof item.fieldKey === 'string'
            ? item.fieldKey
            : typeof query?.field_key === 'string'
              ? (query.field_key as string)
              : '',
        aggregation:
          (item.aggregation as AggregationType) ||
          (typeof query?.aggregation === 'string' ? (query.aggregation as AggregationType) : 'count'),
        groupByKey:
          typeof item.groupByKey === 'string'
            ? item.groupByKey
            : typeof query?.group_by_key === 'string'
              ? (query.group_by_key as string)
              : null,
        chartType: (item.chartType as ChartType) || 'bar',
        colorScheme:
          typeof item.colorScheme === 'string'
            ? item.colorScheme
            : typeof presentation?.color === 'string'
              ? (presentation.color as string)
              : 'default',
        interaction:
          (item.interaction as WidgetInteraction) ||
          (typeof config?.interaction === 'string' ? (config.interaction as WidgetInteraction) : 'none'),
        contentScale:
          typeof item.contentScale === 'number'
            ? item.contentScale
            : typeof presentation?.scale === 'number'
              ? (presentation.scale as number)
              : 1,
        tableColumns:
          Array.isArray(item.tableColumns)
            ? item.tableColumns.map(String)
            : Array.isArray(config?.table_columns)
              ? (config.table_columns as unknown[]).map(String)
              : [],
        filterColumnKey:
          typeof item.filterColumnKey === 'string'
            ? item.filterColumnKey
            : typeof config?.filter_column_key === 'string'
              ? (config.filter_column_key as string)
              : null,
        filterValue:
          typeof item.filterValue === 'string'
            ? item.filterValue
            : typeof config?.filter_value === 'string'
              ? (config.filter_value as string)
              : '',
        pageSize:
          typeof item.pageSize === 'number'
            ? item.pageSize
            : typeof query?.limit === 'number'
              ? (query.limit as number)
              : 10,
        geoLatKey:
          typeof item.geoLatKey === 'string'
            ? item.geoLatKey
            : typeof config?.geo_lat_key === 'string'
              ? (config.geo_lat_key as string)
              : null,
        geoLngKey:
          typeof item.geoLngKey === 'string'
            ? item.geoLngKey
            : typeof config?.geo_lng_key === 'string'
              ? (config.geo_lng_key as string)
              : null,
      }
    })
}

async function saveDashboard() {
  if (!workspaceId.value || !reportName.value.trim()) return

  saving.value = true
  try {
    const primaryTableId =
      widgets.value.find((widget) => typeof widget.sourceTableId === 'number' && widget.sourceTableId > 0)?.sourceTableId ??
      tables.value[0]?.id ??
      null

    if (!primaryTableId) {
      pageError.value = 'Выберите таблицу хотя бы для одного виджета перед сохранением'
      saving.value = false
      return
    }

    const legacyMetrics = widgets.value
      .filter((widget) => widget.type === 'metric' || widget.type === 'gauge')
      .map((widget) => ({
        label: widget.title,
        aggregation: widget.aggregation || 'count',
        field_key: widget.fieldKey || null,
      }))

    const legacyCharts = widgets.value
      .filter((widget) => widget.type === 'chart')
      .map((widget) => ({
        title: widget.title,
        chart_type: 'bar',
        color: widget.colorScheme || null,
        group_by_key: widget.groupByKey || null,
        aggregation: widget.aggregation || 'count',
        value_key: widget.fieldKey || null,
        limit: 10,
      }))
      .filter((chart) => Boolean(chart.group_by_key))

    const legacyWidgets = widgets.value.map((widget) => ({
      id: widget.id,
      type: widget.type,
      title: widget.title,
      description: widget.description,
      gridX: widget.gridX,
      gridY: widget.gridY,
      gridWidth: widget.gridWidth,
      gridHeight: widget.gridHeight,
      source: { table_id: widget.sourceTableId },
      query: {
        aggregation: widget.aggregation || 'count',
        field_key: widget.fieldKey || null,
        group_by_key: widget.groupByKey || null,
        limit: widget.pageSize || 10,
      },
      presentation: {
        width: widget.gridWidth <= Math.ceil(gridCols.value / 2) ? 'half' : 'full',
        color: widget.colorScheme || null,
        scale: widget.contentScale || 1,
      },
      config: {
        interaction: widget.interaction || 'none',
        table_columns: widget.tableColumns || [],
        filter_column_key: widget.filterColumnKey || null,
        filter_value: widget.filterValue || '',
        geo_lat_key: widget.geoLatKey || null,
        geo_lng_key: widget.geoLngKey || null,
      },
    }))

    const settings = {
      grid: {
        cols: gridCols.value,
        rows: gridRows.value,
        cell_size: cellSize.value,
      },
      table_id: primaryTableId,
      metrics: legacyMetrics,
      charts: legacyCharts,
      recent_limit: 10,
      widgets_legacy: legacyWidgets,
      widgets: legacyWidgets,
      widgets_editor: widgets.value.map((widget) => ({
        id: widget.id,
        type: widget.type,
        title: widget.title,
        description: widget.description,
        gridX: widget.gridX,
        gridY: widget.gridY,
        gridWidth: widget.gridWidth,
        gridHeight: widget.gridHeight,
        sourceTableId: widget.sourceTableId,
        fieldKey: widget.fieldKey,
        aggregation: widget.aggregation,
        groupByKey: widget.groupByKey,
        chartType: widget.chartType,
        colorScheme: widget.colorScheme,
        interaction: widget.interaction,
        contentScale: widget.contentScale,
        tableColumns: widget.tableColumns,
        filterColumnKey: widget.filterColumnKey,
        filterValue: widget.filterValue,
        pageSize: widget.pageSize,
        geoLatKey: widget.geoLatKey,
        geoLngKey: widget.geoLngKey,
      })),
    }

    const saved = isCreateMode.value
      ? await reportUseCase.createReport(
          workspaceId.value,
          reportName.value.trim(),
          reportDescription.value.trim(),
          'dashboard',
          settings,
          reportIsPublished.value
        )
      : await reportUseCase.updateReport(
          workspaceId.value,
          reportId.value as number,
          reportName.value.trim(),
          reportDescription.value.trim(),
          'dashboard',
          settings,
          reportIsPublished.value
        )

    if (isCreateMode.value) {
      await router.replace({
        name: 'dashboard-detail',
        params: { workspaceId: workspaceId.value, reportId: saved.id },
      })
    }
  } catch (error) {
    pageError.value = 'Не удалось сохранить дашборд'
    console.error(error)
  } finally {
    saving.value = false
  }
}

function onWidgetDragStart(event: DragEvent, widget: DashboardWidget) {
  draggedWidget.value = widget
  if (event.dataTransfer) {
    event.dataTransfer.effectAllowed = 'move'
  }
}

function onCanvasDragOver(event: DragEvent) {
  event.preventDefault()
}

function onCanvasDrop(event: DragEvent) {
  event.preventDefault()
  if (!draggedWidget.value) return

  const canvas = (event.target as HTMLElement).closest('.dashboard-canvas')
  if (!canvas) return

  const rect = canvas.getBoundingClientRect()
  const gridX = Math.floor((event.clientX - rect.left) / cellSize.value)
  const gridY = Math.floor((event.clientY - rect.top) / cellSize.value)

  updateWidget(draggedWidget.value.id, {
    gridX: Math.max(0, Math.min(gridCols.value - draggedWidget.value.gridWidth, gridX)),
    gridY: Math.max(0, Math.min(gridRows.value - draggedWidget.value.gridHeight, gridY)),
  })

  draggedWidget.value = null
}

watch(
  () => selectedWidgetId.value,
  async (id) => {
    if (!id) return
    const widget = widgets.value.find((item) => item.id === id)
    if (!widget) return

    ensureTablePreviewState(widget.id)

    if (widget.type === 'table' || widget.type === 'chart' || widget.type === 'metric' || widget.type === 'gauge') {
      await loadTablePreview(widget)
    }
  },
  { immediate: true }
)

watch(
  () => [
    selectedWidget.value?.sourceTableId,
    selectedWidget.value?.filterColumnKey,
    selectedWidget.value?.filterValue,
    selectedWidget.value?.pageSize,
  ],
  async () => {
    if (!selectedWidget.value) return
    if (selectedWidget.value.type !== 'table') return

    resetTablePreviewPage(selectedWidget.value.id)
    await loadTablePreview(selectedWidget.value)
  }
)

watch([gridCols, gridRows], () => {
  widgets.value = widgets.value.map((widget) => {
    const safeWidth = Math.max(1, Math.min(gridCols.value, widget.gridWidth))
    const safeHeight = Math.max(1, Math.min(gridRows.value, widget.gridHeight))
    const safeX = Math.max(0, Math.min(gridCols.value - safeWidth, widget.gridX))
    const safeY = Math.max(0, Math.min(gridRows.value - safeHeight, widget.gridY))

    return {
      ...widget,
      gridX: safeX,
      gridY: safeY,
      gridWidth: safeWidth,
      gridHeight: safeHeight,
    }
  })
})

onMounted(loadDashboard)
</script>

<template>
  <main class="dashboard-editor">
    <header class="editor-header">
      <div class="header-left">
        <button class="back-btn" @click="router.push({ name: 'dashboard' })">Назад</button>
        <div>
          <h1>Dashboard Grid Editor</h1>
          <p>Drag-and-drop layout builder with widget-level settings</p>
        </div>
      </div>
      <div class="header-right">
        <button class="btn-soft" :disabled="widgets.length === 0" @click="openDashboardPreview">Общее превью</button>
        <button class="btn-soft" :disabled="!selectedWidgetId" @click="openPreviewModal()">Preview + Data</button>
        <label class="checkbox-label">
          <input v-model="reportIsPublished" type="checkbox" />
          Опубликован
        </label>
        <button class="btn-primary" :disabled="saving" @click="saveDashboard">
          {{ saving ? 'Сохранение...' : 'Сохранить' }}
        </button>
      </div>
    </header>

    <div v-if="loading" class="loading-placeholder">Загрузка...</div>
    <div v-else-if="pageError" class="error-placeholder">{{ pageError }}</div>

    <template v-else>
      <section class="metadata-panel">
        <input v-model="reportName" class="input-text" placeholder="Название дашборда" />
        <input v-model="reportDescription" class="input-text" placeholder="Описание дашборда" />
      </section>

      <section class="grid-controls-panel">
        <div class="grid-control-group">
          <label>Колонки: {{ gridCols }}</label>
          <input v-model.number="gridCols" type="range" min="4" max="24" step="1" />
        </div>
        <div class="grid-control-group">
          <label>Строки: {{ gridRows }}</label>
          <input v-model.number="gridRows" type="range" min="6" max="40" step="1" />
        </div>
        <div class="grid-control-group">
          <label>Размер клетки: {{ cellSize }} px</label>
          <input v-model.number="cellSize" type="range" min="40" max="120" step="4" />
        </div>
      </section>

      <section class="editor-layout">
        <aside class="widgets-sidebar">
          <h3>Витрина виджетов</h3>
          <div class="widgets-list">
            <button v-for="widgetType in WIDGET_TYPES" :key="widgetType.id" class="widget-type-btn" @click="addWidget(widgetType.id)">
              <span class="widget-code">{{ widgetType.icon }}</span>
              <span class="widget-name">{{ widgetType.name }}</span>
              <small>{{ widgetType.description }}</small>
            </button>
          </div>

          <div v-if="selectedWidget" class="widget-settings">
            <h4>Настройки виджета</h4>

            <div class="form-group">
              <label>Название</label>
              <input
                class="input-text"
                :value="selectedWidget.title"
                @input="updateWidget(selectedWidget.id, { title: ($event.target as HTMLInputElement).value })"
              />
            </div>

            <div class="form-group">
              <label>Описание</label>
              <input
                class="input-text"
                :value="selectedWidget.description || ''"
                @input="updateWidget(selectedWidget.id, { description: ($event.target as HTMLInputElement).value })"
              />
            </div>

            <div class="form-group">
              <label>Таблица</label>
              <select class="input-text" :value="selectedWidget.sourceTableId || ''" @change="onSourceTableChange(selectedWidget.id, ($event.target as HTMLSelectElement).value)">
                <option value="">Не выбрана</option>
                <option v-for="table in tables" :key="table.id" :value="table.id">{{ table.name }}</option>
              </select>
            </div>

            <div class="form-group">
              <label>Взаимодействие</label>
              <select
                class="input-text"
                :value="selectedWidget.interaction || 'none'"
                @change="updateWidget(selectedWidget.id, { interaction: ($event.target as HTMLSelectElement).value as WidgetInteraction })"
              >
                <option value="none">Нет</option>
                <option value="highlight">Подсветка</option>
                <option value="filter">Фильтрация других виджетов</option>
                <option value="drilldown">Проваливание в детализацию</option>
              </select>
            </div>

            <div class="form-group">
              <label>Масштаб содержимого: {{ Number(selectedWidget.contentScale || 1).toFixed(2) }}x</label>
              <input
                type="range"
                min="0.6"
                max="1.8"
                step="0.05"
                :value="selectedWidget.contentScale || 1"
                @input="updateWidget(selectedWidget.id, { contentScale: Number(($event.target as HTMLInputElement).value) })"
              />
            </div>

            <div v-if="selectedWidget.type === 'metric' || selectedWidget.type === 'gauge'" class="type-settings">
              <div class="form-group">
                <label>Агрегация</label>
                <select
                  class="input-text"
                  :value="selectedWidget.aggregation || 'count'"
                  @change="updateWidget(selectedWidget.id, { aggregation: ($event.target as HTMLSelectElement).value as AggregationType })"
                >
                  <option value="count">Count</option>
                  <option value="sum">Sum</option>
                  <option value="avg">Avg</option>
                  <option value="min">Min</option>
                  <option value="max">Max</option>
                </select>
              </div>

              <div class="form-group">
                <label>Поле</label>
                <select
                  class="input-text"
                  :value="selectedWidget.fieldKey || ''"
                  @change="updateWidget(selectedWidget.id, { fieldKey: ($event.target as HTMLSelectElement).value })"
                >
                  <option value="">Не выбрано</option>
                  <option v-for="column in selectedWidgetColumns" :key="column.key" :value="column.key">
                    {{ column.name }} ({{ column.key }})
                  </option>
                </select>
              </div>
            </div>

            <div v-if="selectedWidget.type === 'chart'" class="type-settings">
              <div class="form-group">
                <label>Тип графика</label>
                <select
                  class="input-text"
                  :value="selectedWidget.chartType || 'bar'"
                  @change="updateWidget(selectedWidget.id, { chartType: ($event.target as HTMLSelectElement).value as ChartType })"
                >
                  <option value="bar">Bar</option>
                  <option value="line">Line</option>
                  <option value="pie">Pie</option>
                  <option value="area">Area</option>
                  <option value="histogram">Histogram</option>
                </select>
              </div>

              <div class="form-group">
                <label>Поле X (группировка)</label>
                <select
                  class="input-text"
                  :value="selectedWidget.groupByKey || ''"
                  @change="updateWidget(selectedWidget.id, { groupByKey: ($event.target as HTMLSelectElement).value || null })"
                >
                  <option value="">Не выбрано</option>
                  <option v-for="column in selectedWidgetColumns" :key="column.key" :value="column.key">
                    {{ column.name }}
                  </option>
                </select>
              </div>

              <div class="form-group">
                <label>Поле Y</label>
                <select
                  class="input-text"
                  :value="selectedWidget.fieldKey || ''"
                  @change="updateWidget(selectedWidget.id, { fieldKey: ($event.target as HTMLSelectElement).value })"
                >
                  <option value="">Не выбрано</option>
                  <option v-for="column in selectedWidgetColumns" :key="column.key" :value="column.key">
                    {{ column.name }}
                  </option>
                </select>
              </div>
            </div>

            <div v-if="selectedWidget.type === 'map'" class="type-settings">
              <div class="form-group">
                <label>Поле широты (lat)</label>
                <select
                  class="input-text"
                  :value="selectedWidget.geoLatKey || ''"
                  @change="updateWidget(selectedWidget.id, { geoLatKey: ($event.target as HTMLSelectElement).value || null })"
                >
                  <option value="">Не выбрано</option>
                  <option v-for="column in selectedWidgetColumns" :key="column.key" :value="column.key">
                    {{ column.name }}
                  </option>
                </select>
              </div>

              <div class="form-group">
                <label>Поле долготы (lng)</label>
                <select
                  class="input-text"
                  :value="selectedWidget.geoLngKey || ''"
                  @change="updateWidget(selectedWidget.id, { geoLngKey: ($event.target as HTMLSelectElement).value || null })"
                >
                  <option value="">Не выбрано</option>
                  <option v-for="column in selectedWidgetColumns" :key="column.key" :value="column.key">
                    {{ column.name }}
                  </option>
                </select>
              </div>
            </div>

            <div v-if="selectedWidget.type === 'table'" class="type-settings">
              <div class="form-group">
                <label>Колонки таблицы</label>
                <div class="column-tools">
                  <button class="btn-soft" @click="setAllTableColumns(selectedWidget.id, true)">Выбрать все</button>
                  <button class="btn-soft" @click="setAllTableColumns(selectedWidget.id, false)">Очистить</button>
                </div>
                <div class="column-list">
                  <label v-for="column in selectedWidgetColumns" :key="column.key" class="column-item">
                    <input
                      type="checkbox"
                      :checked="(selectedWidget.tableColumns || []).includes(column.key)"
                      @change="toggleTableColumn(selectedWidget.id, column.key, ($event.target as HTMLInputElement).checked)"
                    />
                    <span>{{ column.name }}</span>
                  </label>
                </div>
              </div>

              <div class="form-group">
                <label>Фильтр по полю</label>
                <select
                  class="input-text"
                  :value="selectedWidget.filterColumnKey || ''"
                  @change="updateWidget(selectedWidget.id, { filterColumnKey: ($event.target as HTMLSelectElement).value || null })"
                >
                  <option value="">Без фильтра</option>
                  <option v-for="column in selectedWidgetColumns" :key="column.key" :value="column.key">
                    {{ column.name }}
                  </option>
                </select>
              </div>

              <div class="form-group">
                <label>Значение фильтра</label>
                <input
                  class="input-text"
                  :value="selectedWidget.filterValue || ''"
                  placeholder="Введите текст для фильтра"
                  @input="updateWidget(selectedWidget.id, { filterValue: ($event.target as HTMLInputElement).value })"
                />
              </div>

              <div class="form-group">
                <label>Строк на страницу</label>
                <select
                  class="input-text"
                  :value="selectedWidget.pageSize || 10"
                  @change="updateWidget(selectedWidget.id, { pageSize: Number(($event.target as HTMLSelectElement).value) })"
                >
                  <option :value="5">5</option>
                  <option :value="10">10</option>
                  <option :value="20">20</option>
                  <option :value="30">30</option>
                </select>
              </div>
            </div>

            <div class="layout-settings">
              <div class="layout-head">Позиция и размер</div>
              <div class="move-grid">
                <button class="btn-soft" @click="moveWidget(selectedWidget.id, 'left')">Left</button>
                <button class="btn-soft" @click="moveWidget(selectedWidget.id, 'up')">Up</button>
                <button class="btn-soft" @click="moveWidget(selectedWidget.id, 'down')">Down</button>
                <button class="btn-soft" @click="moveWidget(selectedWidget.id, 'right')">Right</button>
              </div>

              <div class="size-grid">
                <label>W: {{ selectedWidget.gridWidth }}</label>
                <input
                  type="range"
                  min="1"
                  :max="gridCols"
                  :value="selectedWidget.gridWidth"
                  @input="updateWidgetSize(selectedWidget.id, Number(($event.target as HTMLInputElement).value), selectedWidget.gridHeight)"
                />
                <label>H: {{ selectedWidget.gridHeight }}</label>
                <input
                  type="range"
                  min="1"
                  :max="gridRows"
                  :value="selectedWidget.gridHeight"
                  @input="updateWidgetSize(selectedWidget.id, selectedWidget.gridWidth, Number(($event.target as HTMLInputElement).value))"
                />
              </div>
            </div>

            <button class="btn-danger" @click="removeWidget(selectedWidget.id)">Удалить виджет</button>
          </div>
        </aside>

        <section class="editor-main">
          <div class="dashboard-canvas" :style="canvasStyle" @dragover="onCanvasDragOver" @drop="onCanvasDrop">
            <article
              v-for="widget in widgets"
              :key="widget.id"
              class="widget-container"
              :class="{ active: widget.id === selectedWidgetId }"
              :style="{
                gridColumn: `${widget.gridX + 1} / span ${widget.gridWidth}`,
                gridRow: `${widget.gridY + 1} / span ${widget.gridHeight}`,
              }"
              draggable="true"
              @click="selectedWidgetId = widget.id"
              @dragstart="onWidgetDragStart($event, widget)"
            >
              <header class="widget-header">
                <h4>{{ widget.title }}</h4>
                <div class="widget-actions">
                  <button class="icon-btn" @click.stop="openPreviewModal(widget.id)">Preview</button>
                  <button class="icon-btn danger" @click.stop="removeWidget(widget.id)">Delete</button>
                </div>
              </header>

              <div class="widget-body" :style="{ '--widget-scale': String(widget.contentScale || 1) }">
                <div class="widget-body-inner">
                  <div v-if="widget.type === 'metric'" class="preview-metric">
                    <div class="metric-main">{{ widgetAggregateValue(widget) !== null ? Number(widgetAggregateValue(widget)).toFixed(2).replace(/\.00$/, '') : '—' }}</div>
                    <div class="metric-sub">{{ widget.fieldKey || 'all rows' }}</div>
                  </div>

                  <div v-else-if="widget.type === 'gauge'" class="preview-gauge">
                    <div class="gauge-ring" :style="{ '--gauge-fill': String(gaugePercent(widget)) }"><span>{{ gaugePercent(widget) }}%</span></div>
                    <small>{{ widget.fieldKey || 'KPI' }}</small>
                  </div>

                  <div v-else-if="widget.type === 'chart'" class="preview-chart">
                    <div class="bars">
                      <div v-for="(bar, index) in chartBars(widget)" :key="`bar-${widget.id}-${index}`" class="bar" :style="{ height: `${bar}%` }" />
                    </div>
                    <small>{{ widget.chartType || 'bar' }} | {{ widget.groupByKey || 'x' }} / {{ widget.fieldKey || 'y' }}</small>
                  </div>

                  <div v-else-if="widget.type === 'table'" class="preview-table-widget">
                    <div class="table-meta">
                      <span>{{ getTableName(widget.sourceTableId) }}</span>
                      <span v-if="tablePreviewState[widget.id]">{{ tablePreviewState[widget.id].filteredTotal }} rows</span>
                    </div>

                    <div v-if="tablePreviewState[widget.id]?.loading" class="muted">Загрузка preview...</div>
                    <div v-else-if="tablePreviewState[widget.id]?.error" class="error-inline">{{ tablePreviewState[widget.id].error }}</div>
                    <div v-else class="table-scroll">
                      <table>
                        <thead>
                          <tr>
                            <th v-for="column in displayedColumns(widget)" :key="`head-${widget.id}-${column}`">{{ column }}</th>
                          </tr>
                        </thead>
                        <tbody>
                          <tr v-for="row in tablePageRows(widget)" :key="`row-${widget.id}-${row.id}`">
                            <td v-for="column in displayedColumns(widget)" :key="`cell-${widget.id}-${row.id}-${column}`">
                              {{ row.data[column] ?? '' }}
                            </td>
                          </tr>
                        </tbody>
                      </table>
                    </div>

                    <div class="table-pagination">
                      <button class="btn-soft" :disabled="!tableCanPrev(widget)" @click.stop="tablePrevPage(widget)">Prev</button>
                      <span>{{ tablePreviewState[widget.id]?.page || 1 }} / {{ tableTotalPages(widget) }}</span>
                      <button class="btn-soft" :disabled="!tableCanNext(widget)" @click.stop="tableNextPage(widget)">Next</button>
                    </div>
                  </div>

                  <div v-else-if="widget.type === 'text'" class="preview-text">{{ widget.description || 'Text widget' }}</div>

                  <div v-else-if="widget.type === 'map'" class="preview-map">
                    <div class="map-placeholder">MAP</div>
                    <small>{{ widget.geoLatKey || 'lat' }} / {{ widget.geoLngKey || 'lng' }}</small>
                  </div>
                </div>
              </div>
            </article>
          </div>
        </section>
      </section>
    </template>

    <div v-if="previewModalOpen && editingWidget" class="modal-overlay" @click.self="previewModalOpen = false">
      <div class="modal-content">
        <header class="modal-header">
          <h2>{{ editingWidget.title }}: Preview</h2>
          <button class="icon-btn" @click="previewModalOpen = false">Close</button>
        </header>

        <div class="modal-body">
          <div class="preview-meta">
            <p><strong>Тип:</strong> {{ editingWidget.type }}</p>
            <p><strong>Таблица:</strong> {{ getTableName(editingWidget.sourceTableId) }}</p>
            <p><strong>Interaction:</strong> {{ editingWidget.interaction || 'none' }}</p>
          </div>

          <div v-if="editingWidget.type === 'table'" class="modal-table-preview">
            <div v-if="modalTablePreview?.loading" class="muted">Загрузка...</div>
            <div v-else-if="modalTablePreview?.error" class="error-inline">{{ modalTablePreview.error }}</div>
            <div v-else class="table-scroll modal-scroll">
              <table>
                <thead>
                  <tr>
                    <th v-for="column in displayedColumns(editingWidget)" :key="`modal-head-${column}`">{{ column }}</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="row in tablePageRows(editingWidget)" :key="`modal-row-${row.id}`">
                    <td v-for="column in displayedColumns(editingWidget)" :key="`modal-cell-${row.id}-${column}`">
                      {{ row.data[column] ?? '' }}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            <div class="table-pagination">
              <button class="btn-soft" :disabled="!tableCanPrev(editingWidget)" @click="tablePrevPage(editingWidget)">Prev</button>
              <span>{{ modalTablePreview?.page || 1 }} / {{ tableTotalPages(editingWidget) }}</span>
              <button class="btn-soft" :disabled="!tableCanNext(editingWidget)" @click="tableNextPage(editingWidget)">Next</button>
            </div>
          </div>

          <div v-else class="modal-generic-preview">
            <div v-if="editingWidget.type === 'metric'" class="modal-visual-block">
              <div class="metric-main">{{ widgetAggregateValue(editingWidget) !== null ? Number(widgetAggregateValue(editingWidget)).toFixed(2).replace(/\.00$/, '') : '—' }}</div>
              <div class="metric-sub">{{ editingWidget.aggregation || 'count' }} • {{ editingWidget.fieldKey || 'all rows' }}</div>
            </div>

            <div v-else-if="editingWidget.type === 'gauge'" class="modal-visual-block">
              <div class="gauge-ring modal-gauge" :style="{ '--gauge-fill': String(gaugePercent(editingWidget)) }">
                <span>{{ gaugePercent(editingWidget) }}%</span>
              </div>
              <div class="metric-sub">{{ editingWidget.aggregation || 'count' }} • {{ editingWidget.fieldKey || 'KPI' }}</div>
            </div>

            <div v-else-if="editingWidget.type === 'chart'" class="modal-visual-block preview-chart">
              <div class="bars">
                <div v-for="(bar, index) in chartBars(editingWidget)" :key="`modal-chart-${editingWidget.id}-${index}`" class="bar" :style="{ height: `${bar}%` }" />
              </div>
              <small>{{ editingWidget.chartType || 'bar' }} | {{ editingWidget.groupByKey || 'x' }} / {{ editingWidget.fieldKey || 'y' }}</small>
            </div>

            <div v-else>
              <p>Поля и параметры виджета настроены в sidebar.</p>
            </div>

            <div v-if="modalTablePreview?.loading" class="muted">Загрузка данных...</div>
            <div v-else-if="modalTablePreview?.error" class="error-inline">{{ modalTablePreview.error }}</div>
            <div v-else-if="modalPreviewRows.length > 0 && modalPreviewColumns.length > 0" class="table-scroll modal-scroll">
              <table>
                <thead>
                  <tr>
                    <th v-for="column in modalPreviewColumns" :key="`modal-data-head-${column}`">{{ column }}</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="row in modalPreviewRows" :key="`modal-data-row-${row.id}`">
                    <td v-for="column in modalPreviewColumns" :key="`modal-data-cell-${row.id}-${column}`">
                      {{ row.data[column] ?? '' }}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            <p v-else class="muted">Нет данных для предпросмотра.</p>
          </div>
        </div>
      </div>
    </div>

    <div v-if="dashboardPreviewOpen" class="modal-overlay" @click.self="dashboardPreviewOpen = false">
      <div class="modal-content modal-content--wide">
        <header class="modal-header">
          <h2>Общее превью дашборда</h2>
          <button class="icon-btn" @click="dashboardPreviewOpen = false">Close</button>
        </header>

        <div class="modal-body">
          <div class="dashboard-preview-canvas" :style="canvasStyle">
            <article
              v-for="widget in widgets"
              :key="`dashboard-preview-${widget.id}`"
              class="widget-container preview-static"
              :style="{
                gridColumn: `${widget.gridX + 1} / span ${widget.gridWidth}`,
                gridRow: `${widget.gridY + 1} / span ${widget.gridHeight}`,
              }"
            >
              <header class="widget-header">
                <h4>{{ widget.title }}</h4>
              </header>

              <div class="widget-body" :style="{ '--widget-scale': String(widget.contentScale || 1) }">
                <div class="widget-body-inner">
                  <div v-if="widget.type === 'metric'" class="preview-metric">
                    <div class="metric-main">{{ widgetAggregateValue(widget) !== null ? Number(widgetAggregateValue(widget)).toFixed(2).replace(/\.00$/, '') : '—' }}</div>
                    <div class="metric-sub">{{ widget.fieldKey || 'all rows' }}</div>
                  </div>

                  <div v-else-if="widget.type === 'gauge'" class="preview-gauge">
                    <div class="gauge-ring" :style="{ '--gauge-fill': String(gaugePercent(widget)) }"><span>{{ gaugePercent(widget) }}%</span></div>
                    <small>{{ widget.fieldKey || 'KPI' }}</small>
                  </div>

                  <div v-else-if="widget.type === 'chart'" class="preview-chart">
                    <div class="bars">
                      <div v-for="(bar, index) in chartBars(widget)" :key="`dashboard-preview-bar-${widget.id}-${index}`" class="bar" :style="{ height: `${bar}%` }" />
                    </div>
                    <small>{{ widget.chartType || 'bar' }} | {{ widget.groupByKey || 'x' }} / {{ widget.fieldKey || 'y' }}</small>
                  </div>

                  <div v-else-if="widget.type === 'table'" class="preview-table-widget">
                    <div class="table-meta">
                      <span>{{ getTableName(widget.sourceTableId) }}</span>
                      <span v-if="tablePreviewState[widget.id]">{{ tablePreviewState[widget.id].filteredTotal }} rows</span>
                    </div>
                    <div class="table-scroll">
                      <table>
                        <thead>
                          <tr>
                            <th v-for="column in displayedColumns(widget)" :key="`dashboard-preview-head-${widget.id}-${column}`">{{ column }}</th>
                          </tr>
                        </thead>
                        <tbody>
                          <tr v-for="row in tablePageRows(widget).slice(0, 5)" :key="`dashboard-preview-row-${widget.id}-${row.id}`">
                            <td v-for="column in displayedColumns(widget)" :key="`dashboard-preview-cell-${widget.id}-${row.id}-${column}`">{{ row.data[column] ?? '' }}</td>
                          </tr>
                        </tbody>
                      </table>
                    </div>
                  </div>

                  <div v-else-if="widget.type === 'text'" class="preview-text">{{ widget.description || 'Text widget' }}</div>

                  <div v-else-if="widget.type === 'map'" class="preview-map">
                    <div class="map-placeholder">MAP</div>
                    <small>{{ widget.geoLatKey || 'lat' }} / {{ widget.geoLngKey || 'lng' }}</small>
                  </div>
                </div>
              </div>
            </article>
          </div>
        </div>
      </div>
    </div>
  </main>
</template>

<style scoped>
.dashboard-editor {
  min-height: 100vh;
  padding: 20px;
  display: grid;
  gap: 16px;
  background:
    radial-gradient(circle at 12% 18%, rgba(255, 191, 105, 0.18), transparent 30%),
    radial-gradient(circle at 88% 12%, rgba(39, 174, 96, 0.15), transparent 28%),
    linear-gradient(140deg, #f4f7f6 0%, #edf3f2 100%);
  color: #182025;
}

.editor-header,
.metadata-panel,
.widgets-sidebar,
.editor-main,
.modal-content,
.loading-placeholder,
.error-placeholder {
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(28, 63, 62, 0.12);
  border-radius: 14px;
  box-shadow: 0 10px 30px rgba(19, 39, 40, 0.06);
}

.editor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  padding: 16px 18px;
}

.header-left {
  display: flex;
  gap: 14px;
  align-items: center;
}

.header-left h1 {
  margin: 0;
  font-size: 1.35rem;
}

.header-left p {
  margin: 2px 0 0;
  color: #5f7278;
  font-size: 0.88rem;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.back-btn,
.btn-primary,
.icon-btn,
.btn-soft,
.btn-danger {
  border: none;
  border-radius: 10px;
  cursor: pointer;
  font: inherit;
}

.back-btn {
  background: #ebf4f2;
  color: #0d615a;
  padding: 9px 12px;
}

.btn-primary {
  background: #0f766e;
  color: #fff;
  padding: 10px 14px;
}

.btn-primary:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

.icon-btn,
.btn-soft {
  background: #e6efee;
  color: #27504f;
  padding: 6px 10px;
}

.icon-btn.danger,
.btn-danger {
  background: #fae9ec;
  color: #b23c57;
}

.btn-danger {
  width: 100%;
  padding: 9px 12px;
  margin-top: 8px;
}

.metadata-panel {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  padding: 12px;
}

.grid-controls-panel {
  display: grid;
  grid-template-columns: repeat(3, minmax(180px, 1fr));
  gap: 10px;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(28, 63, 62, 0.12);
  border-radius: 14px;
  box-shadow: 0 10px 30px rgba(19, 39, 40, 0.06);
  padding: 12px;
}

.grid-control-group {
  display: grid;
  gap: 6px;
}

.grid-control-group label {
  font-size: 0.8rem;
  color: #466067;
  font-weight: 600;
}

.input-text,
select,
input[type='range'] {
  width: 100%;
}

.input-text,
select {
  border: 1px solid rgba(43, 73, 72, 0.2);
  border-radius: 10px;
  padding: 9px 11px;
  background: #fff;
  font: inherit;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 6px;
}

.editor-layout {
  display: grid;
  grid-template-columns: 330px 1fr;
  gap: 14px;
}

.widgets-sidebar {
  padding: 14px;
  display: grid;
  gap: 14px;
  max-height: calc(100vh - 220px);
  overflow: auto;
}

.widgets-sidebar h3,
.widget-settings h4 {
  margin: 0;
}

.widgets-list {
  display: grid;
  gap: 8px;
}

.widget-type-btn {
  border: 1px solid rgba(31, 63, 61, 0.14);
  border-radius: 12px;
  background: #f7fbfa;
  padding: 10px;
  text-align: left;
  display: grid;
  gap: 3px;
  cursor: pointer;
}

.widget-code {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 8px;
  background: #dff0ee;
  color: #0f766e;
  font-weight: 700;
  font-size: 0.78rem;
}

.widget-name {
  font-weight: 700;
}

.widget-type-btn small {
  color: #60747b;
  font-size: 0.76rem;
}

.widget-settings {
  border-top: 1px solid rgba(32, 61, 59, 0.1);
  padding-top: 12px;
  display: grid;
  gap: 11px;
}

.form-group {
  display: grid;
  gap: 5px;
}

.form-group label,
.layout-head {
  font-size: 0.78rem;
  color: #466067;
  font-weight: 600;
}

.column-tools {
  display: flex;
  gap: 6px;
}

.column-list {
  max-height: 130px;
  overflow: auto;
  border: 1px solid rgba(37, 69, 67, 0.16);
  border-radius: 10px;
  padding: 6px;
  display: grid;
  gap: 4px;
}

.column-item {
  display: flex;
  gap: 6px;
  align-items: center;
  font-size: 0.82rem;
}

.layout-settings {
  border-top: 1px solid rgba(32, 61, 59, 0.1);
  padding-top: 10px;
  display: grid;
  gap: 8px;
}

.move-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 5px;
}

.size-grid {
  display: grid;
  gap: 4px;
}

.editor-main {
  padding: 16px;
  overflow: auto;
}

.dashboard-canvas {
  --cell-size: 64px;
  display: grid;
  gap: 0;
  position: relative;
  border: 1px solid rgba(42, 84, 81, 0.22);
  border-radius: 10px;
  background-image:
    linear-gradient(rgba(42, 84, 81, 0.07) 1px, transparent 1px),
    linear-gradient(90deg, rgba(42, 84, 81, 0.07) 1px, transparent 1px);
  background-size: var(--cell-size) var(--cell-size);
}

.widget-container {
  border: 2px solid rgba(30, 82, 78, 0.25);
  border-radius: 12px;
  padding: 10px;
  background: #fff;
  display: grid;
  grid-template-rows: auto 1fr;
  gap: 8px;
  overflow: hidden;
}

.widget-container.active {
  border-color: #0f766e;
  box-shadow: 0 0 0 3px rgba(15, 118, 110, 0.15);
}

.widget-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}

.widget-header h4 {
  margin: 0;
  font-size: 0.86rem;
}

.widget-actions {
  display: flex;
  gap: 4px;
}

.widget-body {
  position: relative;
  overflow: hidden;
}

.widget-body-inner {
  width: 100%;
  height: 100%;
  transform: scale(var(--widget-scale, 1));
  transform-origin: top left;
  display: flex;
  align-items: center;
  justify-content: center;
}

.preview-metric,
.preview-gauge,
.preview-chart,
.preview-map,
.preview-text {
  width: 100%;
  height: 100%;
  display: grid;
  place-items: center;
  text-align: center;
  gap: 6px;
}

.metric-main {
  font-size: 1.3rem;
  font-weight: 700;
  color: #0f766e;
}

.metric-sub {
  font-size: 0.8rem;
  color: #60747b;
}

.gauge-ring {
  --gauge-fill: 72;
  width: 86px;
  height: 86px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  background: conic-gradient(#0f766e calc(var(--gauge-fill) * 3.6deg), #e6efee 0deg);
  position: relative;
}

.gauge-ring::after {
  content: '';
  position: absolute;
  width: 66px;
  height: 66px;
  border-radius: 50%;
  background: #fff;
}

.gauge-ring span {
  position: relative;
  z-index: 1;
  font-size: 0.95rem;
  font-weight: 700;
  color: #0f766e;
}

.preview-chart .bars {
  width: 100%;
  height: 110px;
  display: flex;
  align-items: flex-end;
  gap: 5px;
  justify-content: center;
}

.preview-chart .bar {
  width: 16px;
  background: linear-gradient(180deg, #1f8c83 0%, #0f766e 100%);
  border-radius: 4px 4px 0 0;
}

.preview-table-widget {
  width: 100%;
  height: 100%;
  display: grid;
  grid-template-rows: auto auto 1fr auto;
  gap: 6px;
}

.table-meta {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  font-size: 0.72rem;
  color: #5f7278;
}

.table-scroll {
  width: 100%;
  overflow: auto;
  border: 1px solid rgba(35, 72, 69, 0.12);
  border-radius: 8px;
}

table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.72rem;
}

th,
td {
  border-bottom: 1px solid rgba(35, 72, 69, 0.1);
  padding: 6px;
  text-align: left;
  white-space: nowrap;
}

th {
  background: #f1f7f6;
  font-weight: 600;
}

.table-pagination {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  font-size: 0.75rem;
}

.map-placeholder {
  width: 92%;
  height: 90px;
  border-radius: 10px;
  background: repeating-linear-gradient(45deg, #dfeceb 0, #dfeceb 8px, #ebf5f4 8px, #ebf5f4 16px);
  display: grid;
  place-items: center;
  color: #376563;
  font-weight: 700;
}

.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(8, 20, 22, 0.46);
  display: grid;
  place-items: center;
  z-index: 100;
}

.modal-content {
  width: min(980px, 94vw);
  max-height: 88vh;
  overflow: auto;
}

.modal-content--wide {
  width: min(1320px, 96vw);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 16px;
  border-bottom: 1px solid rgba(35, 72, 69, 0.12);
}

.modal-header h2 {
  margin: 0;
  font-size: 1.04rem;
}

.modal-body {
  padding: 16px;
  display: grid;
  gap: 12px;
}

.preview-meta {
  display: grid;
  gap: 4px;
  font-size: 0.9rem;
}

.preview-meta p {
  margin: 0;
}

.modal-scroll {
  max-height: 430px;
}

.modal-generic-preview {
  display: grid;
  gap: 10px;
  padding: 14px;
  border-radius: 10px;
  background: #f3f9f8;
  color: #4c666c;
}

.modal-visual-block {
  display: grid;
  justify-items: center;
  gap: 6px;
}

.modal-gauge {
  width: 130px;
  height: 130px;
}

.dashboard-preview-canvas {
  --cell-size: 64px;
  display: grid;
  gap: 0;
  position: relative;
  overflow: auto;
  border: 1px solid rgba(42, 84, 81, 0.22);
  border-radius: 10px;
  background-image:
    linear-gradient(rgba(42, 84, 81, 0.07) 1px, transparent 1px),
    linear-gradient(90deg, rgba(42, 84, 81, 0.07) 1px, transparent 1px);
  background-size: var(--cell-size) var(--cell-size);
}

.preview-static {
  pointer-events: none;
}

.muted {
  color: #5f7278;
  font-size: 0.78rem;
}

.error-inline {
  color: #b23c57;
  font-size: 0.78rem;
}

.loading-placeholder,
.error-placeholder {
  padding: 24px;
  text-align: center;
}

.error-placeholder {
  color: #b23c57;
}

@media (max-width: 1200px) {
  .editor-layout {
    grid-template-columns: 1fr;
  }

  .grid-controls-panel {
    grid-template-columns: 1fr;
  }

  .widgets-sidebar {
    max-height: none;
  }
}

@media (max-width: 760px) {
  .dashboard-editor {
    padding: 12px;
  }

  .editor-header,
  .metadata-panel {
    grid-template-columns: 1fr;
    display: grid;
  }

  .header-right {
    justify-content: flex-start;
    flex-wrap: wrap;
  }

  .dashboard-canvas {
    transform-origin: top left;
    transform: scale(0.82);
  }
}
</style>
