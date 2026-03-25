<template>
  <router-view />
</template>

<script setup lang="ts">
import { useTheme } from './infrastructure/composables/useTheme'

// Инициализирует тему из localStorage или системного предпочтения
useTheme()
</script>
