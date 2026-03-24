<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

interface MultiSelectOption {
  id: number
  name: string
}

const props = withDefaults(
  defineProps<{
    modelValue: number[]
    options: MultiSelectOption[]
    placeholder?: string
  }>(),
  {
    placeholder: 'Выберите значения'
  }
)

const emit = defineEmits<{
  (event: 'update:modelValue', value: number[]): void
  (event: 'change', value: number[]): void
}>()

const rootRef = ref<HTMLElement | null>(null)
const open = ref(false)

const selectedSet = computed(() => new Set(props.modelValue))
const selectedOptions = computed(() => props.options.filter((option) => selectedSet.value.has(option.id)))

const toggleOpen = () => {
  open.value = !open.value
}

const applyValue = (next: number[]) => {
  emit('update:modelValue', next)
  emit('change', next)
}

const toggleOption = (optionId: number) => {
  if (selectedSet.value.has(optionId)) {
    applyValue(props.modelValue.filter((id) => id !== optionId))
    return
  }
  applyValue([...props.modelValue, optionId])
}

const clearAll = () => {
  if (props.modelValue.length === 0) return
  applyValue([])
}

const onDocumentClick = (event: MouseEvent) => {
  if (!open.value) return
  const target = event.target as Node | null
  if (!target) return
  if (!rootRef.value?.contains(target)) {
    open.value = false
  }
}

onMounted(() => {
  document.addEventListener('click', onDocumentClick)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', onDocumentClick)
})
</script>

<template>
  <div ref="rootRef" class="ui-multiselect">
    <button type="button" class="ui-multiselect-trigger" :class="{ open }" @click="toggleOpen">
      <span v-if="selectedOptions.length === 0" class="ui-multiselect-placeholder">{{ placeholder }}</span>
      <span v-else class="ui-multiselect-value">Выбрано: {{ selectedOptions.length }}</span>
      <span class="ui-multiselect-arrow">▾</span>
    </button>

    <div v-if="selectedOptions.length > 0" class="ui-multiselect-tags">
      <span
        v-for="option in selectedOptions"
        :key="`tag-${option.id}`"
        class="ui-multiselect-tag"
        :title="option.name"
      >
        {{ option.name }}
      </span>
      <button type="button" class="ui-multiselect-clear" @click="clearAll">Очистить</button>
    </div>

    <div v-if="open" class="ui-multiselect-dropdown">
      <label
        v-for="option in options"
        :key="`option-${option.id}`"
        class="ui-multiselect-option"
      >
        <input
          type="checkbox"
          :checked="selectedSet.has(option.id)"
          @change="toggleOption(option.id)"
        />
        <span :title="option.name">{{ option.name }}</span>
      </label>
      <p v-if="options.length === 0" class="ui-multiselect-empty">Нет доступных вариантов</p>
    </div>
  </div>
</template>

<style scoped>
.ui-multiselect {
  display: grid;
  gap: 8px;
  position: relative;
}

.ui-multiselect-trigger {
  width: 100%;
  border: 1px solid rgba(64, 90, 97, 0.16);
  border-radius: 12px;
  background: #fff;
  padding: 10px 12px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  font: inherit;
  color: #20373d;
}

.ui-multiselect-trigger.open {
  border-color: #156f69;
}

.ui-multiselect-placeholder {
  color: #6c8189;
}

.ui-multiselect-value {
  color: #20373d;
}

.ui-multiselect-arrow {
  color: #5f757d;
}

.ui-multiselect-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.ui-multiselect-tag {
  display: inline-block;
  max-width: 240px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  background: #ecf4f6;
  color: #355f6b;
  border: 1px solid #9fb8bf;
  border-radius: 999px;
  padding: 2px 8px;
  font-size: 0.76rem;
}

.ui-multiselect-clear {
  border: none;
  background: transparent;
  color: #156f69;
  font-size: 0.8rem;
  cursor: pointer;
}

.ui-multiselect-dropdown {
  position: absolute;
  top: calc(100% + 6px);
  left: 0;
  right: 0;
  z-index: 40;
  border: 1px solid rgba(64, 90, 97, 0.16);
  border-radius: 12px;
  background: #fff;
  box-shadow: 0 12px 26px rgba(31, 61, 67, 0.14);
  max-height: 240px;
  overflow-y: auto;
  padding: 8px;
  display: grid;
  gap: 4px;
}

.ui-multiselect-option {
  display: grid;
  grid-template-columns: auto 1fr;
  align-items: center;
  gap: 8px;
  padding: 6px;
  border-radius: 8px;
}

.ui-multiselect-option span {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ui-multiselect-option:hover {
  background: #f4faf9;
}

.ui-multiselect-empty {
  margin: 0;
  color: #6c8189;
  font-size: 0.85rem;
  padding: 6px;
}
</style>
