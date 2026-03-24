<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'

import { ReportUseCase } from '../../application/usecases/ReportUseCase'
import type { PublicDashboardData } from '../../domain/entities/Report'

const route = useRoute()
const reportId = Number(route.params.reportId)

const dashboard = ref<PublicDashboardData | null>(null)
const loading = ref(true)
const error = ref('')

const columnKeys = computed(() => {
  if (!dashboard.value || dashboard.value.recent_records.length === 0) return []
  return Object.keys(dashboard.value.recent_records[0].data || {})
})

const chartMaxValue = (points: Array<{ value: number }>) => {
  if (points.length === 0) return 1
  return Math.max(...points.map((point) => point.value), 1)
}

const toPercent = (value: number, maxValue: number) => {
  if (maxValue <= 0) return 0
  return Math.max(4, Math.round((value / maxValue) * 100))
}

const formatDate = (value?: string | null) => {
  if (!value) return '—'
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

const loadDashboard = async () => {
  loading.value = true
  error.value = ''
  try {
    dashboard.value = await ReportUseCase.getPublicDashboard(reportId)
  } catch {
    error.value = 'Публичный дашборд не найден или не опубликован'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadDashboard()
})
</script>

<template>
  <main class="public-dashboard-page">
    <section class="dashboard-shell">
      <div v-if="loading" class="muted">Загрузка отчета...</div>
      <div v-else-if="error" class="error">{{ error }}</div>

      <template v-else-if="dashboard">
        <header class="report-header">
          <h1>{{ dashboard.name }}</h1>
          <p>{{ dashboard.description || 'Публичный дашборд без описания' }}</p>
          <small>Обновлено: {{ formatDate(dashboard.generated_at) }}</small>
        </header>

        <section class="metrics-grid">
          <article v-for="metric in dashboard.metrics" :key="metric.label" class="metric-card">
            <h3>{{ metric.label }}</h3>
            <p>{{ metric.value }}</p>
          </article>
        </section>

        <section class="charts-grid" v-if="dashboard.charts.length > 0">
          <article v-for="chart in dashboard.charts" :key="chart.title" class="chart-card">
            <h2>{{ chart.title }}</h2>
            <div v-if="chart.points.length > 0" class="bar-chart-list">
              <div v-for="point in chart.points" :key="`${chart.title}-${point.label}`" class="bar-chart-row">
                <span class="bar-label">{{ point.label }}</span>
                <div class="bar-track">
                  <div
                    class="bar-fill"
                    :style="{ width: `${toPercent(point.value, chartMaxValue(chart.points))}%` }"
                  />
                </div>
                <strong class="bar-value">{{ point.value }}</strong>
              </div>
            </div>
            <p v-else class="muted">Нет данных для графика.</p>
          </article>
        </section>

        <section class="records-block">
          <h2>Последние записи</h2>
          <div class="records-table-wrap" v-if="dashboard.recent_records.length > 0">
            <table class="records-table">
              <thead>
                <tr>
                  <th>#</th>
                  <th v-for="key in columnKeys" :key="key">{{ key }}</th>
                  <th>Создано</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(record, index) in dashboard.recent_records" :key="record.id">
                  <td>{{ index + 1 }}</td>
                  <td v-for="key in columnKeys" :key="`${record.id}-${key}`">
                    {{ record.data[key] ?? '—' }}
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
  padding: 22px;
  background: linear-gradient(145deg, #eaf4f5 0%, #f4f7ef 100%);
}

.dashboard-shell {
  max-width: 1100px;
  margin: 0 auto;
  display: grid;
  gap: 16px;
}

.report-header {
  border: 1px solid #b6c8c9;
  border-radius: 16px;
  padding: 18px;
  background: #f8fcfc;
}

.report-header h1 {
  margin: 0 0 6px;
  color: #244f5e;
}

.report-header p {
  margin: 0 0 8px;
  color: #5b6d73;
}

.report-header small {
  color: #72858b;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 10px;
}

.charts-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 10px;
}

.chart-card {
  border: 1px solid #b6c8c9;
  border-radius: 14px;
  padding: 14px;
  background: #f7fbfb;
  display: grid;
  gap: 8px;
}

.chart-card h2 {
  margin: 0;
  color: #2a5f70;
  font-size: 1rem;
}

.bar-chart-list {
  display: grid;
  gap: 8px;
}

.bar-chart-row {
  display: grid;
  grid-template-columns: 120px 1fr auto;
  gap: 8px;
  align-items: center;
}

.bar-label {
  color: #2b4e5a;
  font-size: 0.88rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.bar-track {
  height: 12px;
  background: #dce8ea;
  border-radius: 999px;
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  background: linear-gradient(90deg, #2b8f86, #2f5f78);
  border-radius: 999px;
}

.bar-value {
  color: #22464e;
  font-size: 0.86rem;
}

.metric-card {
  border: 1px solid #b6c8c9;
  border-radius: 14px;
  padding: 14px;
  background: #f7fbfb;
}

.metric-card h3 {
  margin: 0;
  color: #2a5f70;
  font-size: 0.9rem;
}

.metric-card p {
  margin: 8px 0 0;
  font-size: 1.5rem;
  font-weight: 700;
  color: #22464e;
}

.records-block {
  border: 1px solid #b6c8c9;
  border-radius: 14px;
  padding: 14px;
  background: #f7fbfb;
  display: grid;
  gap: 10px;
}

.records-block h2 {
  margin: 0;
  color: #274e5f;
  font-size: 1.05rem;
}

.records-table-wrap {
  overflow-x: auto;
}

.records-table {
  width: 100%;
  border-collapse: collapse;
}

.records-table th,
.records-table td {
  border-bottom: 1px solid #d6e2e3;
  padding: 10px;
  text-align: left;
  color: #274e5f;
  white-space: nowrap;
}

.records-table th {
  font-size: 0.84rem;
  text-transform: uppercase;
  letter-spacing: 0.02em;
}

.muted {
  color: #72858b;
}

.error {
  color: #b94b59;
}
</style>
