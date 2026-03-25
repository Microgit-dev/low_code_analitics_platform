<script setup lang="ts">
import type { Report, Form } from '../types'
import ReportCard from './ReportCard.vue'

defineProps<{
  reports: Report[]
  forms: Form[]
}>()

defineEmits<{
  'delete-report': [id: number]
}>()
</script>

<template>
  <div class="reports-view">

    <div v-if="reports.length === 0" class="empty-state">
      <svg width="56" height="56" viewBox="0 0 56 56" fill="none">
        <rect x="8" y="10" width="40" height="36" rx="5" stroke="#d3dee2" stroke-width="2"/>
        <path d="M18 22h20M18 29h14M18 36h8" stroke="#d3dee2" stroke-width="2" stroke-linecap="round"/>
      </svg>
      <p class="empty-title">Нет отчётов</p>
      <p class="empty-hint">Нажмите «Создать отчёт» в верхней панели</p>
    </div>

    <div v-else class="cards-row">
      <ReportCard
        v-for="report in reports"
        :key="report.id"
        :report="report"
        :forms="forms"
        @delete="$emit('delete-report', $event)"
      />
    </div>

  </div>
</template>

<style scoped>
.reports-view {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #eef4f6;
  overflow: hidden;
}

/* Cards row — left to right */
.cards-row {
  display: flex;
  flex-direction: row;
  flex-wrap: wrap;
  gap: 16px;
  padding: 20px 20px;
  overflow-y: auto;
  align-content: flex-start;
}

/* Empty state */
.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 40px;
  animation: fade-in 0.3s ease;
}

@keyframes fade-in {
  from { opacity: 0; transform: translateY(10px); }
  to   { opacity: 1; transform: translateY(0); }
}

.empty-title {
  font-size: 18px;
  font-weight: 600;
  color: #9ba3b8;
  margin: 0;
}

.empty-hint {
  font-size: 14px;
  color: #b0bac8;
  margin: 0;
}
</style>
