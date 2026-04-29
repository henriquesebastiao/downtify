<template>
  <div class="relative w-full">
    <input
      type="text"
      :placeholder="placeHolder"
      :class="['input-modern', compact ? 'h-11 text-sm' : 'h-14 text-base']"
      v-model="sm.searchTerm.value"
      @keyup.enter="lookUp(sm.searchTerm.value)"
    />
    <button
      class="absolute right-1.5 top-1/2 -translate-y-1/2 inline-flex items-center justify-center rounded-full bg-primary text-primary-content shadow-glow-sm transition hover:scale-105 active:scale-95 disabled:opacity-60"
      :class="compact ? 'h-9 w-9' : 'h-11 w-11'"
      :disabled="dm.loading.value"
      @click="lookUp(sm.searchTerm.value)"
    >
      <span
        v-if="dm.loading.value"
        class="loading loading-spinner"
        :class="compact ? 'loading-xs' : 'loading-sm'"
      ></span>
      <Icon
        v-else-if="sm.isValidURL(sm.searchTerm.value)"
        icon="clarity:download-line"
        :class="compact ? 'h-4 w-4' : 'h-5 w-5'"
      />
      <svg
        v-else
        xmlns="http://www.w3.org/2000/svg"
        fill="none"
        viewBox="0 0 24 24"
        stroke-width="2"
        stroke="currentColor"
        :class="compact ? 'h-4 w-4' : 'h-5 w-5'"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z"
        />
      </svg>
    </button>
  </div>
</template>

<script setup>
import { ref, computed, onBeforeUnmount } from 'vue'
import { Icon } from '@iconify/vue'

import router from '../router'
import { useSearchManager } from '../model/search'
import { useDownloadManager } from '../model/download'
import { useI18n } from '../i18n'

defineProps({
  compact: { type: Boolean, default: false },
})

const sm = useSearchManager()
const dm = useDownloadManager()
const { t, locale } = useI18n()

const placeHolderRotation = [
  'https://open.spotify.com/track/4vfN00PlILRXy5dcXHQE9M',
  'drugs - EDEN',
  'Não Gosto Eu Amo - Henrique e Juliano',
  'Perfect - Ed Sheeran',
  'Lightning Crashes - Live',
]
const rotationIndex = ref(0)
const placeHolder = computed(() => {
  // depend on locale to refresh translated default placeholder
  const _ = locale.value
  if (rotationIndex.value === 0) return t('search.placeholder')
  return placeHolderRotation[rotationIndex.value - 1]
})

const polling = setInterval(() => {
  rotationIndex.value =
    (rotationIndex.value + 1) % (placeHolderRotation.length + 1)
}, 5000)
onBeforeUnmount(() => clearInterval(polling))

function lookUp(query) {
  if (!query || !query.trim()) return
  if (sm.isValidURL(query)) {
    dm.fromURL(query)
    router.push({ name: 'Download' })
  } else if (sm.isValidSearch(query)) {
    router.push({ name: 'Search', params: { query } })
  }
}
</script>
