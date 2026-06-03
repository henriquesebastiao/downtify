<template>
  <div class="min-h-screen">
    <Navbar />
    <Settings />

    <div class="mx-auto max-w-4xl px-4 py-8 sm:px-6">
      <!-- Header -->
      <div class="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 class="text-2xl font-bold tracking-tight">
            {{ t('library.title') }}
          </h1>
          <p class="mt-1 text-sm text-base-content/60">
            {{ t('library.subtitle') }}
          </p>
        </div>
        <div class="flex flex-wrap items-center gap-2 justify-end">
          <button
            v-if="selectedCount > 0"
            class="btn btn-error btn-sm h-11 px-5 rounded-full btn-outline"
            :disabled="batchDeleting"
            @click="onDeleteSelected"
          >
            <span
              v-if="batchDeleting"
              class="loading loading-spinner loading-xs mr-2"
            />
            {{ t('library.deleteSelected', { count: selectedCount }) }}
          </button>
          <button
            v-if="filteredFiles.length > 0"
            class="btn btn-primary btn-sm h-11 px-5 rounded-full"
            @click="playAll"
            :title="t('library.play')"
          >
            <Icon icon="clarity:play-line" class="h-4 w-4 mr-1.5" />
            {{ t('library.play') }}
          </button>
          <button
            class="btn btn-sm h-11 px-5 rounded-full border-white/10 bg-base-100/85 hover:bg-base-100"
            @click="refresh"
            :disabled="loading"
          >
            <span
              v-if="loading"
              class="loading loading-spinner loading-xs mr-2"
            />
            <Icon v-else icon="clarity:refresh-line" class="h-4 w-4 mr-2" />
            {{ t('common.refresh') }}
          </button>
        </div>
      </div>

      <!-- Library search (local only; navbar search is hidden on this page) -->
      <div class="relative mb-6">
        <Icon
          icon="clarity:search-line"
          class="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-base-content/40 pointer-events-none"
        />
        <input
          v-model="libraryFilterQuery"
          type="search"
          class="input input-bordered w-full pl-10 pr-10 h-11 rounded-full bg-base-100/85 border-white/10"
          :placeholder="t('library.searchPlaceholder')"
          autocomplete="off"
        />
        <button
          v-if="libraryFilterQuery"
          type="button"
          class="absolute right-2 top-1/2 -translate-y-1/2 icon-btn h-8 w-8"
          :title="t('common.close')"
          @click="clearLibraryFilter"
        >
          <Icon icon="clarity:times-line" class="h-4 w-4" />
        </button>
      </div>

      <!-- Playlist filter + bulk selection -->
      <div
        v-if="files.length > 0"
        class="mb-4 flex flex-wrap items-center gap-2"
      >
        <label class="text-xs text-base-content/50 shrink-0">
          {{ t('library.filterByPlaylist') }}
        </label>
        <select
          v-model="playlistFilter"
          class="select select-bordered select-sm rounded-full bg-base-100/85 border-white/10 max-w-xs"
        >
          <option value="">{{ t('library.filterAllPlaylists') }}</option>
          <option v-for="pl in playlistNames" :key="pl" :value="pl">
            {{ pl }}
          </option>
        </select>
        <button
          v-if="playlistFilter"
          type="button"
          class="btn btn-error btn-sm rounded-full btn-outline"
          :disabled="playlistDeleting"
          @click="onDeletePlaylist"
        >
          <span
            v-if="playlistDeleting"
            class="loading loading-spinner loading-xs mr-2"
          />
          {{ t('library.deletePlaylist') }}
        </button>
        <span class="flex-1" />
        <button
          v-if="filteredFiles.length > 0"
          type="button"
          class="btn btn-ghost btn-xs rounded-full"
          @click="toggleSelectAllFiltered"
        >
          {{
            allFilteredSelected
              ? t('library.clearSelection')
              : t('library.selectAllFilteredCount', {
                  count: filteredFiles.length,
                })
          }}
        </button>
      </div>

      <!-- Error -->
      <div
        v-if="error"
        class="surface rounded-2xl p-4 mb-4 flex gap-3 items-center text-sm text-error"
      >
        <Icon icon="clarity:exclamation-circle-line" class="h-5 w-5 shrink-0" />
        <span>{{ error }}</span>
      </div>

      <!-- Loading skeleton -->
      <div v-if="loading && files.length === 0" class="space-y-3">
        <div v-for="n in 4" :key="n" class="skeleton h-16 rounded-2xl" />
      </div>

      <!-- Empty library -->
      <div
        v-else-if="files.length === 0"
        class="surface rounded-2xl p-12 flex flex-col items-center text-center"
      >
        <Icon
          icon="clarity:library-line"
          class="h-12 w-12 text-base-content/20 mb-4"
        />
        <p class="text-base-content/50 text-sm">{{ t('library.empty') }}</p>
        <p class="text-base-content/40 text-xs mt-1">
          {{ t('library.emptyHint') }}
        </p>
      </div>

      <!-- No search matches -->
      <div
        v-else-if="filteredFiles.length === 0"
        class="surface rounded-2xl p-12 flex flex-col items-center text-center"
      >
        <Icon
          icon="clarity:search-line"
          class="h-12 w-12 text-base-content/20 mb-4"
        />
        <p class="text-base-content/50 text-sm">
          {{ t('library.searchNoResults') }}
        </p>
      </div>

      <!-- File list -->
      <ul v-else class="space-y-2">
        <li
          v-for="entry in paginatedFiles"
          :key="entry.file"
          class="surface rounded-2xl p-3 sm:p-4 flex items-center gap-3"
        >
          <input
            type="checkbox"
            class="checkbox checkbox-sm checkbox-primary shrink-0"
            :checked="selectedFiles.has(entry.file)"
            @change="toggleSelect(entry.file)"
          />
          <!-- Cover thumb -->
          <div
            class="relative h-11 w-11 shrink-0 rounded-xl bg-primary/10 text-primary flex items-center justify-center overflow-hidden"
          >
            <img
              v-if="!coverFailed[entry.file]"
              :src="coverUrlFor(entry.file)"
              :alt="entry.title"
              class="absolute inset-0 h-full w-full object-cover"
              loading="lazy"
              @error="markCoverFailed(entry.file)"
            />
            <Icon v-else icon="clarity:music-note-line" class="h-5 w-5" />
          </div>

          <!-- Title / path -->
          <div class="flex-1 min-w-0">
            <span class="text-sm font-medium truncate block">{{
              entry.title
            }}</span>
            <p
              v-if="entry.artist"
              class="text-xs text-base-content/60 truncate"
            >
              {{ entry.artist }}
            </p>
            <p v-if="entry.album" class="text-xs text-base-content/50 truncate">
              {{ entry.album }}
            </p>
            <div
              v-if="entry.playlists?.length"
              class="flex flex-wrap gap-1 mt-1"
            >
              <span
                v-for="pl in entry.playlists"
                :key="pl"
                class="badge badge-xs border-primary/30 bg-primary/10 text-primary max-w-full truncate"
                :title="pl"
              >
                {{ pl }}
              </span>
            </div>
            <span class="text-xs text-base-content/40">
              <span v-if="folderOf(entry.file)" class="mr-2 text-primary/70">
                <Icon
                  icon="clarity:folder-line"
                  class="inline h-3 w-3 mr-0.5 align-text-top"
                />{{ folderOf(entry.file) }}
              </span>
              {{ formatExt(entry.file) }}
            </span>
          </div>

          <!-- Actions -->
          <div class="flex items-center gap-1 shrink-0">
            <button
              class="icon-btn text-primary hover:bg-primary/10"
              @click="playEntry(entry)"
              :title="t('library.play')"
            >
              <Icon icon="clarity:play-line" class="h-4 w-4" />
            </button>
            <a
              class="icon-btn"
              :href="API.downloadFileURL(entry.file)"
              :download="API.downloadSaveName(entry.file)"
              :title="t('library.downloadToDevice')"
            >
              <Icon icon="clarity:download-line" class="h-4 w-4" />
            </a>
            <button
              class="icon-btn text-error/70 hover:text-error hover:bg-error/10"
              :disabled="deleting[entry.file] === true"
              @click="onDelete(entry.file)"
              :title="t('library.deleteFile')"
            >
              <span
                v-if="deleting[entry.file] === true"
                class="loading loading-spinner loading-xs"
              />
              <Icon v-else icon="clarity:trash-line" class="h-4 w-4" />
            </button>
          </div>
        </li>
      </ul>

      <LibraryPagination
        v-if="filteredFiles.length > 0"
        :current-page="currentPage"
        :total-pages="totalPages"
        :total-items="filteredFiles.length"
        :page-size="pageSize"
        @update:current-page="currentPage = $event"
        @update:page-size="onPageSizeChange"
      />

      <!-- Count footer -->
      <p
        v-if="files.length > 0"
        class="mt-4 text-xs text-base-content/40 text-center"
      >
        <template v-if="libraryFilterQuery.trim()">
          {{
            t('library.filteredCount', {
              shown: filteredFiles.length,
              total: files.length,
            })
          }}
        </template>
        <template v-else>
          {{
            files.length === 1
              ? t('library.countOne', { count: files.length })
              : t('library.countMany', { count: files.length })
          }}
        </template>
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { Icon } from '@iconify/vue'
import { useRouter } from 'vue-router'
import Navbar from '/src/components/Navbar.vue'
import Settings from '/src/components/Settings.vue'
import LibraryPagination from '/src/components/LibraryPagination.vue'
import API from '/src/model/api'
import { useI18n } from '/src/i18n'
import {
  useLibraryFilter,
  libraryEntryMatchesQuery,
} from '/src/model/libraryFilter'
import { normalizeLibraryEntry, usePlayer } from '/src/model/player'

const PAGE_SIZE_STORAGE_KEY = 'downtify.libraryPageSize'
const DEFAULT_PAGE_SIZE = 25

const { t } = useI18n()
const player = usePlayer()
const router = useRouter()
const { libraryFilterQuery, clearLibraryFilter } = useLibraryFilter()

const files = ref([])
const loading = ref(false)
const error = ref('')
const deleting = ref({})
const batchDeleting = ref(false)
const playlistDeleting = ref(false)
const coverFailed = ref({})
const currentPage = ref(1)
const pageSize = ref(readPageSize())
const selectedFiles = ref(new Set())
const playlistFilter = ref('')

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
  const query = libraryFilterQuery.value
  if (!String(query || '').trim()) return list
  return list.filter((entry) => libraryEntryMatchesQuery(entry, query))
})

const selectedCount = computed(() => selectedFiles.value.size)

const allFilteredSelected = computed(() => {
  if (!filteredFiles.value.length) return false
  return filteredFiles.value.every((e) => selectedFiles.value.has(e.file))
})

const totalPages = computed(() =>
  Math.max(1, Math.ceil(filteredFiles.value.length / pageSize.value))
)

const paginatedFiles = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  return filteredFiles.value.slice(start, start + pageSize.value)
})

watch([filteredFiles, pageSize], () => {
  if (currentPage.value > totalPages.value) {
    currentPage.value = totalPages.value
  }
})

watch(libraryFilterQuery, () => {
  currentPage.value = 1
})

watch(playlistFilter, () => {
  currentPage.value = 1
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

function removeFilesFromList(paths) {
  const gone = new Set(paths)
  files.value = files.value.filter((entry) => !gone.has(entry.file))
  const next = new Set(selectedFiles.value)
  for (const p of gone) next.delete(p)
  selectedFiles.value = next
}

function readPageSize() {
  try {
    const raw = parseInt(localStorage.getItem(PAGE_SIZE_STORAGE_KEY) || '', 10)
    if ([10, 25, 50, 100].includes(raw)) return raw
  } catch {
    /* ignore */
  }
  return DEFAULT_PAGE_SIZE
}

function onPageSizeChange(size) {
  pageSize.value = size
  currentPage.value = 1
  try {
    localStorage.setItem(PAGE_SIZE_STORAGE_KEY, String(size))
  } catch {
    /* ignore */
  }
}

function coverUrlFor(file) {
  return API.coverFileURL(file)
}

function markCoverFailed(file) {
  coverFailed.value = { ...coverFailed.value, [file]: true }
}

async function refresh() {
  loading.value = true
  error.value = ''
  try {
    const res = await API.listDownloads(true)
    files.value = (res.data || []).map(normalizeLibraryEntry)
  } catch {
    error.value = t('library.failedLoad')
  } finally {
    loading.value = false
  }
}

async function onDelete(file) {
  if (!confirm(t('library.deletePrompt', { file }))) return
  deleting.value = { ...deleting.value, [file]: true }
  error.value = ''
  try {
    const res = await API.deleteDownload(file)
    if (res.data?.deleted === false) {
      error.value = res.data?.error || t('library.failedDelete', { file })
      return
    }
    removeFilesFromList([file])
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
  try {
    const res = await API.deleteDownloadsBatch(paths)
    const deleted = res.data?.deleted || []
    const failed = res.data?.failed || []
    removeFilesFromList(deleted)
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

async function onDeletePlaylist() {
  const name = String(playlistFilter.value || '').trim()
  if (!name) return
  if (!confirm(t('library.deletePlaylistPrompt', { name }))) return
  playlistDeleting.value = true
  error.value = ''
  try {
    const res = await API.deleteLibraryPlaylist(name)
    const count = res.data?.deleted_count ?? 0
    files.value = files.value.filter(
      (entry) => !(entry.playlists || []).includes(name)
    )
    selectedFiles.value = new Set()
    playlistFilter.value = ''
    if ((res.data?.failed_count || 0) > 0) {
      error.value = t('library.batchDeletePartial', {
        ok: count,
        failed: res.data.failed_count,
      })
    }
  } catch (err) {
    const detail = err?.response?.data?.detail
    error.value =
      typeof detail === 'string' && detail
        ? detail
        : t('library.playlistDeleteFailed', { name })
  } finally {
    playlistDeleting.value = false
  }
}

function formatExt(file) {
  const dot = file.lastIndexOf('.')
  return dot > 0 ? file.slice(dot + 1).toUpperCase() : ''
}

function folderOf(file) {
  const slash = file.lastIndexOf('/')
  return slash >= 0 ? file.slice(0, slash) : ''
}

function playEntry(entry) {
  const index = filteredFiles.value.findIndex((row) => row.file === entry.file)
  if (index < 0) return
  player.setPlaylist(filteredFiles.value, { startIndex: index })
  router.push({ name: 'Player' })
}

function playAll() {
  if (!filteredFiles.value.length) return
  player.setPlaylist(filteredFiles.value, { startIndex: 0 })
  router.push({ name: 'Player' })
}

onMounted(refresh)

onUnmounted(() => {
  clearLibraryFilter()
})
</script>
