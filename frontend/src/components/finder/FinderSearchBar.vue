<template>
  <form
    role="search"
    class="flex min-w-0 items-center gap-2"
    @submit.prevent="submit"
  >
    <span
      class="flex h-11 min-w-0 flex-1 items-center gap-2.5 rounded-[12px] border border-line-2 bg-surface pr-1.5 pl-3.5 transition-colors focus-within:border-accent"
    >
      <AppIcon name="deezer" :size="18" class="text-deezer" />
      <label for="finder-search" class="sr-only">{{
        t('finder.placeholder')
      }}</label>
      <input
        id="finder-search"
        ref="input"
        :value="modelValue"
        type="search"
        enterkeyhint="search"
        autocomplete="off"
        :placeholder="t('finder.placeholder')"
        class="h-full min-w-0 flex-1 bg-transparent text-sm text-fg outline-none placeholder:text-faint [&::-webkit-search-cancel-button]:hidden"
        @input="emit('update:modelValue', $event.target.value)"
      />
      <button
        v-if="modelValue"
        type="button"
        class="flex size-8 items-center justify-center rounded-control text-faint hover:text-fg"
        :aria-label="t('common.clear')"
        @click="clear"
      >
        <AppIcon name="x" :size="16" />
      </button>
    </span>
    <UiButton
      type="submit"
      variant="primary"
      icon="search"
      :disabled="!modelValue.trim()"
    >
      {{ t('search.searchButton') }}
    </UiButton>
  </form>
</template>

<script setup>
// The Finder's search box: Deezer only, with its own button. It only holds
// the text - `submit` (with the term) and `clear` say what the user did,
// and the page decides what that means.
import { ref } from 'vue'
import AppIcon from '../ui/AppIcon.vue'
import UiButton from '../ui/UiButton.vue'
import { useI18n } from '/src/i18n'

const props = defineProps({
  modelValue: { type: String, default: '' },
})
const emit = defineEmits(['update:modelValue', 'submit', 'clear'])

const { t } = useI18n()
const input = ref(null)

function submit() {
  const term = props.modelValue.trim()
  if (!term) return
  emit('submit', term)
  input.value?.blur()
}

function clear() {
  emit('update:modelValue', '')
  emit('clear')
  input.value?.focus()
}
</script>
