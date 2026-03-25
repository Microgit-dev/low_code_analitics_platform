<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'

import AuthLayout from './AuthLayout.vue'
import { useAuthStore } from '../stores/authStore'

const router = useRouter()
const authStore = useAuthStore()

const email = ref('')
const password = ref('')
const localError = ref('')

const submit = async () => {
  localError.value = ''
  try {
    await authStore.login(email.value, password.value)
    router.push({ name: 'dashboard' })
  } catch {
    localError.value = authStore.error || 'Ошибка входа'
  }
}
</script>

<template>
  <AuthLayout>
    <h2>Вход</h2>
    <p class="sub">Продолжить работу с вашими workspace</p>

    <form class="form" @submit.prevent="submit">
      <label>
        Email
        <input v-model="email" type="email" required autocomplete="email" />
      </label>

      <label>
        Пароль
        <input v-model="password" type="password" required minlength="8" autocomplete="current-password" />
      </label>

      <button type="submit" :disabled="authStore.loading">
        {{ authStore.loading ? 'Входим...' : 'Войти' }}
      </button>
    </form>

    <p v-if="localError" class="error">{{ localError }}</p>
    <p class="switch">Нет аккаунта? <router-link to="/register">Создать</router-link></p>
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
  background: #f8faff;
  padding: 10px 12px;
  border-radius: 12px;
}

button {
  border: none;
  background: linear-gradient(140deg, #1e63d8, #2b7df4);
  color: var(--text-main);
  font-weight: 700;
  padding: 11px 14px;
  border-radius: 12px;
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
