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
  border: 1.5px solid #d3dee2;
  border-radius: 14px;
  padding: 14px;
  background: #ffffff;
  display: grid;
  gap: 10px;
  transition: transform 0.16s ease, background-color 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
}

.dashboard-tile-card:hover {
  background: #f8fcfd;
  border-color: #8eacb1;
  transform: translateY(-1px);
}

.dashboard-tile-card.active {
  background: #f5fafb;
  border-color: #8eacb1;
  box-shadow: 0 4px 16px rgba(142, 172, 177, 0.2);
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
