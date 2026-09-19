<template>
  <form
    role="search"
    class="group relative flex h-11 items-center gap-2.5 rounded-[12px] border bg-surface pr-1.5 pl-3.5 transition-colors focus-within:border-accent"
    :class="kind.type === 'link' ? 'border-accent/60' : 'border-line-2'"
    @submit.prevent="submit"
  >
    <AppIcon
      :name="kind.type === 'link' ? 'link' : 'search'"
      :size="18"
      :class="kind.type === 'link' ? 'text-accent' : 'text-faint'"
    />
    <label for="global-search" class="sr-only">{{
      t('search.placeholder')
    }}</label>
    <input
      id="global-search"
      ref="input"
      v-model="text"
      type="search"
      enterkeyhint="search"
      autocomplete="off"
      :placeholder="t('search.placeholder')"
      class="h-full min-w-0 flex-1 bg-transparent text-sm text-fg outline-none placeholder:text-faint [&::-webkit-search-cancel-button]:hidden"
    />
    <button
      v-if="text"
      type="button"
      class="flex size-8 items-center justify-center rounded-control text-faint hover:text-fg"
      :aria-label="t('common.clear')"
      @click="clear"
    >
      <AppIcon name="x" :size="16" />
    </button>
    <span
      v-if="!text"
      class="hidden rounded-md border border-line-3 px-1.5 py-0.5 text-[11px] text-faint lg:inline"
      >{{ isMac ? '⌘K' : 'Ctrl K' }}</span
    >
    <button
      v-else-if="kind.type === 'link'"
      type="submit"
      class="flex h-8 items-center gap-1.5 rounded-[8px] bg-accent px-3 text-[13px] font-semibold text-on-accent"
    >
      <AppIcon name="arrow-up-right" :size="14" stroke-width="2.2" />
      {{ t('search.open') }}
    </button>
  </form>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppIcon from '../ui/AppIcon.vue'
import { classifyInput } from '/src/lib/input'
import { useUi } from '/src/model/ui'
import { useI18n } from '/src/i18n'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const ui = useUi()
const input = ref(null)
const text = ref('')
const isMac =
  typeof navigator !== 'undefined' && /Mac|iPhone|iPad/.test(navigator.platform)

const kind = computed(() => classifyInput(text.value))

ui.registerSearchFocus(() => {
  input.value?.focus()
  input.value?.select()
})

// Mirror the page being shown, so the box reads what was searched/pasted.
watch(
  () => [route.name, route.params.query, route.query.url],
  ([name, query, url]) => {
    if (name === 'Search') text.value = String(query || '')
    else if (name === 'Link') text.value = String(url || '')
  },
  { immediate: true }
)

function submit() {
  const result = kind.value
  if (result.type === 'search') {
    router.push({ name: 'Search', params: { query: result.query } })
  } else if (result.type === 'link') {
    router.push({ name: 'Link', query: { url: result.url } })
  } else if (result.type === 'unsupported') {
    ui.toast(
      result.kind === 'artist' && result.source === 'spotify'
        ? t('search.spotifyArtistUnsupported')
        : t('search.unsupportedLink'),
      { kind: 'error' }
    )
    return
  } else {
    return
  }
  input.value?.blur()
}

function clear() {
  text.value = ''
  input.value?.focus()
}
</script>
