<script setup lang="ts">
import { ref, watch } from 'vue'
import type { Form, Table } from '../types'

const props = defineProps<{
  form: Form
  tables: Table[]
}>()

const emit = defineEmits<{
  'update': [form: Form]
}>()

const name         = ref(props.form.name)
const description  = ref(props.form.description)
const selectedIds  = ref<number[]>([...props.form.tableIds])
const isPublic     = ref(props.form.isPublic)
const collectEmail = ref(props.form.collectEmail)

watch(() => props.form, (f) => {
  name.value         = f.name
  description.value  = f.description
  selectedIds.value  = [...f.tableIds]
  isPublic.value     = f.isPublic
  collectEmail.value = f.collectEmail
}, { deep: true })

function toggleTable(id: number) {
  const idx = selectedIds.value.indexOf(id)
  if (idx === -1) selectedIds.value.push(id)
  else selectedIds.value.splice(idx, 1)
}

function save() {
  emit('update', {
    ...props.form,
    name: name.value.trim() || props.form.name,
    description: description.value.trim(),
    tableIds: selectedIds.value,
    isPublic: isPublic.value,
    collectEmail: collectEmail.value,
  })
}
</script>

<template>
  <!-- Single white card for form settings -->
  <div class="editor-card">
    <h2 class="card-title">Настройка формы</h2>

    <div class="fields">
      <input
        v-model="name"
        class="f-input"
        type="text"
        placeholder="Название формы..."
      />

      <textarea
        v-model="description"
        class="f-input f-textarea"
        placeholder="Описание..."
        rows="3"
      />
    </div>

    <div class="section">
      <p class="section-label">Таблицы формы</p>
      <div class="table-list">
        <div
          v-for="table in tables"
          :key="table.id"
          class="table-item"
          :class="{ active: selectedIds.includes(table.id) }"
          @click="toggleTable(table.id)"
        >
          {{ table.name }}
        </div>
        <div v-if="tables.length === 0" class="table-empty">Нет таблиц</div>
      </div>
    </div>

    <div class="checkboxes">
      <label class="cb-row" @click="isPublic = !isPublic">
        <span class="cb" :class="{ checked: isPublic }">
          <svg v-if="isPublic" width="10" height="10" viewBox="0 0 10 10" fill="none">
            <path d="M2 5l2.5 2.5L8 3" stroke="#fff" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </span>
        <span class="cb-label">Опубликовать</span>
      </label>

      <label class="cb-row" @click="collectEmail = !collectEmail">
        <span class="cb" :class="{ checked: collectEmail }">
          <svg v-if="collectEmail" width="10" height="10" viewBox="0 0 10 10" fill="none">
            <path d="M2 5l2.5 2.5L8 3" stroke="#fff" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </span>
        <span class="cb-label">Собрать email</span>
      </label>
    </div>

    <div class="spacer" />

    <button class="btn-save" @click="save">Сохранить форму</button>
  </div>
</template>

<style scoped>
/* White card — fixed width right panel */
.editor-card {
  width: 280px;
  flex-shrink: 0;
  background: #ffffff;
  border-radius: 18px;
  box-shadow: 0 1px 6px rgba(90, 93, 114, 0.07);
  padding: 20px 16px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  overflow-y: auto;
  animation: slide-in 0.3s ease;
}

@keyframes slide-in {
  from { transform: translateX(24px); opacity: 0; }
  to   { transform: translateX(0);    opacity: 1; }
}

.card-title {
  font-size: 17px;
  font-weight: 700;
  color: #3c3f52;
  margin: 0;
}

/* Input fields */
.fields {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.f-input {
  padding: 9px 12px;
  border: 1.5px solid #d3dee2;
  border-radius: 12px;
  font-size: 14px;
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
.f-textarea           { min-height: 72px; }

/* Table multi-select */
.section { display: flex; flex-direction: column; gap: 6px; }

.section-label {
  font-size: 13px;
  font-weight: 600;
  color: #5a5d72;
  margin: 0;
}

.table-list {
  border: 1.5px solid #d3dee2;
  border-radius: 12px;
  overflow: hidden;
}

.table-item {
  padding: 9px 12px;
  font-size: 14px;
  color: #5a5d72;
  cursor: pointer;
  transition: background 0.12s;
  border-bottom: 1px solid #f3f9fa;
  user-select: none;
}

.table-item:last-child { border-bottom: none; }
.table-item:hover      { background: #f3f9fa; }

.table-item.active {
  background: #d3dee2;
  color: #3c3f52;
  font-weight: 600;
}

.table-empty {
  padding: 10px 12px;
  font-size: 13px;
  color: #b0bac8;
}

/* Checkboxes */
.checkboxes { display: flex; flex-direction: column; gap: 10px; }

.cb-row {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  user-select: none;
}

.cb {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  border: 1.5px solid #d3dee2;
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: background 0.15s, border-color 0.15s;
}

.cb.checked { background: #2f8486; border-color: #2f8486; }

.cb-label { font-size: 14px; color: #5a5d72; }

/* Save button */
.spacer { flex: 1; min-height: 12px; }

.btn-save {
  padding: 11px 0;
  border-radius: 12px;
  background: #2f8486;
  border: none;
  font-size: 14px;
  font-weight: 600;
  color: #fff;
  cursor: pointer;
  font-family: inherit;
  transition: filter 0.15s;
  width: 100%;
}

.btn-save:hover  { filter: brightness(0.92); }
.btn-save:active { filter: brightness(0.85); }
</style>
