<script setup lang="ts">
import type { TableStructure } from '../../../domain/entities/TableSchema'

interface DashboardWidget {
  id: string
  type: 'metric' | 'chart' | 'table' | 'gauge' | 'text' | 'map'
  title: string
  description?: string
  gridX: number
  gridY: number
  gridWidth: number
  gridHeight: number
  sourceTableId: number | null
  fieldKey?: string
  aggregation?: 'count' | 'sum' | 'avg' | 'min' | 'max'
  groupByKey?: string | null
  filters?: Record<string, unknown>[]
  chartType?: 'bar' | 'line' | 'pie' | 'area'
  colorScheme?: string
  previewData?: unknown
}

interface Props {
  widget: DashboardWidget
  tables: TableStructure[]
}

const props = defineProps<Props>()

const TABLE_NAME = {
  count: 'Количество',
  sum: 'Сумма',
  avg: 'Среднее',
  min: 'Минимум',
  max: 'Максимум',
}

const CHART_NAMES = {
  bar: 'Столбчатая диаграмма',
  line: 'Линейный график',
  pie: 'Круговая диаграмма',
  area: 'Диаграмма площади',
}

const getTableName = (tableId: number | null) => {
  if (!tableId) return 'Таблица не выбрана'
  return props.tables.find((t) => t.id === tableId)?.name || 'Unknown'
}

const getAggregationLabel = (agg?: string) => {
  return TABLE_NAME[agg as keyof typeof TABLE_NAME] || agg || '—'
}
</script>

<template>
  <div class="widget-preview">
    <div v-if="widget.type === 'metric'" class="preview-metric">
      <div class="metric-value">—</div>
      <div class="metric-label">{{ widget.type === 'metric' ? getAggregationLabel(widget.aggregation) : widget.fieldKey }}</div>
      <div class="metric-source">Источник: {{ getTableName(widget.sourceTableId) }}</div>
    </div>

    <div v-else-if="widget.type === 'chart'" class="preview-chart">
      <div class="chart-type">{{ CHART_NAMES[widget.chartType as keyof typeof CHART_NAMES] || 'Chart' }}</div>
      <div class="chart-placeholder">
        <svg viewBox="0 0 200 120" class="chart-icon">
          <rect v-for="i in 5" :key="i" :x="i * 38 + 5" y="100" width="30" :height="100 - i * 15" fill="#156f69" opacity="0.6" />
        </svg>
      </div>
      <div class="chart-source">{{ getTableName(widget.sourceTableId) }}</div>
    </div>

    <div v-else-if="widget.type === 'table'" class="preview-table">
      <table>
        <thead>
          <tr>
            <th v-for="i in 3" :key="i">Столбец {{ i }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="i in 3" :key="i">
            <td v-for="j in 3" :key="j">—</td>
          </tr>
        </tbody>
      </table>
      <div class="table-source">{{ getTableName(widget.sourceTableId) }}</div>
    </div>

    <div v-else-if="widget.type === 'gauge'" class="preview-gauge">
      <div class="gauge-circle">
        <div class="gauge-value">0%</div>
      </div>
      <div class="gauge-label">{{ widget.fieldKey || 'Значение' }}</div>
    </div>

    <div v-else-if="widget.type === 'text'" class="preview-text">
      <p>{{ widget.description || 'Текстовый блок' }}</p>
    </div>

    <div v-else-if="widget.type === 'map'" class="preview-map">
      <svg viewBox="0 0 200 120" class="map-icon">
        <path
          d="M 50 30 Q 100 20, 150 40 T 150 100 Q 100 110, 50 90 Z"
          fill="#e8f1f0"
          stroke="#156f69"
          stroke-width="2"
        />
        <circle cx="80" cy="60" r="4" fill="#156f69" />
        <circle cx="120" cy="70" r="4" fill="#156f69" />
      </svg>
      <div class="map-label">Географическая карта</div>
    </div>
  </div>
</template>

<style scoped>
.widget-preview {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 12px;
  text-align: center;
}

/* Metric Preview */
.preview-metric {
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: center;
}

.metric-value {
  font-size: 2.5rem;
  font-weight: 700;
  color: #156f69;
  font-family: monospace;
}

.metric-label {
  font-size: 0.9rem;
  color: #6c8189;
}

.metric-source {
  font-size: 0.75rem;
  color: #a0b0b7;
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Chart Preview */
.preview-chart {
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: center;
  width: 100%;
}

.chart-type {
  font-size: 0.85rem;
  color: #6c8189;
  font-weight: 600;
}

.chart-placeholder {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
}

.chart-icon {
  width: 120px;
  height: 80px;
  opacity: 0.6;
}

.chart-source {
  font-size: 0.75rem;
  color: #a0b0b7;
}

/* Table Preview */
.preview-table {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.preview-table table {
  width: 100%;
  font-size: 0.7rem;
  border-collapse: collapse;
}

.preview-table th,
.preview-table td {
  border: 1px solid rgba(64, 90, 97, 0.15);
  padding: 4px;
  text-align: center;
}

.preview-table th {
  background: #f5f9f8;
  font-weight: 600;
  color: #6c8189;
}

.preview-table td {
  background: white;
  color: #6c8189;
}

.table-source {
  font-size: 0.75rem;
  color: #a0b0b7;
}

/* Gauge Preview */
.preview-gauge {
  display: flex;
  flex-direction: column;
  gap: 12px;
  align-items: center;
}

.gauge-circle {
  width: 100px;
  height: 100px;
  border-radius: 50%;
  background: conic-gradient(#156f69 0deg, #156f69 180deg, #e8f1f0 180deg, #e8f1f0 360deg);
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}

.gauge-circle::after {
  content: '';
  position: absolute;
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: white;
}

.gauge-value {
  position: absolute;
  z-index: 1;
  font-size: 1.2rem;
  font-weight: 700;
  color: #156f69;
}

.gauge-label {
  font-size: 0.85rem;
  color: #6c8189;
}

/* Text Preview */
.preview-text {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  min-height: 60px;
}

.preview-text p {
  margin: 0;
  font-size: 0.9rem;
  color: #6c8189;
  max-width: 250px;
  word-break: break-word;
}

/* Map Preview */
.preview-map {
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: center;
  width: 100%;
}

.map-icon {
  width: 120px;
  height: 80px;
  opacity: 0.7;
}

.map-label {
  font-size: 0.85rem;
  color: #6c8189;
}
</style>
