<script setup lang="ts">
import { computed } from 'vue'
import type { Report, Form } from '../types'

const props = defineProps<{
  report: Report
  forms: Form[]
}>()

const emit = defineEmits<{
  delete: [id: number]
}>()

const linkedForms = computed(() =>
  props.forms.filter(f => props.report.formIds.includes(f.id))
)

const formNames = computed(() =>
  linkedForms.value.map(f => f.name).join(', ') || '—'
)

const OUTPUT_LABELS: Record<string, { label: string; color: string }> = {
  excel:     { label: 'Excel',     color: '#1d7044' },
  word:      { label: 'Word',      color: '#2b5eb8' },
  dashboard: { label: 'Dashboard', color: '#7b4db8' },
}

const outputInfo = computed(() => OUTPUT_LABELS[props.report.outputType] ?? { label: props.report.outputType, color: '#5a5d72' })
</script>

<template>
  <div class="report-card">
    <div class="card-header">
      <div class="card-title-row">
        <h3 class="card-name">{{ report.name }}</h3>
        <span class="badge" :style="{ color: outputInfo.color, borderColor: outputInfo.color }">
          {{ outputInfo.label }}
        </span>
      </div>
      <p class="card-desc">{{ report.description || 'Нет описания' }}</p>
    </div>

    <div class="card-meta">
      <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
        <rect x="1" y="3" width="12" height="9" rx="2" stroke="#9ba3b8" stroke-width="1.3"/>
        <path d="M4 3V2M10 3V2M1 6h12" stroke="#9ba3b8" stroke-width="1.3" stroke-linecap="round"/>
      </svg>
      <span>Форм: {{ linkedForms.length }}</span>
      <span class="meta-sep">·</span>
      <span class="meta-forms">{{ formNames }}</span>
    </div>

    <div class="card-footer">
      <button class="btn-delete" @click.stop="emit('delete', report.id)">
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
          <path d="M2 3.5h10M5.5 3.5V2.5h3v1M5 3.5l.5 8M9 3.5l-.5 8" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        Удалить
      </button>
    </div>
  </div>
</template>

<style scoped>
.report-card {
  width: 300px;
  flex-shrink: 0;
  background: #ffffff;
  border: 1.5px solid #d3dee2;
  border-radius: 14px;
  padding: 18px 16px 14px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  transition: box-shadow 0.15s;
}

.report-card:hover {
  box-shadow: 0 4px 16px rgba(90, 93, 114, 0.1);
}

.card-header { display: flex; flex-direction: column; gap: 6px; }

.card-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.card-name {
  font-size: 16px;
  font-weight: 700;
  color: #3c3f52;
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.badge {
  font-size: 11px;
  font-weight: 600;
  border: 1.5px solid;
  border-radius: 8px;
  padding: 2px 9px;
  white-space: nowrap;
  flex-shrink: 0;
}

.card-desc {
  font-size: 13px;
  color: #9ba3b8;
  margin: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.card-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #5a5d72;
}

.meta-sep   { color: #d3dee2; }
.meta-forms {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
  min-width: 0;
  color: #9ba3b8;
}

.card-footer { display: flex; justify-content: flex-end; }

.btn-delete {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 7px 14px;
  border-radius: 10px;
  background: #fef0f0;
  border: 1.5px solid #f5c6c6;
  color: #d95f5f;
  font-size: 13px;
  font-weight: 600;
  font-family: inherit;
  cursor: pointer;
  transition: background 0.15s, filter 0.15s;
}

.btn-delete:hover { background: #fde0e0; }
</style>
