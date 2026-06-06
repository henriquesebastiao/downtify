<template>
  <div ref="rootRef" class="playlist-filter relative min-w-[12rem] max-w-xs">
    <button
      type="button"
      class="playlist-filter-trigger"
      :class="{
        'playlist-filter-trigger-open': open,
        'tooltip tooltip-bottom z-40': showTriggerTip,
      }"
      :data-tip="showTriggerTip ? displayLabel : undefined"
      :title="displayLabel"
      :aria-expanded="open"
      aria-haspopup="listbox"
      @click="open = !open"
    >
      <span class="truncate text-left flex-1">{{ displayLabel }}</span>
      <Icon
        icon="clarity:angle-line"
        class="h-4 w-4 shrink-0 transition-transform"
        :class="open ? '-rotate-90' : 'rotate-90'"
        aria-hidden="true"
      />
    </button>
    <ul
      v-if="open"
      class="playlist-filter-menu"
      role="listbox"
      :aria-label="allLabel"
    >
      <li role="presentation">
        <button
          type="button"
          role="option"
          class="playlist-filter-item"
          :class="{ 'playlist-filter-item-active': !modelValue }"
          :aria-selected="!modelValue"
          @click="choose('')"
        >
          {{ allLabel }}
        </button>
      </li>
      <li v-for="name in options" :key="name" role="presentation">
        <button
          type="button"
          role="option"
          class="playlist-filter-item"
          :class="{ 'playlist-filter-item-active': modelValue === name }"
          :title="name"
          :aria-selected="modelValue === name"
          @click="choose(name)"
        >
          <span class="block truncate">{{ name }}</span>
        </button>
      </li>
    </ul>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { Icon } from '@iconify/vue'

const props = defineProps({
  modelValue: { type: String, default: '' },
  options: { type: Array, default: () => [] },
  allLabel: { type: String, default: 'All playlists' },
})

const emit = defineEmits(['update:modelValue'])

const open = ref(false)
const rootRef = ref(null)

const displayLabel = computed(() => {
  const current = String(props.modelValue || '').trim()
  if (!current) return props.allLabel
  return current
})

const showTriggerTip = computed(() => {
  const label = displayLabel.value
  return Boolean(String(props.modelValue || '').trim() && label.length > 20)
})

function choose(value) {
  emit('update:modelValue', value)
  open.value = false
}

function onDocumentPointerDown(event) {
  const root = rootRef.value
  if (!root || !open.value) return
  if (event.target instanceof Node && root.contains(event.target)) return
  open.value = false
}

function onDocumentKeydown(event) {
  if (event.key === 'Escape') open.value = false
}

onMounted(() => {
  document.addEventListener('pointerdown', onDocumentPointerDown)
  document.addEventListener('keydown', onDocumentKeydown)
})

onUnmounted(() => {
  document.removeEventListener('pointerdown', onDocumentPointerDown)
  document.removeEventListener('keydown', onDocumentKeydown)
})
</script>
