<script setup lang="ts">
import { computed, defineComponent, h, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import VChart from 'vue-echarts'
import { BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { use } from 'echarts/core'
import maplibregl from 'maplibre-gl'

import { ReportUseCase } from '../../application/usecases/ReportUseCase'
import type { PublicDashboardChart, PublicDashboardChartPoint, PublicDashboardData, PublicDashboardWidget } from '../../domain/entities/Report'

use([CanvasRenderer, BarChart, GridComponent, TooltipComponent])

const route = useRoute()
const reportId = Number(route.params.reportId)

const dashboard = ref<PublicDashboardData | null>(null)
const loading = ref(true)
const error = ref('')

const globalSearch = ref('')
const columnFilters = ref<Record<string, string>>({})
const sortKey = ref<string>('created_at')
const sortDirection = ref<'asc' | 'desc'>('desc')
const widgetTableSearch = ref<Record<string, string>>({})
const widgetTableFilters = ref<Record<string, Record<string, string>>>({})
const widgetTableSortKey = ref<Record<string, string>>({})
const widgetTableSortDirection = ref<Record<string, 'asc' | 'desc'>>({})
const widgetTablePage = ref<Record<string, number>>({})

const columnKeys = computed(() => {
  if (!dashboard.value || dashboard.value.recent_records.length === 0) return []
  const keys = new Set<string>()
  dashboard.value.recent_records.forEach((record) => {
    Object.keys(record.data || {}).forEach((key) => keys.add(key))
  })
  return Array.from(keys)
})

const filteredRecords = computed(() => {
  if (!dashboard.value) return []

  const searchValue = globalSearch.value.trim().toLowerCase()

  return [...dashboard.value.recent_records]
    .filter((record) => {
      const rawValues = [
        ...columnKeys.value.map((key) => formatCell(record.data[key])),
        formatDate(record.submitted_at || record.created_at),
      ]

      if (searchValue && !rawValues.some((value) => value.toLowerCase().includes(searchValue))) {
        return false
      }

      return Object.entries(columnFilters.value).every(([key, filterValue]) => {
        if (!filterValue.trim()) return true
        return formatCell(record.data[key]).toLowerCase().includes(filterValue.trim().toLowerCase())
      })
    })
    .sort((left, right) => compareRecords(left, right, sortKey.value, sortDirection.value))
})

const mapPoints = computed(() => {
  if (!dashboard.value) return []

  return dashboard.value.recent_records
    .map((record) => extractPoint(record))
    .filter(Boolean) as Array<{ lat: number; lng: number; label: string }>
})

const hasWidgetLayout = computed(() => Boolean(dashboard.value?.widgets?.length))

const hasPositionedWidgetLayout = computed(() =>
  Boolean(
    dashboard.value?.widgets?.some(
      (widget) =>
        typeof widget.grid_x === 'number' &&
        typeof widget.grid_y === 'number' &&
        typeof widget.grid_width === 'number' &&
        typeof widget.grid_height === 'number'
    )
  )
)

const widgetGridColumns = computed(() => {
  if (!dashboard.value) return 12
  if (!hasPositionedWidgetLayout.value) return 12
  const maxCol = dashboard.value.widgets.reduce((maxValue, widget) => {
    if (typeof widget.grid_x !== 'number' || typeof widget.grid_width !== 'number') return maxValue
    return Math.max(maxValue, widget.grid_x + widget.grid_width)
  }, 12)
  return Math.max(4, Math.min(24, maxCol))
})

const widgetGridRows = computed(() => {
  if (!dashboard.value) return 8
  if (!hasPositionedWidgetLayout.value) {
    return Math.max(8, dashboard.value.widgets.length * 2)
  }
  const maxRow = dashboard.value.widgets.reduce((maxValue, widget) => {
    if (typeof widget.grid_y !== 'number' || typeof widget.grid_height !== 'number') return maxValue
    return Math.max(maxValue, widget.grid_y + widget.grid_height)
  }, 8)
  return Math.max(8, maxRow)
})

function widgetLayoutStyle(widget: PublicDashboardWidget) {
  if (
    hasPositionedWidgetLayout.value &&
    typeof widget.grid_x === 'number' &&
    typeof widget.grid_y === 'number' &&
    typeof widget.grid_width === 'number' &&
    typeof widget.grid_height === 'number'
  ) {
    return {
      gridColumn: `${widget.grid_x + 1} / span ${Math.max(1, widget.grid_width)}`,
      gridRow: `${widget.grid_y + 1} / span ${Math.max(1, widget.grid_height)}`,
    }
  }

  return {
    gridColumn: widget.width === 'half' ? 'span 1' : '1 / -1',
    gridRow: 'auto',
  }
}

function compareRecords(
  left: PublicDashboardData['recent_records'][number],
  right: PublicDashboardData['recent_records'][number],
  key: string,
  direction: 'asc' | 'desc'
) {
  const factor = direction === 'asc' ? 1 : -1

  const leftValue = key === 'created_at' ? left.submitted_at || left.created_at : left.data[key]
  const rightValue = key === 'created_at' ? right.submitted_at || right.created_at : right.data[key]

  const leftNumber = toNumber(leftValue)
  const rightNumber = toNumber(rightValue)
  if (leftNumber !== null && rightNumber !== null) {
    return (leftNumber - rightNumber) * factor
  }

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

function setColumnFilter(key: string, value: string) {
  columnFilters.value = {
    ...columnFilters.value,
    [key]: value,
  }
}

function chartOption(chart: PublicDashboardChart) {
  const baseColor = chart.color || '#1e63d8'
  return {
    color: [baseColor],
    grid: { left: 24, right: 18, top: 20, bottom: 46, containLabel: true },
    tooltip: { trigger: 'axis' },
    xAxis: {
      type: 'category',
      data: chart.points.map((point) => point.label),
      axisLabel: {
        color: '#5c7281',
        interval: 0,
        rotate: chart.points.length > 5 ? 18 : 0,
      },
      axisTick: { show: false },
    },
    yAxis: {
      type: 'value',
      axisLabel: { color: '#5c7281' },
      splitLine: { lineStyle: { color: 'rgba(80, 98, 106, 0.10)' } },
    },
    series: [
      {
        type: 'bar',
        barMaxWidth: 56,
        borderRadius: [10, 10, 0, 0],
        itemStyle: {
          color: baseColor,
        },
        data: chart.points.map((point) => point.value),
      },
    ],
  }
}

function widgetChartOption(widget: PublicDashboardWidget) {
  const points = resolveWidgetChartPoints(widget)
  return chartOption({
    title: widget.title,
    chart_type: 'bar',
    color: widget.color || '#1e63d8',
    points,
  })
}

function resolveWidgetChartPoints(widget: PublicDashboardWidget): PublicDashboardChartPoint[] {
  const directPoints = widget.points || []
  if (directPoints.length > 0) return directPoints
  if (!dashboard.value) return []

  const sameTitle = dashboard.value.charts.find((chart) => chart.title === widget.title && chart.points.length > 0)
  if (sameTitle) return sameTitle.points

  const firstNonEmpty = dashboard.value.charts.find((chart) => chart.points.length > 0)
  return firstNonEmpty?.points || []
}

function resolveWidgetGaugeValue(widget: PublicDashboardWidget): number | null {
  if (typeof widget.value === 'number' && Number.isFinite(widget.value)) {
    return widget.value
  }
  if (!dashboard.value) return null

  const sameTitleMetric = dashboard.value.metrics.find((metric) => metric.label === widget.title)
  if (sameTitleMetric) return sameTitleMetric.value
  return dashboard.value.metrics[0]?.value ?? null
}

function resolveWidgetGaugePercent(widget: PublicDashboardWidget): number {
  const raw = resolveWidgetGaugeValue(widget)
  if (raw === null) return 0
  const normalized = raw > 1 && raw <= 100 ? raw : raw <= 1 ? raw * 100 : raw
  return Math.max(0, Math.min(100, Math.round(normalized)))
}

function getWidgetTableSearch(widgetId: string) {
  return widgetTableSearch.value[widgetId] || ''
}

function getWidgetTableFilters(widgetId: string) {
  return widgetTableFilters.value[widgetId] || {}
}

function getWidgetTableSortKey(widget: PublicDashboardWidget) {
  return widgetTableSortKey.value[widget.id] || widget.columns?.[0]?.key || ''
}

function getWidgetTableSortDirection(widgetId: string) {
  return widgetTableSortDirection.value[widgetId] || 'asc'
}

function getWidgetTablePage(widgetId: string) {
  return widgetTablePage.value[widgetId] || 1
}

function setWidgetTableSearch(widgetId: string, value: string) {
  widgetTableSearch.value = { ...widgetTableSearch.value, [widgetId]: value }
  widgetTablePage.value = { ...widgetTablePage.value, [widgetId]: 1 }
}

function setWidgetTableFilter(widgetId: string, key: string, value: string) {
  widgetTableFilters.value = {
    ...widgetTableFilters.value,
    [widgetId]: {
      ...(widgetTableFilters.value[widgetId] || {}),
      [key]: value,
    },
  }
  widgetTablePage.value = { ...widgetTablePage.value, [widgetId]: 1 }
}

function toggleWidgetTableSort(widget: PublicDashboardWidget, key: string) {
  const currentKey = getWidgetTableSortKey(widget)
  const currentDirection = getWidgetTableSortDirection(widget.id)
  if (currentKey === key) {
    widgetTableSortDirection.value = {
      ...widgetTableSortDirection.value,
      [widget.id]: currentDirection === 'asc' ? 'desc' : 'asc',
    }
    return
  }
  widgetTableSortKey.value = { ...widgetTableSortKey.value, [widget.id]: key }
  widgetTableSortDirection.value = { ...widgetTableSortDirection.value, [widget.id]: key === 'created_at' ? 'desc' : 'asc' }
}

function getFilteredWidgetRows(widget: PublicDashboardWidget) {
  const rows = widget.rows || []
  const columns = widget.columns || []
  const search = getWidgetTableSearch(widget.id).trim().toLowerCase()
  const filters = getWidgetTableFilters(widget.id)
  const sortKey = getWidgetTableSortKey(widget)
  const direction = getWidgetTableSortDirection(widget.id)
  const factor = direction === 'asc' ? 1 : -1

  return [...rows]
    .filter((row) => {
      const values = columns.map((column) => formatCell(row[column.key]))
      if (search && !values.some((value) => value.toLowerCase().includes(search))) {
        return false
      }
      return columns.every((column) => {
        const filterValue = filters[column.key] || ''
        if (!filterValue.trim()) return true
        return formatCell(row[column.key]).toLowerCase().includes(filterValue.trim().toLowerCase())
      })
    })
    .sort((left, right) => {
      const leftValue = left[sortKey]
      const rightValue = right[sortKey]
      const leftNumber = toNumber(leftValue)
      const rightNumber = toNumber(rightValue)
      if (leftNumber !== null && rightNumber !== null) return (leftNumber - rightNumber) * factor
      return String(leftValue ?? '').localeCompare(String(rightValue ?? ''), 'ru') * factor
    })
}

function getWidgetPageSize(widget: PublicDashboardWidget) {
  return widget.page_size && widget.page_size > 0 ? widget.page_size : 20
}

function getWidgetPagedRows(widget: PublicDashboardWidget) {
  const rows = getFilteredWidgetRows(widget)
  const pageSize = getWidgetPageSize(widget)
  const page = getWidgetTablePage(widget.id)
  const start = (page - 1) * pageSize
  return rows.slice(start, start + pageSize)
}

function getWidgetTotalPages(widget: PublicDashboardWidget) {
  return Math.max(1, Math.ceil(getFilteredWidgetRows(widget).length / getWidgetPageSize(widget)))
}

function changeWidgetPage(widget: PublicDashboardWidget, nextPage: number) {
  const totalPages = getWidgetTotalPages(widget)
  const safePage = Math.min(Math.max(1, nextPage), totalPages)
  widgetTablePage.value = { ...widgetTablePage.value, [widget.id]: safePage }
}

function toNumber(value: unknown): number | null {
  if (typeof value === 'number' && Number.isFinite(value)) return value
  if (typeof value === 'string' && value.trim()) {
    const parsed = Number(value)
    return Number.isFinite(parsed) ? parsed : null
  }
  return null
}

function formatCell(value: unknown): string {
  if (value === null || value === undefined || value === '') return '—'
  if (Array.isArray(value)) return value.map((item) => formatCell(item)).join(', ')
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

function formatMetricValue(value: number) {
  return new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 2 }).format(value)
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

function extractPoint(record: PublicDashboardData['recent_records'][number]) {
  const directLat = findNumericValue(record.data, ['lat', 'latitude'])
  const directLng = findNumericValue(record.data, ['lng', 'lon', 'longitude'])

  if (directLat !== null && directLng !== null) {
    return {
      lat: directLat,
      lng: directLng,
      label: String(record.data.name ?? record.data.label ?? record.data.title ?? `#${record.id}`),
    }
  }

  for (const value of Object.values(record.data)) {
    const point = parsePointObject(value)
    if (point) {
      return {
        ...point,
        label: String(record.data.name ?? record.data.label ?? record.data.title ?? `#${record.id}`),
      }
    }
  }

  return null
}

function findNumericValue(source: Record<string, unknown>, keys: string[]) {
  for (const [key, value] of Object.entries(source)) {
    if (!keys.includes(key.toLowerCase())) continue
    const numeric = toNumber(value)
    if (numeric !== null) return numeric
  }
  return null
}

function parsePointObject(value: unknown) {
  if (!value || typeof value !== 'object') {
    if (typeof value === 'string') {
      try {
        return parsePointObject(JSON.parse(value))
      } catch {
        return null
      }
    }
    return null
  }

  const source = value as Record<string, unknown>
  const lat = findNumericValue(source, ['lat', 'latitude'])
  const lng = findNumericValue(source, ['lng', 'lon', 'longitude'])
  if (lat === null || lng === null) return null
  return { lat, lng }
}

const ChartCard = defineComponent({
  name: 'ChartCard',
  props: {
    option: { type: Object, required: true },
  },
  setup(props) {
    return () =>
      h(VChart, {
        option: props.option,
        autoresize: true,
        style: { width: '100%', height: '320px' },
      })
  },
})

const MapCard = defineComponent({
  name: 'MapCard',
  props: {
    points: {
      type: Array as () => Array<{ lat: number; lng: number; label: string }>,
      required: true,
    },
  },
  setup(props) {
    const el = ref<HTMLDivElement | null>(null)
    let map: maplibregl.Map | null = null
    let markerObjects: maplibregl.Marker[] = []

    const syncMap = () => {
      if (!map) return
      markerObjects.forEach((marker) => marker.remove())
      markerObjects = []
      markerObjects = props.points.map(
        (point) =>
          new maplibregl.Marker({ color: '#1e63d8' })
            .setLngLat([point.lng, point.lat])
            .setPopup(new maplibregl.Popup({ offset: 12 }).setText(point.label))
            .addTo(map)
      )

      if (props.points.length === 0) return
      if (props.points.length === 1) {
        map.setCenter([props.points[0].lng, props.points[0].lat])
        map.setZoom(10)
        return
      }

      const bounds = new maplibregl.LngLatBounds()
      props.points.forEach((point) => bounds.extend([point.lng, point.lat]))
      map.fitBounds(bounds, { padding: 40, maxZoom: 11, animate: false })
    }

    onMounted(async () => {
      await nextTick()
      if (!el.value) return
      map = new maplibregl.Map({
        container: el.value,
        style: 'https://tiles.openfreemap.org/styles/liberty',
        center: [37.618423, 55.751244],
        zoom: 4,
        attributionControl: true,
      })
      map.on('load', syncMap)
    })

    watch(
      () => props.points,
      () => {
        syncMap()
      },
      { deep: true }
    )

    onBeforeUnmount(() => {
      markerObjects.forEach((marker) => marker.remove())
      markerObjects = []
      map?.remove()
      map = null
    })

    return () =>
      h('div', {
        ref: el,
        style: {
          width: '100%',
          height: '360px',
          borderRadius: '18px',
          overflow: 'hidden',
        },
      })
  },
})

const loadDashboard = async () => {
  loading.value = true
  error.value = ''
  try {
    dashboard.value = await ReportUseCase.getPublicDashboard(reportId)
  } catch (err: unknown) {
    const detail =
      typeof err === 'object' &&
      err !== null &&
      'response' in err &&
      typeof (err as { response?: { data?: { detail?: string } } }).response?.data?.detail === 'string'
        ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
        : null
    error.value = detail || 'Публичный дашборд не найден или не опубликован'
  } finally {
    loading.value = false
  }
}

onMounted(loadDashboard)
</script>

<template>
  <main class="public-dashboard-page">
    <section class="dashboard-shell">
      <div v-if="loading" class="loading-state">Загрузка дашборда...</div>
      <div v-else-if="error" class="error-state">{{ error }}</div>

      <template v-else-if="dashboard">
        <header class="hero-card">
          <div class="hero-copy">
            <span class="eyebrow">Analytics Dashboard</span>
            <h1>{{ dashboard.name }}</h1>
            <p>{{ dashboard.description || 'Публичный дашборд без описания' }}</p>
          </div>
          <div class="hero-meta">
            <span>Обновлено</span>
            <strong>{{ formatDate(dashboard.generated_at) }}</strong>
          </div>
        </header>

        <section
          v-if="hasWidgetLayout"
          class="widget-grid"
          :class="{ 'widget-grid--positioned': hasPositionedWidgetLayout }"
          :style="{
            gridTemplateColumns: `repeat(${hasPositionedWidgetLayout ? widgetGridColumns : 2}, minmax(0, 1fr))`,
            gridTemplateRows: hasPositionedWidgetLayout ? `repeat(${widgetGridRows}, minmax(80px, auto))` : 'none',
          }"
        >
          <article
            v-for="widget in dashboard.widgets"
            :key="widget.id"
            class="widget-shell"
            :class="{ 'widget-shell--full': !hasPositionedWidgetLayout && widget.width !== 'half' }"
            :style="widgetLayoutStyle(widget)"
          >
            <header class="widget-header" v-if="widget.description">
              <p v-if="widget.description" class="widget-description">{{ widget.description }}</p>
            </header>

            <div v-if="widget.type === 'text'" class="widget-text">
              {{ widget.content || 'Пустой текстовый блок' }}
            </div>

            <div v-else-if="widget.type === 'metric'" class="widget-metric" :style="{ color: widget.color || '#1e63d8' }">
              {{ widget.value !== null && widget.value !== undefined ? formatMetricValue(widget.value) : '—' }}
            </div>

            <ChartCard
              v-else-if="widget.type === 'chart' && resolveWidgetChartPoints(widget).length > 0"
              :option="widgetChartOption(widget)"
            />

            <div v-else-if="widget.type === 'gauge'" class="widget-gauge">
              <div
                class="gauge-ring"
                :style="{ '--gauge-fill': String(resolveWidgetGaugePercent(widget)) }"
              >
                <span>{{ resolveWidgetGaugePercent(widget) }}%</span>
              </div>
              <strong>{{ resolveWidgetGaugeValue(widget) !== null ? formatMetricValue(resolveWidgetGaugeValue(widget) as number) : '—' }}</strong>
            </div>

            <MapCard
              v-else-if="widget.type === 'map' && (widget.map_points?.length || 0) > 0"
              :points="widget.map_points || []"
            />

            <div v-else-if="widget.type === 'table' && (widget.columns?.length || 0) > 0" class="widget-table-block">
              <div class="table-toolbar">
                <input
                  :value="getWidgetTableSearch(widget.id)"
                  class="search-input"
                  placeholder="Поиск по таблице"
                  @input="setWidgetTableSearch(widget.id, ($event.target as HTMLInputElement).value)"
                />
              </div>

              <div class="records-table-wrap">
                <table class="records-table">
                  <thead>
                    <tr>
                      <th
                        v-for="column in widget.columns"
                        :key="column.key"
                        class="sortable"
                        @click="toggleWidgetTableSort(widget, column.key)"
                      >
                        {{ column.label }}
                        <small v-if="getWidgetTableSortKey(widget) === column.key">
                          {{ getWidgetTableSortDirection(widget.id) === 'asc' ? '↑' : '↓' }}
                        </small>
                      </th>
                    </tr>
                    <tr class="filter-row">
                      <th v-for="column in widget.columns" :key="`widget-filter-${widget.id}-${column.key}`">
                        <input
                          :value="getWidgetTableFilters(widget.id)[column.key] || ''"
                          placeholder="Фильтр"
                          @input="setWidgetTableFilter(widget.id, column.key, ($event.target as HTMLInputElement).value)"
                        />
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(row, rowIndex) in getWidgetPagedRows(widget)" :key="`${widget.id}-${rowIndex}`">
                      <td v-for="column in widget.columns" :key="column.key">{{ formatCell(row[column.key]) }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <div class="pagination-bar" v-if="getFilteredWidgetRows(widget).length > getWidgetPageSize(widget)">
                <button class="page-btn" :disabled="getWidgetTablePage(widget.id) <= 1" @click="changeWidgetPage(widget, getWidgetTablePage(widget.id) - 1)">
                  ←
                </button>
                <span>
                  Страница {{ getWidgetTablePage(widget.id) }} из {{ getWidgetTotalPages(widget) }}
                </span>
                <button
                  class="page-btn"
                  :disabled="getWidgetTablePage(widget.id) >= getWidgetTotalPages(widget)"
                  @click="changeWidgetPage(widget, getWidgetTablePage(widget.id) + 1)"
                >
                  →
                </button>
              </div>
            </div>

            <p v-else class="muted">Для этого виджета пока нет данных.</p>
          </article>
        </section>

        <section v-else-if="dashboard.metrics.length > 0" class="metrics-grid">
          <article v-for="metric in dashboard.metrics" :key="metric.label" class="metric-card">
            <span>{{ metric.label }}</span>
            <strong>{{ formatMetricValue(metric.value) }}</strong>
          </article>
        </section>

        <section v-if="!hasWidgetLayout && dashboard.charts.length > 0" class="charts-grid">
          <article v-for="chart in dashboard.charts" :key="chart.title" class="chart-card">
            <div class="block-head">
              <h2>{{ chart.title }}</h2>
              <small>{{ chart.points.length }} категорий</small>
            </div>
            <ChartCard v-if="chart.points.length > 0" :option="chartOption(chart)" />
            <p v-else class="muted">Нет данных для графика.</p>
          </article>
        </section>

        <section v-if="!hasWidgetLayout && mapPoints.length > 0" class="map-block">
          <div class="block-head">
            <h2>Карта</h2>
            <small>{{ mapPoints.length }} точек</small>
          </div>
          <MapCard :points="mapPoints" />
        </section>

        <section v-if="!hasWidgetLayout" class="records-block">
          <div class="block-head">
            <h2>Таблица данных</h2>
            <small>{{ filteredRecords.length }} строк</small>
          </div>

          <div class="table-toolbar">
            <input v-model="globalSearch" class="search-input" placeholder="Поиск по всей таблице" />
          </div>

          <div v-if="dashboard.recent_records.length > 0" class="records-table-wrap">
            <table class="records-table">
              <thead>
                <tr>
                  <th class="index-col">#</th>
                  <th
                    v-for="key in columnKeys"
                    :key="key"
                    class="sortable"
                    @click="toggleSort(key)"
                  >
                    <span>{{ key }}</span>
                    <small v-if="sortKey === key">{{ sortDirection === 'asc' ? '↑' : '↓' }}</small>
                  </th>
                  <th class="sortable" @click="toggleSort('created_at')">
                    <span>Создано</span>
                    <small v-if="sortKey === 'created_at'">{{ sortDirection === 'asc' ? '↑' : '↓' }}</small>
                  </th>
                </tr>
                <tr class="filter-row">
                  <th />
                  <th v-for="key in columnKeys" :key="`filter-${key}`">
                    <input
                      :value="columnFilters[key] || ''"
                      placeholder="Фильтр"
                      @input="setColumnFilter(key, ($event.target as HTMLInputElement).value)"
                    />
                  </th>
                  <th />
                </tr>
              </thead>
              <tbody>
                <tr v-for="(record, index) in filteredRecords" :key="record.id">
                  <td class="index-col">{{ index + 1 }}</td>
                  <td v-for="key in columnKeys" :key="`${record.id}-${key}`">
                    {{ formatCell(record.data[key]) }}
                  </td>
                  <td>{{ formatDate(record.submitted_at || record.created_at) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <p v-else class="muted">Нет данных для отображения.</p>
        </section>
      </template>
    </section>
  </main>
</template>

<style scoped>
.public-dashboard-page {
  min-height: 100vh;
  padding: 24px;
  background:
    radial-gradient(circle at top left, rgba(89, 123, 229, 0.15), transparent 28%),
    radial-gradient(circle at bottom right, rgba(54, 191, 175, 0.12), transparent 24%),
    linear-gradient(180deg, #f6f8fc 0%, #edf1f8 100%);
}

.dashboard-shell {
  max-width: 1320px;
  margin: 0 auto;
  display: grid;
  gap: 18px;
}

.hero-card,
.metric-card,
.chart-card,
.records-block,
.map-block,
.loading-state,
.error-state {
  border: 1px solid var(--line);
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.9);
  box-shadow: var(--shadow-soft);
  backdrop-filter: blur(12px);
}

.hero-card {
  padding: 30px 32px;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 20px;
  align-items: end;
}

.eyebrow {
  display: inline-flex;
  margin-bottom: 10px;
  padding: 6px 12px;
  border-radius: 999px;
  background: rgba(30, 99, 216, 0.12);
  color: #355f9b;
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.hero-card h1 {
  margin: 0;
  font-size: clamp(2.4rem, 5vw, 4.2rem);
  line-height: 0.95;
  color: var(--text-main);
}

.hero-card p {
  max-width: 720px;
  margin: 14px 0 0;
  color: var(--text-muted);
  font-size: 1.02rem;
}

.hero-meta {
  display: grid;
  gap: 6px;
  justify-items: end;
  color: var(--text-muted);
}

.hero-meta strong {
  color: var(--text-main);
  font-size: 1.02rem;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 14px;
}

.metric-card {
  padding: 18px 20px;
  display: grid;
  gap: 14px;
}

.metric-card span {
  color: var(--text-muted);
  font-weight: 600;
}

.metric-card strong {
  color: #1e63d8;
  font-size: clamp(2rem, 4vw, 3rem);
  line-height: 1;
}

.charts-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(380px, 1fr));
  gap: 16px;
}

.widget-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 28px 20px;
}

.widget-grid--positioned {
  grid-auto-flow: dense;
  align-items: stretch;
}

.chart-card,
.records-block,
.map-block,
.widget-shell {
  display: grid;
  gap: 16px;
}

.widget-shell {
  padding: 0;
  border: none;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
  backdrop-filter: none;
}

.widget-grid--positioned .widget-shell {
  padding: 16px;
  border: 1px solid var(--line);
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.9);
  box-shadow: 0 18px 36px rgba(26, 44, 74, 0.09);
}

.widget-shell--full {
  grid-column: 1 / -1;
}

.widget-header {
  display: grid;
  gap: 6px;
}

.widget-header h2 {
  margin: 0;
  color: var(--text-main);
  font-size: 1.28rem;
}

.widget-description {
  margin: 0;
  color: var(--text-muted);
  line-height: 1.5;
}

.widget-text {
  white-space: pre-wrap;
  line-height: 1.6;
  color: var(--text-main);
}

.widget-metric {
  font-size: clamp(2.2rem, 5vw, 4rem);
  font-weight: 800;
  line-height: 1;
  padding-top: 6px;
}

.widget-gauge {
  display: grid;
  justify-items: start;
  gap: 10px;
}

.gauge-ring {
  --gauge-fill: 0;
  width: 126px;
  height: 126px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  background: conic-gradient(#1e63d8 calc(var(--gauge-fill) * 3.6deg), #e3ebfb 0deg);
  position: relative;
}

.gauge-ring::after {
  content: '';
  position: absolute;
  width: 96px;
  height: 96px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.95);
}

.gauge-ring span {
  position: relative;
  z-index: 1;
  font-size: 1.25rem;
  font-weight: 800;
  color: #1e63d8;
}

.widget-gauge strong {
  color: var(--text-main);
  font-size: 1.1rem;
}

.widget-table-block {
  display: grid;
  gap: 14px;
}

.block-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: baseline;
}

.block-head h2 {
  margin: 0;
  color: var(--text-main);
  font-size: 1.28rem;
}

.block-head small,
.muted {
  color: var(--text-muted);
}

.table-toolbar {
  display: flex;
  justify-content: flex-end;
}

.pagination-bar {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  color: var(--text-muted);
}

.page-btn {
  border: 1px solid var(--line);
  border-radius: 10px;
  background: rgba(245, 248, 255, 0.95);
  padding: 8px 12px;
  cursor: pointer;
  color: var(--text-main);
}

.page-btn:disabled {
  opacity: 0.45;
  cursor: default;
}

.search-input,
.filter-row input {
  width: 100%;
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 10px 12px;
  background: rgba(245, 248, 255, 0.95);
  font: inherit;
  color: var(--text-main);
}

.search-input {
  max-width: 320px;
}

.records-table-wrap {
  overflow: auto;
}

.records-table {
  width: 100%;
  min-width: 720px;
  border-collapse: collapse;
}

.records-table th,
.records-table td {
  padding: 14px 16px;
  border-bottom: 1px solid var(--line);
  text-align: left;
  vertical-align: top;
  color: var(--text-main);
}

.records-table th {
  background: rgba(242, 246, 255, 0.95);
  font-size: 0.82rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.records-table td {
  font-size: 0.96rem;
  line-height: 1.45;
}

.sortable {
  cursor: pointer;
  user-select: none;
}

.sortable span,
.sortable small {
  display: inline-block;
}

.sortable small {
  margin-left: 6px;
}

.filter-row th {
  padding-top: 10px;
  padding-bottom: 10px;
}

.filter-row input {
  min-width: 120px;
  text-transform: none;
  letter-spacing: normal;
}

.index-col {
  width: 52px;
}

.loading-state,
.error-state {
  padding: 28px;
  color: var(--text-main);
}

.error-state {
  color: var(--danger);
}

@media (max-width: 920px) {
  .public-dashboard-page {
    padding: 14px;
  }

  .hero-card {
    grid-template-columns: 1fr;
    align-items: start;
  }

  .hero-meta,
  .table-toolbar {
    justify-items: start;
    justify-content: flex-start;
  }

  .charts-grid {
    grid-template-columns: 1fr;
  }

  .widget-grid {
    grid-template-columns: 1fr;
  }

  .search-input {
    max-width: none;
  }
}
</style>
