<template>
  <div class="flex min-w-0 flex-col gap-1.5">
    <label
      v-if="label"
      :for="inputId"
      class="text-[13px] font-semibold text-fg-3"
      >{{ label }}</label
    >
    <span
      class="flex h-11 items-center gap-2.5 rounded-control border bg-bg px-3 transition-colors focus-within:border-accent"
      :class="error ? 'border-danger' : 'border-line-3'"
    >
      <AppIcon v-if="icon" :name="icon" :size="17" class="text-faint" />
      <input
        :id="inputId"
        :type="inputType"
        :value="modelValue"
        :placeholder="placeholder"
        :inputmode="inputmode"
        :min="min"
        :max="max"
        :autocomplete="autocomplete"
        :spellcheck="false"
        :aria-invalid="error ? 'true' : undefined"
        :aria-describedby="error || hint ? noteId : undefined"
        class="h-full min-w-0 flex-1 bg-transparent text-sm text-fg outline-none placeholder:text-faint"
        :class="mono ? 'font-mono text-[13px]' : ''"
        @input="onInput"
        @change="$emit('change', $event.target.value)"
      />
      <span v-if="suffix" class="text-xs text-faint">{{ suffix }}</span>
      <button
        v-if="type === 'password'"
        type="button"
        class="text-xs font-semibold text-muted hover:text-fg"
        @click="reveal = !reveal"
      >
        {{ reveal ? t('common.hide') : t('common.show') }}
      </button>
    </span>
    <span v-if="error" :id="noteId" class="text-xs text-danger">{{
      error
    }}</span>
    <span v-else-if="hint" :id="noteId" class="text-xs text-muted">{{
      hint
    }}</span>
  </div>
</template>

<script setup>
import { computed, ref, useId } from 'vue'
import AppIcon from './AppIcon.vue'
import { useI18n } from '/src/i18n'

const props = defineProps({
  modelValue: { type: [String, Number], default: '' },
  label: { type: String, default: '' },
  hint: { type: String, default: '' },
  error: { type: String, default: '' },
  placeholder: { type: String, default: '' },
  type: { type: String, default: 'text' },
  icon: { type: String, default: '' },
  suffix: { type: String, default: '' },
  mono: { type: Boolean, default: false },
  min: { type: [String, Number], default: undefined },
  max: { type: [String, Number], default: undefined },
  inputmode: { type: String, default: undefined },
  autocomplete: { type: String, default: 'off' },
  modelModifiers: { type: Object, default: () => ({}) },
})
const emit = defineEmits(['update:modelValue', 'change'])
const { t } = useI18n()
const reveal = ref(false)
const inputId = `input-${useId()}`
const noteId = `${inputId}-note`

const inputType = computed(() =>
  props.type === 'password' && reveal.value ? 'text' : props.type
)

function onInput(event) {
  let raw = event.target.value
  if (props.modelModifiers.trim) raw = raw.trim()
  emit(
    'update:modelValue',
    props.type === 'number' && raw !== '' ? Number(raw) : raw
  )
}
</script>
