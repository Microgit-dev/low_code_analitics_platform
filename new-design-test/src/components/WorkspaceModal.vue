<script setup lang="ts">
import { ref, watch } from 'vue'

const props = defineProps<{
  defaultName: string
}>()

const emit = defineEmits<{
  'create': [name: string, description: string]
  'close': []
}>()

const name = ref(props.defaultName)
const description = ref('')

watch(() => props.defaultName, (val) => {
  name.value = val
})

function submit() {
  const trimmed = name.value.trim() || props.defaultName
  emit('create', trimmed, description.value.trim())
}

function onOverlayClick(e: MouseEvent) {
  if (e.target === e.currentTarget) {
    emit('close')
  }
}
</script>

<template>
  <div class="modal-overlay" @click="onOverlayClick">
    <div class="modal">
      <div class="modal-header">
        <h2 class="modal-title">Создать рабочее пространство</h2>
        <button class="modal-close" @click="$emit('close')">
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
            <path d="M1 1L17 17M17 1L1 17" stroke="#5a5d72" stroke-width="2" stroke-linecap="round"/>
          </svg>
        </button>
      </div>

      <div class="modal-body">
        <div class="field">
          <label class="field-label">Название</label>
          <input
            v-model="name"
            class="field-input"
            type="text"
            :placeholder="defaultName"
          />
        </div>

        <div class="field">
          <label class="field-label">Описание</label>
          <textarea
            v-model="description"
            class="field-input field-textarea"
            placeholder="Введите описание..."
            rows="3"
          />
        </div>
      </div>

      <div class="modal-footer">
        <button class="btn-cancel" @click="$emit('close')">Отмена</button>
        <button class="btn-create" @click="submit">Создать</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(90, 93, 114, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(2px);
}

.modal {
  background: #ffffff;
  border-radius: 16px;
  width: 480px;
  box-shadow: 0 8px 40px rgba(90, 93, 114, 0.2);
  overflow: hidden;
  animation: modal-in 0.2s ease;
}

@keyframes modal-in {
  from {
    opacity: 0;
    transform: scale(0.95) translateY(-10px);
  }
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 24px 24px 0;
}

.modal-title {
  font-size: 20px;
  font-weight: 600;
  color: #5a5d72;
}

.modal-close {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: transparent;
  border: none;
  cursor: pointer;
  transition: background 0.15s;
}

.modal-close:hover {
  background: #f3f9fa;
}

.modal-body {
  padding: 20px 24px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field-label {
  font-size: 14px;
  font-weight: 500;
  color: #5a5d72;
}

.field-input {
  padding: 10px 14px;
  border: 1.5px solid #d3dee2;
  border-radius: 10px;
  font-size: 15px;
  font-weight: 400;
  color: #5a5d72;
  background: #f3f9fa;
  outline: none;
  transition: border-color 0.15s;
  resize: none;
}

.field-input:focus {
  border-color: #2f8486;
  background: #ffffff;
}

.field-input::placeholder {
  color: #a0a8b8;
}

.field-textarea {
  min-height: 80px;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 0 24px 24px;
}

.btn-cancel {
  padding: 10px 22px;
  border-radius: 10px;
  border: 1.5px solid #d3dee2;
  background: transparent;
  font-size: 15px;
  font-weight: 500;
  color: #5a5d72;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s;
}

.btn-cancel:hover {
  background: #e9f1f3;
  border-color: #d3dee2;
}

.btn-create {
  padding: 10px 28px;
  border-radius: 10px;
  background: #2f8486;
  border: none;
  font-size: 15px;
  font-weight: 500;
  color: #ffffff;
  cursor: pointer;
  transition: background 0.15s, transform 0.1s;
}

.btn-create:hover {
  filter: brightness(0.92);
}

.btn-create:active {
  transform: scale(0.98);
}
</style>
