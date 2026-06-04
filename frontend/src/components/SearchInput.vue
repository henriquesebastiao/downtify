<template>
  <div class="relative w-full">
    <input
      type="text"
      :placeholder="placeHolder"
      :class="[
        'input-modern',
        compact ? 'h-11 text-sm' : 'h-14 text-base',
        inputPadClass,
      ]"
      v-model="sm.searchTerm.value"
      @keyup.enter="submit()"
    />
    <div
      v-if="!compact"
      class="absolute right-1.5 top-1/2 -translate-y-1/2"
    >
      <button
        type="button"
        class="inline-flex h-11 w-11 items-center justify-center rounded-full bg-primary text-primary-content shadow-glow-sm transition hover:scale-105 active:scale-95 disabled:opacity-60"
        :disabled="dm.loading.value || !canSubmit"
        :title="t('search.submitSearch')"
        @click="submit()"
      >
        <span
          v-if="dm.loading.value"
          class="loading loading-spinner loading-sm"
        />
        <Icon v-else icon="clarity:search-line" class="h-5 w-5" />
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onBeforeUnmount } from 'vue'
import { Icon } from '@iconify/vue'

import router from '../router'
import {
  useSearchManager,
  PLAYLIST_ROUTE_QUERY,
  PLAYLIST_URL_KEY,
} from '../model/search'
import { useDownloadManager } from '../model/download'
import { useI18n } from '../i18n'

const props = defineProps({
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
  const _ = locale.value
  if (rotationIndex.value === 0) return t('search.placeholder')
  return placeHolderRotation[rotationIndex.value - 1]
})

const inputText = computed(() => String(sm.searchTerm.value || '').trim())

const showPlaylistAction = computed(() =>
  sm.isSpotifyPlaylistURL(inputText.value)
)

const showDownloadAction = computed(() =>
  sm.isSpotifyDirectDownloadURL(inputText.value)
)

const canSubmit = computed(() => {
  if (!inputText.value) return false
  return (
    sm.isValidSearch(inputText.value) ||
    showPlaylistAction.value ||
    showDownloadAction.value
  )
})

const inputPadClass = computed(() => (props.compact ? '' : 'pr-14'))

const polling = setInterval(() => {
  rotationIndex.value =
    (rotationIndex.value + 1) % (placeHolderRotation.length + 1)
}, 5000)
onBeforeUnmount(() => clearInterval(polling))

function browsePlaylist() {
  const text = inputText.value
  if (!text || !sm.isSpotifyPlaylistURL(text)) return
  try {
    sessionStorage.setItem(PLAYLIST_URL_KEY, text)
  } catch {
    // ignore
  }
  router.push({ name: 'Search', params: { query: PLAYLIST_ROUTE_QUERY } })
  sm.loadSpotifyPlaylist(text)
}

function downloadLink() {
  const text = inputText.value
  if (!text || !sm.isSpotifyDirectDownloadURL(text)) return
  dm.fromURL(text)
  router.push({ name: 'Download' })
}

function textSearch() {
  const text = inputText.value
  if (!text || !sm.isValidSearch(text)) return
  router.push({ name: 'Search', params: { query: text } })
}

function submit() {
  const text = inputText.value
  if (!text) return
  if (sm.isSpotifyPlaylistURL(text)) {
    browsePlaylist()
  } else if (sm.isSpotifyDirectDownloadURL(text)) {
    downloadLink()
  } else if (sm.isValidSearch(text)) {
    textSearch()
  }
}
</script>
