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
  tableIds: number[]
  tableOptions: TableOption[]
}>()

const emit = defineEmits<{
  (event: 'close'): void
  (event: 'update:tableIds', value: number[]): void
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
        <h4>Report service: генерация HTML</h4>
        <button class="small ghost" :disabled="uploading" @click="emit('close')">Закрыть</button>
      </header>

      <UiStatusText v-pre>
        Поддерживаемые выражения в Word-шаблоне: {{ count(key) }}, {{ sum(key) }}, {{ avg(key) }},
        {{ min(key) }}, {{ max(key) }}.
      </UiStatusText>

      <label>Таблицы источника (необязательно)</label>
      <div class="template-table-list">
        <label
          v-for="table in tableOptions"
          :key="`template-table-${table.id}`"
          class="checkbox-inline"
        >
          <input
            type="checkbox"
            :disabled="uploading"
            :checked="tableIds.includes(table.id)"
            @change="
              emit(
                'update:tableIds',
                ($event.target as HTMLInputElement).checked
                  ? [...tableIds, table.id]
                  : tableIds.filter((item) => item !== table.id)
              )
            "
          />
          <span>{{ table.name }}</span>
        </label>
      </div>
      <UiStatusText>
        Если таблицы не выбраны, сервис использует все таблицы workspace.
      </UiStatusText>

      <div
        class="template-dropzone"
        :class="{ active: dragActive, disabled: uploading }"
        @dragover="emit('drag-over', $event)"
        @dragleave="emit('drag-leave', $event)"
        @drop="emit('drop', $event)"
      >
        <p>{{ uploading ? 'Генерируем HTML...' : 'Перетащите сюда .docx файл' }}</p>
        <UiStatusText>или</UiStatusText>
        <button class="small" :disabled="uploading" @click="openFilePicker">Выбрать файл</button>
        <UiStatusText v-if="fileName">Текущий файл: {{ fileName }}</UiStatusText>
      </div>

      <input
        ref="templateFileInput"
        class="template-file-input"
        type="file"
        accept=".docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
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

.template-table-list {
  max-height: 220px;
  overflow: auto;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: #ffffff;
  padding: 8px;
  display: grid;
  gap: 8px;
}

.checkbox-inline {
  display: flex;
  align-items: center;
  gap: 8px;
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
