<script setup lang="ts">
type StatusVariant = 'muted' | 'error' | 'success'

withDefaults(
  defineProps<{
    variant?: StatusVariant
    as?: 'p' | 'div' | 'span'
  }>(),
  {
    variant: 'muted',
    as: 'p'
  }
)
</script>

<template>
  <component :is="as" class="ui-status-text" :class="`is-${variant}`">
    <slot />
  </component>
</template>

<style scoped>
.ui-status-text {
  margin: 0;
}

.ui-status-text.is-muted {
  color: var(--text-muted);
}

.ui-status-text.is-error {
  color: var(--danger);
}

.ui-status-text.is-success {
  color: #276f45;
  font-weight: 600;
}
</style>
