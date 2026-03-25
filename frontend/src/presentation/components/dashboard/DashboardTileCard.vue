<script setup lang="ts">
defineProps<{
  active?: boolean
}>()
</script>

<template>
  <article class="dashboard-tile-card" :class="{ active }">
    <header class="dashboard-tile-card-header">
      <div class="dashboard-tile-card-title">
        <slot name="title" />
      </div>
      <div v-if="$slots.badge" class="dashboard-tile-card-badge">
        <slot name="badge" />
      </div>
    </header>

    <div class="dashboard-tile-card-body">
      <slot />
    </div>

    <slot v-if="$slots.actions" name="actions" />
  </article>
</template>

<style scoped>
.dashboard-tile-card {
  border: 1.5px solid var(--line);
  border-radius: 14px;
  padding: 14px;
  background: var(--bg-panel);
  display: flex;
  flex-direction: column;
  gap: 10px;
  transition: transform 0.16s ease, background-color 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
  align-self: start;
}

.dashboard-tile-card:hover {
  background: var(--bg-soft);
  border-color: var(--line-strong);
  transform: translateY(-1px);
}

.dashboard-tile-card.active {
  background: var(--bg-soft);
  border-color: var(--accent-soft);
  box-shadow: 0 4px 16px color-mix(in srgb, var(--accent) 20%, transparent);
}

.dashboard-tile-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.dashboard-tile-card-title :deep(h4) {
  margin: 0;
}

.dashboard-tile-card-badge {
  display: inline-flex;
}

.dashboard-tile-card-body {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.dashboard-tile-card-body :deep(p) {
  margin: 0;
}
</style>
