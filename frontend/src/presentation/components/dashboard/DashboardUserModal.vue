<script setup lang="ts">
import { ref } from 'vue'

const props = defineProps<{
  email: string
  userId: number | null
  loading: boolean
  error: string
}>()

const emit = defineEmits<{
  (event: 'close'): void
  (event: 'change-password', payload: { currentPassword: string; newPassword: string }): void
}>()

const currentPassword = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const localError = ref('')
const success = ref('')

const submit = () => {
  localError.value = ''
  success.value = ''

  if (newPassword.value.length < 8) {
    localError.value = 'Новый пароль должен быть не менее 8 символов.'
    return
  }

  if (newPassword.value !== confirmPassword.value) {
    localError.value = 'Новый пароль и подтверждение не совпадают.'
    return
  }

  emit('change-password', {
    currentPassword: currentPassword.value,
    newPassword: newPassword.value
  })
  success.value = 'Запрос отправлен.'
  currentPassword.value = ''
  newPassword.value = ''
  confirmPassword.value = ''
}

const onOverlay = (event: MouseEvent) => {
  if (event.target === event.currentTarget) {
    emit('close')
  }
}
</script>

<template>
  <div class="overlay" @click="onOverlay">
    <article class="modal">
      <header class="head">
        <h3>Профиль пользователя</h3>
        <button class="close" @click="emit('close')">×</button>
      </header>

      <section class="user-info">
        <p><strong>ID:</strong> {{ userId ?? '—' }}</p>
        <p><strong>Email:</strong> {{ email }}</p>
      </section>

      <section class="password-section">
        <h4>Сменить пароль</h4>
        <label>
          Текущий пароль
          <input v-model="currentPassword" type="password" minlength="8" autocomplete="current-password" />
        </label>
        <label>
          Новый пароль
          <input v-model="newPassword" type="password" minlength="8" autocomplete="new-password" />
        </label>
        <label>
          Повторите новый пароль
          <input v-model="confirmPassword" type="password" minlength="8" autocomplete="new-password" />
        </label>

        <p v-if="localError" class="error">{{ localError }}</p>
        <p v-if="error" class="error">{{ error }}</p>
        <p v-if="success && !error" class="success">{{ success }}</p>

        <button class="submit" :disabled="loading" @click="submit">
          {{ loading ? 'Сохраняем...' : 'Обновить пароль' }}
        </button>
      </section>
    </article>
  </div>
</template>

<style scoped>
.overlay {
  position: fixed;
  inset: 0;
  background: rgba(9, 14, 24, 0.44);
  backdrop-filter: blur(3px);
  display: grid;
  place-items: center;
  z-index: 140;
}

.modal {
  width: min(460px, 92vw);
  border-radius: 16px;
  border: 1px solid #2e3d56;
  background: #10192a;
  color: #dbe7f8;
  box-shadow: 0 20px 44px rgba(0, 0, 0, 0.42);
  padding: 16px;
  display: grid;
  gap: 14px;
}

.head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.head h3 {
  margin: 0;
}

.close {
  border: none;
  background: transparent;
  color: #9fb2cf;
  font-size: 24px;
  line-height: 1;
  cursor: pointer;
}

.user-info {
  border: 1px solid #2e3d56;
  border-radius: 10px;
  background: #152238;
  padding: 10px;
}

.user-info p {
  margin: 0;
}

.user-info p + p {
  margin-top: 6px;
}

.password-section {
  display: grid;
  gap: 10px;
}

.password-section h4 {
  margin: 0;
}

label {
  display: grid;
  gap: 6px;
  font-size: 0.9rem;
}

input {
  border: 1px solid #2f4767;
  background: #0c1526;
  color: #dbe7f8;
  border-radius: 10px;
  padding: 10px;
}

.error {
  margin: 0;
  color: #ff95a6;
}

.success {
  margin: 0;
  color: #77d7a2;
}

.submit {
  border: none;
  border-radius: 10px;
  background: linear-gradient(140deg, #3d83ff, #5f99ff);
  color: #f4f8ff;
  padding: 10px 14px;
  font-weight: 700;
  cursor: pointer;
}

.submit:disabled {
  opacity: 0.6;
  cursor: default;
}
</style>
