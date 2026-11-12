<template>
  <article class="tile group relative flex min-w-0 flex-col gap-2.5">
    <RouterLink :to="linkTo" class="block" :aria-label="item.name">
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
    <!-- Outside the link, so opening the menu doesn't also open the card. -->
    <div v-if="menu.length" class="absolute top-2 right-2">
      <UiMenu :items="menu" :label="t('common.more')">
        <template #trigger>
          <button
            type="button"
            class="flex size-9 items-center justify-center rounded-full bg-black/55 text-white backdrop-blur transition-colors hover:bg-black/75"
            :aria-label="t('common.more')"
          >
            <AppIcon name="more" :size="18" />
          </button>
        </template>
      </UiMenu>
    </div>
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
      :to="linkTo"
      class="flex min-w-0 flex-col gap-0.5"
      :class="round ? 'items-center text-center' : ''"
    >
      <span class="w-full truncate text-sm font-semibold">{{ item.name }}</span>
      <span class="w-full truncate text-[13px] text-muted">{{ subtitle }}</span>
    </RouterLink>
  </article>
</template>

<script setup>
// A Deezer chart card (album, artist or playlist), styled and wired like
// search's ReleaseCard: a cover that opens the item's /link page, and -
// for kinds /link can turn into a flat downloadable tracklist (album,
// playlist) - a green download button over it, same as ReleaseCard's. An
// artist resolves to release summaries, not songs (like ReleaseCard's own
// round/artist tiles), so it only navigates. Chart tracks are the only
// immediately-downloadable kind and use TrackDownPlay instead, not this
// card. A Deezer playlist also gets a menu with what its /link page
// offers besides downloading: watching it, and saving the songs of it
// already in the library as one of the user's playlists.
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { localCatalogRoute } from '/src/lib/library'
import { playableQueue } from '/src/lib/topSongs'
import AppIcon from '../ui/AppIcon.vue'
import CoverArt from '../ui/CoverArt.vue'
import UiMenu from '../ui/UiMenu.vue'
import API from '/src/model/api'
import monitorAPI from '/src/model/monitor'
import { useDownloadManager } from '/src/model/download'
import { useLibrary } from '/src/model/library'
import { usePlaylistActions } from '/src/model/playlistActions'
import { useUi } from '/src/model/ui'
import { useI18n } from '/src/i18n'

const props = defineProps({
  item: { type: Object, required: true },
  kind: {
    type: String,
    required: true,
    validator: (value) => ['album', 'artist', 'playlist'].includes(value),
  },
  rank: { type: Number, default: null },
})
const { t } = useI18n()
const router = useRouter()
const dm = useDownloadManager()
const library = useLibrary()
const playlistActions = usePlaylistActions()
const ui = useUi()
const queued = ref(props.item.source === 'library')
const watching = ref(false)
const watched = ref(false)
const saving = ref(false)

const round = computed(() => props.kind === 'artist')
// An artist resolves to release summaries, not songs - nothing fromURL
// could queue directly, so no download button for it (same reasoning as
// ReleaseCard's own round tiles).
const downloadable = computed(
  () => props.kind === 'album' || props.kind === 'playlist'
)
const linkTo = computed(
  () =>
    localCatalogRoute(props.item, props.kind) || {
      name: 'Link',
      query: { url: props.item.url },
    }
)

const icon = computed(
  () => ({ album: 'disc', artist: 'user', playlist: 'playlist' })[props.kind]
)

const subtitle = computed(() => {
  switch (props.kind) {
    case 'artist':
      return t('search.artist')
    case 'album':
      return props.item.artist || ''
    case 'playlist':
      return props.item.owner || t('charts.playlist')
    default:
      return ''
  }
})

// Library-only mode lists the library's own playlists here: nothing to
// watch or save there.
const menu = computed(() =>
  props.kind === 'playlist' && props.item.source !== 'library'
    ? [
        {
          label: t('link.watchPlaylist'),
          icon: 'radar',
          disabled: watching.value || watched.value,
          action: watchPlaylist,
        },
        {
          label: t('link.addPlaylist'),
          icon: 'playlist',
          disabled: saving.value,
          action: savePlaylist,
        },
      ]
    : []
)

function failed(err) {
  ui.toast(err?.response?.data?.detail || t('toast.actionFailed'), {
    kind: 'error',
  })
}

async function download() {
  queued.value = true
  try {
    const count = await dm.fromURL(props.item.url)
    ui.toast(t('toast.queuedTracks', { count, name: props.item.name }), {
      kind: 'success',
    })
  } catch (err) {
    queued.value = false
    failed(err)
  }
}

// Same interval as the /link page's own Watch for new tracks.
async function watchPlaylist() {
  if (watching.value || watched.value) return
  watching.value = true
  try {
    await monitorAPI.addMonitoredPlaylist(props.item.url, 360)
    watched.value = true
    ui.toast(t('toast.watching', { name: props.item.name }), {
      kind: 'success',
      action: {
        label: t('nav.monitor'),
        run: () =>
          router.push({ name: 'Monitor', params: { tab: 'playlists' } }),
      },
    })
  } catch (err) {
    failed(err)
  } finally {
    watching.value = false
  }
}

// As the /link page's Add to my playlists: the songs already in the
// library, nothing downloaded.
async function savePlaylist() {
  if (saving.value) return
  saving.value = true
  try {
    const { data } = await API.resolveUrl(props.item.url)
    const tracks = data?.tracks || []
    await library.lookupSongs(tracks)
    const files = playableQueue(tracks, library.findTrack)
    if (!files.length) {
      ui.toast(t('link.noAvailableTracks'), { kind: 'error' })
      return
    }
    playlistActions.openCreate(files, {
      name: data?.name || props.item.name,
      sourcePlaylistUrl: props.item.url,
      description: t('link.saveAvailableHint', {
        count: files.length,
        total: tracks.length,
      }),
    })
  } catch (err) {
    failed(err)
  } finally {
    saving.value = false
  }
}
</script>
