<template>
  <div class="min-w-0 flex-1">
    <UiInput
      :model-value="modelValue"
      :label="label"
      :hint="hint"
      :placeholder="placeholder"
      :error="error"
      :mono="mono"
      :list="listId"
      autocomplete="off"
      @update:model-value="onInput"
    />
    <datalist :id="listId">
      <option v-for="dir in dirs" :key="dir" :value="dir" />
    </datalist>
  </div>
</template>

<script setup>
import { onBeforeUnmount, ref, useId, watch } from 'vue'
import { useDebounceFn } from '@vueuse/core'
import UiInput from '/src/components/ui/UiInput.vue'
import API from '/src/model/api'

const props = defineProps({
  modelValue: { type: String, default: '' },
  label: { type: String, default: '' },
  hint: { type: String, default: '' },
  placeholder: { type: String, default: '' },
  error: { type: String, default: '' },
  mono: { type: Boolean, default: true },
})
const emit = defineEmits(['update:modelValue'])

const listId = `path-suggest-${useId()}`
const dirs = ref([])
let seq = 0

const fetchDirs = useDebounceFn(async (value) => {
  const token = ++seq
  try {
    const { data } = await API.suggestDirs(value)
    if (token !== seq) return
    dirs.value = Array.isArray(data.dirs) ? data.dirs : []
  } catch {
    if (token !== seq) return
    dirs.value = []
  }
}, 180)

function onInput(value) {
  emit('update:modelValue', value)
}

watch(
  () => props.modelValue,
  (value) => {
    fetchDirs(String(value || ''))
  },
  { immediate: true }
)

onBeforeUnmount(() => {
  seq += 1
})
</script>
