<script setup lang="ts">
import { computed, ref, watch } from 'vue'

const props = withDefaults(
  defineProps<{
    modelValue: string[]
    suggestions?: string[]
    placeholder?: string
    addButtonText?: string
  }>(),
  {
    suggestions: () => [],
    placeholder: 'Введите тег',
    addButtonText: 'Добавить'
  }
)

const emit = defineEmits<{
  (event: 'update:modelValue', value: string[]): void
}>()

const draft = ref('')

const normalizedSuggestions = computed(() =>
  props.suggestions
    .map((item: string) => item.trim())
    .filter((item: string) => item.length > 0)
)

const selectedSet = computed(() => new Set(props.modelValue.map((item: string) => item.trim().toLowerCase())))

const availableSuggestions = computed(() =>
  normalizedSuggestions.value.filter((item: string) => !selectedSet.value.has(item.toLowerCase()))
)

const normalizeTags = (tags: string[]): string[] => {
  const seen = new Set<string>()
  const result: string[] = []

  tags.forEach((tag) => {
    const normalized = tag.trim()
    if (!normalized) return
    const key = normalized.toLowerCase()
    if (seen.has(key)) return
    seen.add(key)
    result.push(normalized)
  })

  return result
}

const apply = (next: string[]) => {
  emit('update:modelValue', normalizeTags(next))
}

const addTag = (raw?: string) => {
  const value = (raw ?? draft.value).trim()
  if (!value) return
  apply([...props.modelValue, value])
  if (!raw) {
    draft.value = ''
  }
}

const removeTag = (index: number) => {
  if (index < 0 || index >= props.modelValue.length) return
  const next = props.modelValue.filter((_: string, currentIndex: number) => currentIndex !== index)
  apply(next)
}

const onKeydown = (event: KeyboardEvent) => {
  if (event.key === 'Enter' || event.key === ',') {
    event.preventDefault()
    addTag()
    return
  }

  if (event.key === 'Backspace' && draft.value.length === 0 && props.modelValue.length > 0) {
    event.preventDefault()
    removeTag(props.modelValue.length - 1)
  }
}

watch(
  () => props.modelValue,
  (value: string[]) => {
    const normalized = normalizeTags(value)
    if (normalized.length !== value.length || normalized.some((tag, index) => tag !== value[index])) {
      emit('update:modelValue', normalized)
    }
  },
  { immediate: true }
)
</script>

<template>
  <div class="ui-tag-list-input">
    <div class="ui-tag-list-selected" v-if="modelValue.length > 0">
      <span v-for="(tag, index) in modelValue" :key="`${tag}-${index}`" class="ui-tag-chip">
        <span>{{ tag }}</span>
        <button type="button" class="ui-tag-chip-remove" @click="removeTag(index)">×</button>
      </span>
    </div>

    <div class="ui-tag-list-editor">
      <input
        v-model="draft"
        :placeholder="placeholder"
        @keydown="onKeydown"
      />
      <button type="button" class="small" @click="addTag()">{{ addButtonText }}</button>
    </div>

    <div v-if="availableSuggestions.length > 0" class="ui-tag-list-suggestions">
      <button
        v-for="tag in availableSuggestions"
        :key="`suggestion-${tag}`"
        type="button"
        class="ui-tag-suggestion"
        @click="addTag(tag)"
      >
        {{ tag }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.ui-tag-list-input {
  display: grid;
  gap: 8px;
}

.ui-tag-list-selected {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.ui-tag-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border-radius: 999px;
  border: 1px solid color-mix(in srgb, var(--accent) 26%, var(--line));
  background: color-mix(in srgb, var(--accent) 10%, var(--bg-soft));
  padding: 2px 8px;
  font-size: 0.78rem;
  color: var(--text-main);
}

.ui-tag-chip-remove {
  border: none;
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  padding: 0;
  line-height: 1;
}

.ui-tag-list-editor {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 8px;
}

.ui-tag-list-suggestions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.ui-tag-suggestion {
  border: 1px solid var(--line);
  background: var(--bg-soft);
  color: var(--text-main);
  border-radius: 999px;
  padding: 4px 9px;
  font-size: 0.75rem;
}
</style>
