<template>
  <div class="min-h-screen">
    <Navbar />
    <Settings />

    <div class="mx-auto max-w-4xl px-4 py-8 sm:px-6">
      <!-- Header -->
      <div class="mb-8 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 class="text-2xl font-bold tracking-tight">
            {{ t('library.title') }}
          </h1>
          <p class="mt-1 text-sm text-base-content/60">
            {{ t('library.subtitle') }}
          </p>
        </div>
        <div class="flex items-center gap-2">
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

      <!-- Filter by playlist / artist / album -->
      <div v-if="hasFilterableGroups" class="mb-6">
        <label
          class="block text-xs font-semibold uppercase tracking-wider text-base-content/50 mb-1.5"
        >
          {{ t('library.filterBy') }}
        </label>
        <select
          v-model="selectedGroup"
          class="select select-sm w-full sm:w-64 rounded-xl bg-base-100/85 border border-white/10 focus:border-primary/60"
        >
          <option :value="null">
            {{ t('player.allSongs', { count: files.length }) }}
          </option>
          <optgroup
            v-if="playlists.length > 0"
            :label="t('player.playlistsGroup')"
          >
            <option
              v-for="pl in playlists"
              :key="'playlist-' + pl.name"
              :value="{ type: 'playlist', name: pl.name }"
            >
              {{ pl.name }} ({{ pl.count }})
            </option>
          </optgroup>
          <optgroup
            v-if="artistGroups.length > 0"
            :label="t('player.artistsGroup')"
          >
            <option
              v-for="a in artistGroups"
              :key="'artist-' + a.name"
              :value="{ type: 'artist', name: a.name }"
            >
              {{ a.name }} ({{ a.count }})
            </option>
          </optgroup>
          <optgroup
            v-if="albumGroups.length > 0"
            :label="t('player.albumsGroup')"
          >
            <option
              v-for="al in albumGroups"
              :key="'album-' + al.name"
              :value="{ type: 'album', name: al.name }"
            >
              {{ al.name }} ({{ al.count }})
            </option>
          </optgroup>
        </select>
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

      <!-- Empty state -->
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

      <!-- Filter matched nothing (library itself isn't empty) -->
      <div
        v-else-if="filteredFiles.length === 0"
        class="surface rounded-2xl p-12 flex flex-col items-center text-center"
      >
        <Icon
          icon="clarity:search-line"
          class="h-12 w-12 text-base-content/20 mb-4"
        />
        <p class="text-base-content/50 text-sm">
          {{ t('library.filterEmpty') }}
        </p>
        <button
          class="mt-3 text-xs text-primary hover:underline"
          @click="selectedGroup = null"
        >
          {{ t('library.clearFilter') }}
        </button>
      </div>

      <!-- Selection toolbar -->
      <div v-else class="flex flex-wrap items-center gap-3 mb-3 text-sm">
        <label
          class="flex items-center gap-2 cursor-pointer select-none text-base-content/70"
        >
          <input
            type="checkbox"
            class="checkbox checkbox-sm checkbox-primary"
            :checked="allFilteredSelected"
            :disabled="bulkDeleting"
            @change="toggleSelectAllFiltered"
          />
          {{
            allFilteredSelected
              ? t('library.deselectAll')
              : t('library.selectAll', { count: filteredFiles.length })
          }}
        </label>

        <div
          v-if="selectedFiles.size > 0"
          class="flex items-center gap-2 ml-auto"
        >
          <span class="text-base-content/50">
            {{ t('library.selectedCount', { count: selectedFiles.size }) }}
          </span>
          <button
            type="button"
            class="btn btn-sm h-9 px-4 rounded-full border-error/30 bg-error/10 text-error hover:bg-error/20"
            :disabled="bulkDeleting"
            @click="onBulkDelete"
          >
            <span
              v-if="bulkDeleting"
              class="loading loading-spinner loading-xs mr-1.5"
            />
            <Icon v-else icon="clarity:trash-line" class="h-4 w-4 mr-1.5" />
            {{ t('library.deleteSelected') }}
          </button>
          <button
            type="button"
            class="icon-btn"
            :disabled="bulkDeleting"
            @click="clearSelection"
            :title="t('library.clearSelection')"
          >
            <Icon icon="clarity:close-line" class="h-4 w-4" />
          </button>
        </div>
      </div>

      <!-- File list -->
      <ul v-if="filteredFiles.length > 0" class="space-y-2">
        <li
          v-for="file in paginatedFiles"
          :key="file"
          class="surface rounded-2xl p-3 sm:p-4 flex items-center gap-3"
          :class="{ 'ring-1 ring-primary/40': selectedFiles.has(file) }"
        >
          <input
            type="checkbox"
            class="checkbox checkbox-sm checkbox-primary shrink-0"
            :checked="selectedFiles.has(file)"
            :disabled="bulkDeleting"
            @change="toggleFile(file)"
            :aria-label="t('library.selectFile', { file: displayName(file) })"
          />

          <!-- Cover thumb -->
          <div
            class="relative h-11 w-11 shrink-0 rounded-xl bg-primary/10 text-primary flex items-center justify-center overflow-hidden"
          >
            <img
              v-if="!coverFailed[file]"
              :src="coverUrlFor(file)"
              :alt="file"
              class="absolute inset-0 h-full w-full object-cover"
              loading="lazy"
              @error="markCoverFailed(file)"
            />
            <Icon v-else icon="clarity:music-note-line" class="h-5 w-5" />
          </div>

          <!-- Filename -->
          <div class="flex-1 min-w-0">
            <span class="text-sm font-medium truncate block">{{
              displayName(file)
            }}</span>
            <span class="text-xs text-base-content/40">
              <span v-if="folderOf(file)" class="mr-2 text-primary/70">
                <Icon
                  icon="clarity:folder-line"
                  class="inline h-3 w-3 mr-0.5 align-text-top"
                />{{ folderOf(file) }}
              </span>
              {{ formatExt(file) }}
            </span>
          </div>

          <!-- Actions -->
          <div class="flex items-center gap-1 shrink-0">
            <button
              class="icon-btn text-primary hover:bg-primary/10"
              @click="playFile(file)"
              :title="t('library.play')"
            >
              <Icon icon="clarity:play-line" class="h-4 w-4" />
            </button>
            <a
              class="icon-btn"
              :href="API.downloadFileURL(file)"
              download
              :title="t('library.downloadToDevice')"
            >
              <Icon icon="clarity:download-line" class="h-4 w-4" />
            </a>
            <button
              class="icon-btn text-error/70 hover:text-error hover:bg-error/10"
              :disabled="deleting[file] === true || bulkDeleting"
              @click="onDelete(file)"
              :title="t('library.deleteFile')"
            >
              <span
                v-if="deleting[file] === true"
                class="loading loading-spinner loading-xs"
              />
              <Icon v-else icon="clarity:trash-line" class="h-4 w-4" />
            </button>
          </div>
        </li>
      </ul>

      <!-- Pagination -->
      <nav
        v-if="totalPages > 1"
        class="mt-8 flex items-center justify-center gap-1 flex-wrap"
      >
        <button
          class="icon-btn"
          :disabled="currentPage === 1"
          @click="currentPage--"
          :title="t('common.previousPage')"
        >
          <Icon icon="clarity:angle-line" class="h-4 w-4 rotate-[-90deg]" />
        </button>
        <button
          v-for="page in totalPages"
          :key="page"
          class="h-10 min-w-[2.5rem] rounded-full px-3 text-sm font-medium transition-colors"
          :class="
            page === currentPage
              ? 'bg-primary text-primary-content shadow-glow-sm'
              : 'text-base-content/70 hover:text-base-content hover:bg-white/10'
          "
          @click="currentPage = page"
        >
          {{ page }}
        </button>
        <button
          class="icon-btn"
          :disabled="currentPage === totalPages"
          @click="currentPage++"
          :title="t('common.nextPage')"
        >
          <Icon icon="clarity:angle-line" class="h-4 w-4 rotate-90" />
        </button>
      </nav>

      <!-- Count footer -->
      <p
        v-if="filteredFiles.length > 0"
        class="mt-6 text-xs text-base-content/40 text-center"
      >
        {{
          filteredFiles.length === 1
            ? t('library.countOne', { count: filteredFiles.length })
            : t('library.countMany', { count: filteredFiles.length })
        }}
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { Icon } from '@iconify/vue'
import { useRouter } from 'vue-router'
import Navbar from '/src/components/Navbar.vue'
import Settings from '/src/components/Settings.vue'
import API from '/src/model/api'
import { useI18n } from '/src/i18n'
import { usePlayer } from '/src/model/player'
import { buildGroups, filesForGroup } from '/src/model/trackGroups'

const PAGE_SIZE = 10

const { t } = useI18n()
const player = usePlayer()
const router = useRouter()

const files = ref([])
const tracks = ref([]) // [{ file, artist, album }] — from GET /tracks
const playlists = ref([])
// null = "All Songs"; otherwise { type: 'playlist' | 'artist' | 'album', name }
const selectedGroup = ref(null)
const loading = ref(false)
const error = ref('')
const deleting = ref({})
const coverFailed = ref({})
const currentPage = ref(1)
const selectedFiles = ref(new Set())
const bulkDeleting = ref(false)

const artistGroups = computed(() => buildGroups(tracks.value, 'artist'))
const albumGroups = computed(() => buildGroups(tracks.value, 'album'))

const hasFilterableGroups = computed(
  () =>
    playlists.value.length > 0 ||
    artistGroups.value.length > 0 ||
    albumGroups.value.length > 0
)

const filteredFiles = computed(() =>
  filesForGroup(selectedGroup.value, {
    files: files.value,
    playlists: playlists.value,
    artistGroups: artistGroups.value,
    albumGroups: albumGroups.value,
  })
)

const totalPages = computed(() =>
  Math.ceil(filteredFiles.value.length / PAGE_SIZE)
)

const paginatedFiles = computed(() => {
  const start = (currentPage.value - 1) * PAGE_SIZE
  return filteredFiles.value.slice(start, start + PAGE_SIZE)
})

const allFilteredSelected = computed(
  () =>
    filteredFiles.value.length > 0 &&
    filteredFiles.value.every((f) => selectedFiles.value.has(f))
)

watch(filteredFiles, () => {
  currentPage.value = 1
  // The filtered set just changed shape (filter switched, or a file was
  // deleted) — a selection made against the previous set no longer
  // means the same thing, so don't carry it over silently.
  clearSelection()
})

function toggleFile(file) {
  const next = new Set(selectedFiles.value)
  if (next.has(file)) next.delete(file)
  else next.add(file)
  selectedFiles.value = next
}

function toggleSelectAllFiltered() {
  selectedFiles.value = allFilteredSelected.value
    ? new Set()
    : new Set(filteredFiles.value)
}

function clearSelection() {
  selectedFiles.value = new Set()
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
    const [tracksRes, playlistsRes] = await Promise.all([
      API.listTracks(),
      API.listPlaylists(),
    ])
    tracks.value = tracksRes.data || []
    files.value = tracks.value.map((tr) => tr.file)
    playlists.value = playlistsRes.data || []
  } catch {
    error.value = t('library.failedLoad')
  } finally {
    loading.value = false
  }
}

async function onDelete(file) {
  if (!confirm(t('library.deletePrompt', { file }))) return
  deleting.value = { ...deleting.value, [file]: true }
  try {
    await API.deleteDownload(file)
    files.value = files.value.filter((f) => f !== file)
    tracks.value = tracks.value.filter((tr) => tr.file !== file)
  } catch {
    error.value = t('library.failedDelete', { file })
  } finally {
    deleting.value = { ...deleting.value, [file]: false }
  }
}

async function onBulkDelete() {
  const targets = Array.from(selectedFiles.value)
  if (!targets.length) return
  if (!confirm(t('library.bulkDeletePrompt', { count: targets.length }))) {
    return
  }
  bulkDeleting.value = true
  error.value = ''
  try {
    const res = await API.deleteDownloadsBatch(targets)
    const results = res.data.results || {}
    const removed = new Set(
      Object.keys(results).filter((f) => results[f].deleted)
    )
    files.value = files.value.filter((f) => !removed.has(f))
    tracks.value = tracks.value.filter((tr) => !removed.has(tr.file))
    const failedCount = res.data.failed_count || 0
    if (failedCount > 0) {
      error.value = t('library.bulkDeletePartialError', {
        count: failedCount,
      })
    }
  } catch {
    error.value = t('library.bulkDeleteFailed')
  } finally {
    clearSelection()
    bulkDeleting.value = false
  }
}

function formatExt(file) {
  const dot = file.lastIndexOf('.')
  return dot > 0 ? file.slice(dot + 1).toUpperCase() : ''
}

function displayName(file) {
  const slash = file.lastIndexOf('/')
  return slash >= 0 ? file.slice(slash + 1) : file
}

function folderOf(file) {
  const slash = file.lastIndexOf('/')
  return slash >= 0 ? file.slice(0, slash) : ''
}

function playFile(file) {
  const index = filteredFiles.value.indexOf(file)
  player.setPlaylist(filteredFiles.value, { startIndex: Math.max(0, index) })
  router.push({ name: 'Player' })
}

function playAll() {
  if (!filteredFiles.value.length) return
  player.setPlaylist(filteredFiles.value, { startIndex: 0 })
  router.push({ name: 'Player' })
}

onMounted(refresh)
</script>
