<script setup lang="ts">
import { ref } from 'vue'
import type { Form, OutputType } from '../types'

const props = defineProps<{
  forms: Form[]
  defaultName: string
}>()

const emit = defineEmits<{
  create: [name: string, description: string, formIds: number[], outputType: OutputType]
  close:  []
}>()

const name        = ref(props.defaultName)
const description = ref('')
const selectedIds = ref<number[]>([])
const outputType  = ref<OutputType>('excel')

const OUTPUT_OPTIONS: { value: OutputType; label: string; icon: string }[] = [
  {
    value: 'excel',
    label: 'Excel',
    icon: `<svg width="22" height="22" viewBox="0 0 22 22" fill="none">
      <rect x="2" y="2" width="18" height="18" rx="3" fill="#1d7044" opacity=".15"/>
      <path d="M6 7l3.5 4L6 15M10 15h6M10 7h6" stroke="#1d7044" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>`,
  },
  {
    value: 'word',
    label: 'Word',
    icon: `<svg width="22" height="22" viewBox="0 0 22 22" fill="none">
      <rect x="2" y="2" width="18" height="18" rx="3" fill="#2b5eb8" opacity=".15"/>
      <path d="M6 7l2 8 3-5 3 5 2-8" stroke="#2b5eb8" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>`,
  },
  {
    value: 'dashboard',
    label: 'Dashboard',
    icon: `<svg width="22" height="22" viewBox="0 0 22 22" fill="none">
      <rect x="2" y="2" width="18" height="18" rx="3" fill="#7b4db8" opacity=".15"/>
      <rect x="5" y="12" width="3" height="5" rx="1" fill="#7b4db8"/>
      <rect x="9.5" y="8" width="3" height="9" rx="1" fill="#7b4db8"/>
      <rect x="14" y="5" width="3" height="12" rx="1" fill="#7b4db8"/>
    </svg>`,
  },
]

function toggleForm(id: number) {
  const idx = selectedIds.value.indexOf(id)
  if (idx === -1) selectedIds.value.push(id)
  else selectedIds.value.splice(idx, 1)
}

function submit() {
  const trimmed = name.value.trim() || props.defaultName
  emit('create', trimmed, description.value.trim(), selectedIds.value, outputType.value)
}

function onOverlay(e: MouseEvent) {
  if (e.target === e.currentTarget) emit('close')
}
</script>

<template>
  <div class="overlay" @click="onOverlay">
    <div class="modal">

      <!-- Header -->
      <div class="modal-head">
        <h2 class="modal-title">Создать отчёт</h2>
        <button class="btn-close" @click="emit('close')">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path d="M1 1l14 14M15 1L1 15" stroke="#5a5d72" stroke-width="1.8" stroke-linecap="round"/>
          </svg>
        </button>
      </div>

      <!-- Body -->
      <div class="modal-body">

        <!-- Name -->
        <div class="field">
          <label class="field-label">Название</label>
          <input
            v-model="name"
            class="f-input"
            type="text"
            :placeholder="defaultName"
          />
        </div>

        <!-- Description -->
        <div class="field">
          <label class="field-label">Описание</label>
          <textarea
            v-model="description"
            class="f-input f-textarea"
            placeholder="Описание отчёта..."
            rows="3"
          />
        </div>

        <!-- Forms multi-select -->
        <div class="field">
          <label class="field-label">Формы</label>
          <div class="form-list" :class="{ empty: forms.length === 0 }">
            <div v-if="forms.length === 0" class="list-empty">Нет созданных форм</div>
            <div
              v-for="form in forms"
              :key="form.id"
              class="list-item"
              :class="{ active: selectedIds.includes(form.id) }"
              @click="toggleForm(form.id)"
            >
              <span class="list-check">
                <svg v-if="selectedIds.includes(form.id)" width="11" height="11" viewBox="0 0 11 11" fill="none">
                  <path d="M2 5.5l2.5 2.5L9 3" stroke="#fff" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
              </span>
              {{ form.name }}
            </div>
          </div>
        </div>

        <!-- Output type -->
        <div class="field">
          <label class="field-label">Тип вывода</label>
          <div class="output-grid">
            <button
              v-for="opt in OUTPUT_OPTIONS"
              :key="opt.value"
              class="output-btn"
              :class="{ active: outputType === opt.value }"
              @click="outputType = opt.value"
            >
              <span class="output-icon" v-html="opt.icon" />
              <span class="output-label">{{ opt.label }}</span>
            </button>
          </div>
        </div>

      </div>

      <!-- Footer -->
      <div class="modal-foot">
        <button class="btn-cancel" @click="emit('close')">Отмена</button>
        <button class="btn-create" @click="submit">Создать отчёт</button>
      </div>

    </div>
  </div>
</template>

<style scoped>
.overlay {
  position: fixed;
  inset: 0;
  background: rgba(60, 63, 82, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(2px);
}

.modal {
  background: #fff;
  border-radius: 18px;
  width: 520px;
  max-height: 88vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 12px 48px rgba(60, 63, 82, 0.2);
  animation: modal-in 0.2s ease;
  overflow: hidden;
}

@keyframes modal-in {
  from { opacity: 0; transform: scale(0.96) translateY(-10px); }
  to   { opacity: 1; transform: scale(1) translateY(0); }
}

/* Header */
.modal-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 22px 24px 0;
}

.modal-title {
  font-size: 20px;
  font-weight: 700;
  color: #3c3f52;
  margin: 0;
}

.btn-close {
  width: 30px;
  height: 30px;
  border-radius: 8px;
  border: none;
  background: transparent;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.15s;
}

.btn-close:hover { background: #f3f9fa; }

/* Body */
.modal-body {
  padding: 18px 24px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.field { display: flex; flex-direction: column; gap: 6px; }

.field-label {
  font-size: 13px;
  font-weight: 600;
  color: #5a5d72;
}

.f-input {
  padding: 10px 14px;
  border: 1.5px solid #d3dee2;
  border-radius: 12px;
  font-size: 14px;
  color: #3c3f52;
  background: #f3f9fa;
  outline: none;
  font-family: inherit;
  transition: border-color 0.15s, background 0.15s;
  resize: none;
  width: 100%;
  box-sizing: border-box;
}

.f-input:focus        { border-color: #8eacb1; background: #fff; }
.f-input::placeholder { color: #b0bac8; }
.f-textarea           { min-height: 72px; }

/* Forms list */
.form-list {
  border: 1.5px solid #d3dee2;
  border-radius: 12px;
  overflow: hidden;
  max-height: 150px;
  overflow-y: auto;
}

.list-empty {
  padding: 12px 14px;
  font-size: 13px;
  color: #b0bac8;
  font-style: italic;
}

.list-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  font-size: 14px;
  color: #5a5d72;
  cursor: pointer;
  transition: background 0.12s;
  border-bottom: 1px solid #f3f9fa;
  user-select: none;
}

.list-item:last-child  { border-bottom: none; }
.list-item:hover       { background: #f3f9fa; }

.list-item.active {
  background: #e6f2f2;
  color: #2f8486;
  font-weight: 600;
}

.list-check {
  width: 18px;
  height: 18px;
  border-radius: 5px;
  border: 1.5px solid #d3dee2;
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: background 0.12s, border-color 0.12s;
}

.list-item.active .list-check {
  background: #2f8486;
  border-color: #2f8486;
}

/* Output type grid */
.output-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}

.output-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 14px 10px;
  border-radius: 12px;
  border: 1.5px solid #d3dee2;
  background: #f3f9fa;
  cursor: pointer;
  font-family: inherit;
  transition: border-color 0.15s, background 0.15s, box-shadow 0.15s;
}

.output-btn:hover {
  background: #e9f4f4;
  border-color: #8eacb1;
}

.output-btn.active {
  border-color: #2f8486;
  background: #e6f2f2;
  box-shadow: 0 0 0 2px rgba(47, 132, 134, 0.15);
}

.output-icon {
  display: flex;
  align-items: center;
  justify-content: center;
}

.output-label {
  font-size: 13px;
  font-weight: 600;
  color: #5a5d72;
}

.output-btn.active .output-label { color: #2f8486; }

/* Footer */
.modal-foot {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 0 24px 22px;
}

.btn-cancel {
  padding: 10px 22px;
  border-radius: 10px;
  border: 1.5px solid #d3dee2;
  background: transparent;
  font-size: 14px;
  font-weight: 500;
  color: #5a5d72;
  cursor: pointer;
  font-family: inherit;
  transition: background 0.15s;
}

.btn-cancel:hover { background: #f3f9fa; }

.btn-create {
  padding: 10px 26px;
  border-radius: 10px;
  background: #2f8486;
  border: none;
  font-size: 14px;
  font-weight: 600;
  color: #fff;
  cursor: pointer;
  font-family: inherit;
  transition: filter 0.15s;
}

.btn-create:hover  { filter: brightness(0.92); }
.btn-create:active { filter: brightness(0.85); }
</style>
