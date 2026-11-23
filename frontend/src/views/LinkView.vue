<template>
  <div>
    <Transition name="reveal">
      <!-- Loading -->
      <div
        v-if="loading"
        class="mx-auto flex max-w-[1680px] flex-col gap-8 px-4 pt-10 sm:px-6 md:flex-row md:items-end lg:px-10"
      >
        <UiSkeleton
          class="size-48 self-center !rounded-[16px] sm:size-56 md:self-auto"
        />
        <div class="flex flex-1 flex-col gap-3">
          <UiSkeleton class="h-3 w-32" />
          <UiSkeleton class="h-12 w-2/3" />
          <p class="flex items-center gap-2 text-sm text-muted">
            <span
              class="size-4 animate-spin rounded-full border-2 border-accent border-r-transparent"
            />
            {{ t('link.resolving') }}
          </p>
        </div>
      </div>

      <div
        v-else-if="error"
        class="mx-auto max-w-[1680px] px-4 pt-10 sm:px-6 lg:px-10"
      >
        <UiEmpty icon="alert" :title="t('link.failed')" :body="error">
          <UiButton icon="refresh" @click="resolve">{{
            t('common.retry')
          }}</UiButton>
        </UiEmpty>
      </div>

      <div v-else-if="details">
        <CollectionHero
          :title="details.name || t('link.untitled')"
          :kicker="kicker"
          :cover="heroCover.cover"
          :cover-fallback="heroCover.fallback"
          :covers="details.cover_url ? [] : mosaic"
          :name="details.name"
          :icon="
            details.kind === 'artist'
              ? 'user'
              : details.kind === 'playlist'
                ? 'playlist'
                : 'disc'
          "
          :round="details.kind === 'artist'"
        >
          <template #subtitle>
            <span v-if="details.subtitle" class="line-clamp-2">{{
              details.subtitle
            }}</span>
            <span v-if="details.tracks.length" class="tabular">
              {{
                [
                  details.year,
                  t('common.tracks', { count: details.tracks.length }),
                  lengthLabel,
                ]
                  .filter(Boolean)
                  .join(' · ')
              }}
            </span>
            <span v-else-if="details.albums.length">
              {{ t('link.releases', { count: details.albums.length }) }}
            </span>
          </template>
          <template #actions>
            <template v-if="details.tracks.length">
              <UiButton
                v-if="newSongs.length"
                variant="primary"
                size="lg"
                icon="download"
                :loading="submitting"
                @click="download(newSongs)"
              >
                {{
                  newSongs.length === details.tracks.length
                    ? t('link.downloadAll', { count: newSongs.length })
                    : t('link.downloadNew', { count: newSongs.length })
                }}
              </UiButton>
              <span
                v-else
                class="inline-flex h-12 items-center gap-2 rounded-control bg-accent/12 px-5 text-[15px] font-semibold text-accent"
              >
                <AppIcon
                  :name="allInLibrary ? 'check-circle' : 'queue'"
                  :size="18"
                />{{
                  t(allInLibrary ? 'link.allInLibrary' : 'link.allHandled')
                }}
              </span>
              <UiButton
                v-if="
                  newSongs.length && newSongs.length < details.tracks.length
                "
                variant="ghost"
                size="lg"
                @click="download(details.tracks)"
              >
                {{ t('link.redownloadAll') }}
              </UiButton>
            </template>
            <!-- Every song, as one album named after the playlist, in
                 one folder (issue #531). -->
            <UiButton
              v-if="details.kind === 'playlist' && details.tracks.length"
              variant="ghost"
              size="lg"
              icon="disc"
              :loading="submitting"
              :title="t('link.downloadAsAlbumHint')"
              @click="download(details.tracks, { asAlbum: true })"
            >
              {{ t('link.downloadAsAlbum') }}
            </UiButton>
            <UiButton
              v-if="details.kind === 'playlist' && details.tracks.length"
              variant="primary"
              size="lg"
              icon="playlist"
              :loading="savingPlaylist"
              @click="savePlaylist"
            >
              {{ t('link.addPlaylist') }}
            </UiButton>
            <!-- Already watched: say so, with its page and Stop watching. -->
            <UiMenu v-if="watchable && existingWatch" :items="watchedMenu">
              <template #trigger>
                <UiButton
                  variant="ghost"
                  size="lg"
                  icon="check"
                  :loading="watching"
                >
                  {{ t('monitor.watched') }}
                </UiButton>
              </template>
            </UiMenu>
            <UiButton
              v-else-if="watchable"
              variant="ghost"
              size="lg"
              icon="radar"
              :loading="watching"
              @click="watch"
            >
              {{
                details.kind === 'artist'
                  ? t('link.watchArtist')
                  : t('link.watchPlaylist')
              }}
            </UiButton>
            <UiButton
              v-if="details.kind === 'artist'"
              variant="ghost"
              size="lg"
              icon="trending"
              :to="{ name: 'TopSongs', query: { url } }"
            >
              {{ t('link.topSongs') }}
            </UiButton>
            <UiButton
              variant="plain"
              size="lg"
              icon="arrow-up-right"
              :href="url"
            >
              <span class="max-sm:sr-only">{{ sourceLabel }}</span>
            </UiButton>
          </template>
        </CollectionHero>

        <div
          class="mx-auto flex max-w-[1680px] flex-col gap-6 px-4 sm:px-6 lg:px-10"
        >
          <!-- A Spotify mix made for one listener: what Downtify reads is
               the signed-out version, not the listener's own. -->
          <p
            v-if="personalMix"
            class="flex items-start gap-3 rounded-[12px] border border-line-2 bg-surface px-4 py-3 text-[13px] text-pretty text-fg-3"
            role="note"
          >
            <AppIcon
              name="alert"
              :size="18"
              class="mt-0.5 shrink-0 text-warn"
            />
            <span>
              <span class="font-semibold text-fg">{{
                t('monitor.personalMixTitle')
              }}</span>
              {{ t('monitor.personalMixBody') }}
            </span>
          </p>

          <!-- Tracks -->
          <template v-if="details.tracks.length">
            <div class="flex flex-wrap items-center gap-3">
              <UiChips v-model="filter" :items="filters" />
              <span
                v-if="selected.size"
                class="ml-auto flex items-center gap-2"
              >
                <span class="tabular text-sm text-muted">{{
                  t('library.selectedCount', { count: selected.size })
                }}</span>
                <UiButton
                  size="sm"
                  variant="primary"
                  icon="download"
                  @click="download(selectedSongs)"
                >
                  {{ t('link.downloadSelected') }}
                </UiButton>
                <UiIconButton
                  icon="x"
                  :label="t('library.clearSelection')"
                  size="sm"
                  @click="selected = new Set()"
                />
              </span>
            </div>
            <ol class="-mx-3 flex flex-col">
              <li
                v-for="row in visibleRows"
                :key="row.key"
                class="group flex h-16 items-center gap-3 rounded-[12px] px-3 transition-colors hover:bg-surface"
                :class="selected.has(row.key) ? 'bg-accent/8' : ''"
              >
                <button
                  type="button"
                  role="checkbox"
                  :aria-checked="selected.has(row.key)"
                  :aria-label="
                    t('library.selectTrack', { title: row.song.name })
                  "
                  class="flex size-[18px] shrink-0 items-center justify-center rounded-[5px] border-[1.5px] transition-colors"
                  :class="
                    selected.has(row.key)
                      ? 'border-accent bg-accent text-on-accent'
                      : 'border-line-3 hover:border-fg-3'
                  "
                  @click="toggle(row.key)"
                >
                  <AppIcon
                    v-if="selected.has(row.key)"
                    name="check"
                    :size="13"
                    stroke-width="3"
                  />
                </button>
                <SongPlayCell
                  :song="row.song"
                  :index="row.index"
                  :queue="playQueue"
                  :context="playContext"
                  :songs="playSongs"
                />
                <CoverArt
                  :src="row.song.cover_url"
                  :name="row.song.album_name || row.song.name"
                  rounded="rounded-[8px]"
                  :letter-size="14"
                  class="size-11"
                />
                <div class="min-w-0 flex-1">
                  <p class="truncate text-sm font-semibold">
                    {{ row.song.name }}
                  </p>
                  <p class="truncate text-[13px] text-muted">
                    {{ (row.song.artists || []).join(', ') || row.song.artist }}
                  </p>
                </div>
                <span
                  class="hidden w-[28%] truncate text-[13px] text-muted lg:block"
                  >{{ row.song.album_name }}</span
                >
                <span
                  class="tabular hidden w-12 text-right text-[13px] text-muted sm:block"
                >
                  {{
                    row.song.duration ? formatDuration(row.song.duration) : ''
                  }}
                </span>
                <SimilarButton
                  :artist="(row.song.artists || [])[0] || row.song.artist || ''"
                  :title="row.song.name"
                />
                <div class="flex w-28 shrink-0 justify-end">
                  <DownloadState :song="row.song" />
                </div>
              </li>
            </ol>
            <p
              v-if="!visibleRows.length"
              class="py-10 text-center text-sm text-muted"
            >
              {{ t('library.noMatches') }}
            </p>
          </template>

          <!-- Artist releases -->
          <div
            v-else-if="details.albums.length"
            class="grid grid-cols-2 gap-x-5 gap-y-7 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 2xl:grid-cols-6"
          >
            <ReleaseCard
              v-for="album in details.albums"
              :key="album.album_id || album.url"
              :release="album"
            />
          </div>

          <UiEmpty v-else icon="search" :title="t('link.empty')" />
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { computed, ref, watch as watchValue } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppIcon from '/src/components/ui/AppIcon.vue'
import CoverArt from '/src/components/ui/CoverArt.vue'
import UiButton from '/src/components/ui/UiButton.vue'
import UiChips from '/src/components/ui/UiChips.vue'
import UiEmpty from '/src/components/ui/UiEmpty.vue'
import UiIconButton from '/src/components/ui/UiIconButton.vue'
import UiMenu from '/src/components/ui/UiMenu.vue'
import UiSkeleton from '/src/components/ui/UiSkeleton.vue'
import CollectionHero from '/src/components/library/CollectionHero.vue'
import { knownArtistPhoto } from '/src/lib/artistPhotoProxy'
import DownloadState from '/src/components/search/DownloadState.vue'
import SimilarButton from '/src/components/similar/SimilarButton.vue'
import ReleaseCard from '/src/components/search/ReleaseCard.vue'
import SongPlayCell from '/src/components/library/SongPlayCell.vue'
import API from '/src/model/api'
import monitorAPI from '/src/model/monitor'
import {
  jobSongKey,
  useDownloadManager,
  useProgressTracker,
} from '/src/model/download'
import { useLibrary } from '/src/model/library'
import { usePlaylistActions } from '/src/model/playlistActions'
import { songDownloadState } from '/src/lib/downloadState'
import { useUi } from '/src/model/ui'
import { useAuth } from '/src/model/auth'
import { classifyInput } from '/src/lib/input'
import { findWatch } from '/src/lib/watchMatch'
import { watchRouteFor } from '/src/lib/watchStats'
import { confirmWatchMix, isPersonalMix } from '/src/lib/spotifyMix'
import { playableQueue } from '/src/lib/topSongs'
import { formatDuration, splitLength } from '/src/lib/format'
import { useI18n } from '/src/i18n'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const dm = useDownloadManager()
const tracker = useProgressTracker()
const library = useLibrary()
const playlistActions = usePlaylistActions()
const ui = useUi()
const auth = useAuth()

const details = ref(null)
// An artist link's photo: the one saved in the library when there is one,
// else the platform's own (Spotify, Deezer or YouTube Music) relayed by the
// photo proxy - and that picture straight from the platform if the proxy
// can't answer. Any other link keeps its cover as it is.
const heroCover = computed(() => {
  const d = details.value
  if (d?.kind !== 'artist') return { cover: d?.cover_url || '', fallback: '' }
  return knownArtistPhoto(d.name, d.cover_url)
})
const loading = ref(false)
const error = ref('')
const submitting = ref(false)
const watching = ref(false)
// This user's watch of the link (or, for an artist, of their name).
const existingWatch = ref(null)
const savingPlaylist = ref(false)
const filter = ref('all')
const selected = ref(new Set())

const url = computed(() => String(route.query.url || ''))
const kind = computed(() => classifyInput(url.value))

async function resolve() {
  if (!url.value) return
  loading.value = true
  error.value = ''
  details.value = null
  existingWatch.value = null
  selected.value = new Set()
  filter.value = 'all'
  try {
    const res = await API.resolveUrl(url.value)
    details.value = res.data
    library.lookupSongs(res.data?.tracks || [])
    lookupWatch()
  } catch (err) {
    error.value = err?.response?.data?.detail || err?.message || ''
  } finally {
    loading.value = false
  }
}

watchValue(url, resolve, { immediate: true })

const SOURCE_LABELS = {
  spotify: () => t('link.openSpotify'),
  youtube: () => t('link.openYoutube'),
  deezer: () => t('link.openDeezer'),
  soundcloud: () => t('link.openSoundcloud'),
}
const sourceLabel = computed(() =>
  (SOURCE_LABELS[kind.value.source] || SOURCE_LABELS.youtube)()
)

const kicker = computed(() => {
  const names = {
    spotify: 'Spotify',
    youtube: 'YouTube Music',
    deezer: 'Deezer',
    soundcloud: 'SoundCloud',
  }
  const source = names[kind.value.source] || kind.value.source
  return `${source} · ${t(`link.kind.${details.value?.kind || 'track'}`)}`
})

// Playing a downloaded song from here queues the list's other downloaded
// songs after it, in the list's order; the rest stream in full.
const playQueue = computed(() =>
  playableQueue(details.value?.tracks || [], library.findTrack)
)
// The whole list for a mixed queue: downloaded rows from the library,
// the rest streamed, played through to the end.
const playSongs = computed(() => visibleRows.value.map((row) => row.song))
const playContext = computed(() =>
  details.value
    ? {
        type: details.value.kind === 'playlist' ? 'playlist' : 'album',
        title: details.value.name || '',
        subtitle: details.value.subtitle || '',
        cover: details.value.cover_url || '',
        route: { name: 'Link', query: { url: url.value } },
      }
    : null
)

// A Deezer playlist can be watched, a Deezer artist can't: an artist
// watch follows a YouTube Music artist, found from a Spotify or YouTube
// Music link.
const watchable = computed(
  () =>
    (details.value?.kind === 'playlist' || details.value?.kind === 'artist') &&
    (kind.value.source !== 'deezer' || details.value?.kind === 'playlist')
)

const personalMix = computed(
  () => details.value?.kind === 'playlist' && isPersonalMix(url.value)
)

const mosaic = computed(() =>
  [
    ...new Set(
      (details.value?.tracks || [])
        .map((song) => song.cover_url)
        .filter(Boolean)
    ),
  ].slice(0, 4)
)

const lengthLabel = computed(() => {
  const total = (details.value?.tracks || []).reduce(
    (sum, song) => sum + (song.duration || 0),
    0
  )
  if (!total) return ''
  const { hours, minutes } = splitLength(total)
  return hours
    ? t('common.lengthHours', { hours, minutes })
    : t('common.lengthMinutes', { minutes })
})

function keyOf(song, index) {
  return jobSongKey(song) || `row-${index}`
}

function statusOf(song) {
  tracker.queueVersion.value
  const artist = (song.artists || [])[0] || song.artist
  // On an album, a song only counts as in the library when it's there on
  // this album: one it has from another release (a greatest hits, a
  // single) is still offered, so the album can be completed (#546).
  const inLibrary =
    details.value?.kind === 'album'
      ? library.hasSongOnAlbum(
          artist,
          song.name,
          song.album_name || details.value.name
        )
      : library.hasSong(artist, song.name)
  const state = songDownloadState(tracker.getBySong(song), inLibrary)
  // Every queue state shows the same neutral chip here; a song that is
  // neither queued nor in the library is downloadable.
  return state === 'library' || state === 'new' ? state : 'queue'
}

const rows = computed(() =>
  (details.value?.tracks || []).map((song, index) => ({
    song,
    index,
    key: keyOf(song, index),
    status: statusOf(song),
  }))
)

const newSongs = computed(() =>
  rows.value.filter((row) => row.status === 'new').map((row) => row.song)
)
const allInLibrary = computed(
  () =>
    rows.value.length > 0 && rows.value.every((row) => row.status === 'library')
)

async function savePlaylist() {
  if (savingPlaylist.value) return
  savingPlaylist.value = true
  const requestedUrl = url.value
  const collection = details.value
  try {
    await library.lookupSongs(collection.tracks)
    if (url.value !== requestedUrl || details.value !== collection) return
    const files = playableQueue(collection.tracks, library.findTrack)
    if (!files.length) {
      ui.toast(t('link.noAvailableTracks'), { kind: 'error' })
      return
    }
    playlistActions.openCreate(files, {
      name: collection.name || '',
      sourcePlaylistUrl: requestedUrl,
      description: t('link.saveAvailableHint', {
        count: files.length,
        total: collection.tracks.length,
      }),
    })
  } catch (err) {
    ui.toast(err?.response?.data?.detail || t('toast.actionFailed'), {
      kind: 'error',
    })
  } finally {
    savingPlaylist.value = false
  }
}

const filters = computed(() => {
  const count = (status) =>
    rows.value.filter((row) => row.status === status).length
  return [
    { id: 'all', label: t('link.filterAll'), count: rows.value.length },
    { id: 'new', label: t('link.filterNew'), count: count('new') },
    { id: 'library', label: t('link.filterLibrary'), count: count('library') },
    { id: 'queue', label: t('link.filterQueue'), count: count('queue') },
  ].filter((item) => item.id === 'all' || item.count)
})

const visibleRows = computed(() =>
  filter.value === 'all'
    ? rows.value
    : rows.value.filter((row) => row.status === filter.value)
)

const selectedSongs = computed(() =>
  rows.value.filter((row) => selected.value.has(row.key)).map((row) => row.song)
)

function toggle(key) {
  const next = new Set(selected.value)
  if (next.has(key)) next.delete(key)
  else next.add(key)
  selected.value = next
}

async function download(songs, { asAlbum = false } = {}) {
  if (!songs.length) return
  submitting.value = true
  try {
    const isPlaylist = details.value.kind === 'playlist'
    // Keep the playlist's own order for the M3U even when only some
    // tracks are sent.
    const withOrder = songs.map((song) => ({
      ...song,
      downtify_track_order: details.value.tracks.indexOf(song),
    }))
    const count = await dm.fromSongs(withOrder, {
      playlistUrl: isPlaylist ? url.value : '',
      ...(asAlbum
        ? { asAlbum: true, coverUrl: details.value.cover_url || '' }
        : {}),
    })
    selected.value = new Set()
    ui.toast(t('toast.queuedTracks', { count, name: details.value.name }), {
      kind: 'success',
      action: {
        label: t('nav.queue'),
        run: () => router.push({ name: 'Queue' }),
      },
    })
  } catch (err) {
    ui.toast(err?.response?.data?.detail || t('toast.actionFailed'), {
      kind: 'error',
    })
  } finally {
    submitting.value = false
  }
}

// Whether this user already watches the link; a failed lookup leaves the
// Watch button (the server refuses a second watch anyway).
async function lookupWatch() {
  const shown = details.value
  if (!watchable.value) return
  try {
    const { data } = await monitorAPI.listMonitoredPlaylists()
    if (details.value !== shown) return
    existingWatch.value = findWatch(data, {
      kind: shown.kind,
      url: url.value,
      name: shown.kind === 'artist' ? shown.name : '',
      userId: auth.user.value?.id ?? null,
    })
  } catch {
    /* keep offering to watch */
  }
}

const watchedMenu = computed(() => [
  {
    label: t('watchStats.details'),
    icon: 'activity',
    action: () => router.push(watchRouteFor(existingWatch.value)),
  },
  { divider: true },
  {
    label: t('monitor.stop'),
    icon: 'trash',
    danger: true,
    action: stopWatching,
  },
])

async function stopWatching() {
  const target = existingWatch.value
  if (!target?.id) return
  const ok = await ui.confirm({
    title: t('confirm.stopWatchingTitle', { name: target.name }),
    body: t('confirm.stopWatchingBody'),
    confirmLabel: t('monitor.stop'),
    danger: true,
  })
  if (!ok) return
  watching.value = true
  try {
    await monitorAPI.deleteMonitoredPlaylist(target.id)
    if (existingWatch.value === target) existingWatch.value = null
  } catch {
    ui.toast(t('toast.actionFailed'), { kind: 'error' })
  } finally {
    watching.value = false
  }
}

async function watch() {
  if (!(await confirmWatchMix(url.value, { ui, t }))) return
  watching.value = true
  try {
    const res = await monitorAPI.addMonitoredPlaylist(url.value, 360)
    if (res?.data?.id) existingWatch.value = res.data
    ui.toast(t('toast.watching', { name: details.value.name }), {
      kind: 'success',
      action: {
        label: t('nav.monitor'),
        run: () =>
          router.push({
            name: 'Monitor',
            params: {
              tab: details.value.kind === 'artist' ? 'artists' : 'playlists',
            },
          }),
      },
    })
  } catch (err) {
    ui.toast(err?.response?.data?.detail || t('toast.actionFailed'), {
      kind: 'error',
    })
    // Watched already (another tab, or under another link): show it.
    if (err?.response?.status === 409) lookupWatch()
  } finally {
    watching.value = false
  }
}
</script>
