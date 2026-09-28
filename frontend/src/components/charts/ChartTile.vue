<template>
  <article class="tile group relative flex min-w-0 flex-col gap-2.5">
    <RouterLink
      v-if="resolvable"
      :to="linkTo"
      class="block"
      :aria-label="item.name"
    >
      <CoverArt
        :src="item.cover_url"
        :name="item.name"
        :round="round"
        :icon="icon"
        shadow
        :letter-size="round ? 40 : 52"
        class="aspect-square w-full"
      >
        <span
          v-if="rank && !round"
          class="absolute top-2.5 left-2.5 rounded-full bg-black/55 px-2 py-0.5 text-[11px] font-semibold text-white backdrop-blur"
          >{{ rank }}</span
        >
      </CoverArt>
    </RouterLink>
    <a
      v-else
      :href="item.url"
      target="_blank"
      rel="noopener"
      class="block"
      :aria-label="item.name"
    >
      <CoverArt
        :src="item.cover_url"
        :name="item.name"
        :icon="icon"
        shadow
        :letter-size="52"
        class="aspect-square w-full"
      >
        <span
          class="absolute right-2.5 bottom-2.5 flex size-8 items-center justify-center rounded-full bg-black/55 text-white opacity-0 backdrop-blur transition-opacity group-hover:opacity-100"
        >
          <AppIcon name="arrow-up-right" :size="16" />
        </span>
      </CoverArt>
    </a>
    <button
      v-if="downloadable"
      type="button"
      class="tile-play absolute right-3 bottom-[4.25rem] flex size-11 items-center justify-center rounded-full shadow-float transition-transform hover:scale-105"
      :class="queued ? 'bg-surface text-accent' : 'bg-accent text-on-accent'"
      :aria-label="t('actions.downloadItem', { name: item.name })"
      :disabled="queued"
      @click="download"
    >
      <AppIcon
        :name="queued ? 'check' : 'download'"
        :size="18"
        stroke-width="2.2"
      />
    </button>
    <RouterLink
      v-if="resolvable"
      :to="linkTo"
      class="flex min-w-0 flex-col gap-0.5"
      :class="round ? 'items-center text-center' : ''"
    >
      <span class="w-full truncate text-sm font-semibold">{{ item.name }}</span>
      <span class="w-full truncate text-[13px] text-muted">{{ subtitle }}</span>
    </RouterLink>
    <a
      v-else
      :href="item.url"
      target="_blank"
      rel="noopener"
      class="flex min-w-0 flex-col gap-0.5"
    >
      <span class="w-full truncate text-sm font-semibold">{{ item.name }}</span>
      <span class="w-full truncate text-[13px] text-muted">{{ subtitle }}</span>
    </a>
  </article>
</template>

<script setup>
// A Deezer chart card (album, artist, playlist or podcast), styled and wired
// like search's ReleaseCard: a cover that opens the item's /link page,
// and - for kinds /link can turn into a flat downloadable tracklist
// (album, playlist) - a green download button over it, same as
// ReleaseCard's. An artist resolves to release summaries, not songs (like
// ReleaseCard's own round/artist tiles), so it only navigates. Podcasts
// aren't a Downtify input type at all, so their card still just opens on
// Deezer. Chart tracks are the only immediately-downloadable kind and use
// TrackDownPlay instead, not this card.
import { computed, ref } from 'vue'
import AppIcon from '../ui/AppIcon.vue'
import CoverArt from '../ui/CoverArt.vue'
import { useDownloadManager } from '/src/model/download'
import { useUi } from '/src/model/ui'
import { useI18n } from '/src/i18n'

const props = defineProps({
  item: { type: Object, required: true },
  kind: {
    type: String,
    required: true,
    validator: (value) =>
      ['album', 'artist', 'playlist', 'podcast'].includes(value),
  },
  rank: { type: Number, default: null },
})
const { t } = useI18n()
const dm = useDownloadManager()
const ui = useUi()
const queued = ref(false)

const round = computed(() => props.kind === 'artist')
const resolvable = computed(() => props.kind !== 'podcast')
// An artist resolves to release summaries, not songs - nothing fromURL
// could queue directly, so no download button for it (same reasoning as
// ReleaseCard's own round tiles).
const downloadable = computed(
  () => props.kind === 'album' || props.kind === 'playlist'
)
const linkTo = computed(() => ({
  name: 'Link',
  query: { url: props.item.url },
}))

const icon = computed(
  () =>
    ({ album: 'disc', artist: 'user', playlist: 'playlist', podcast: 'mic' })[
      props.kind
    ]
)

const subtitle = computed(() => {
  switch (props.kind) {
    case 'artist':
      return t('search.artist')
    case 'album':
      return props.item.artist || ''
    case 'playlist':
      return props.item.owner || t('charts.playlist')
    case 'podcast':
      return t('charts.podcast')
    default:
      return ''
  }
})

async function download() {
  queued.value = true
  try {
    const count = await dm.fromURL(props.item.url)
    ui.toast(t('toast.queuedTracks', { count, name: props.item.name }), {
      kind: 'success',
    })
  } catch (err) {
    queued.value = false
    ui.toast(err?.response?.data?.detail || t('toast.actionFailed'), {
      kind: 'error',
    })
  }
}
</script>
