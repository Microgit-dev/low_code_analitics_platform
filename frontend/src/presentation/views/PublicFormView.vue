<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import type { FormConfiguration } from '../../domain/entities/FormBuilder'
import { httpClient } from '../../infrastructure/api/httpClient'

const route = useRoute()
const formId = Number(route.params.formId)

const form = ref<FormConfiguration | null>(null)
const loading = ref(true)
const error = ref('')
const submitting = ref(false)
const submitted = ref(false)

// Form data
const formData = ref<Record<string, any>>({})
const submitterEmail = ref('')
const listDraftValues = ref<Record<string, string>>({})

const getFieldInputType = (widgetType: string): string => {
  const typeMap: Record<string, string> = {
    number_input: 'number',
    date_input: 'date',
    datetime_input: 'datetime-local'
  }
  return typeMap[widgetType] || 'text'
}

const getFieldOptions = (field: FormConfiguration['fields'][number]): string[] => {
  const options = field.widget_settings?.options
  if (!Array.isArray(options)) return []
  return options.map((item) => String(item)).filter(Boolean)
}

const isArrayWidget = (field: FormConfiguration['fields'][number]): boolean =>
  field.widget_type === 'multiselect' || (field.widget_type === 'checkbox' && getFieldOptions(field).length > 0) || field.widget_type === 'list_input'

const isFieldFilled = (field: FormConfiguration['fields'][number], value: unknown): boolean => {
  if (isArrayWidget(field)) {
    return Array.isArray(value) && value.length > 0
  }

  return value !== null && value !== undefined && value !== ''
}

const getWidgetTypeLabel = (type: string): string => {
  const labels: Record<string, string> = {
    text_input: 'Текстовое поле',
    textarea: 'Многострочный текст',
    number_input: 'Числовое поле',
    date_input: 'Дата',
    datetime_input: 'Дата и время',
    select: 'Выпадающий список',
    multiselect: 'Множественный выбор',
    list_input: 'Список значений',
    checkbox: 'Чекбокс',
    radio: 'Радио'
  }
  return labels[type] || type
}

const ensureArrayFieldValue = (fieldKey: string) => {
  if (!Array.isArray(formData.value[fieldKey])) {
    formData.value[fieldKey] = []
  }
}

const addListItem = (fieldKey: string) => {
  const draft = (listDraftValues.value[fieldKey] || '').trim()
  if (!draft) return

  ensureArrayFieldValue(fieldKey)
  const current = formData.value[fieldKey] as string[]
  if (current.includes(draft)) {
    listDraftValues.value[fieldKey] = ''
    return
  }
  current.push(draft)
  listDraftValues.value[fieldKey] = ''
}

const removeListItem = (fieldKey: string, index: number) => {
  ensureArrayFieldValue(fieldKey)
  const current = formData.value[fieldKey] as unknown[]
  if (index < 0 || index >= current.length) return
  current.splice(index, 1)
}

const isFormValid = computed(() => {
  if (!form.value) return false
  return form.value.fields.every((field) => {
    if (!field.required) return true
    const value = formData.value[field.column_key]
    return isFieldFilled(field, value)
  })
})

const loadForm = async () => {
  loading.value = true
  error.value = ''
  try {
    const response = await httpClient.get<FormConfiguration>(`/forms/${formId}`)
    form.value = response.data

    for (const field of form.value.fields) {
      if (isArrayWidget(field)) {
        ensureArrayFieldValue(field.column_key)
      }
    }
  } catch (err) {
    error.value = 'Форма не найдена или не опубликована'
    console.error(err)
  } finally {
    loading.value = false
  }
}

const handleSubmit = async () => {
  if (!form.value || !isFormValid.value || submitting.value) return

  submitting.value = true
  try {
    await httpClient.post(`/forms/${form.value.id}/submit`, {
      data: formData.value,
      submitter_email: form.value.collect_email ? submitterEmail.value : undefined
    })
    submitted.value = true
  } catch (err) {
    error.value = 'Ошибка при отправке формы. Попробуйте ещё раз.'
    console.error(err)
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  loadForm()
})
</script>

<template>
  <main class="public-form-page">
    <div class="form-container">
      <div v-if="loading" class="loading">Загрузка формы...</div>
      <div v-else-if="error" class="error">{{ error }}</div>
      <div v-else-if="submitted" class="success">
        <h2>✓ Спасибо!</h2>
        <p>Ваша форма успешно отправлена.</p>
      </div>
      <article v-else-if="form" class="form-card">
        <header class="form-header">
          <h1>{{ form.name }}</h1>
          <p v-if="form.description">{{ form.description }}</p>
        </header>

        <form @submit.prevent="handleSubmit">
          <div v-if="form.collect_email" class="form-field">
            <label for="email">Email <span class="required">*</span></label>
            <input
              id="email"
              v-model="submitterEmail"
              type="email"
              required
              placeholder="your@email.com"
            />
          </div>

          <div v-for="field in form.fields" :key="field.column_key" class="form-field">
            <label :for="`field-${field.column_key}`">
              {{ field.field_label }}
              <span v-if="field.required" class="required">*</span>
            </label>

            <input
              v-if="['text_input', 'number_input', 'date_input', 'datetime_input'].includes(field.widget_type)"
              :id="`field-${field.column_key}`"
              v-model="formData[field.column_key]"
              :type="getFieldInputType(field.widget_type)"
              :placeholder="field.placeholder"
              :required="field.required"
            />

            <textarea
              v-else-if="field.widget_type === 'textarea'"
              :id="`field-${field.column_key}`"
              v-model="formData[field.column_key]"
              :placeholder="field.placeholder"
              :required="field.required"
              rows="4"
            />

            <select
              v-else-if="field.widget_type === 'select' && field.widget_settings.options"
              :id="`field-${field.column_key}`"
              v-model="formData[field.column_key]"
              :required="field.required"
            >
              <option value="">{{ field.placeholder || 'Выберите...' }}</option>
              <option v-for="opt in field.widget_settings.options" :key="opt" :value="opt">{{ opt }}</option>
            </select>

            <select
              v-else-if="field.widget_type === 'multiselect' && field.widget_settings.options"
              :id="`field-${field.column_key}`"
              v-model="formData[field.column_key]"
              multiple
            >
              <option v-for="opt in field.widget_settings.options" :key="`multi-${field.column_key}-${opt}`" :value="opt">{{ opt }}</option>
            </select>

            <div v-else-if="field.widget_type === 'list_input'" class="list-editor">
              <div class="list-editor-add-row">
                <input
                  v-model="listDraftValues[field.column_key]"
                  :placeholder="field.placeholder || 'Добавить элемент списка'"
                  @keydown.enter.prevent="addListItem(field.column_key)"
                />
                <button type="button" class="small-btn" @click="addListItem(field.column_key)">Добавить</button>
              </div>
              <ul v-if="Array.isArray(formData[field.column_key]) && formData[field.column_key].length > 0" class="list-editor-items">
                <li v-for="(item, idx) in formData[field.column_key]" :key="`li-${field.column_key}-${idx}`">
                  <span>{{ item }}</span>
                  <button type="button" class="small-btn danger-btn" @click="removeListItem(field.column_key, Number(idx))">Удалить</button>
                </li>
              </ul>
            </div>

            <div v-else-if="field.widget_type === 'checkbox'" class="checkbox-wrapper">
              <template v-if="getFieldOptions(field).length > 0">
                <label v-for="opt in getFieldOptions(field)" :key="`checkbox-${field.column_key}-${opt}`">
                  <input
                    v-model="formData[field.column_key]"
                    type="checkbox"
                    :value="opt"
                  />
                  {{ opt }}
                </label>
              </template>
              <input
                v-else
                :id="`field-${field.column_key}`"
                v-model="formData[field.column_key]"
                type="checkbox"
                :required="field.required"
              />
            </div>

            <div v-else-if="field.widget_type === 'radio' && field.widget_settings.options" class="radio-wrapper">
              <label v-for="opt in field.widget_settings.options" :key="opt">
                <input
                  v-model="formData[field.column_key]"
                  type="radio"
                  :name="`field-${field.column_key}`"
                  :value="opt"
                  :required="field.required"
                />
                {{ opt }}
              </label>
            </div>

            <p v-if="field.help_text" class="help-text">{{ field.help_text }}</p>
          </div>

          <div class="form-actions">
            <button
              type="submit"
              :disabled="!isFormValid || submitting"
            >
              {{ submitting ? 'Отправляем...' : 'Отправить' }}
            </button>
          </div>
        </form>
      </article>
    </div>
  </main>
</template>

<style scoped>
.public-form-page {
  min-height: 100vh;
  padding: 20px;
  background:
    radial-gradient(circle at 12% 18%, rgba(89, 123, 229, 0.16), transparent 34%),
    radial-gradient(circle at 88% 12%, rgba(54, 191, 175, 0.12), transparent 30%),
    linear-gradient(140deg, #f8faff 0%, #eff4fc 100%);
  display: flex;
  align-items: center;
  justify-content: center;
}

.form-container {
  width: 100%;
  max-width: 620px;
}

.form-card {
  background: var(--bg-panel);
  border: 1px solid var(--line);
  border-radius: 18px;
  padding: 32px;
  box-shadow: var(--shadow-soft);
}

.form-header {
  margin-bottom: 24px;
  text-align: center;
}

.form-header h1 {
  margin: 0 0 8px;
  font-size: 1.8rem;
  color: var(--text-main);
}

.form-header p {
  margin: 0;
  color: var(--text-muted);
  line-height: 1.5;
}

form {
  display: grid;
  gap: 18px;
}

.form-field {
  display: grid;
  gap: 6px;
}

.form-field label {
  font-weight: 600;
  font-size: 0.95rem;
  color: var(--text-main);
}

.required {
  color: var(--danger);
}

.form-field input[type='text'],
.form-field input[type='email'],
.form-field input[type='number'],
.form-field input[type='date'],
.form-field input[type='datetime-local'],
.form-field textarea,
.form-field select {
  width: 100%;
  border: 1px solid var(--line);
  background: #f8faff;
  padding: 11px 13px;
  border-radius: 12px;
  font: inherit;
  color: var(--text-main);
  font-size: 0.95rem;
}

.form-field textarea {
  resize: vertical;
  min-height: 100px;
}

.form-field input:focus,
.form-field textarea:focus,
.form-field select:focus {
  outline: none;
  border-color: var(--accent-soft);
  background: var(--bg-panel);
  box-shadow: 0 0 0 3px rgba(30, 99, 216, 0.16);
}

.checkbox-wrapper,
.radio-wrapper {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.list-editor {
  display: grid;
  gap: 8px;
}

.list-editor-add-row {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 8px;
}

.list-editor-items {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 6px;
}

.list-editor-items li {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  border: 1px solid var(--line);
  background: var(--bg-soft);
  border-radius: 10px;
  padding: 7px 10px;
}

.small-btn {
  border: none;
  border-radius: 10px;
  padding: 7px 10px;
  font-size: 0.84rem;
  font-weight: 600;
  background: linear-gradient(140deg, #1e63d8, #2b7df4);
  color: var(--text-main);
  cursor: pointer;
}

.danger-btn {
  background: linear-gradient(140deg, #d93c56, #c72e48);
}

.checkbox-wrapper input,
.radio-wrapper input {
  width: auto;
  margin-right: 6px;
}

.radio-wrapper label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: normal;
  color: var(--text-main);
}

.help-text {
  margin: 0;
  font-size: 0.85rem;
  color: var(--text-muted);
  font-style: italic;
}

.form-actions {
  margin-top: 24px;
  display: flex;
  gap: 12px;
}

.form-actions button {
  flex: 1;
  background: linear-gradient(140deg, #1e63d8, #2b7df4);
  color: var(--text-main);
  border: none;
  padding: 12px 16px;
  border-radius: 12px;
  font-weight: 700;
  font-size: 1rem;
  cursor: pointer;
  transition: all 0.2s ease;
}

.form-actions button:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 14px rgba(30, 99, 216, 0.24);
}

.form-actions button:disabled {
  background: #dfe7f4;
  color: #7a8ead;
  cursor: not-allowed;
}

.loading,
.error,
.success {
  text-align: center;
  padding: 40px 20px;
  background: var(--bg-panel);
  border: 1px solid var(--line);
  border-radius: 16px;
}

.error {
  color: var(--danger);
  background: #fff7f9;
  border-color: #f0c9d1;
}

.success {
  background: #f2f8ff;
  border-color: #cfdcf3;
}

.success h2 {
  margin: 0 0 8px;
  color: #1e63d8;
  font-size: 1.6rem;
}

.success p {
  margin: 0;
  color: var(--text-muted);
}

@media (max-width: 600px) {
  .form-card {
    padding: 20px;
  }

  .form-header h1 {
    font-size: 1.4rem;
  }
}
</style>
