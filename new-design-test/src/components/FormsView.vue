<script setup lang="ts">
import { ref, computed } from 'vue'
import FormCard    from './FormCard.vue'
import FormPreview from './FormPreview.vue'
import FormEditor  from './FormEditor.vue'
import type { Form, Table } from '../types'

const props = defineProps<{
  forms: Form[]
  tables: Table[]
}>()

const emit = defineEmits<{
  'update-form':    [form: Form]
  'delete-form':    [id: number]
  'submit-record':  [formId: number, values: Record<string, unknown>]
}>()

const selectedFormId = ref<number | null>(null)

const selectedForm = computed(
  () => props.forms.find(f => f.id === selectedFormId.value) ?? null
)

function selectForm(id: number) {
  selectedFormId.value = id
}

function handleDelete(id: number) {
  emit('delete-form', id)
  if (selectedFormId.value === id) selectedFormId.value = null
}
</script>

<template>
  <div class="forms-view">
    <!-- Hint + cards row -->
    <div class="forms-top">
      <p class="hint">Создайте несколько форм для одной таблицы или для набора таблиц</p>

      <div class="cards-row">
        <FormCard
          v-for="form in forms"
          :key="form.id"
          :form="form"
          :tables="tables"
          :selected="form.id === selectedFormId"
          @edit="selectForm"
          @delete="handleDelete"
        />

        <div v-if="forms.length === 0" class="no-forms">
          Нажмите «Создать форму» чтобы добавить первую форму
        </div>
      </div>
    </div>

    <!-- Form preview + editor (shown when form selected) -->
    <Transition name="slide-up">
      <div v-if="selectedForm" class="forms-bottom">
        <FormPreview
          :form="selectedForm"
          :tables="tables"
          @submit-record="(fid, vals) => emit('submit-record', fid, vals)"
        />
        <FormEditor
          :form="selectedForm"
          :tables="tables"
          @update="emit('update-form', $event)"
        />
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.forms-view {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: #eef4f6;
}

/* Top section */
.forms-top {
  flex-shrink: 0;
  padding: 20px 24px 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  background: #eef4f6;
}

.hint {
  font-size: 15px;
  color: #5a5d72;
  margin: 0;
  font-weight: 500;
}

.cards-row {
  display: flex;
  flex-direction: row;
  gap: 16px;
  overflow-x: auto;
  padding-bottom: 4px;
}

/* Hide scrollbar but keep scrollable */
.cards-row::-webkit-scrollbar { height: 4px; }
.cards-row::-webkit-scrollbar-track { background: transparent; }
.cards-row::-webkit-scrollbar-thumb { background: #d3dee2; border-radius: 2px; }

.no-forms {
  font-size: 14px;
  color: #b0bac8;
  padding: 16px 0;
  font-style: italic;
}

/* Bottom: two white cards on gray background */
.forms-bottom {
  flex: 1;
  display: flex;
  gap: 14px;
  padding: 0 16px 16px;
  overflow: hidden;
  background: #eef4f6;
}

/* Slide-up transition */
.slide-up-enter-active { transition: opacity 0.25s ease, transform 0.25s ease; }
.slide-up-leave-active { transition: opacity 0.2s ease, transform 0.2s ease; }
.slide-up-enter-from  { opacity: 0; transform: translateY(16px); }
.slide-up-leave-to    { opacity: 0; transform: translateY(16px); }
</style>
