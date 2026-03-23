<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'

import AuthLayout from './AuthLayout.vue'
import { useAuthStore } from '../stores/authStore'

const router = useRouter()
const authStore = useAuthStore()

const email = ref('')
const password = ref('')
const confirmPassword = ref('')
const localError = ref('')

const submit = async () => {
  localError.value = ''

  if (password.value !== confirmPassword.value) {
    localError.value = 'Пароли не совпадают'
    return
  }

  try {
    await authStore.register(email.value, password.value)
    router.push({ name: 'dashboard' })
  } catch {
    localError.value = authStore.error || 'Ошибка регистрации'
  }
}
</script>

<template>
  <AuthLayout>
    <h2>Регистрация</h2>
    <p class="sub">Создать личный аккаунт для работы с таблицами и отчетами</p>

    <form class="form" @submit.prevent="submit">
      <label>
        Email
        <input v-model="email" type="email" required autocomplete="email" />
      </label>

      <label>
        Пароль
        <input v-model="password" type="password" required minlength="8" autocomplete="new-password" />
      </label>

      <label>
        Повторите пароль
        <input v-model="confirmPassword" type="password" required minlength="8" autocomplete="new-password" />
      </label>

      <button type="submit" :disabled="authStore.loading">
        {{ authStore.loading ? 'Создаем...' : 'Создать аккаунт' }}
      </button>
    </form>

    <p v-if="localError" class="error">{{ localError }}</p>
    <p class="switch">Уже есть аккаунт? <router-link to="/login">Войти</router-link></p>
  </AuthLayout>
</template>

<style scoped>
h2 {
  margin: 0;
}

.sub {
  color: var(--text-muted);
  margin-top: 4px;
}

.form {
  margin-top: 18px;
  display: grid;
  gap: 12px;
}

label {
  display: grid;
  gap: 6px;
  font-size: 0.95rem;
}

input {
  border: 1px solid var(--line);
  background: #edf4f5;
  padding: 10px 12px;
  border-radius: 10px;
}

button {
  border: none;
  background: var(--ok);
  color: #fff;
  font-weight: 700;
  padding: 11px 14px;
  border-radius: 10px;
  margin-top: 4px;
}

.error {
  margin-top: 12px;
  color: var(--danger);
}

.switch {
  margin-top: 12px;
  color: var(--text-muted);
}

.switch a {
  color: var(--accent);
}
</style>
