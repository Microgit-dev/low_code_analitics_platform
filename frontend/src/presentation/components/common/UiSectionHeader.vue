<script setup lang="ts">
defineProps<{
  title: string
  description?: string
  headingTag?: 'h2' | 'h3' | 'h4'
}>()
</script>

<template>
  <div class="ui-section-header">
    <div class="ui-section-headline">
      <component :is="headingTag || 'h3'">{{ title }}</component>
      <p v-if="description" class="ui-section-description">{{ description }}</p>
    </div>
    <div v-if="$slots.actions" class="ui-section-actions">
      <slot name="actions" />
    </div>
  </div>
</template>

<style scoped>
.ui-section-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}

.ui-section-headline {
  min-width: 0;
}

.ui-section-description {
  margin: 6px 0 0;
  color: var(--text-muted);
}

.ui-section-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

@media (max-width: 1100px) {
  .ui-section-header {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
