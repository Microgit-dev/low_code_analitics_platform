<script setup lang="ts">
// Hot Bar sprite from Figma (node 23:632, asset 442052de)
// Icons are 52×52 at x:8 in a 68×1080 image, spaced 72px apart:
// Таблицы y:134 | Форма y:206 | Данные y:278 | Отчёты y:350
const HOT_BAR = 'https://www.figma.com/api/mcp/asset/442052de-1a91-402a-9573-3b42e20597f7'

defineProps<{
  activeItem: string
}>()

defineEmits<{
  'nav-click': [id: string]
}>()

const navItems = [
  { id: 'tables',  label: 'Таблицы', y: 134 },
  { id: 'forms',   label: 'Форма',   y: 206 },
  { id: 'data',    label: 'Данные',  y: 278 },
  { id: 'reports', label: 'Отчёты',  y: 350 },
]

function spriteStyle(y: number) {
  return {
    backgroundImage: `url(${HOT_BAR})`,
    backgroundSize: '68px 1080px',
    backgroundPosition: `-8px -${y}px`,
    backgroundRepeat: 'no-repeat',
    mixBlendMode: 'multiply' as const,
  }
}
</script>

<template>
  <aside class="sidebar">
    <nav class="sidebar-nav">
      <button
        v-for="item in navItems"
        :key="item.id"
        class="nav-item"
        :class="{ active: activeItem === item.id }"
        @click="$emit('nav-click', item.id)"
      >
        <span class="nav-icon" :style="spriteStyle(item.y)" />
        <span class="nav-label">{{ item.label }}</span>
      </button>
    </nav>

    <div class="sidebar-profile">
      <div class="profile-avatar">
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
          <circle cx="10" cy="7" r="4" fill="#8e93aa"/>
          <path d="M2 18c0-4 3.58-7 8-7s8 3 8 7" stroke="#8e93aa" stroke-width="1.5" stroke-linecap="round"/>
        </svg>
      </div>
    </div>
  </aside>
</template>

<style scoped>
.sidebar {
  width: 68px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  background: #ffffff;
  padding: 12px 0;
  position: relative;
  z-index: 100;
}

.sidebar-nav {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding-top: 72px;
}

.nav-item {
  position: relative;
  width: 52px;
  height: 52px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
  border: none;
  background: transparent;
  cursor: pointer;
  transition: background 0.15s;
  outline: none;
  overflow: visible;
}

.nav-item:hover {
  background: rgba(211, 222, 226, 0.5);
}

.nav-item.active {
  background: #d3dee2;
}

/* Figma sprite icon */
.nav-icon {
  display: block;
  width: 52px;
  height: 52px;
  flex-shrink: 0;
  border-radius: 12px;
  overflow: hidden;
}

/* Hover label (appears to the right of the icon) */
.nav-label {
  position: absolute;
  left: calc(100% + 10px);
  top: 50%;
  transform: translateY(-50%);
  background: #d3dee2;
  border-radius: 10px;
  padding: 6px 14px;
  font-family: 'Montserrat', sans-serif;
  font-size: 14px;
  font-weight: 500;
  color: #5a5d72;
  white-space: nowrap;
  pointer-events: none;
  opacity: 0;
  transition: opacity 0.15s;
  z-index: 200;
}

.nav-item:hover .nav-label {
  opacity: 1;
}

/* Profile */
.sidebar-profile {
  display: flex;
  justify-content: center;
  padding-bottom: 4px;
}

.profile-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: #d3dee2;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: background 0.15s;
}

.profile-avatar:hover {
  background: #c8d5da;
}
</style>
