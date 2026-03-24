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
import type { PublicDashboardChart, PublicDashboardData, PublicDashboardWidget } from '../../domain/entities/Report'

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
  const baseColor = chart.color || '#1c8c83'
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
  return chartOption({
    title: widget.title,
    chart_type: 'bar',
    color: widget.color || '#1c8c83',
    points: widget.points || [],
  })
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
          new maplibregl.Marker({ color: '#1c8c83' })
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

        <section v-if="hasWidgetLayout" class="widget-grid">
          <article
            v-for="widget in dashboard.widgets"
            :key="widget.id"
            class="widget-shell"
            :class="{ 'widget-shell--full': widget.width !== 'half' }"
          >
            <header class="widget-header" v-if="widget.description">
              <p v-if="widget.description" class="widget-description">{{ widget.description }}</p>
            </header>

            <div v-if="widget.type === 'text'" class="widget-text">
              {{ widget.content || 'Пустой текстовый блок' }}
            </div>

            <div v-else-if="widget.type === 'metric'" class="widget-metric" :style="{ color: widget.color || '#1c8c83' }">
              {{ widget.value !== null && widget.value !== undefined ? formatMetricValue(widget.value) : '—' }}
            </div>

            <ChartCard
              v-else-if="widget.type === 'chart' && (widget.points?.length || 0) > 0"
              :option="widgetChartOption(widget)"
            />

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
    radial-gradient(circle at top left, rgba(66, 164, 156, 0.16), transparent 28%),
    radial-gradient(circle at bottom right, rgba(47, 95, 120, 0.18), transparent 24%),
    linear-gradient(180deg, #eef7f6 0%, #f7faf8 100%);
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
  border: 1px solid rgba(56, 92, 105, 0.14);
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.84);
  box-shadow: 0 24px 60px rgba(39, 73, 80, 0.08);
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
  background: rgba(28, 140, 131, 0.12);
  color: #1c6f6f;
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.hero-card h1 {
  margin: 0;
  font-size: clamp(2.4rem, 5vw, 4.2rem);
  line-height: 0.95;
  color: #214e61;
}

.hero-card p {
  max-width: 720px;
  margin: 14px 0 0;
  color: #59717b;
  font-size: 1.02rem;
}

.hero-meta {
  display: grid;
  gap: 6px;
  justify-items: end;
  color: #68808a;
}

.hero-meta strong {
  color: #244f5e;
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
  color: #5f7782;
  font-weight: 600;
}

.metric-card strong {
  color: #1c4351;
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

.widget-shell--full {
  grid-column: 1 / -1;
}

.widget-header {
  display: grid;
  gap: 6px;
}

.widget-header h2 {
  margin: 0;
  color: #224d5f;
  font-size: 1.28rem;
}

.widget-description {
  margin: 0;
  color: #667d86;
  line-height: 1.5;
}

.widget-text {
  white-space: pre-wrap;
  line-height: 1.6;
  color: #294e5d;
}

.widget-metric {
  font-size: clamp(2.2rem, 5vw, 4rem);
  font-weight: 800;
  line-height: 1;
  padding-top: 6px;
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
  color: #224d5f;
  font-size: 1.28rem;
}

.block-head small,
.muted {
  color: #6c838b;
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
  color: #627982;
}

.page-btn {
  border: 1px solid rgba(56, 92, 105, 0.14);
  border-radius: 10px;
  background: rgba(247, 251, 251, 0.9);
  padding: 8px 12px;
  cursor: pointer;
  color: #294e5d;
}

.page-btn:disabled {
  opacity: 0.45;
  cursor: default;
}

.search-input,
.filter-row input {
  width: 100%;
  border: 1px solid rgba(56, 92, 105, 0.14);
  border-radius: 12px;
  padding: 10px 12px;
  background: rgba(247, 251, 251, 0.9);
  font: inherit;
  color: #294e5d;
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
  border-bottom: 1px solid rgba(56, 92, 105, 0.10);
  text-align: left;
  vertical-align: top;
  color: #294e5d;
}

.records-table th {
  background: rgba(240, 247, 247, 0.95);
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
  color: #355867;
}

.error-state {
  color: #b24c60;
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
