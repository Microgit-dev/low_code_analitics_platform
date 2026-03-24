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

const getFieldInputType = (widgetType: string): string => {
  const typeMap: Record<string, string> = {
    number_input: 'number',
    date_input: 'date',
    datetime_input: 'datetime-local'
  }
  return typeMap[widgetType] || 'text'
}

const getWidgetTypeLabel = (type: string): string => {
  const labels: Record<string, string> = {
    text_input: 'Текстовое поле',
    textarea: 'Многострочный текст',
    number_input: 'Числовое поле',
    date_input: 'Дата',
    datetime_input: 'Дата и время',
    select: 'Выпадающий список',
    checkbox: 'Чекбокс',
    radio: 'Радио'
  }
  return labels[type] || type
}

const isFormValid = computed(() => {
  if (!form.value) return false
  return form.value.fields.every((field) => {
    if (!field.required) return true
    const value = formData.value[field.column_key]
    return value !== null && value !== undefined && value !== ''
  })
})

const loadForm = async () => {
  loading.value = true
  error.value = ''
  try {
    const response = await httpClient.get<FormConfiguration>(`/forms/${formId}`)
    form.value = response.data
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

            <div v-else-if="field.widget_type === 'checkbox'" class="checkbox-wrapper">
              <input
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
  background: linear-gradient(135deg, #e8f4f6 0%, #f0f7f9 100%);
  display: flex;
  align-items: center;
  justify-content: center;
}

.form-container {
  width: 100%;
  max-width: 600px;
}

.form-card {
  background: #fff;
  border: 1px solid #b4c6cd;
  border-radius: 16px;
  padding: 32px;
  box-shadow: 0 8px 24px rgba(38, 74, 85, 0.08);
}

.form-header {
  margin-bottom: 24px;
  text-align: center;
}

.form-header h1 {
  margin: 0 0 8px;
  font-size: 1.8rem;
  color: #2f5f78;
}

.form-header p {
  margin: 0;
  color: #7a8c92;
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
  color: #2f5f78;
}

.required {
  color: #b94b59;
}

.form-field input[type='text'],
.form-field input[type='email'],
.form-field input[type='number'],
.form-field input[type='date'],
.form-field input[type='datetime-local'],
.form-field textarea,
.form-field select {
  width: 100%;
  border: 1px solid #b4c6cd;
  background: #fafbfc;
  padding: 11px 13px;
  border-radius: 8px;
  font: inherit;
  color: #2f5f78;
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
  border-color: #2e8d78;
  background: #fff;
  box-shadow: 0 0 0 3px rgba(46, 141, 120, 0.1);
}

.checkbox-wrapper,
.radio-wrapper {
  display: flex;
  flex-direction: column;
  gap: 8px;
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
  color: #2f5f78;
}

.help-text {
  margin: 0;
  font-size: 0.85rem;
  color: #7a8c92;
  font-style: italic;
}

.form-actions {
  margin-top: 24px;
  display: flex;
  gap: 12px;
}

.form-actions button {
  flex: 1;
  background: linear-gradient(135deg, #2f5f78, #2e8d78);
  color: #e8fbff;
  border: none;
  padding: 12px 16px;
  border-radius: 8px;
  font-weight: 700;
  font-size: 1rem;
  cursor: pointer;
  transition: all 0.2s ease;
}

.form-actions button:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(46, 141, 120, 0.3);
}

.form-actions button:disabled {
  background: #d9e3e5;
  color: #7a8c92;
  cursor: not-allowed;
}

.loading,
.error,
.success {
  text-align: center;
  padding: 40px 20px;
  background: #fff;
  border: 1px solid #b4c6cd;
  border-radius: 16px;
}

.error {
  color: #b94b59;
  background: #fef5f6;
  border-color: #f0c1c8;
}

.success {
  background: #f0f9f7;
  border-color: #c9e8e3;
}

.success h2 {
  margin: 0 0 8px;
  color: #2e8d78;
  font-size: 1.6rem;
}

.success p {
  margin: 0;
  color: #7a8c92;
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
