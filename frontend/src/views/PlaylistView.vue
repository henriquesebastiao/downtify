<template>
  <div>
    <DetailState
      :loaded="library.loaded.value"
      :found="!!playlist"
      icon="playlist"
      :missing="t('playlists.notFound')"
    >
      <CollectionHero
        :title="playlist.title"
        :kicker="t('playlists.kicker')"
        :covers="playlist.covers"
        :cover="playlist.cover"
        :name="playlist.title"
        :icon="playlist.liked ? 'heart' : 'playlist'"
        :symbol="playlist.liked"
      >
        <template #subtitle>
          <span
            v-if="batch"
            class="mr-1 inline-flex translate-y-0.5 items-center gap-1.5 font-semibold text-spotify"
          >
            <AppIcon name="spotify" :size="14" />Spotify
          </span>
          {{ facts }}
          <template v-if="sharingLine"> · {{ sharingLine }}</template>
        </template>
        <template #actions>
          <PlaylistStatus
            v-if="batch?.expected_count"
            :playlist="playlist"
            class="w-full max-w-sm basis-full"
          />
          <PlayButton
            :label="t('actions.playItem', { name: playlist.title })"
            :playing="isThisPlaying"
            :disabled="!playlist.tracks.length"
            @click="togglePlay"
          />
          <UiIconButton
            icon="shuffle"
            :label="t('actions.shuffle')"
            size="lg"
            round
            :disabled="!playlist.tracks.length"
            @click="playlistActions.play(playlist, { shuffled: true })"
          />
          <UiButton
            v-if="batch?.missing_count"
            variant="primary"
            icon="download"
            @click="playlistActions.downloadMissing(playlist)"
          >
            {{ t('playlists.downloadMissing', { count: batch.missing_count }) }}
          </UiButton>
          <UiButton
            v-if="playlist.manual && playlist.mine"
            variant="secondary"
            icon="plus"
            @click="playlistActions.openAddSongs(playlist)"
          >
            {{ t('playlists.addSongs') }}
          </UiButton>
          <UiButton
            v-if="!playlist.liked && playlist.mine"
            variant="ghost"
            icon="pencil"
            @click="playlistActions.openRename(playlist)"
          >
            {{ t('playlists.rename') }}
          </UiButton>
          <UiButton
            v-if="!playlist.mine && playlist.visibility === 'public'"
            :variant="playlist.followed ? 'secondary' : 'primary'"
            :icon="playlist.followed ? 'heart' : 'heart-outline'"
            @click="playlistActions.setFollowing(playlist, !playlist.followed)"
          >
            {{
              playlist.followed ? t('sharing.following') : t('sharing.follow')
            }}
          </UiButton>
          <UiButton
            v-if="!playlist.mine"
            variant="secondary"
            icon="copy"
            @click="playlistActions.copy(playlist)"
          >
            {{ t('sharing.saveCopy') }}
          </UiButton>
          <UiButton
            v-if="canShare"
            variant="ghost"
            :icon="
              playlist.visibility === 'public'
                ? 'globe'
                : playlist.visibility === 'shared'
                  ? 'users'
                  : 'share'
            "
            @click="playlistActions.openShare(playlist)"
          >
            {{ t('sharing.share') }}
          </UiButton>
          <UiButton
            v-if="canDetach"
            variant="ghost"
            icon="link"
            @click="playlistActions.detach(playlist)"
          >
            {{ t('sharing.detach') }}
          </UiButton>
          <UiButton
            v-if="playlist.tracks.length"
            variant="ghost"
            icon="zip"
            class="max-sm:hidden"
            @click="actions.downloadZip(playlist.tracks)"
          >
            {{ t('library.downloadZip') }}
          </UiButton>
          <UiMenu :items="menu" :label="t('common.more')" size="lg" />
        </template>
      </CollectionHero>

      <div
        class="mx-auto flex max-w-[1680px] flex-col gap-10 px-4 sm:px-6 lg:px-10"
      >
        <div
          v-if="playlist.tracks.length || batch?.missing_count"
          class="flex flex-col gap-3"
        >
          <!-- Search and filters over the whole playlist: the list below
               only renders the rows on screen, so the browser's own find
               can't see the rest. -->
          <div class="flex flex-wrap items-center gap-2">
            <label
              class="flex h-10 min-w-0 flex-1 basis-56 items-center gap-2.5 rounded-control border border-line-2 bg-surface px-3 focus-within:border-accent sm:max-w-xs"
            >
              <AppIcon name="search" :size="16" class="text-faint" />
              <span class="sr-only">{{ t('playlistSearch.placeholder') }}</span>
              <input
                ref="searchInput"
                v-model="query"
                type="search"
                :placeholder="t('playlistSearch.placeholder')"
                class="h-full min-w-0 flex-1 bg-transparent text-sm outline-none placeholder:text-faint"
                @keydown.esc="query = ''"
              />
            </label>
            <UiChips
              v-if="views.length > 1"
              v-model="view"
              :items="views"
              class="max-w-full"
            />
            <TrackSortSelect
              v-if="!isSongView(view) && playlist.tracks.length"
              v-model="trackSort"
              playlist-order
              class="ml-auto"
            />
          </div>
          <p
            v-if="filtering"
            class="tabular text-[13px] text-muted"
            aria-live="polite"
          >
            {{ t('playlistSearch.showing', { count: shown, total }) }}
          </p>

          <template v-if="isSongView(view)">
            <p class="text-[13px] text-muted">
              {{ t('playlists.missingHint') }}
            </p>
            <ul v-if="loadingMissing" class="flex flex-col gap-2">
              <li
                v-for="n in 4"
                :key="n"
                class="h-14 animate-pulse rounded-[10px] bg-surface-2"
              />
            </ul>
            <ul v-else-if="shownSongs.length" class="-mx-2 flex flex-col">
              <li
                v-for="song in shownSongs"
                :key="song.song_id"
                class="flex h-14 items-center gap-3 rounded-[10px] px-2 hover:bg-surface-2"
              >
                <CoverArt
                  :src="song.cover_url"
                  :name="song.album_name || song.name"
                  rounded="rounded-[6px]"
                  :letter-size="12"
                  class="size-10"
                />
                <div class="min-w-0 flex-1">
                  <p class="truncate text-sm font-semibold">{{ song.name }}</p>
                  <p class="truncate text-[13px] text-muted">
                    {{ (song.artists || []).join(', ') || song.artist }}
                  </p>
                </div>
                <DownloadState :song="song" />
              </li>
            </ul>
            <UiEmpty
              v-else
              icon="search"
              :title="t('playlistSearch.noMatch')"
              :body="t('playlistSearch.noMatchHint')"
            />
          </template>
          <template v-else>
            <TrackList
              v-if="shownTracks.length"
              v-model:sort="trackSort"
              :tracks="shownTracks"
              :positions="filtering ? positions : null"
              :context="playlistActions.contextFor(playlist)"
            />
            <UiEmpty
              v-else
              icon="search"
              :title="t('playlistSearch.noMatch')"
              :body="t('playlistSearch.noMatchHint')"
            />
          </template>
        </div>
        <UiEmpty
          v-else
          icon="download"
          :title="t('playlists.nothingYet')"
          :body="
            playlist.manual
              ? t('playlists.nothingYetManualHint')
              : t('playlists.nothingYetHint')
          "
        />

        <UiPanel
          v-if="canHide && playlist.hiddenCount"
          :title="t('playlists.hiddenTitle', { count: playlist.hiddenCount })"
          :description="t('playlists.hiddenHint')"
        >
          <template #actions>
            <UiButton
              v-if="!hidden.length"
              variant="ghost"
              size="sm"
              :loading="loadingHidden"
              @click="loadHidden"
            >
              {{ t('playlists.showMissing') }}
            </UiButton>
          </template>
          <ul v-if="hidden.length" class="-mx-2 flex flex-col">
            <li
              v-for="song in hidden"
              :key="song.key"
              class="flex h-14 items-center gap-3 rounded-[10px] px-2 hover:bg-surface-2"
            >
              <CoverArt
                :src="song.present ? coverURL(song.file) : ''"
                :name="song.label"
                rounded="rounded-[6px]"
                :letter-size="12"
                class="size-10"
              />
              <div class="min-w-0 flex-1">
                <p class="truncate text-sm font-semibold">{{ song.label }}</p>
                <p v-if="!song.present" class="truncate text-[13px] text-muted">
                  {{ t('playlists.hiddenGone') }}
                </p>
              </div>
              <UiButton
                variant="ghost"
                size="sm"
                icon="eye"
                :loading="showing === song.key"
                @click="unhide(song)"
              >
                {{ t('playlists.unhide') }}
              </UiButton>
            </li>
          </ul>
        </UiPanel>
      </div>
    </DetailState>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useEventListener, useLocalStorage } from '@vueuse/core'
import { useRoute, useRouter } from 'vue-router'
import AppIcon from '/src/components/ui/AppIcon.vue'
import CoverArt from '/src/components/ui/CoverArt.vue'
import UiButton from '/src/components/ui/UiButton.vue'
import UiChips from '/src/components/ui/UiChips.vue'
import UiEmpty from '/src/components/ui/UiEmpty.vue'
import UiIconButton from '/src/components/ui/UiIconButton.vue'
import UiMenu from '/src/components/ui/UiMenu.vue'
import UiPanel from '/src/components/ui/UiPanel.vue'
import CollectionHero from '/src/components/library/CollectionHero.vue'
import DetailState from '/src/components/library/DetailState.vue'
import PlayButton from '/src/components/library/PlayButton.vue'
import PlaylistStatus from '/src/components/library/PlaylistStatus.vue'
import TrackList from '/src/components/library/TrackList.vue'
import TrackSortSelect from '/src/components/library/TrackSortSelect.vue'
import DownloadState from '/src/components/search/DownloadState.vue'
import API from '/src/model/api'
import { useAccount } from '/src/model/account'
import { useProgressTracker } from '/src/model/download'
import { useLibrary } from '/src/model/library'
import { usePlayer } from '/src/model/player'
import { usePlaylistActions } from '/src/model/playlistActions'
import { useTrackActions } from '/src/model/trackActions'
import { sortTracks } from '/src/lib/library'
import { songDownloadState } from '/src/lib/downloadState'
import {
  filterPlaylistSongs,
  filterPlaylistTracks,
  isSongView,
  providerCounts,
} from '/src/lib/playlistFilter'
import { coverURL } from '/src/lib/paths'
import { splitLength } from '/src/lib/format'
import { useI18n } from '/src/i18n'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const library = useLibrary()
const player = usePlayer()
const actions = useTrackActions()
const playlistActions = usePlaylistActions()
const account = useAccount()
const tracker = useProgressTracker()

const playlist = computed(() =>
  library.findPlaylist(String(route.query.name || ''))
)
const batch = computed(() => playlist.value?.batch || null)

// How the songs are ordered: the playlist's own order until picked
// otherwise (remembered for every playlist).
const trackSort = useLocalStorage('downtify-playlist-track-sort', {
  key: 'order',
  dir: 'asc',
})
const sortedTracks = computed(() =>
  sortTracks(playlist.value?.tracks || [], trackSort.value)
)

// The source playlist's songs that aren't in the library (Spotify
// playlists tracked as a download), fetched when first asked for.
const missing = ref([])
const missingLoaded = ref(false)
const loadingMissing = ref(false)

// ── Search and filters (over every song, not just the rendered rows) ──
const query = ref('')
const view = ref('all')
const searchInput = ref(null)
// {providers, navidrome} from the server (see downtify/file_providers.py).
const details = ref(null)
const providers = computed(() => details.value?.providers || {})
const unmatched = computed(() => details.value?.navidrome?.unmatched || [])

const PROVIDER_LABELS = {
  'youtube-music': 'settings.sourceYtm',
  youtube: 'settings.sourceYt',
  slskd: 'settings.sourceSlskd',
  deemix: 'settings.deemixTitle',
  folder: 'playlistSearch.fromFolders',
  '': 'playlistSearch.unknownSource',
}

function providerLabel(id) {
  return PROVIDER_LABELS[id] !== undefined ? t(PROVIDER_LABELS[id]) : id
}

// Missing songs whose download failed (the queue says so).
const failedSongs = computed(() => {
  tracker.queueVersion.value
  return missing.value.filter((song) => {
    const artist = (song.artists || [])[0] || song.artist
    return (
      songDownloadState(
        tracker.getBySong(song),
        library.hasSong(artist, song.name)
      ) === 'failed'
    )
  })
})

const views = computed(() => {
  const p = playlist.value
  if (!p) return []
  const items = [
    { id: 'all', label: t('playlistSearch.all'), count: p.tracks.length },
  ]
  if (batch.value?.missing_count) {
    items.push({
      id: 'missing',
      label: t('playlistSearch.missing'),
      count: missingLoaded.value
        ? missing.value.length
        : batch.value.missing_count,
    })
  }
  if (failedSongs.value.length) {
    items.push({
      id: 'failed',
      label: t('playlistSearch.failed'),
      count: failedSongs.value.length,
    })
  }
  for (const { id, count } of providerCounts(p.tracks, providers.value)) {
    items.push({ id: `provider:${id}`, label: providerLabel(id), count })
  }
  if (unmatched.value.length) {
    items.push({
      id: 'navidrome',
      label: t('playlistSearch.notInNavidrome'),
      count: unmatched.value.length,
    })
  }
  return items
})

const shownTracks = computed(() =>
  sortTracks(
    filterPlaylistTracks(playlist.value?.tracks || [], {
      query: query.value,
      view: view.value,
      providers: providers.value,
      unmatched: unmatched.value,
    }),
    trackSort.value
  )
)
const viewSongs = computed(() =>
  view.value === 'failed' ? failedSongs.value : missing.value
)
const shownSongs = computed(() =>
  filterPlaylistSongs(viewSongs.value, query.value)
)
const filtering = computed(
  () => Boolean(query.value.trim()) || view.value !== 'all'
)
// Where each song sits in the playlist, numbered while filtering so a
// song found by the search shows its real place.
const positions = computed(
  () => new Map((playlist.value?.tracks || []).map((t, i) => [t.file, i + 1]))
)
const shown = computed(() =>
  isSongView(view.value) ? shownSongs.value.length : shownTracks.value.length
)
const total = computed(() =>
  isSongView(view.value)
    ? viewSongs.value.length
    : playlist.value?.tracks.length || 0
)

// A filter whose chip went away (the last failed song was retried, the
// missing ones downloaded) falls back to every song.
watch(views, (items) => {
  if (!items.some((item) => item.id === view.value)) view.value = 'all'
})

watch(view, (next) => {
  if (isSongView(next) && !missingLoaded.value && !loadingMissing.value) {
    loadMissing()
  }
})

async function loadDetails(name) {
  try {
    const res = await API.getPlaylistDetails(name)
    if (String(route.query.name || '') === name) details.value = res.data
  } catch {
    // Only the provider and Navidrome filters need it.
  }
}

// Ctrl/⌘+F searches the playlist; pressed again in the box, it is the
// browser's own find.
useEventListener(window, 'keydown', (event) => {
  if (
    !(event.ctrlKey || event.metaKey) ||
    event.altKey ||
    event.shiftKey ||
    event.key.toLowerCase() !== 'f'
  ) {
    return
  }
  const input = searchInput.value
  if (!input || document.activeElement === input) return
  if (document.querySelector('[aria-modal="true"]')) return
  event.preventDefault()
  input.focus()
  input.select()
})

const canShare = computed(
  () =>
    playlist.value?.mine &&
    !playlist.value.liked &&
    account.playlistSharing.value
)
// An imported playlist can be turned into an editable one.
const canDetach = computed(
  () =>
    playlist.value?.mine &&
    !playlist.value.liked &&
    !playlist.value.manual &&
    playlist.value.fileCount > 0
)

// Songs are hidden from the user's own imported playlists (a Library one
// is edited instead).
const canHide = computed(
  () => playlist.value?.mine && !playlist.value.liked && !playlist.value.manual
)

// "by ana", or how the user's own playlist is shared.
const sharingLine = computed(() => {
  const p = playlist.value
  if (!p || p.liked) return ''
  if (!p.mine) return t('sharing.by', { owner: p.owner })
  if (p.visibility === 'public') return t('sharing.public')
  if (p.visibility === 'shared') {
    return t('sharing.sharedWithCount', { count: p.sharedWith.length })
  }
  return ''
})

const facts = computed(() => {
  const p = playlist.value
  const { hours, minutes } = splitLength(p.duration)
  return [
    t('common.tracks', { count: p.tracks.length || p.fileCount || 0 }),
    p.duration
      ? hours
        ? t('common.lengthHours', { hours, minutes })
        : t('common.lengthMinutes', { minutes })
      : '',
  ]
    .filter(Boolean)
    .join(' · ')
})

const isThisPlaying = computed(
  () =>
    player.isPlaying.value &&
    player.context.value?.type === 'playlist' &&
    player.context.value?.title === playlist.value?.title
)

function togglePlay() {
  if (isThisPlaying.value) player.pause()
  else playlistActions.play(playlist.value, { tracks: sortedTracks.value })
}

const menu = computed(() =>
  playlistActions.menuFor(playlist.value).map((item) =>
    item.icon === 'trash'
      ? {
          ...item,
          action: async () => {
            if (await playlistActions.remove(playlist.value)) {
              router.push({ name: 'Library', params: { tab: 'playlists' } })
            }
          },
        }
      : item
  )
)

async function loadMissing() {
  if (!batch.value) return
  loadingMissing.value = true
  try {
    const res = await API.getPlaylistBatchDetails(
      batch.value.spotify_playlist_id
    )
    missing.value = (res.data?.missing_tracks || []).map((song) => ({
      ...song,
      downtify_playlist_url: batch.value.playlist_url,
    }))
    missingLoaded.value = true
  } finally {
    loadingMissing.value = false
  }
}

const hidden = ref([])
const loadingHidden = ref(false)
const showing = ref('')

async function loadHidden() {
  if (!playlist.value) return
  loadingHidden.value = true
  try {
    const res = await API.getHiddenPlaylistSongs(playlist.value.name)
    hidden.value = res.data?.songs || []
  } finally {
    loadingHidden.value = false
  }
}

async function unhide(song) {
  showing.value = song.key
  try {
    if (await playlistActions.showHidden(playlist.value, [song.key])) {
      hidden.value = hidden.value.filter((item) => item.key !== song.key)
    }
  } finally {
    showing.value = ''
  }
}

// An open list follows songs hidden from the track menu meanwhile.
watch(
  () => playlist.value?.hiddenCount,
  (count) => {
    if (hidden.value.length && count !== hidden.value.length) loadHidden()
  }
)

watch(
  () => String(route.query.name || ''),
  async (name) => {
    missing.value = []
    missingLoaded.value = false
    hidden.value = []
    query.value = ''
    view.value = 'all'
    details.value = null
    loadDetails(name)
    await library.loadPlaylistTracks(name)
    // Opening a playlist shared with the user clears its "new" marker.
    playlistActions.markSeen(library.findPlaylist(name))
  },
  { immediate: true }
)

// New songs arrive with a provider (and maybe a Navidrome match) of their
// own: refresh what the filters know.
watch(
  () => playlist.value?.fileCount,
  (count, before) => {
    if (playlist.value && before !== undefined && count !== before) {
      loadDetails(playlist.value.name)
    }
  }
)

// The liked songs playlist goes when the last heart is removed: leave the
// page rather than show "not found" for something that was just here.
watch(playlist, (now, before) => {
  if (before?.liked && !now && library.loaded.value) {
    router.replace({ name: 'Library', params: { tab: 'playlists' } })
  }
})
</script>
