<template>
  <div class="mb-8">
    <div
      v-if="loadError"
      class="surface rounded-2xl p-4 mb-3 text-sm text-error flex gap-2 items-center"
    >
      <Icon icon="clarity:exclamation-circle-line" class="h-5 w-5 shrink-0" />
      <span>{{ loadError }}</span>
    </div>

    <div
      v-if="loading && playlists.length === 0"
      class="surface rounded-2xl p-8 flex flex-col items-center justify-center gap-3"
    >
      <span class="loading loading-spinner loading-md text-primary" />
      <p class="text-sm text-base-content/50">
        {{ t('search.playlistBatchesLoading') }}
      </p>
    </div>

    <div
      v-else-if="playlists.length > 0"
      class="surface rounded-2xl p-4 sm:p-5"
    >
      <button
        type="button"
        class="flex w-full items-start gap-2 text-left"
        :aria-expanded="sectionOpen"
        @click="sectionOpen = !sectionOpen"
      >
        <Icon
          icon="clarity:angle-line"
          class="h-4 w-4 shrink-0 mt-0.5 transition-transform text-base-content/60"
          :class="sectionOpen ? 'rotate-90' : '-rotate-90'"
        />
        <span class="min-w-0 flex-1">
          <span class="text-sm font-semibold block">
            {{ t('search.playlistBatchesTitle') }}
          </span>
          <span class="text-xs text-base-content/50 block mt-0.5">
            {{ t('search.playlistBatchesHint') }}
          </span>
        </span>
        <span
          class="inline-flex h-4 w-4 shrink-0 mt-1 items-center justify-center"
          aria-hidden="true"
        >
          <span
            class="loading loading-spinner loading-xs"
            :class="refreshing ? 'opacity-100' : 'opacity-0'"
          />
        </span>
      </button>

      <div v-show="sectionOpen" class="mt-4 space-y-3">
        <div class="flex flex-wrap items-center gap-2">
          <div class="relative min-w-[12rem] flex-1">
            <Icon
              icon="clarity:search-line"
              class="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-base-content/40 pointer-events-none"
            />
            <input
              v-model="filterQuery"
              type="text"
              class="input input-bordered input-sm w-full pl-9 pr-9 rounded-full bg-base-100/85 border-white/10"
              :placeholder="t('search.playlistBatchesSearchPlaceholder')"
              autocomplete="off"
            />
            <button
              v-if="filterQuery"
              type="button"
              class="absolute right-1 top-1/2 -translate-y-1/2 icon-btn h-7 w-7"
              :title="t('common.close')"
              @click="filterQuery = ''"
            >
              <Icon icon="clarity:times-line" class="h-3.5 w-3.5" />
            </button>
          </div>
          <button
            type="button"
            class="btn btn-ghost btn-xs rounded-full shrink-0"
            @click="expandAll"
          >
            {{ t('search.playlistBatchesExpandAll') }}
          </button>
          <button
            type="button"
            class="btn btn-ghost btn-xs rounded-full shrink-0"
            @click="collapseAll"
          >
            {{ t('search.playlistBatchesCollapseAll') }}
          </button>
        </div>

        <p
          v-if="filteredPlaylists.length === 0"
          class="text-sm text-base-content/50 text-center py-6"
        >
          {{ t('search.playlistBatchesNoMatch') }}
        </p>

        <ul v-else class="space-y-2">
          <li
            v-for="pl in filteredPlaylists"
            :key="pl.spotify_playlist_id"
            class="rounded-xl border border-white/5 bg-base-100/40 overflow-hidden"
          >
            <div
              class="flex items-center gap-1.5 sm:gap-2 px-3 py-2.5 sm:px-4 min-w-0"
            >
              <button
                type="button"
                class="flex min-w-0 flex-1 items-center gap-2 text-left"
                :aria-expanded="isExpanded(pl.spotify_playlist_id)"
                @click="toggleExpanded(pl.spotify_playlist_id)"
              >
                <Icon
                  icon="clarity:angle-line"
                  class="h-4 w-4 shrink-0 transition-transform text-base-content/60"
                  :class="
                    isExpanded(pl.spotify_playlist_id)
                      ? 'rotate-90'
                      : '-rotate-90'
                  "
                />
                <span
                  class="icon-btn shrink-0 cursor-default pointer-events-none"
                  :class="statusIconClassFor(pl)"
                  :title="statusLabelFor(pl)"
                  role="img"
                  :aria-label="statusLabelFor(pl)"
                >
                  <span
                    v-if="effectiveStatus(pl) === 'pending' || isVerifying(pl)"
                    class="loading loading-spinner loading-sm"
                  />
                  <Icon
                    v-else
                    :icon="statusIconFor(pl)"
                    class="h-5 w-5"
                    :class="{
                      'animate-spin': effectiveStatus(pl) === 'in_progress',
                    }"
                  />
                </span>
                <span class="min-w-0">
                  <span
                    class="font-medium truncate block"
                    :title="pl.playlist_name"
                  >
                    {{ pl.playlist_name }}
                  </span>
                  <span class="text-xs text-base-content/60 block truncate">
                    {{ playlistSummary(displayPl(pl)) }}
                  </span>
                </span>
              </button>
              <div class="flex items-center gap-1 shrink-0">
                <a
                  v-if="pl.playlist_url"
                  class="icon-btn shrink-0"
                  :href="pl.playlist_url"
                  target="_blank"
                  rel="noopener noreferrer"
                  :title="t('search.openPlaylistOnSpotify')"
                  :aria-label="t('search.openPlaylistOnSpotify')"
                >
                  <Icon icon="clarity:pop-out-line" class="h-5 w-5" />
                </a>
                <button
                  v-if="pl.downloaded_count > 0"
                  type="button"
                  class="icon-btn shrink-0"
                  :disabled="playingPlaylist === pl.spotify_playlist_id"
                  :title="t('search.playPlaylist')"
                  :aria-label="t('search.playPlaylist')"
                  @click="onPlayPlaylist(pl)"
                >
                  <Icon icon="clarity:play-line" class="h-5 w-5" />
                </button>
                <button
                  v-if="displayPl(pl).missing_count > 0"
                  type="button"
                  class="icon-btn shrink-0 text-primary hover:bg-primary/10"
                  :disabled="downloadingMissing === pl.spotify_playlist_id"
                  :title="
                    t('search.downloadMissing', {
                      count: displayPl(pl).missing_count,
                    })
                  "
                  :aria-label="
                    t('search.downloadMissing', {
                      count: displayPl(pl).missing_count,
                    })
                  "
                  @click="onDownloadMissing(pl)"
                >
                  <Icon icon="clarity:download-line" class="h-5 w-5" />
                </button>
                <button
                  type="button"
                  class="icon-btn shrink-0 text-error hover:bg-error/10"
                  :disabled="deletingPlaylist === pl.spotify_playlist_id"
                  :title="t('library.deletePlaylist')"
                  :aria-label="t('library.deletePlaylist')"
                  @click="onDeletePlaylist(pl)"
                >
                  <Icon icon="clarity:trash-line" class="h-5 w-5" />
                </button>
              </div>
            </div>

            <div
              v-if="isExpanded(pl.spotify_playlist_id)"
              class="border-t border-white/5"
            >
              <div
                v-if="isTracksLoading(pl)"
                class="flex flex-col items-center justify-center gap-2 px-4 py-8"
              >
                <span class="loading loading-spinner loading-sm text-primary" />
                <p class="text-xs text-base-content/50">
                  {{ t('search.playlistBatchesTracksLoading') }}
                </p>
              </div>

              <ul
                v-else
                class="divide-y divide-white/5 max-h-80 overflow-y-auto"
              >
                <li
                  v-if="effectiveStatus(pl) === 'complete'"
                  class="px-4 py-3 text-xs text-base-content/50"
                >
                  {{ t('search.playlistBatchComplete') }}
                </li>
                <li
                  v-else-if="missingTracksFor(pl).length === 0"
                  class="px-4 py-3 text-xs text-base-content/50"
                >
                  {{ tracksEmptyMessage(pl) }}
                </li>
                <template v-else>
                  <li
                    v-for="(track, index) in missingTracksFor(pl)"
                    :key="track.song_id || index"
                    class="flex items-center gap-3 px-3 py-2 sm:px-4"
                  >
                    <div class="track-cover h-10 w-10 shrink-0">
                      <img
                        v-if="track.cover_url"
                        :src="track.cover_url"
                        :alt="track.name"
                        class="h-full w-full object-cover"
                        loading="lazy"
                      />
                      <div
                        v-else
                        class="h-full w-full flex items-center justify-center text-base-content/30"
                      >
                        <Icon icon="clarity:music-note-line" class="h-4 w-4" />
                      </div>
                    </div>
                    <div class="min-w-0 flex-1">
                      <div class="text-sm font-medium truncate">
                        {{ track.name }}
                      </div>
                      <div class="text-xs text-base-content/60 truncate">
                        {{ artistsOf(track) }}
                      </div>
                    </div>
                    <button
                      type="button"
                      class="icon-btn text-primary hover:bg-primary/10 shrink-0"
                      :title="t('search.download')"
                      @click="onDownloadTrack(pl, track)"
                    >
                      <Icon icon="clarity:download-line" class="h-5 w-5" />
                    </button>
                  </li>
                </template>
              </ul>
            </div>
          </li>
        </ul>
      </div>
    </div>

    <div
      v-else-if="!loading"
      class="surface rounded-2xl p-6 text-center text-sm text-base-content/50"
    >
      <p>{{ t('search.playlistBatchesEmpty') }}</p>
      <p class="text-xs mt-2 text-base-content/40">
        {{ t('search.playlistBatchesEmptyHint') }}
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { Icon } from '@iconify/vue'
import API from '../model/api'
import { syncQueueFromServer } from '../model/download'
import {
  normalizeLibraryEntry,
  savePlayerViewPrefs,
  usePlayer,
} from '../model/player'
import { useI18n } from '../i18n'

const emit = defineEmits(['download'])

const { t } = useI18n()
const router = useRouter()
const player = usePlayer()

const playlists = ref([])
const loading = ref(true)
const refreshing = ref(false)
const loadError = ref('')
const sectionOpen = ref(false)
const filterQuery = ref('')
const expanded = reactive({})
const playlistDetails = reactive({})
const downloadingMissing = ref(null)
const deletingPlaylist = ref(null)
const playingPlaylist = ref(null)
let refreshTimer = null
let verifyTimer = null
let progressRefreshTimer = null
let verifyBusy = false
let progressRefreshBusy = false
const progressWatchIds = new Set()

const VERIFY_STALE_MS = 5 * 60 * 1000
const VERIFY_TICK_MS = 1200
const REFRESH_MS = 30000
const PROGRESS_REFRESH_MS = 5000

const filteredPlaylists = computed(() => {
  const query = filterQuery.value.trim().toLowerCase()
  if (!query) {
    return playlists.value
  }
  return playlists.value.filter((pl) => playlistMatchesQuery(pl, query))
})

function displayPl(pl) {
  const detail = playlistDetails[pl.spotify_playlist_id]
  if (!detail?.verified) {
    return pl
  }
  return {
    ...pl,
    playlist_name: detail.playlist_name || pl.playlist_name,
    expected_count: detail.expected_count ?? pl.expected_count,
    downloaded_count: detail.downloaded_count ?? pl.downloaded_count,
    missing_count: detail.missing_count ?? pl.missing_count,
    status: detail.status ?? pl.status,
    active_in_queue: detail.active_in_queue ?? pl.active_in_queue,
  }
}

function isVerifying(pl) {
  const row = displayPl(pl)
  if (row.status === 'pending' || row.source === 'pending') {
    return true
  }
  return Boolean(playlistDetails[pl.spotify_playlist_id]?.verifying)
}

function detailIsStale(detail) {
  if (!detail?.verified || !detail.verifiedAt) {
    return true
  }
  return Date.now() - detail.verifiedAt > VERIFY_STALE_MS
}

function applyVerifiedReport(id, data, { tracks = false } = {}) {
  const prev = playlistDetails[id] || {}
  playlistDetails[id] = {
    ...prev,
    verified: true,
    verifiedAt: Date.now(),
    verifying: false,
    loading: false,
    playlist_name: data.playlist_name,
    expected_count: data.expected_count,
    downloaded_count: data.downloaded_count,
    missing_count: data.missing_count,
    status: data.status,
    active_in_queue: data.active_in_queue,
    tracksLoaded: tracks || prev.tracksLoaded,
    missing_tracks: tracks
      ? data.missing_tracks || []
      : prev.missing_tracks || [],
    error: false,
  }
  const idx = playlists.value.findIndex((row) => row.spotify_playlist_id === id)
  if (idx >= 0) {
    playlists.value[idx] = { ...playlists.value[idx], ...data }
  }
}

function playlistMatchesQuery(pl, query) {
  const name = String(pl.playlist_name || '').toLowerCase()
  if (name.includes(query)) {
    return true
  }
  const detail = playlistDetails[pl.spotify_playlist_id]
  const tracks = detail?.missing_tracks ?? pl.missing_tracks ?? []
  return tracks.some((track) => trackMatchesQuery(track, query))
}

function trackMatchesQuery(track, query) {
  const name = String(track.name || '').toLowerCase()
  const artists = artistsOf(track).toLowerCase()
  const album = String(track.album_name || '').toLowerCase()
  return (
    name.includes(query) || artists.includes(query) || album.includes(query)
  )
}

function filterMatchesPlaylistName(pl, query) {
  const name = String(displayPl(pl).playlist_name || '').toLowerCase()
  return name.includes(query)
}

function visibleTracksFromList(tracks, pl) {
  const query = filterQuery.value.trim().toLowerCase()
  if (!query) {
    return tracks
  }
  // Searching by playlist title should not hide every missing row inside it.
  if (pl && filterMatchesPlaylistName(pl, query)) {
    return tracks
  }
  return tracks.filter((track) => trackMatchesQuery(track, query))
}

function missingTracksFor(pl) {
  const detail = playlistDetails[pl.spotify_playlist_id]
  const tracks = detail?.missing_tracks ?? pl.missing_tracks ?? []
  return visibleTracksFromList(tracks, pl)
}

function tracksDetailReady(pl) {
  const detail = playlistDetails[pl.spotify_playlist_id]
  return Boolean(detail?.tracksLoaded)
}

function tracksEmptyMessage(pl) {
  const detail = playlistDetails[pl.spotify_playlist_id]
  const row = displayPl(pl)
  if (detail?.error) {
    return t('search.incompleteTracksLoading')
  }
  if (!tracksDetailReady(pl) && effectiveStatus(pl) !== 'complete') {
    return t('search.incompleteTracksLoading')
  }
  const query = filterQuery.value.trim().toLowerCase()
  if (query) {
    if (filterMatchesPlaylistName(pl, query)) {
      return t('search.playlistBatchesNoMissingLoaded')
    }
    return t('search.playlistBatchesNoTrackMatch')
  }
  if ((row.missing_count || 0) > 0) {
    return t('search.incompleteTracksLoading')
  }
  return t('search.playlistBatchComplete')
}

function isExpanded(id) {
  return Boolean(expanded[id])
}

function expandAll() {
  for (const pl of filteredPlaylists.value) {
    expanded[pl.spotify_playlist_id] = true
    loadPlaylistDetails(pl.spotify_playlist_id, pl, {
      tracks: true,
      force: true,
    })
  }
}

function collapseAll() {
  for (const pl of playlists.value) {
    expanded[pl.spotify_playlist_id] = false
  }
}

function isTracksLoading(pl) {
  const id = pl.spotify_playlist_id
  if (!isExpanded(id)) {
    return false
  }
  return Boolean(playlistDetails[id]?.loading)
}

function trackProgressPlaylist(id) {
  if (id) {
    progressWatchIds.add(id)
  }
}

function playlistsNeedingProgressRefresh() {
  const ids = new Set(progressWatchIds)
  for (const pl of playlists.value) {
    const row = displayPl(pl)
    if ((row.active_in_queue || 0) > 0) {
      ids.add(pl.spotify_playlist_id)
    }
  }
  if (downloadingMissing.value) {
    ids.add(downloadingMissing.value)
  }
  return playlists.value.filter((pl) => ids.has(pl.spotify_playlist_id))
}

function clearProgressWatchIfSettled(pl) {
  const id = pl.spotify_playlist_id
  const row = displayPl(pl)
  if ((row.active_in_queue || 0) > 0) {
    return
  }
  if (downloadingMissing.value === id) {
    return
  }
  progressWatchIds.delete(id)
}

async function refreshInProgressPlaylists() {
  if (progressRefreshBusy || loading.value || refreshing.value || verifyBusy) {
    return
  }
  const active = playlistsNeedingProgressRefresh()
  if (!active.length) {
    return
  }
  progressRefreshBusy = true
  try {
    for (const pl of active) {
      const id = pl.spotify_playlist_id
      const prev = playlistDetails[id] || {}
      if (prev.loading || prev.verifying) {
        continue
      }
      await loadPlaylistDetails(id, pl, {
        tracks: isExpanded(id),
        force: true,
        silent: true,
      })
      clearProgressWatchIfSettled(pl)
    }
  } finally {
    progressRefreshBusy = false
  }
}

async function loadPlaylistDetails(
  id,
  pl,
  { tracks = true, force = false, silent = false } = {}
) {
  const prev = playlistDetails[id] || {}
  if (prev.loading) {
    return
  }
  if (tracks) {
    if (prev.tracksLoaded && !force && !detailIsStale(prev)) {
      return
    }
  } else if (prev.verified && !force && !detailIsStale(prev)) {
    return
  }

  if (!silent) {
    playlistDetails[id] = {
      ...prev,
      loading: tracks,
      verifying: !tracks,
      error: false,
    }
  }
  try {
    const res = await API.getPlaylistBatchDetails(id, { tracks })
    applyVerifiedReport(id, res.data || {}, { tracks })
  } catch (e) {
    console.log('Failed to load playlist batch details:', e)
    if (!silent) {
      playlistDetails[id] = {
        ...playlistDetails[id],
        loading: false,
        verifying: false,
        error: true,
      }
    }
  }
}

function nextPlaylistToVerify() {
  const list = playlists.value
  if (!list.length) {
    return null
  }
  const pending = list.filter((pl) => {
    const detail = playlistDetails[pl.spotify_playlist_id]
    if (detail?.loading || detail?.verifying) {
      return false
    }
    return detailIsStale(detail)
  })
  if (!pending.length) {
    return null
  }
  pending.sort((a, b) => {
    const rowA = displayPl(a)
    const rowB = displayPl(b)
    const aDone = rowA.status === 'complete' && rowA.missing_count === 0
    const bDone = rowB.status === 'complete' && rowB.missing_count === 0
    if (aDone !== bDone) {
      return aDone ? 1 : -1
    }
    return 0
  })
  return pending[0]
}

async function tickVerify() {
  if (verifyBusy || loading.value || refreshing.value) {
    return
  }
  const pl = nextPlaylistToVerify()
  if (!pl) {
    return
  }
  verifyBusy = true
  try {
    await loadPlaylistDetails(pl.spotify_playlist_id, pl, { tracks: false })
  } finally {
    verifyBusy = false
  }
}

async function toggleExpanded(id) {
  const next = !expanded[id]
  expanded[id] = next
  if (!next) {
    return
  }
  const pl = playlists.value.find((row) => row.spotify_playlist_id === id)
  await loadPlaylistDetails(id, pl, { tracks: true, force: true })
}

async function refreshPlaylists() {
  const initial = playlists.value.length === 0
  if (initial) {
    loading.value = true
  } else {
    refreshing.value = true
  }
  loadError.value = ''
  try {
    const res = await API.getPlaylistBatches()
    playlists.value = res.data?.playlists || []
    for (const pl of playlists.value) {
      if (pl.spotify_playlist_id in expanded) {
        continue
      }
      expanded[pl.spotify_playlist_id] = false
    }
  } catch (e) {
    loadError.value = t('search.playlistBatchesLoadFailed')
    console.log('Failed to load playlist batches:', e)
  } finally {
    loading.value = false
    refreshing.value = false
  }
}

function effectiveStatus(pl) {
  const row = displayPl(pl)
  if (row.status === 'pending' || row.source === 'pending') {
    return 'pending'
  }
  if ((row.active_in_queue || 0) > 0) {
    return 'in_progress'
  }
  if ((row.missing_count || 0) > 0) {
    return 'incomplete'
  }
  if ((row.expected_count || 0) > 0) {
    return 'complete'
  }
  return row.status || 'incomplete'
}

function playlistSummary(pl) {
  return t('search.incompleteSummary', {
    downloaded: pl.downloaded_count,
    expected: pl.expected_count,
    missing: pl.missing_count,
  })
}

function statusLabel(status) {
  if (status === 'pending') return t('search.playlistBatchesVerifying')
  if (status === 'in_progress') return t('search.incompleteInProgress')
  if (status === 'complete') return t('search.playlistBatchStatusComplete')
  return t('search.incompleteFinished')
}

function statusLabelFor(pl) {
  if (isVerifying(pl)) {
    return t('search.playlistBatchesVerifying')
  }
  return statusLabel(effectiveStatus(pl))
}

function statusIconFor(pl) {
  const status = effectiveStatus(pl)
  if (status === 'in_progress') {
    return 'clarity:sync-line'
  }
  return 'clarity:success-standard-line'
}

function statusIconClass(status) {
  if (status === 'pending') {
    return 'text-base-content/50'
  }
  if (status === 'in_progress') {
    return 'text-primary'
  }
  if (status === 'complete') {
    return 'text-success'
  }
  if (status === 'incomplete') {
    return 'text-warning'
  }
  return 'text-warning'
}

function statusIconClassFor(pl) {
  return statusIconClass(effectiveStatus(pl))
}

function artistsOf(song) {
  if (Array.isArray(song.artists) && song.artists.length) {
    return song.artists.join(', ')
  }
  return song.artist || t('common.unknownArtist')
}

async function onDownloadMissing(pl) {
  const id = pl.spotify_playlist_id
  downloadingMissing.value = id
  trackProgressPlaylist(id)
  try {
    await API.downloadMissingPlaylistTracks({
      spotify_playlist_id: id,
      playlist_url: pl.playlist_url,
    })
    await syncQueueFromServer()
    delete playlistDetails[id]
    await refreshPlaylists()
    trackProgressPlaylist(id)
    await refreshInProgressPlaylists()
  } catch (e) {
    console.error('download missing failed:', e)
    progressWatchIds.delete(id)
  } finally {
    downloadingMissing.value = null
  }
}

async function onDeletePlaylist(pl) {
  const name = String(pl.playlist_name || '').trim()
  if (!name) {
    return
  }
  if (!confirm(t('library.deletePlaylistPrompt', { name }))) {
    return
  }
  deletingPlaylist.value = pl.spotify_playlist_id
  try {
    await API.deletePlaylistBatch(pl.spotify_playlist_id)
    delete playlistDetails[pl.spotify_playlist_id]
    delete expanded[pl.spotify_playlist_id]
    await refreshPlaylists()
  } catch (e) {
    console.error('delete playlist failed:', e)
    loadError.value = t('library.playlistDeleteFailed', { name })
  } finally {
    deletingPlaylist.value = null
  }
}

async function onPlayPlaylist(pl) {
  const name = String(pl.playlist_name || '').trim()
  if (!name) return
  playingPlaylist.value = pl.spotify_playlist_id
  try {
    const res = await API.listDownloads()
    const tracks = (res.data || [])
      .map(normalizeLibraryEntry)
      .filter((entry) => (entry.playlists || []).includes(name))
    if (!tracks.length) {
      window.alert(t('search.playlistBatchNothingToPlay'))
      return
    }
    savePlayerViewPrefs({ playlistFilter: name, filterQuery: '' })
    player.setPlaylist(tracks, { startIndex: 0, autoplay: true })
    router.push({ name: 'Player' })
  } catch (e) {
    console.error('play playlist failed:', e)
  } finally {
    playingPlaylist.value = null
  }
}

function onDownloadTrack(pl, track) {
  trackProgressPlaylist(pl.spotify_playlist_id)
  emit('download', {
    ...track,
    downtify_playlist_url: pl.playlist_url,
  })
}

onMounted(() => {
  refreshPlaylists()
    .then(() => {
      tickVerify().catch(() => {})
    })
    .catch(() => {})
  refreshTimer = setInterval(() => {
    refreshPlaylists().catch(() => {})
  }, REFRESH_MS)
  verifyTimer = setInterval(() => {
    tickVerify().catch(() => {})
  }, VERIFY_TICK_MS)
  progressRefreshTimer = setInterval(() => {
    refreshInProgressPlaylists().catch(() => {})
  }, PROGRESS_REFRESH_MS)
})

onUnmounted(() => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
    refreshTimer = null
  }
  if (verifyTimer) {
    clearInterval(verifyTimer)
    verifyTimer = null
  }
  if (progressRefreshTimer) {
    clearInterval(progressRefreshTimer)
    progressRefreshTimer = null
  }
  progressWatchIds.clear()
})
</script>
