<template>
  <div class="min-h-dvh overflow-x-hidden pb-[max(1rem,env(safe-area-inset-bottom))]">
    <Navbar />
    <Settings />

    <div class="mx-auto max-w-5xl px-4 py-4 sm:py-8 sm:px-6">
      <!-- Header -->
      <div class="mb-6">
        <h1 class="text-2xl font-bold tracking-tight">
          {{ t('player.title') }}
        </h1>
        <p class="mt-1 text-sm text-base-content/60">
          {{ t('player.subtitle') }}
        </p>
      </div>

      <div
        v-if="files.length > 0"
        class="mb-6 flex flex-col gap-3"
      >
        <div class="flex flex-col gap-3 sm:flex-row sm:items-center">
          <div class="relative flex-1 min-w-0">
          <Icon
            icon="clarity:search-line"
            class="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-base-content/40 pointer-events-none"
          />
          <input
            v-model="filterQuery"
            type="text"
            class="input input-bordered w-full pl-10 pr-10 h-11 rounded-full bg-base-100/85 border-white/10"
            :placeholder="t('library.searchPlaceholder')"
            autocomplete="off"
          />
          <button
            v-if="filterQuery"
            type="button"
            class="absolute right-2 top-1/2 -translate-y-1/2 icon-btn h-8 w-8"
            :title="t('common.close')"
            @click="filterQuery = ''"
          >
            <Icon icon="clarity:times-line" class="h-4 w-4" />
          </button>
        </div>
        <select
          v-model="playlistFilter"
          class="select select-bordered select-sm rounded-full bg-base-100/85 border-white/10 sm:max-w-xs sm:min-w-[12rem]"
        >
          <option value="">{{ t('library.filterAllPlaylists') }}</option>
          <option v-for="pl in playlistNames" :key="pl" :value="pl">
            {{ pl }}
          </option>
        </select>
        </div>
      </div>

      <p
        v-if="error"
        class="mb-4 rounded-xl border border-error/30 bg-error/10 px-4 py-2 text-sm text-error"
      >
        {{ error }}
      </p>

      <!-- Empty state -->
      <div
        v-if="files.length === 0 && !loading"
        class="surface rounded-2xl p-12 flex flex-col items-center text-center"
      >
        <Icon
          icon="clarity:headphones-line"
          class="h-12 w-12 text-base-content/20 mb-4"
        />
        <p class="text-base-content/50 text-sm">{{ t('player.empty') }}</p>
        <p class="text-base-content/40 text-xs mt-1">
          {{ t('player.emptyHint') }}
        </p>
      </div>

      <!-- Skeleton -->
      <div v-else-if="loading && !player.currentTrack.value" class="space-y-3">
        <div class="skeleton h-72 rounded-3xl" />
        <div class="skeleton h-16 rounded-2xl" />
        <div class="skeleton h-16 rounded-2xl" />
      </div>

      <!-- Player + queue -->
      <div
        v-else
        class="grid gap-4 sm:gap-6 lg:grid-cols-[1fr_360px] min-w-0"
      >
        <!-- Player card -->
        <section
          class="surface rounded-3xl p-4 sm:p-8 flex flex-col items-center text-center min-w-0 w-full"
        >
          <!-- Cover -->
          <div
            class="relative w-[min(100%,11rem)] aspect-square sm:w-64 rounded-3xl bg-primary/10 text-primary flex items-center justify-center overflow-hidden shadow-glow shrink-0"
            :class="{ 'pulse-glow': player.isPlaying.value }"
          >
            <img
              v-if="
                player.currentTrack.value &&
                player.currentTrack.value.has_cover &&
                !coverFailed[player.currentTrack.value.file]
              "
              :src="player.currentTrack.value.cover"
              :alt="player.currentTrack.value.title"
              class="absolute inset-0 h-full w-full object-cover"
              @error="markCoverFailed(player.currentTrack.value.file)"
            />
            <Icon
              v-else
              icon="clarity:music-note-line"
              class="h-16 w-16 sm:h-24 sm:w-24"
            />
            <div
              v-if="player.isPlaying.value"
              class="absolute bottom-3 right-3 equalizer h-5"
              aria-hidden="true"
            >
              <span></span><span></span><span></span>
            </div>
          </div>

          <!-- Title / artist -->
          <div class="mt-4 sm:mt-6 w-full min-w-0 px-1">
            <p class="text-lg sm:text-xl font-bold tracking-tight truncate">
              {{ trackTitle }}
            </p>
            <p class="text-sm text-base-content/60 truncate mt-0.5">
              {{ trackArtist }}
            </p>
          </div>

          <!-- Progress -->
          <div class="mt-4 sm:mt-6 w-full min-w-0 touch-pan-y">
            <div
              class="relative h-2.5 sm:h-2 rounded-full bg-white/10 overflow-hidden cursor-pointer group"
              ref="progressBar"
              @click="onSeekClick"
              @pointerdown="onSeekStart"
            >
              <div
                class="h-full bg-primary transition-[width] duration-150"
                :style="`width: ${player.progressPct.value}%`"
              />
              <div
                class="progress-thumb absolute top-1/2 -translate-y-1/2 h-4 w-4 sm:h-3.5 sm:w-3.5 rounded-full bg-primary shadow-glow-sm transition-all duration-150"
                :style="`left: calc(${player.progressPct.value}% - 8px)`"
              />
            </div>
            <div
              class="mt-2 flex items-center justify-between text-xs text-base-content/50 tabular-nums"
            >
              <span>{{ formatTime(player.currentTime.value) }}</span>
              <span>{{ formatTime(player.duration.value) }}</span>
            </div>
          </div>

          <!-- Transport -->
          <div
            class="mt-4 sm:mt-5 flex flex-wrap items-center justify-center gap-1.5 sm:gap-3 max-w-full px-1"
          >
            <button
              class="icon-btn icon-btn-compact"
              :class="{ 'icon-btn-active': player.shuffle.value }"
              @click="player.toggleShuffle()"
              :title="
                player.shuffle.value
                  ? t('player.shuffleOn')
                  : t('player.shuffleOff')
              "
            >
              <Icon icon="clarity:shuffle-line" class="h-5 w-5" />
            </button>
            <button
              class="icon-btn icon-btn-compact"
              @click="player.prev()"
              :title="t('player.previous')"
              :disabled="filteredFiles.length === 0"
            >
              <Icon
                icon="clarity:step-forward-2-line"
                class="h-5 w-5 -scale-x-100"
              />
            </button>
            <button
              class="inline-flex h-12 w-12 sm:h-14 sm:w-14 shrink-0 items-center justify-center rounded-full bg-primary text-primary-content shadow-glow-sm hover:scale-105 active:scale-95 transition disabled:opacity-50"
              @click="player.toggle()"
              :disabled="filteredFiles.length === 0"
              :title="
                player.isPlaying.value ? t('player.pause') : t('player.play')
              "
            >
              <Icon
                :icon="
                  player.isPlaying.value
                    ? 'clarity:pause-solid'
                    : 'clarity:play-solid'
                "
                class="h-6 w-6"
              />
            </button>
            <button
              class="icon-btn icon-btn-compact"
              @click="player.next()"
              :title="t('player.next')"
              :disabled="filteredFiles.length === 0"
            >
              <Icon icon="clarity:step-forward-2-line" class="h-5 w-5" />
            </button>
            <button
              class="icon-btn icon-btn-compact relative"
              :class="{ 'icon-btn-active': player.repeatMode.value !== 'off' }"
              @click="player.cycleRepeat()"
              :title="repeatTitle"
            >
              <Icon icon="clarity:refresh-line" class="h-5 w-5" />
              <span
                v-if="player.repeatMode.value === 'one'"
                class="absolute -bottom-0.5 -right-0.5 h-4 min-w-[1rem] px-1 rounded-full bg-primary text-primary-content text-[9px] font-bold flex items-center justify-center"
              >
                1
              </span>
            </button>
          </div>

          <!-- Volume -->
          <div
            class="mt-4 sm:mt-6 w-full max-w-xs flex items-center gap-2 sm:gap-3 min-w-0 px-1"
          >
            <button
              class="icon-btn icon-btn-compact shrink-0"
              @click="player.toggleMute()"
              :title="
                player.isMuted.value ? t('player.unmute') : t('player.mute')
              "
            >
              <Icon
                :icon="
                  player.isMuted.value || player.volume.value === 0
                    ? 'clarity:volume-mute-line'
                    : player.volume.value < 0.5
                      ? 'clarity:volume-down-line'
                      : 'clarity:volume-up-line'
                "
                class="h-5 w-5"
              />
            </button>
            <input
              type="range"
              min="0"
              max="1"
              step="0.01"
              :value="player.isMuted.value ? 0 : player.volume.value"
              @input="onVolume($event)"
              class="player-range flex-1"
              :title="t('player.volume')"
            />
          </div>

          <button
            v-if="player.currentTrack.value"
            type="button"
            class="btn btn-ghost btn-sm mt-5 text-error/80 hover:text-error hover:bg-error/10 rounded-full"
            :disabled="deleting[player.currentTrack.value.file] === true"
            @click="onDelete(player.currentTrack.value.file)"
          >
            <span
              v-if="deleting[player.currentTrack.value.file] === true"
              class="loading loading-spinner loading-xs mr-1.5"
            />
            <Icon v-else icon="clarity:trash-line" class="h-4 w-4 mr-1.5" />
            {{ t('player.deleteTrack') }}
          </button>
        </section>

        <!-- Queue list -->
        <aside
          class="surface rounded-3xl p-4 sm:p-5 min-w-0 max-h-[min(52vh,28rem)] sm:max-h-[min(60vh,32rem)] lg:max-h-[640px] overflow-y-auto overscroll-contain"
        >
          <div class="flex items-center justify-between mb-2 px-1">
            <h2
              class="text-xs font-semibold uppercase tracking-wider text-base-content/50"
            >
              {{ t('player.queue') }}
            </h2>
            <span class="text-[11px] text-base-content/40">
              <template v-if="hasActiveFilter">
                {{ t('library.filteredCount', {
                  shown: filteredFiles.length,
                  total: files.length,
                }) }}
              </template>
              <template v-else>
                {{
                  files.length === 1
                    ? t('player.countOne', { count: files.length })
                    : t('player.countMany', { count: files.length })
                }}
              </template>
            </span>
          </div>

          <div
            v-if="filteredFiles.length > 0"
            class="mb-3 px-1 flex flex-wrap items-center gap-2 border-b border-white/5 pb-3"
          >
            <label
              class="flex items-center gap-2.5 cursor-pointer flex-1 min-w-0"
            >
              <input
                ref="selectAllCheckbox"
                type="checkbox"
                class="checkbox checkbox-sm checkbox-primary shrink-0"
                :checked="allFilteredSelected"
                @change="toggleSelectAllFiltered"
              />
              <span class="text-xs text-base-content/70 truncate">
                <template v-if="selectedCount > 0">
                  {{
                    t('player.selectedCount', {
                      selected: selectedCount,
                      total: filteredFiles.length,
                    })
                  }}
                </template>
                <template v-else>
                  {{ t('player.selectAll') }}
                  <span class="text-base-content/40">
                    ({{ filteredFiles.length }})
                  </span>
                </template>
              </span>
            </label>
            <button
              v-if="selectedCount > 0"
              type="button"
              class="btn btn-ghost btn-xs rounded-full shrink-0 h-8 min-h-0 px-2"
              @click="clearSelection"
            >
              {{ t('library.clearSelection') }}
            </button>
            <button
              v-if="selectedCount > 0"
              type="button"
              class="btn btn-error btn-xs rounded-full btn-outline shrink-0 h-8 min-h-0 px-3"
              :disabled="batchDeleting"
              @click="onDeleteSelected"
            >
              <span
                v-if="batchDeleting"
                class="loading loading-spinner loading-xs mr-1"
              />
              <Icon
                v-else
                icon="clarity:trash-line"
                class="h-3.5 w-3.5 mr-1"
              />
              {{ selectedCount }}
            </button>
          </div>

          <p
            v-if="files.length > 0 && filteredFiles.length === 0"
            class="text-sm text-base-content/50 text-center py-8 px-2"
          >
            {{ t('library.searchNoResults') }}
          </p>

          <ul v-else-if="filteredFiles.length > 0" class="space-y-1">
            <li
              v-for="(entry, idx) in filteredFiles"
              :key="entry.file"
              class="rounded-xl px-2 py-2 flex items-center gap-3 cursor-pointer transition-colors"
              :class="
                idx === player.currentIndex.value
                  ? 'bg-primary/10 text-primary'
                  : 'hover:bg-white/5'
              "
              @click="onPick(idx)"
            >
              <input
                type="checkbox"
                class="checkbox checkbox-sm checkbox-primary shrink-0"
                :checked="selectedFiles.has(entry.file)"
                @click.stop
                @change="toggleSelect(entry.file)"
              />
              <div
                class="relative h-9 w-9 shrink-0 rounded-lg overflow-hidden flex items-center justify-center"
                :class="
                  idx === player.currentIndex.value
                    ? 'bg-primary/15'
                    : 'bg-base-100/60'
                "
              >
                <img
                  v-if="entry.has_cover && !coverFailed[entry.file]"
                  :src="coverUrlFor(entry.file)"
                  :alt="entry.title"
                  class="absolute inset-0 h-full w-full object-cover"
                  loading="lazy"
                  @error="markCoverFailed(entry.file)"
                />
                <span
                  v-if="
                    idx === player.currentIndex.value && player.isPlaying.value
                  "
                  class="relative equalizer h-3"
                  aria-hidden="true"
                >
                  <span></span><span></span><span></span>
                </span>
                <Icon
                  v-else-if="!entry.has_cover || coverFailed[entry.file]"
                  icon="clarity:music-note-line"
                  class="h-4 w-4 text-base-content/50"
                />
              </div>
              <div class="flex-1 min-w-0">
                <p class="text-sm truncate font-medium">
                  {{ entry.title }}
                </p>
                <p class="text-[11px] truncate text-base-content/50">
                  {{ entry.artist || t('common.unknownArtist') }}
                </p>
              </div>
              <button
                type="button"
                class="icon-btn shrink-0 text-error/60 hover:text-error hover:bg-error/10"
                :disabled="deleting[entry.file] === true"
                :title="t('library.deleteFile')"
                @click.stop="onDelete(entry.file)"
              >
                <span
                  v-if="deleting[entry.file] === true"
                  class="loading loading-spinner loading-xs"
                />
                <Icon v-else icon="clarity:trash-line" class="h-4 w-4" />
              </button>
            </li>
          </ul>

          <div v-else class="text-center py-10">
            <p class="text-base-content/50 text-sm">{{ t('player.empty') }}</p>
          </div>
        </aside>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed, watch, nextTick } from 'vue'
import { Icon } from '@iconify/vue'
import Navbar from '/src/components/Navbar.vue'
import Settings from '/src/components/Settings.vue'
import API from '/src/model/api'
import {
  usePlayer,
  formatTime,
  trackInfoFromFile,
  normalizeLibraryEntry,
} from '/src/model/player'
import { useI18n } from '/src/i18n'
import { libraryEntryMatchesQuery } from '/src/model/libraryFilter'

const { t } = useI18n()
const player = usePlayer()

const files = ref([])
const filterQuery = ref('')
const playlistFilter = ref('')
const loading = ref(false)
const error = ref('')
const deleting = ref({})
const batchDeleting = ref(false)
const selectedFiles = ref(new Set())
const selectAllCheckbox = ref(null)
const progressBar = ref(null)
const coverFailed = ref({})
let dragging = false

function coverUrlFor(file) {
  return API.coverFileURL(file)
}

function markCoverFailed(file) {
  coverFailed.value = { ...coverFailed.value, [file]: true }
}

const playlistNames = computed(() => {
  const names = new Set()
  for (const entry of files.value) {
    for (const pl of entry.playlists || []) {
      if (pl) names.add(pl)
    }
  }
  return [...names].sort((a, b) => a.localeCompare(b))
})

const filteredFiles = computed(() => {
  let list = files.value
  const pl = String(playlistFilter.value || '').trim()
  if (pl) {
    list = list.filter((entry) => (entry.playlists || []).includes(pl))
  }
  const query = filterQuery.value
  if (!String(query || '').trim()) return list
  return list.filter((entry) => libraryEntryMatchesQuery(entry, query))
})

const hasActiveFilter = computed(
  () =>
    Boolean(String(filterQuery.value || '').trim()) ||
    Boolean(String(playlistFilter.value || '').trim())
)

const selectedCount = computed(() => selectedFiles.value.size)

const allFilteredSelected = computed(() => {
  if (!filteredFiles.value.length) return false
  return filteredFiles.value.every((entry) => selectedFiles.value.has(entry.file))
})

const someFilteredSelected = computed(() => {
  const total = filteredFiles.value.length
  const n = selectedCount.value
  return total > 0 && n > 0 && n < total
})

function updateSelectAllIndeterminate() {
  const el = selectAllCheckbox.value
  if (el) el.indeterminate = someFilteredSelected.value
}

watch([someFilteredSelected, allFilteredSelected, selectedCount], () => {
  nextTick(updateSelectAllIndeterminate)
})

function toggleSelect(file) {
  const next = new Set(selectedFiles.value)
  if (next.has(file)) next.delete(file)
  else next.add(file)
  selectedFiles.value = next
}

function toggleSelectAllFiltered() {
  if (allFilteredSelected.value) {
    selectedFiles.value = new Set()
    return
  }
  selectedFiles.value = new Set(filteredFiles.value.map((entry) => entry.file))
}

function clearSelection() {
  selectedFiles.value = new Set()
}

function syncPlayerQueue(options = {}) {
  const list = filteredFiles.value
  if (!list.length) return

  if (typeof options.startIndex === 'number') {
    player.setPlaylist(list, {
      startIndex: options.startIndex,
      autoplay: options.autoplay === true,
    })
    return
  }

  player.setPlaylist(list, { preservePlayback: true })
}

watch([filteredFiles, playlistFilter, filterQuery], () => {
  if (!files.value.length) return
  if (!filteredFiles.value.length) return
  syncPlayerQueue()
})

async function load() {
  loading.value = true
  try {
    const res = await API.listDownloads()
    files.value = (res.data || []).map(normalizeLibraryEntry)
    if (player.playlist.value.length === 0 && filteredFiles.value.length > 0) {
      player.setPlaylist(filteredFiles.value, { preservePlayback: true })
    }
  } finally {
    loading.value = false
  }
}

function onPick(idx) {
  syncPlayerQueue({ startIndex: idx, autoplay: true })
}

function removeFilesFromList(paths) {
  const gone = new Set(paths)
  files.value = files.value.filter((entry) => !gone.has(entry.file))
  const next = new Set(selectedFiles.value)
  for (const path of gone) next.delete(path)
  selectedFiles.value = next
}

function syncPlayerAfterRemovals(deletedPaths, idxBefore, wasPlaying) {
  const gone = new Set(deletedPaths)
  const list = filteredFiles.value
  if (!list.length) {
    player.setPlaylist([])
    player.pause()
    return
  }
  const currentFile = player.currentTrack.value?.file
  if (currentFile && gone.has(currentFile)) {
    const nextIdx = Math.min(Math.max(idxBefore, 0), list.length - 1)
    player.setPlaylist(list, {
      startIndex: nextIdx,
      autoplay: wasPlaying === true,
    })
    return
  }
  syncPlayerQueue()
}

function syncPlayerAfterDelete(file, idxBefore, wasPlaying) {
  syncPlayerAfterRemovals([file], idxBefore, wasPlaying)
}

async function onDelete(file) {
  if (!confirm(t('library.deletePrompt', { file }))) return
  deleting.value = { ...deleting.value, [file]: true }
  error.value = ''
  const idxBefore = player.currentIndex.value
  const wasCurrent = player.currentTrack.value?.file === file
  const wasPlaying = wasCurrent && player.isPlaying.value
  try {
    const res = await API.deleteDownload(file)
    if (res.data?.deleted === false) {
      error.value = res.data?.error || t('library.failedDelete', { file })
      return
    }
    removeFilesFromList([file])
    syncPlayerAfterDelete(
      file,
      wasCurrent ? idxBefore : -1,
      wasPlaying,
    )
  } catch (err) {
    const detail = err?.response?.data?.error
    error.value =
      typeof detail === 'string' && detail
        ? detail
        : t('library.failedDelete', { file })
  } finally {
    deleting.value = { ...deleting.value, [file]: false }
  }
}

async function onDeleteSelected() {
  const paths = [...selectedFiles.value]
  if (!paths.length) return
  if (!confirm(t('library.deleteSelectedPrompt', { count: paths.length })))
    return
  batchDeleting.value = true
  error.value = ''
  const idxBefore = player.currentIndex.value
  const currentFile = player.currentTrack.value?.file
  const wasPlaying = Boolean(currentFile && player.isPlaying.value)
  try {
    const res = await API.deleteDownloadsBatch(paths)
    const deleted = res.data?.deleted || []
    const failed = res.data?.failed || []
    removeFilesFromList(deleted)
    if (deleted.length) {
      syncPlayerAfterRemovals(
        deleted,
        currentFile && deleted.includes(currentFile) ? idxBefore : -1,
        wasPlaying && currentFile && deleted.includes(currentFile),
      )
    }
    if (failed.length) {
      error.value = t('library.batchDeletePartial', {
        ok: deleted.length,
        failed: failed.length,
      })
    }
  } catch (err) {
    const detail = err?.response?.data?.detail
    error.value =
      typeof detail === 'string' && detail
        ? detail
        : t('library.failedDelete', { file: paths[0] })
  } finally {
    batchDeleting.value = false
  }
}

function trackInfo(file) {
  return trackInfoFromFile(file)
}

const trackTitle = computed(() => {
  const c = player.currentTrack.value
  if (c && c.title) return c.title
  return t('player.empty')
})

const trackArtist = computed(() => {
  const c = player.currentTrack.value
  if (c && c.artist) return c.artist
  if (c) return t('common.unknownArtist')
  return ''
})

const repeatTitle = computed(() => {
  if (player.repeatMode.value === 'one') return t('player.repeatOne')
  if (player.repeatMode.value === 'all') return t('player.repeatAll')
  return t('player.repeatOff')
})

function onVolume(e) {
  player.setVolume(parseFloat(e.target.value))
}

function ratioFromEvent(e) {
  const el = progressBar.value
  if (!el) return 0
  const rect = el.getBoundingClientRect()
  const x = (e.clientX || 0) - rect.left
  return Math.max(0, Math.min(1, x / rect.width))
}

function onSeekClick(e) {
  player.seekRatio(ratioFromEvent(e))
}

function onSeekStart(e) {
  dragging = true
  player.seekRatio(ratioFromEvent(e))
  window.addEventListener('pointermove', onSeekDrag)
  window.addEventListener('pointerup', onSeekEnd, { once: true })
}

function onSeekDrag(e) {
  if (!dragging) return
  player.seekRatio(ratioFromEvent(e))
}

function onSeekEnd() {
  dragging = false
  window.removeEventListener('pointermove', onSeekDrag)
}

onMounted(() => {
  window.scroll(0, 0)
  load()
  nextTick(updateSelectAllIndeterminate)
})

onUnmounted(() => {
  window.removeEventListener('pointermove', onSeekDrag)
})
</script>

<style scoped>
.player-range {
  -webkit-appearance: none;
  appearance: none;
  background: rgba(255, 255, 255, 0.1);
  height: 4px;
  border-radius: 9999px;
  outline: none;
}
[data-theme='downtify-light'] .player-range {
  background: rgba(0, 0, 0, 0.1);
}
.player-range::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  height: 14px;
  width: 14px;
  border-radius: 9999px;
  background: #1ad05c;
  cursor: pointer;
  box-shadow: 0 0 12px rgba(26, 208, 92, 0.45);
}
.player-range::-moz-range-thumb {
  height: 14px;
  width: 14px;
  border-radius: 9999px;
  background: #1ad05c;
  border: none;
  cursor: pointer;
  box-shadow: 0 0 12px rgba(26, 208, 92, 0.45);
}
.pulse-glow {
  animation: glow 2.4s ease-in-out infinite;
}
@keyframes glow {
  0%,
  100% {
    box-shadow: 0 0 36px rgba(26, 208, 92, 0.3);
  }
  50% {
    box-shadow: 0 0 60px rgba(26, 208, 92, 0.55);
  }
}
</style>
