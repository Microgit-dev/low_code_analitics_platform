<script setup lang="ts">
defineEmits<{
  'open-modal': []
}>()
</script>

<template>
  <div class="welcome">
    <h1 class="welcome-title">Начнём работу?</h1>
    <p class="welcome-subtitle">Создайте рабочее пространство</p>
    <button class="welcome-btn" @click="$emit('open-modal')">
      Создать workspace
      <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
        <path d="M10 4V16M4 10H16" stroke="white" stroke-width="2.5" stroke-linecap="round"/>
      </svg>
    </button>
  </div>
</template>

<style scoped>
.welcome {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  animation: fade-in 0.3s ease;
}

@keyframes fade-in {
  from { opacity: 0; transform: translateY(12px); }
  to   { opacity: 1; transform: translateY(0); }
}

.welcome-title {
  font-size: 42px;
  font-weight: 600;
  color: #5a5d72;
  text-align: center;
}

.welcome-subtitle {
  font-size: 22px;
  font-weight: 500;
  color: #5a5d72;
  text-align: center;
}

.welcome-btn {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 8px;
  padding: 14px 36px;
  background: #2f8486;
  border: none;
  border-radius: 20px;
  font-family: 'Montserrat', sans-serif;
  font-size: 20px;
  font-weight: 500;
  color: #ffffff;
  cursor: pointer;
  transition: background 0.15s, transform 0.1s;
}

.welcome-btn:hover {
  filter: brightness(0.92);
}

.welcome-btn:active {
  transform: scale(0.98);
}
</style>
