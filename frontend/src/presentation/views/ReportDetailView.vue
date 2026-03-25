<script setup lang="ts">
import { computed, defineComponent, h, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import VChart from 'vue-echarts'
import { BarChart, LineChart } from 'echarts/charts'
import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { use } from 'echarts/core'
import maplibregl from 'maplibre-gl'

import { FormBuilderUseCase } from '../../application/usecases/FormBuilderUseCase'
import { ReportUseCase } from '../../application/usecases/ReportUseCase'
import { TableSchemaUseCase } from '../../application/usecases/TableSchemaUseCase'
import type { TableDataRecord } from '../../domain/entities/FormBuilder'
import type { DashboardReportSettings, DashboardWidget, DashboardWidgetType, WidgetMetricAggregation } from '../../domain/entities/Report'
import type { ColumnType, TableStructure } from '../../domain/entities/TableSchema'
import { useAuthStore } from '../stores/authStore'

use([CanvasRenderer, BarChart, LineChart, GridComponent, TooltipComponent, LegendComponent])

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const workspaceId = computed(() => Number(route.params.workspaceId))
const reportId = computed(() => (route.params.reportId ? Number(route.params.reportId) : null))
const isCreateMode = computed(() => route.name === 'report-create')

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
const previewRows = ref<TableDataRecord[]>([])
const previewLoading = ref(false)
const previewError = ref('')

const widgetPalette: Array<{ type: DashboardWidgetType; title: string }> = [
  { type: 'text', title: 'Текст' },
  { type: 'metric', title: 'Метрика' },
  { type: 'chart', title: 'График' },
  { type: 'table', title: 'Таблица' },
  { type: 'map', title: 'Карта' },
]

const aggregationOptions: WidgetMetricAggregation[] = ['count', 'sum', 'avg', 'min', 'max']

const selectedWidget = computed(() => widgets.value.find((item) => item.id === selectedWidgetId.value) ?? null)
const selectedTable = computed(() => {
  if (!selectedWidget.value?.source.table_id) return null
  return tables.value.find((table) => table.id === selectedWidget.value?.source.table_id) ?? null
})
const selectedFields = computed(() => selectedTable.value?.columns ?? [])
const numericFields = computed(() => selectedFields.value.filter((field) => field.type === 'number'))

const tablePreviewColumns = computed(() => {
  if (!selectedWidget.value || selectedWidget.value.type !== 'table') return []
  const keys = Array.isArray(selectedWidget.value.config.columns)
    ? selectedWidget.value.config.columns.map((item: unknown) => String(item))
    : []
  return selectedFields.value.filter((field) => keys.includes(field.key))
})

const metricPreview = computed(() => {
  if (!selectedWidget.value || selectedWidget.value.type !== 'metric') return null
  const aggregation = selectedWidget.value.query.aggregation || 'count'
  if (aggregation === 'count') return previewRows.value.length

  const values = previewRows.value
    .map((row) => toNumber(row.data[selectedWidget.value?.query.field_key || '']))
    .filter((value): value is number => value !== null)

  if (values.length === 0) return null
  return aggregate(values, aggregation)
})

const chartPreview = computed(() => {
  if (!selectedWidget.value || selectedWidget.value.type !== 'chart') return []
  const groupKey = String(selectedWidget.value.query.group_by_key || '')
  if (!groupKey) return []

  const buckets = new Map<string, number[]>()
  for (const row of previewRows.value) {
    const label = String(row.data[groupKey] ?? '').trim()
    if (!label) continue
    const bucket = buckets.get(label) ?? []
    if ((selectedWidget.value.query.aggregation || 'count') === 'count') {
      bucket.push(1)
    } else {
      const numeric = toNumber(row.data[selectedWidget.value.query.field_key || ''])
      if (numeric !== null) bucket.push(numeric)
    }
    buckets.set(label, bucket)
  }

  return Array.from(buckets.entries())
    .map(([label, values]) => ({
      label,
      value: aggregate(values, selectedWidget.value?.query.aggregation || 'count'),
    }))
    .filter((item) => Number.isFinite(item.value))
    .slice(0, Number(selectedWidget.value.query.limit || 8))
})

const chartOption = computed(() => {
  if (!selectedWidget.value || selectedWidget.value.type !== 'chart') return {}
  const chartType = selectedWidget.value.config.chartType === 'line' ? 'line' : 'bar'
  return {
    color: [selectedWidget.value.presentation.color || '#156f69'],
    grid: { left: 28, right: 12, top: 24, bottom: 24, containLabel: true },
    tooltip: { trigger: 'axis' },
    xAxis: {
      type: 'category',
      data: chartPreview.value.map((item) => item.label),
      axisLabel: { color: '#617780' },
    },
    yAxis: {
      type: 'value',
      axisLabel: { color: '#617780' },
      splitLine: { lineStyle: { color: 'rgba(80, 100, 107, 0.12)' } },
    },
    series: [
      {
        type: chartType,
        data: chartPreview.value.map((item) => item.value),
        smooth: chartType === 'line',
        areaStyle: chartType === 'line' ? { opacity: 0.12 } : undefined,
      },
    ],
  }
})

const mapPoints = computed(() => {
  if (!selectedWidget.value || selectedWidget.value.type !== 'map') return []
  const latField = String(selectedWidget.value.config.latField || '')
  const lngField = String(selectedWidget.value.config.lngField || '')
  const labelField = String(selectedWidget.value.config.labelField || '')
  if (!latField || !lngField) return []

  return previewRows.value
    .map((row) => {
      const lat = toNumber(row.data[latField])
      const lng = toNumber(row.data[lngField])
      if (lat === null || lng === null) return null
      return {
        lat,
        lng,
        label: labelField ? String(row.data[labelField] ?? '') : `(${lat}, ${lng})`,
      }
    })
    .filter(Boolean) as Array<{ lat: number; lng: number; label: string }>
})

function createWidget(type: DashboardWidgetType): DashboardWidget {
  const tableId = tables.value[0]?.id ?? null
  const id = `widget_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`

  const base: DashboardWidget = {
    id,
    type,
    title: '',
    source: { table_id: type === 'text' ? null : tableId },
    query: { aggregation: 'count', field_key: null, group_by_key: null, limit: 8 },
    presentation: { color: '#156f69', width: type === 'metric' || type === 'chart' ? 'half' : 'full' },
    config: {},
  }

  if (type === 'text') base.config.content = 'Добавьте текстовый блок'
  if (type === 'chart') base.config.chartType = 'bar'
  if (type === 'table') base.config.columns = []
  if (type === 'map') {
    base.config.latField = ''
    base.config.lngField = ''
    base.config.labelField = ''
    base.query.limit = 50
  }

  return base
}

function emptySettings(): DashboardReportSettings {
  const baseWidgets = [createWidget('metric'), createWidget('chart'), createWidget('table')]
  return {
    widgets: baseWidgets,
    layout: [],
    global_filters: [],
    canvas: { columns: 12, row_height: 92 },
  }
}

function buildLegacyDashboardSettings(items: DashboardWidget[]) {
  const dataWidgets = items.filter((widget) => typeof widget.source.table_id === 'number')
  const tableWidget = dataWidgets.find((widget) => widget.type === 'table')
  const primaryWidget = tableWidget ?? dataWidgets[0] ?? null

  return {
    table_id: primaryWidget?.source.table_id ?? null,
    metrics: items
      .filter((widget) => widget.type === 'metric')
      .map((widget) => ({
        label: widget.title,
        aggregation: widget.query.aggregation || 'count',
        field_key: widget.query.aggregation === 'count' ? null : widget.query.field_key || null,
      })),
    charts: items
      .filter(
        (widget) =>
          widget.type === 'chart' &&
          typeof widget.source.table_id === 'number' &&
          typeof widget.query.group_by_key === 'string' &&
          widget.query.group_by_key
      )
      .map((widget) => ({
        title: widget.title,
        chart_type: 'bar',
        color: widget.presentation.color || '#156f69',
        group_by_key: widget.query.group_by_key,
        aggregation: widget.query.aggregation || 'count',
        value_key: widget.query.aggregation === 'count' ? null : widget.query.field_key || null,
        limit: positive(widget.query.limit, 8),
      })),
    recent_limit: positive(tableWidget?.query.limit, 10),
  }
}

function normalizeWidgetType(value: unknown): DashboardWidgetType {
  const raw = String(value || '')
  if (raw === 'chart_bar' || raw === 'chart_line' || raw === 'chart') return 'chart'
  if (raw === 'text' || raw === 'metric' || raw === 'table' || raw === 'map') return raw
  return 'text'
}

function normalizeAggregation(value: unknown): WidgetMetricAggregation {
  return aggregationOptions.includes(value as WidgetMetricAggregation) ? (value as WidgetMetricAggregation) : 'count'
}

function normalizeSettings(raw: Record<string, unknown>): DashboardReportSettings {
  const rawWidgets = Array.isArray(raw.widgets) ? raw.widgets : []
  const normalizedWidgets = rawWidgets
    .filter((item): item is Record<string, unknown> => !!item && typeof item === 'object')
    .map((item, index) => ({
      id: String(item.id || `widget_${index + 1}`),
      type: normalizeWidgetType(item.type),
      title: typeof item.title === 'string' ? item.title : '',
      source: {
        table_id: typeof (item.source as Record<string, unknown> | undefined)?.table_id === 'number'
          ? Number((item.source as Record<string, unknown>).table_id)
          : null,
      },
      query: {
        aggregation: normalizeAggregation((item.query as Record<string, unknown> | undefined)?.aggregation),
        field_key: stringOrNull((item.query as Record<string, unknown> | undefined)?.field_key),
        group_by_key: stringOrNull((item.query as Record<string, unknown> | undefined)?.group_by_key),
        limit: positive((item.query as Record<string, unknown> | undefined)?.limit, 8),
      },
      presentation: {
        color: String((item.presentation as Record<string, unknown> | undefined)?.color || '#156f69'),
        width: (item.presentation as Record<string, unknown> | undefined)?.width === 'half' ? 'half' : 'full',
      },
      config: {
        ...(item.config && typeof item.config === 'object' ? item.config : {}),
      },
    })) as DashboardWidget[]

  return {
    widgets: normalizedWidgets.length > 0 ? normalizedWidgets : emptySettings().widgets,
    layout: [],
    global_filters: [],
    canvas: { columns: 12, row_height: 92 },
  }
}

async function loadPage() {
  if (!authStore.token || !workspaceId.value) return
  loading.value = true
  pageError.value = ''

  try {
    tables.value = await tableSchemaUseCase.listTables(authStore.token, workspaceId.value)

    if (isCreateMode.value) {
      reportName.value = ''
      reportDescription.value = ''
      reportIsPublished.value = false
      widgets.value = emptySettings().widgets
      selectedWidgetId.value = widgets.value[0]?.id ?? null
      return
    }

    if (!reportId.value) throw new Error('Missing report id')
    const report = await reportUseCase.getReport(workspaceId.value, reportId.value)
    reportName.value = report.name
    reportDescription.value = report.description || ''
    reportIsPublished.value = report.is_published

    if (report.report_type !== 'dashboard') {
      pageError.value = 'Этот экран сейчас работает только с dashboard reports.'
      return
    }

    widgets.value = normalizeSettings(report.settings || {}).widgets
    selectedWidgetId.value = widgets.value[0]?.id ?? null
  } catch (error) {
    pageError.value = 'Не удалось загрузить редактор отчета'
    console.error(error)
  } finally {
    loading.value = false
  }
}

async function saveReport() {
  if (!workspaceId.value || !reportName.value.trim()) return
  saving.value = true

  try {
    const legacySettings = buildLegacyDashboardSettings(widgets.value)
    const settings: DashboardReportSettings = {
      widgets: widgets.value,
      layout: [],
      global_filters: [],
      canvas: { columns: 12, row_height: 92 },
    }

    const saved = isCreateMode.value
      ? await reportUseCase.createReport(
          workspaceId.value,
          reportName.value.trim(),
          reportDescription.value.trim(),
          'dashboard',
          {
            ...(settings as unknown as Record<string, unknown>),
            ...legacySettings,
          },
          reportIsPublished.value
        )
      : await reportUseCase.updateReport(
          workspaceId.value,
          reportId.value as number,
          reportName.value.trim(),
          reportDescription.value.trim(),
          'dashboard',
          {
            ...(settings as unknown as Record<string, unknown>),
            ...legacySettings,
          },
          reportIsPublished.value
        )

    if (isCreateMode.value) {
      await router.replace({
        name: 'report-detail',
        params: { workspaceId: workspaceId.value, reportId: saved.id },
      })
    }
  } catch (error) {
    pageError.value = 'Не удалось сохранить отчет'
    console.error(error)
  } finally {
    saving.value = false
  }
}

function addWidget(type: DashboardWidgetType) {
  const widget = createWidget(type)
  widgets.value.push(widget)
  selectedWidgetId.value = widget.id
}

function removeWidget(widgetId: string) {
  widgets.value = widgets.value.filter((item) => item.id !== widgetId)
  selectedWidgetId.value = widgets.value[0]?.id ?? null
}

function moveWidget(widgetId: string, direction: -1 | 1) {
  const index = widgets.value.findIndex((item) => item.id === widgetId)
  const targetIndex = index + direction
  if (index < 0 || targetIndex < 0 || targetIndex >= widgets.value.length) return
  const next = [...widgets.value]
  const [widget] = next.splice(index, 1)
  next.splice(targetIndex, 0, widget)
  widgets.value = next
}

function duplicateWidget(widgetId: string) {
  const source = widgets.value.find((item) => item.id === widgetId)
  if (!source) return
  const clone = structuredClone(source) as DashboardWidget
  clone.id = `widget_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`
  clone.title = `${source.title} copy`
  widgets.value.push(clone)
  selectedWidgetId.value = clone.id
}

async function loadPreview() {
  if (!selectedWidget.value?.source.table_id) {
    previewRows.value = []
    previewError.value = ''
    return
  }

  previewLoading.value = true
  previewError.value = ''
  try {
    const result = await formBuilderUseCase.listTableData(
      workspaceId.value,
      selectedWidget.value.source.table_id,
      0,
      positive(selectedWidget.value.query.limit, selectedWidget.value.type === 'map' ? 50 : 10)
    )
    previewRows.value = result.items
  } catch (error) {
    previewRows.value = []
    previewError.value = 'Не удалось загрузить preview'
    console.error(error)
  } finally {
    previewLoading.value = false
  }
}

function aggregate(values: number[], mode: WidgetMetricAggregation): number {
  if (mode === 'count') return values.length
  if (mode === 'sum') return values.reduce((sum, value) => sum + value, 0)
  if (mode === 'avg') return values.reduce((sum, value) => sum + value, 0) / values.length
  if (mode === 'min') return Math.min(...values)
  if (mode === 'max') return Math.max(...values)
  return values.length
}

function toNumber(value: unknown): number | null {
  if (typeof value === 'number' && Number.isFinite(value)) return value
  if (typeof value === 'string' && value.trim() !== '') {
    const parsed = Number(value)
    return Number.isFinite(parsed) ? parsed : null
  }
  return null
}

function stringOrNull(value: unknown): string | null {
  return typeof value === 'string' && value.trim() ? value : null
}

function positive(value: unknown, fallback: number): number {
  const parsed = Number(value)
  return Number.isFinite(parsed) && parsed > 0 ? Math.floor(parsed) : fallback
}

function formatValue(value: unknown, type: ColumnType): string {
  if (value === null || value === undefined || value === '') return '—'
  if (type === 'boolean') return value ? 'Да' : 'Нет'
  if (type === 'date' || type === 'datetime') return new Date(String(value)).toLocaleString('ru-RU')
  if (Array.isArray(value)) return value.join(', ')
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

const ChartPreview = defineComponent({
  name: 'ChartPreview',
  props: {
    option: { type: Object, required: true },
    height: { type: Number, default: 280 },
  },
  setup(props) {
    return () =>
      h(VChart, {
        option: props.option,
        autoresize: true,
        style: { width: '100%', height: `${props.height}px` },
      })
  },
})

const MapPreview = defineComponent({
  name: 'MapPreview',
  props: {
    points: {
      type: Array as () => Array<{ lat: number; lng: number; label: string }>,
      required: true,
    },
    height: { type: Number, default: 300 },
  },
  setup(props) {
    const el = ref<HTMLDivElement | null>(null)
    let map: maplibregl.Map | null = null
    let markers: maplibregl.Marker[] = []

    const syncMap = () => {
      if (!map) return
      markers.forEach((marker) => marker.remove())
      markers = props.points.map((point) =>
        new maplibregl.Marker({ color: '#156f69' })
          .setLngLat([point.lng, point.lat])
          .setPopup(new maplibregl.Popup({ offset: 12 }).setText(point.label || 'Point'))
          .addTo(map!)
      )

      if (props.points.length === 0) return
      if (props.points.length === 1) {
        map.setCenter([props.points[0].lng, props.points[0].lat])
        map.setZoom(11)
        return
      }

      const bounds = new maplibregl.LngLatBounds()
      props.points.forEach((point) => bounds.extend([point.lng, point.lat]))
      map.fitBounds(bounds, { padding: 32, maxZoom: 12, animate: false })
    }

    onMounted(async () => {
      await nextTick()
      if (!el.value) return
      map = new maplibregl.Map({
        container: el.value,
        style: 'https://demotiles.maplibre.org/style.json',
        center: [37.618423, 55.751244],
        zoom: 4,
        attributionControl: false,
      })
      map.on('load', syncMap)
    })

    watch(
      () => props.points,
      () => syncMap(),
      { deep: true }
    )

    onBeforeUnmount(() => {
      markers.forEach((marker) => marker.remove())
      markers = []
      map?.remove()
      map = null
    })

    return () =>
      h('div', {
        ref: el,
        style: {
          width: '100%',
          height: `${props.height}px`,
          borderRadius: '18px',
          overflow: 'hidden',
        },
      })
  },
})

watch(
  selectedWidget,
  async (widget) => {
    if (!widget) return
    if (widget.type === 'metric' && widget.query.aggregation !== 'count' && !widget.query.field_key) {
      widget.query.field_key = numericFields.value[0]?.key ?? null
    }
    if (widget.type === 'chart' && !widget.query.group_by_key) {
      widget.query.group_by_key = selectedFields.value[0]?.key ?? null
    }
    if (widget.type === 'map') {
      if (!widget.config.latField) {
        widget.config.latField = selectedFields.value.find((field) => /lat/i.test(field.key))?.key ?? ''
      }
      if (!widget.config.lngField) {
        widget.config.lngField = selectedFields.value.find((field) => /lng|lon/i.test(field.key))?.key ?? ''
      }
    }
    await loadPreview()
  }
)

watch(
  () => [
    selectedWidget.value?.source.table_id,
    selectedWidget.value?.query.aggregation,
    selectedWidget.value?.query.field_key,
    selectedWidget.value?.query.group_by_key,
    selectedWidget.value?.query.limit,
    selectedWidget.value?.config.chartType,
    selectedWidget.value?.config.latField,
    selectedWidget.value?.config.lngField,
    selectedWidget.value?.config.labelField,
  ],
  async () => {
    if (!selectedWidget.value) return
    await loadPreview()
  }
)

onMounted(loadPage)
</script>

<template>
  <main class="builder-page">
    <header class="topbar">
      <div>
        <button class="ghost-link" @click="router.push({ name: 'dashboard' })">← Назад</button>
        <h1>Конструктор дашборда</h1>
        <p>Сверху выбираешь виджет, ниже редактируешь только его.</p>
      </div>
      <div class="topbar-actions">
        <label class="publish-toggle">
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
          <input v-model="reportName" placeholder="Например: Анализ ДТП" />
        </div>
        <div>
          <label>Описание</label>
          <input v-model="reportDescription" placeholder="Коротко про назначение отчета" />
        </div>
      </section>

      <section class="surface-card widget-toolbar">
        <div class="toolbar-row">
          <div class="toolbar-label">Виджеты отчета</div>
          <div class="widget-tabs">
            <button
              v-for="widget in widgets"
              :key="widget.id"
              class="widget-tab"
              :class="{ active: widget.id === selectedWidgetId }"
              @click="selectedWidgetId = widget.id"
            >
              {{ widget.title }}
            </button>
          </div>
        </div>

        <div class="toolbar-row">
          <div class="toolbar-label">Добавить</div>
          <div class="widget-actions-row">
            <button
              v-for="item in widgetPalette"
              :key="item.type"
              class="add-widget-btn"
              @click="addWidget(item.type)"
            >
              + {{ item.title }}
            </button>
          </div>
        </div>
      </section>

      <section v-if="selectedWidget" class="editor-layout">
        <aside class="surface-card editor-panel">
          <div class="panel-head">
            <div>
              <h3>Редактор виджета</h3>
              <p>{{ selectedWidget.type }}</p>
            </div>
            <div class="inline-actions">
              <button @click="moveWidget(selectedWidget.id, -1)">↑</button>
              <button @click="moveWidget(selectedWidget.id, 1)">↓</button>
              <button @click="duplicateWidget(selectedWidget.id)">Копия</button>
              <button class="danger-text" @click="removeWidget(selectedWidget.id)">Удалить</button>
            </div>
          </div>

          <div class="field-block">
            <label>Название</label>
            <input v-model="selectedWidget.title" />
          </div>

          <div class="field-block">
            <label>Подпись / описание</label>
            <textarea v-model="selectedWidget.description" rows="3" placeholder="Необязательно" />
          </div>

          <div v-if="selectedWidget.type === 'text'" class="field-block">
            <label>Текст</label>
            <textarea v-model="selectedWidget.config.content" rows="10" />
          </div>

          <template v-else>
            <div class="field-block">
              <label>Таблица-источник</label>
              <select v-model.number="selectedWidget.source.table_id">
                <option :value="null">Выберите таблицу</option>
                <option v-for="table in tables" :key="table.id" :value="table.id">{{ table.name }}</option>
              </select>
            </div>

            <div v-if="selectedWidget.type === 'metric'" class="field-block">
              <label>Агрегация</label>
              <select v-model="selectedWidget.query.aggregation">
                <option v-for="aggregation in aggregationOptions" :key="aggregation" :value="aggregation">{{ aggregation }}</option>
              </select>

              <label>Поле</label>
              <select v-model="selectedWidget.query.field_key" :disabled="selectedWidget.query.aggregation === 'count'">
                <option :value="null">Не требуется для count</option>
                <option v-for="field in numericFields" :key="field.key" :value="field.key">{{ field.name }}</option>
              </select>
            </div>

            <div v-if="selectedWidget.type === 'chart'" class="field-block">
              <label>Тип графика</label>
              <select v-model="selectedWidget.config.chartType">
                <option value="bar">bar</option>
                <option value="line">line</option>
              </select>

              <label>Группировка</label>
              <select v-model="selectedWidget.query.group_by_key">
                <option :value="null">Выберите поле</option>
                <option v-for="field in selectedFields" :key="field.key" :value="field.key">{{ field.name }}</option>
              </select>

              <label>Агрегация</label>
              <select v-model="selectedWidget.query.aggregation">
                <option v-for="aggregation in aggregationOptions" :key="aggregation" :value="aggregation">{{ aggregation }}</option>
              </select>

              <label>Поле значения</label>
              <select v-model="selectedWidget.query.field_key" :disabled="selectedWidget.query.aggregation === 'count'">
                <option :value="null">Не требуется для count</option>
                <option v-for="field in numericFields" :key="field.key" :value="field.key">{{ field.name }}</option>
              </select>
            </div>

            <div v-if="selectedWidget.type === 'table'" class="field-block">
              <label>Колонки таблицы</label>
              <div class="checkbox-grid">
                <label v-for="field in selectedFields" :key="field.key" class="checkbox-row">
                  <input
                    type="checkbox"
                    :checked="Array.isArray(selectedWidget.config.columns) && selectedWidget.config.columns.includes(field.key)"
                    @change="
                      selectedWidget.config.columns = ($event.target as HTMLInputElement).checked
                        ? [...(Array.isArray(selectedWidget.config.columns) ? selectedWidget.config.columns : []), field.key]
                        : (Array.isArray(selectedWidget.config.columns) ? selectedWidget.config.columns : []).filter((key) => key !== field.key)
                    "
                  />
                  {{ field.name }}
                </label>
              </div>
            </div>

            <div v-if="selectedWidget.type === 'map'" class="field-block">
              <label>Широта</label>
              <select v-model="selectedWidget.config.latField">
                <option value="">Выберите поле</option>
                <option v-for="field in selectedFields" :key="field.key" :value="field.key">{{ field.name }}</option>
              </select>

              <label>Долгота</label>
              <select v-model="selectedWidget.config.lngField">
                <option value="">Выберите поле</option>
                <option v-for="field in selectedFields" :key="field.key" :value="field.key">{{ field.name }}</option>
              </select>

              <label>Подпись</label>
              <select v-model="selectedWidget.config.labelField">
                <option value="">Без подписи</option>
                <option v-for="field in selectedFields" :key="field.key" :value="field.key">{{ field.name }}</option>
              </select>
            </div>

            <div class="field-block">
              <label>Ширина в сетке</label>
              <select v-model="selectedWidget.presentation.width">
                <option value="half">Половина строки</option>
                <option value="full">Во всю строку</option>
              </select>
            </div>

            <div class="field-block">
              <label>Цвет</label>
              <input v-model="selectedWidget.presentation.color" type="color" />
            </div>
          </template>
        </aside>

        <section class="surface-card preview-panel">
          <div class="panel-head">
            <div>
              <h3>Предпросмотр</h3>
              <p>{{ selectedWidget.title }}</p>
            </div>
          </div>

          <div v-if="previewLoading" class="muted">Загрузка preview...</div>
          <div v-else-if="previewError" class="error">{{ previewError }}</div>

          <div v-else-if="selectedWidget.type === 'text'" class="text-preview">
            {{ String(selectedWidget.config.content || 'Пустой текст') }}
          </div>

          <div v-else-if="selectedWidget.type === 'metric'" class="metric-preview">
            {{ metricPreview !== null ? metricPreview.toLocaleString('ru-RU') : 'Нет данных' }}
          </div>

          <ChartPreview v-else-if="selectedWidget.type === 'chart' && chartPreview.length > 0" :option="chartOption" />

          <MapPreview v-else-if="selectedWidget.type === 'map' && mapPoints.length > 0" :points="mapPoints.slice(0, 50)" />

          <div v-else-if="selectedWidget.type === 'table' && tablePreviewColumns.length > 0" class="table-preview">
            <div class="table-head-row">
              <span v-for="column in tablePreviewColumns" :key="column.key">{{ column.name }}</span>
            </div>
            <div v-for="row in previewRows.slice(0, 8)" :key="row.id" class="table-body-row">
              <span v-for="column in tablePreviewColumns" :key="column.key">{{ formatValue(row.data[column.key], column.type) }}</span>
            </div>
          </div>

          <div v-else class="muted">Настрой виджет, чтобы увидеть результат.</div>
        </section>
      </section>

      <div v-else class="surface-card muted">Добавь первый виджет.</div>
    </template>
  </main>
</template>

<style scoped>
.builder-page {
  min-height: 100vh;
  padding: 28px;
  background: linear-gradient(180deg, #f8faff 0%, #eff4fc 100%);
  display: grid;
  gap: 18px;
}

.surface-card {
  border: 1px solid var(--line);
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.94);
  padding: 18px;
  box-shadow: var(--shadow-soft);
}

.topbar,
.topbar-actions,
.toolbar-row,
.widget-tabs,
.widget-actions-row,
.panel-head,
.inline-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.topbar,
.toolbar-row,
.panel-head {
  justify-content: space-between;
}

.topbar h1,
.panel-head h3 {
  margin: 0;
}

.topbar p,
.panel-head p,
.muted {
  margin: 4px 0 0;
  color: var(--text-muted);
}

.ghost-link,
.primary-btn,
.widget-tab,
.add-widget-btn,
.inline-actions button {
  border: none;
  cursor: pointer;
  border-radius: 12px;
}

.ghost-link {
  background: transparent;
  padding: 0;
  color: #156f69;
}

.primary-btn {
  background: var(--accent);
  color: var(--text-main);
  padding: 10px 16px;
}

.publish-toggle {
  display: flex;
  align-items: center;
  gap: 8px;
}

.meta-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.widget-toolbar {
  display: grid;
  gap: 14px;
}

.toolbar-label {
  min-width: 130px;
  font-weight: 600;
  color: var(--text-main);
}

.widget-tabs,
.widget-actions-row {
  flex-wrap: wrap;
}

.widget-tab,
.add-widget-btn {
  background: #f2f6ff;
  color: var(--text-main);
  padding: 10px 14px;
}

.widget-tab.active {
  background: var(--accent);
  color: var(--text-main);
}

.editor-layout {
  display: grid;
  grid-template-columns: 380px minmax(0, 1fr);
  gap: 16px;
  align-items: start;
}

.editor-panel,
.preview-panel,
.field-block {
  display: grid;
  gap: 12px;
}

.danger-text {
  background: transparent !important;
  color: #bb4458;
  padding: 0 !important;
}

.checkbox-grid {
  display: grid;
  gap: 8px;
}

.checkbox-row {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 8px;
  align-items: center;
}

.text-preview {
  white-space: pre-wrap;
  line-height: 1.6;
}

.metric-preview {
  font-size: 2.4rem;
  font-weight: 700;
  color: #1e63d8;
}

.table-preview {
  display: grid;
  gap: 8px;
}

.table-head-row,
.table-body-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 8px;
}

.table-head-row {
  text-transform: uppercase;
  font-size: 0.8rem;
  color: var(--text-muted);
}

input,
select,
textarea {
  width: 100%;
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 10px 12px;
  background: var(--bg-panel);
  font: inherit;
}

input[type='checkbox'] {
  width: auto;
}

.error {
  color: var(--danger);
}

@media (max-width: 1100px) {
  .editor-layout,
  .meta-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .builder-page {
    padding: 16px;
  }

  .toolbar-row {
    flex-direction: column;
    align-items: start;
  }
}
</style>
