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
      :aria-label="play.playLabel.value"
      :disabled="!play.playable.value"
      @click.stop="play.toggle()"
    >
      <CoverArt
        :src="song.cover_url"
        :name="song.name"
        rounded="rounded-[8px]"
        :letter-size="14"
        class="size-11"
      />
      <span
        v-if="play.playable.value"
        class="absolute inset-0 hidden items-center justify-center rounded-[8px] bg-black/45 text-white group-hover:flex"
        :class="play.isCurrent.value ? '!flex' : ''"
      >
        <AppIcon
          v-if="play.loading.value"
          name="refresh"
          :size="16"
          class="animate-spin"
        />
        <AppIcon v-else :name="overlayIcon" :size="16" />
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
// One similar track: full playback on the cover (from the library, else
// streamed), and a download button straight from its video id. The row
// hands off to DownloadState, so progress, queue and retry look exactly
// like search results.
import { computed, ref } from 'vue'
import AppIcon from '../ui/AppIcon.vue'
import CoverArt from '../ui/CoverArt.vue'
import UiBadge from '../ui/UiBadge.vue'
import DownloadState from '../search/DownloadState.vue'
import API from '/src/model/api'
import { useDownloadManager } from '/src/model/download'
import { useLibrary } from '/src/model/library'
import { usePlayer } from '/src/model/player'
import { useSongPlay } from '/src/model/songPlay'
import { useUi } from '/src/model/ui'
import { useI18n } from '/src/i18n'

const props = defineProps({
  song: { type: Object, required: true },
  index: { type: Number, default: null },
  // The whole song list, for a mixed queue (downloaded rows from the
  // library, the rest streamed) the player works through to the end.
  songs: { type: Array, default: null },
})

const { t } = useI18n()
const player = usePlayer()
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

// Playing works like every other track row: a downloaded song plays in
// full through the built-in player (so the player shows this track),
// anything else plays its 30 s preview clip on the row itself. `props`
// goes in whole so a new song object for the row stays reactive;
// useSongPlay only reads song/queue/context.
const play = useSongPlay(props)
const overlayIcon = computed(() =>
  play.isCurrent.value && player.isPlaying.value ? 'pause' : 'play'
)

const inLibrary = computed(() =>
  library.hasSong(artistName.value, props.song.name)
)

// Every row already is a downloadable song (video id + link).
const downloadable = computed(() => !!String(props.song.song_id || '').trim())

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
