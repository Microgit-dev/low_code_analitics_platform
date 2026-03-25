<script setup lang="ts">
import { ref, computed } from 'vue'
import MapField from './MapField.vue'
import type { Form, Table } from '../types'

const props = defineProps<{
  form: Form
  tables: Table[]
}>()

const emit = defineEmits<{
  'submit-record': [formId: number, values: Record<string, unknown>]
}>()

const linkedTables = computed(() =>
  props.tables.filter(t => props.form.tableIds.includes(t.id))
)

type FieldMap = Record<string, unknown>
const values = ref<FieldMap>({})
const submitted = ref(false)

function key(tableId: number, colId: number) {
  return `${tableId}_${colId}`
}

function buildReadableValues(): Record<string, unknown> {
  const result: Record<string, unknown> = {}
  for (const table of linkedTables.value) {
    for (const col of table.columns) {
      const k = key(table.id, col.id)
      result[col.name] = values.value[k] ?? null
    }
  }
  return result
}

function submitRecord() {
  emit('submit-record', props.form.id, buildReadableValues())
  // Reset values
  values.value = {}
  submitted.value = true
  setTimeout(() => (submitted.value = false), 2000)
}
</script>

<template>
  <div class="preview-card">
    <div class="preview-scroll">
      <template v-for="table in linkedTables" :key="table.id">
        <h2 class="table-title">{{ table.name }}</h2>
        <hr class="divider" />

        <div v-for="col in table.columns" :key="col.id" class="field-block">
          <div class="field-header">
            <span class="field-name">{{ col.name }}</span>
            <span class="field-source">Таблица: {{ table.name }}</span>
          </div>

          <input
            v-if="col.type === 'text'"
            v-model="(values as FieldMap)[key(table.id, col.id)] as string"
            class="f-input"
            type="text"
            placeholder="Введите текст..."
          />
          <textarea
            v-else-if="col.type === 'longText'"
            v-model="(values as FieldMap)[key(table.id, col.id)] as string"
            class="f-input f-textarea"
            placeholder="Введите текст..."
            rows="3"
          />
          <input
            v-else-if="col.type === 'number'"
            v-model.number="(values as FieldMap)[key(table.id, col.id)] as number"
            class="f-input"
            type="number"
            placeholder="0"
          />
          <input
            v-else-if="col.type === 'datetime'"
            v-model="(values as FieldMap)[key(table.id, col.id)] as string"
            class="f-input"
            type="datetime-local"
          />
          <label v-else-if="col.type === 'checkbox'" class="f-checkbox">
            <input
              v-model="(values as FieldMap)[key(table.id, col.id)] as boolean"
              type="checkbox"
            />
            <span>{{ col.name }}</span>
          </label>
          <div v-else-if="col.type === 'radio'" class="f-radio-group">
            <label v-for="opt in ['Вариант 1', 'Вариант 2', 'Вариант 3']" :key="opt" class="f-radio">
              <input
                :name="`radio_${key(table.id, col.id)}`"
                type="radio"
                :value="opt"
                v-model="(values as FieldMap)[key(table.id, col.id)] as string"
              />
              <span>{{ opt }}</span>
            </label>
          </div>
          <select
            v-else-if="col.type === 'select'"
            v-model="(values as FieldMap)[key(table.id, col.id)] as string"
            class="f-input f-select"
          >
            <option value="" disabled>Выберите...</option>
            <option value="opt1">Вариант 1</option>
            <option value="opt2">Вариант 2</option>
          </select>
          <select
            v-else-if="col.type === 'multiselect'"
            multiple
            v-model="(values as FieldMap)[key(table.id, col.id)] as string[]"
            class="f-input f-multiselect"
          >
            <option value="opt1">Вариант 1</option>
            <option value="opt2">Вариант 2</option>
            <option value="opt3">Вариант 3</option>
          </select>
          <MapField
            v-else-if="col.type === 'geoPoint'"
            v-model="(values as FieldMap)[key(table.id, col.id)] as [number, number] | null"
          />
        </div>
      </template>

      <div v-if="linkedTables.length === 0" class="empty">
        Нет выбранных таблиц. Добавьте таблицы в настройках формы справа.
      </div>

      <!-- Submit button -->
      <div v-if="linkedTables.length > 0" class="submit-row">
        <Transition name="fade">
          <span v-if="submitted" class="success-msg">
            ✓ Данные добавлены
          </span>
        </Transition>
        <button class="btn-submit" @click="submitRecord">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path d="M8 3v10M3 8h10" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
          </svg>
          Добавить данные
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.preview-card {
  flex: 1;
  background: #ffffff;
  border-radius: 18px;
  box-shadow: 0 1px 6px rgba(90, 93, 114, 0.07);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.preview-scroll {
  flex: 1;
  overflow-y: auto;
  padding: 28px 32px;
  display: flex;
  flex-direction: column;
  gap: 0;
}

.table-title {
  font-size: 26px;
  font-weight: 700;
  color: #3c3f52;
  margin: 0 0 12px;
}

.divider {
  border: none;
  border-top: 1px solid #e9f1f3;
  margin: 0 0 24px;
}

.field-block {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 22px;
}

.field-header { display: flex; flex-direction: column; gap: 2px; }

.field-name   { font-size: 16px; font-weight: 700; color: #3c3f52; }
.field-source { font-size: 12px; color: #9ba3b8; }

.f-input {
  padding: 12px 14px;
  border: 1.5px solid #d3dee2;
  border-radius: 10px;
  font-size: 15px;
  color: #3c3f52;
  background: #fff;
  outline: none;
  font-family: inherit;
  transition: border-color 0.15s;
  resize: none;
  width: 100%;
  box-sizing: border-box;
}

.f-input:focus        { border-color: #8eacb1; }
.f-input::placeholder { color: #b0bac8; }
.f-textarea           { min-height: 80px; }
.f-select             { appearance: none; cursor: pointer; }
.f-multiselect        { min-height: 90px; }

.f-checkbox {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  font-size: 15px;
  color: #3c3f52;
}

.f-radio-group { display: flex; flex-direction: column; gap: 8px; }

.f-radio {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  font-size: 15px;
  color: #3c3f52;
}

/* Submit section */
.submit-row {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 14px;
  margin-top: 12px;
  padding-top: 20px;
  border-top: 1px solid #e9f1f3;
}

.btn-submit {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 11px 28px;
  border-radius: 12px;
  background: #2f8486;
  border: none;
  font-size: 15px;
  font-weight: 600;
  color: #fff;
  cursor: pointer;
  font-family: inherit;
  transition: filter 0.15s;
}

.btn-submit:hover  { filter: brightness(0.92); }
.btn-submit:active { filter: brightness(0.85); }

.success-msg {
  font-size: 14px;
  font-weight: 500;
  color: #2f8486;
}

.fade-enter-active, .fade-leave-active { transition: opacity 0.3s; }
.fade-enter-from, .fade-leave-to       { opacity: 0; }

.empty {
  color: #9ba3b8;
  font-size: 15px;
  text-align: center;
  margin-top: 60px;
}
</style>
