<template>
  <div
    class="group flex h-16 items-center gap-3 rounded-[12px] px-3 transition-colors hover:bg-surface"
  >
    <span
      v-if="index !== null"
      class="tabular w-6 text-center text-[13px] text-faint max-sm:hidden"
    >
      {{ index + 1 }}
    </span>
    <button
      type="button"
      class="relative shrink-0"
      :aria-label="previewLabel"
      :disabled="!canPreview"
      @click="togglePreview"
    >
      <CoverArt
        :src="song.cover_url"
        :name="song.name"
        rounded="rounded-[8px]"
        :letter-size="14"
        class="size-11"
      />
      <span
        v-if="canPreview"
        class="absolute inset-0 hidden items-center justify-center rounded-[8px] bg-black/45 text-white group-hover:flex"
        :class="previewActive ? '!flex' : ''"
      >
        <AppIcon
          :name="previewPlaying ? 'pause' : 'play'"
          :size="16"
          :class="previewLoading ? 'animate-pulse' : ''"
        />
      </span>
    </button>
    <div class="min-w-0 flex-1">
      <p class="truncate text-sm font-semibold">{{ song.name }}</p>
      <p class="truncate text-[13px] text-muted">{{ artistName }}</p>
    </div>
    <span
      v-if="song.match > 0"
      class="tabular hidden w-14 text-right text-[13px] text-muted sm:block"
      :title="t('similar.matchHint')"
    >
      {{ Math.round(song.match * 100) }}%
    </span>
    <a
      v-if="song.lastfm_url"
      :href="song.lastfm_url"
      target="_blank"
      rel="noopener"
      class="hidden size-8 items-center justify-center rounded-control text-faint hover:bg-surface-2 hover:text-fg sm:flex lg:opacity-0 lg:group-hover:opacity-100"
      :title="t('similar.openLastfm')"
      :aria-label="t('similar.openLastfm')"
    >
      <AppIcon name="arrow-up-right" :size="16" />
    </a>
    <div class="flex w-28 shrink-0 justify-end">
      <UiBadge v-if="inLibrary" tone="accent" icon="check">
        {{ t('search.inLibrary') }}
      </UiBadge>
      <DownloadState
        v-else-if="resolved || downloadable"
        :song="resolved || song"
      />
      <button
        v-else
        type="button"
        class="flex size-9 shrink-0 items-center justify-center rounded-full bg-surface-2 text-fg-3 transition-colors hover:bg-accent hover:text-on-accent disabled:opacity-50"
        :title="t('actions.download')"
        :aria-label="t('actions.downloadItem', { name: song.name })"
        :disabled="resolving"
        @click="resolveAndDownload"
      >
        <AppIcon
          :name="resolving ? 'refresh' : 'download'"
          :size="16"
          stroke-width="2"
          :class="resolving ? 'animate-spin' : ''"
        />
      </button>
    </div>
  </div>
</template>

<script setup>
// One similar track: a 30 s Deezer preview on the cover, and a download
// button. YouTube rows already carry their video id and download
// directly; Last.fm rows have no URL of their own, so the button first
// resolves the row through search. Either way the row hands off to
// DownloadState, so progress, queue and retry look exactly like search
// results.
import { computed, ref } from 'vue'
import AppIcon from '../ui/AppIcon.vue'
import CoverArt from '../ui/CoverArt.vue'
import UiBadge from '../ui/UiBadge.vue'
import DownloadState from '../search/DownloadState.vue'
import API from '/src/model/api'
import { useDownloadManager } from '/src/model/download'
import { useLibrary } from '/src/model/library'
import { usePreview } from '/src/model/preview'
import { useUi } from '/src/model/ui'
import { previewKey } from '/src/lib/preview'
import { useI18n } from '/src/i18n'

const props = defineProps({
  song: { type: Object, required: true },
  index: { type: Number, default: null },
})

const { t } = useI18n()
const preview = usePreview()
const library = useLibrary()
const dm = useDownloadManager()
const ui = useUi()

const resolving = ref(false)
const resolved = ref(null)

const artistName = computed(
  () =>
    (props.song.artists || []).join(', ') ||
    props.song.artist ||
    t('common.unknownArtist')
)

const songId = computed(() => previewKey(props.song))
const canPreview = computed(() => preview.canPreview(props.song))
const previewActive = computed(
  () => !!songId.value && preview.activeId.value === songId.value
)
const previewPlaying = computed(
  () => previewActive.value && preview.isPlaying.value
)
const previewLoading = computed(
  () => previewActive.value && preview.isLoading.value
)
const previewLabel = computed(() =>
  t(previewPlaying.value ? 'actions.pausePreview' : 'actions.playPreview', {
    name: props.song.name,
  })
)

const inLibrary = computed(() =>
  library.hasSong(artistName.value, props.song.name)
)

// A YouTube row already is a downloadable song (video id + link), so it
// skips the resolve step a Last.fm row needs.
const downloadable = computed(() => !!String(props.song.song_id || '').trim())

function togglePreview() {
  if (!canPreview.value) return
  Promise.resolve(preview.toggle(props.song)).then((ok) => {
    if (!ok) ui.toast(t('actions.noPreview', { name: props.song.name }))
  })
}

async function resolveAndDownload() {
  if (resolving.value || resolved.value) return
  resolving.value = true
  try {
    const res = await API.search(`${artistName.value} ${props.song.name}`)
    const first = res.data?.[0]
    if (!first) {
      ui.toast(t('similar.noDownloadMatch', { name: props.song.name }), {
        kind: 'error',
      })
      return
    }
    resolved.value = first
    dm.queue(first)
  } catch (err) {
    ui.toast(err?.response?.data?.detail || t('similar.resolveFailed'), {
      kind: 'error',
    })
  } finally {
    resolving.value = false
  }
}
</script>
