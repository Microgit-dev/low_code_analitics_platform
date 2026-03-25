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
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 12px;
  background: var(--bg-panel);
  display: grid;
  gap: 8px;
  transition: background-color 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
}

.dashboard-tile-card:hover {
  background: var(--bg-soft);
  border-color: var(--accent-soft);
}

.dashboard-tile-card.active {
  background: var(--bg-soft);
  border-color: var(--accent);
  box-shadow: inset 0 0 0 1px var(--accent);
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
  display: grid;
  gap: 6px;
}

.dashboard-tile-card-body :deep(p) {
  margin: 0;
}
</style>
