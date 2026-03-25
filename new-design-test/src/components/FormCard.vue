<script setup lang="ts">
import { computed } from 'vue'
import type { Form, Table } from '../types'

const props = defineProps<{
  form: Form
  tables: Table[]
  selected: boolean
}>()

const emit = defineEmits<{
  edit:   [id: number]
  delete: [id: number]
}>()

// Reactive — updates when form.tableIds changes after save
const linkedTables = computed(() =>
  props.tables.filter(t => props.form.tableIds.includes(t.id))
)

const tableNames = computed(() =>
  linkedTables.value.map(t => t.name).join(', ') || '—'
)
</script>

<template>
  <div class="form-card" :class="{ selected }">
    <div class="card-top">
      <div class="card-head">
        <h3 class="card-name">{{ form.name }}</h3>
        <span v-if="form.isPublic" class="badge">Публичная</span>
      </div>
      <!-- single line, overflow ellipsis -->
      <p class="card-desc">{{ form.description || 'Нет описания' }}</p>
    </div>

    <div class="card-meta">
      <span class="meta-row">Таблица: <b>{{ tableNames }}</b></span>
    </div>

    <div class="card-footer">
      <button class="btn-edit"   @click="emit('edit', form.id)">Редактировать</button>
      <button class="btn-delete" @click.stop="emit('delete', form.id)">Удалить</button>
    </div>
  </div>
</template>

<style scoped>
.form-card {
  width: 340px;
  flex-shrink: 0;
  background: #ffffff;
  border: 1.5px solid #d3dee2;
  border-radius: 14px;
  padding: 18px 16px 14px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  transition: border-color 0.15s, box-shadow 0.15s;
}

.form-card.selected {
  border-color: #8eacb1;
  border-width: 2px;
  box-shadow: 0 4px 16px rgba(142, 172, 177, 0.2);
}

.card-top { display: flex; flex-direction: column; gap: 6px; }

.card-head {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.card-name {
  font-size: 16px;
  font-weight: 700;
  color: #3c3f52;
  margin: 0;
}

.badge {
  font-size: 12px;
  color: #5a5d72;
  border: 1px solid #d3dee2;
  border-radius: 8px;
  padding: 2px 10px;
  white-space: nowrap;
}

/* Single line + ellipsis */
.card-desc {
  font-size: 13px;
  color: #9ba3b8;
  margin: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.card-meta {
  font-size: 13px;
  color: #5a5d72;
}

.meta-row {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  display: block;
}

.meta-row b {
  font-weight: 600;
  color: #3c3f52;
}

.card-footer {
  display: flex;
  gap: 8px;
  margin-top: 2px;
}

.btn-edit, .btn-delete {
  flex: 1;
  padding: 8px 0;
  border-radius: 10px;
  border: none;
  font-size: 13px;
  font-weight: 600;
  font-family: inherit;
  cursor: pointer;
  transition: filter 0.15s;
}

.btn-edit   { background: #2f8486; color: #fff; }
.btn-delete { background: #d95f5f; color: #fff; }

.btn-edit:hover,
.btn-delete:hover { filter: brightness(0.92); }
</style>
