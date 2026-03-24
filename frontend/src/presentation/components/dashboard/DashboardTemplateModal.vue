<script setup lang="ts">
import { ref } from 'vue'
import UiStatusText from '../common/UiStatusText.vue'

interface TableOption {
  id: number
  name: string
}

const props = defineProps<{
  open: boolean
  uploading: boolean
  dragActive: boolean
  error: string
  fileName: string
  tableId: number | null
  tableOptions: TableOption[]
}>()

const emit = defineEmits<{
  (event: 'close'): void
  (event: 'update:tableId', value: number | null): void
  (event: 'drag-over', eventObj: DragEvent): void
  (event: 'drag-leave', eventObj: DragEvent): void
  (event: 'drop', eventObj: DragEvent): void
  (event: 'file-selected', file: File): void
}>()

const templateFileInput = ref<HTMLInputElement | null>(null)

const openFilePicker = () => {
  if (props.uploading) return
  templateFileInput.value?.click()
}

const onFileChange = (event: Event) => {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return
  emit('file-selected', file)
}
</script>

<template>
  <div v-if="open" class="template-modal-backdrop" @click.self="emit('close')">
    <article class="template-modal">
      <header class="template-modal-header">
        <h4>Посчитать по шаблону</h4>
        <button class="small ghost" :disabled="uploading" @click="emit('close')">Закрыть</button>
      </header>

      <UiStatusText v-pre>
        Поддерживаемые выражения в `.odt`: {{ count(key) }}, {{ sum(key) }}, {{ avg(key) }}, {{ min(key) }},
        {{ max(key) }}.
      </UiStatusText>

      <label>Таблица источника</label>
      <select
        :value="tableId"
        :disabled="uploading"
        @change="emit('update:tableId', Number(($event.target as HTMLSelectElement).value) || null)"
      >
        <option :value="null">Выберите таблицу</option>
        <option v-for="table in tableOptions" :key="`template-table-${table.id}`" :value="table.id">
          {{ table.name }}
        </option>
      </select>

      <div
        class="template-dropzone"
        :class="{ active: dragActive, disabled: uploading }"
        @dragover="emit('drag-over', $event)"
        @dragleave="emit('drag-leave', $event)"
        @drop="emit('drop', $event)"
      >
        <p>{{ uploading ? 'Обрабатываем шаблон...' : 'Перетащите сюда .odt файл' }}</p>
        <UiStatusText>или</UiStatusText>
        <button class="small" :disabled="uploading" @click="openFilePicker">Выбрать файл</button>
        <UiStatusText v-if="fileName">Текущий файл: {{ fileName }}</UiStatusText>
      </div>

      <input
        ref="templateFileInput"
        class="template-file-input"
        type="file"
        accept=".odt,application/vnd.oasis.opendocument.text"
        @change="onFileChange"
      />

      <UiStatusText v-if="error" variant="error">{{ error }}</UiStatusText>
    </article>
  </div>
</template>

<style scoped>
.template-modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(25, 48, 57, 0.4);
  display: grid;
  place-items: center;
  z-index: 30;
  padding: 16px;
}

.template-modal {
  width: min(560px, 100%);
  border: 1px solid var(--line);
  border-radius: 14px;
  background: #f8fcfc;
  padding: 14px;
  display: grid;
  gap: 12px;
}

.template-modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.template-dropzone {
  border: 2px dashed #84a7ae;
  border-radius: 12px;
  background: #eef6f8;
  padding: 18px;
  display: grid;
  gap: 8px;
  justify-items: center;
  text-align: center;
}

.template-dropzone.active {
  border-color: #2b8f86;
  background: #e4f6f1;
}

.template-dropzone.disabled {
  opacity: 0.7;
}

.template-dropzone p {
  margin: 0;
}

.template-file-input {
  display: none;
}

button.small {
  padding: 7px 10px;
  font-size: 0.84rem;
}

button.ghost {
  background: #d9e3e5;
  color: #1f353b;
}
</style>
