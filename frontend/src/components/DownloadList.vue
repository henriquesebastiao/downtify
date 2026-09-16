<template>
  <div class="mx-auto max-w-4xl px-4 py-8 sm:px-6">
    <!-- Header -->
    <div
      class="mb-6 flex flex-col items-stretch gap-4 sm:flex-row sm:flex-wrap sm:items-end sm:justify-between"
    >
      <div>
        <h1 class="text-2xl font-bold tracking-tight">
          {{ t('queue.title') }}
        </h1>
        <p class="mt-1 text-sm text-base-content/60">
          {{ t('queue.subtitle') }}
        </p>
      </div>
      <!-- Stacked full-width on phones: right-aligned pills wrap one per
           line there, which reads as misplaced rather than as a row. -->
      <div
        v-if="queueLength > 0"
        class="grid grid-cols-1 gap-2 sm:flex sm:flex-wrap sm:justify-end"
      >
        <button
          v-if="failedCount > 0"
          class="btn btn-sm h-11 w-full justify-center px-4 rounded-full border-white/10 bg-base-100/85 hover:bg-base-100 sm:w-auto"
          @click="dm.retryAllFailed()"
        >
          <Icon icon="fa6-solid:arrows-rotate" class="h-4 w-4 mr-1.5" />
          {{ t('queue.retryAllFailed', { count: failedCount }) }}
        </button>
        <button
          v-if="doneCount > 0"
          class="btn btn-sm h-11 w-full justify-center px-4 rounded-full border-white/10 bg-base-100/85 hover:bg-base-100 sm:w-auto"
          @click="dm.clearCompleted()"
        >
          {{ t('queue.clearCompleted', { count: doneCount }) }}
        </button>
        <button
          class="btn btn-sm h-11 w-full justify-center px-5 rounded-full border-white/10 bg-base-100/85 hover:bg-base-100 text-error/70 hover:text-error sm:w-auto"
          @click="onClearAll"
          :title="t('queue.clearAll')"
        >
          <Icon icon="fa6-solid:trash" class="h-4 w-4 mr-1.5" />
          {{ t('queue.clearAll') }}
        </button>
      </div>
    </div>

    <!-- Status filters -->
    <div v-if="queueLength > 0" class="mb-6 flex flex-wrap gap-2">
      <button
        v-for="tab in filterTabs"
        :key="tab.id"
        type="button"
        class="btn btn-sm rounded-full border-white/10"
        :class="
          statusFilter === tab.id
            ? 'btn-primary'
            : 'bg-base-100/85 hover:bg-base-100'
        "
        @click="statusFilter = tab.id"
      >
        {{ tab.label }}
        <span v-if="tab.count > 0" class="ml-1 opacity-80 tabular-nums"
          >({{ tab.count }})</span
        >
      </button>
    </div>

    <!-- Empty state -->
    <div
      v-if="queueLength === 0"
      class="surface rounded-2xl p-12 flex flex-col items-center text-center"
    >
      <Icon
        icon="fa6-solid:download"
        class="h-12 w-12 text-base-content/20 mb-4"
      />
      <p class="text-base-content/50 text-sm">{{ t('queue.empty') }}</p>
      <p class="text-base-content/40 text-xs mt-1">
        {{ t('queue.emptyHint') }}
      </p>
    </div>

    <!-- Filter matched nothing (queue itself isn't empty) -->
    <div
      v-else-if="filteredQueue.length === 0"
      class="surface rounded-2xl p-8 text-center text-sm text-base-content/50"
    >
      {{ t('queue.emptyFilter') }}
    </div>

    <!-- Queue items -->
    <ul v-else class="space-y-3">
      <li
        v-for="(item, index) in paginatedQueue"
        :key="jobKey(item) || index"
        class="surface rounded-2xl p-3 sm:p-4"
      >
        <div class="flex items-center gap-4">
          <!-- Cover -->
          <div class="track-cover h-16 w-16 sm:h-20 sm:w-20 shrink-0">
            <img
              v-if="item.song.cover_url"
              :src="item.song.cover_url"
              :alt="item.song.name"
              class="h-full w-full object-cover"
            />
            <div
              v-else
              class="h-full w-full flex items-center justify-center text-base-content/30"
            >
              <Icon icon="fa6-solid:music" class="h-6 w-6" />
            </div>
          </div>

          <!-- Title + status -->
          <div class="flex-1 min-w-0">
            <div class="flex flex-wrap items-center gap-2 mb-0.5">
              <span class="font-semibold truncate">{{ item.song.name }}</span>
              <span
                v-if="providerOf(item)"
                class="shrink-0 gap-1"
                :class="providerOf(item).badge"
                :title="
                  t('queue.providerTitle', { provider: providerOf(item).label })
                "
              >
                <Icon :icon="providerOf(item).icon" class="h-3 w-3" />
                {{ providerOf(item).label }}
              </span>
              <span :class="statusClass(item)" class="shrink-0">
                {{ item.message || item.web_status }}
              </span>
            </div>
            <p class="text-xs text-base-content/60 truncate">
              {{ artistsOf(item.song) }}
            </p>
            <p
              v-if="item.song.album_name"
              class="text-xs text-base-content/40 truncate"
            >
              {{ item.song.album_name }}
            </p>
          </div>

          <!-- Progress / actions -->
          <div class="flex items-center gap-2 shrink-0">
            <button
              v-if="item.isErrored()"
              class="icon-btn text-primary hover:bg-primary/10"
              :title="t('queue.retry')"
              @click="dm.retry(item.song)"
            >
              <Icon icon="fa6-solid:arrows-rotate" class="h-4 w-4" />
            </button>
            <a
              v-else-if="item.isDownloaded()"
              class="icon-btn text-primary hover:bg-primary/10"
              href="javascript:;"
              @click="forceDownload(item.web_download_url)"
              :title="t('queue.saveToDevice')"
            >
              <Icon icon="fa6-solid:download" class="h-4 w-4" />
            </a>
            <div
              v-else-if="item.progress > 0"
              class="radial-progress text-primary"
              :style="`--value:${item.progress}; --size:2.75rem; --thickness:3px`"
            >
              <span class="text-[10px] font-semibold">
                {{ Math.round(item.progress) }}%
              </span>
            </div>
            <!-- A queued item isn't downloading yet, so no spinner —
                 only jobs actively downloading (progress not reported
                 yet) get one. -->
            <span
              v-else-if="queueItemState(item) === 'active'"
              class="loading loading-spinner loading-sm text-primary"
            />

            <button
              class="icon-btn text-error/70 hover:text-error hover:bg-error/10"
              @click="dm.remove(item.song)"
              :title="t('queue.removeFromQueue')"
            >
              <Icon icon="fa6-solid:trash" class="h-4 w-4" />
            </button>
          </div>
        </div>

        <!-- YouTube URL override for failed tracks -->
        <template v-if="item.isErrored()">
          <div
            v-if="overrideOpen[jobKey(item)]"
            class="mt-3 pt-3 border-t border-white/10 flex flex-wrap items-center gap-2"
          >
            <input
              v-model="overrideUrls[jobKey(item)]"
              type="text"
              class="input input-sm flex-1 min-w-[12rem] rounded-xl bg-base-100/80"
              :placeholder="t('queue.overridePlaceholder')"
            />
            <button
              class="btn btn-sm btn-primary rounded-full"
              @click="applyOverride(item)"
            >
              {{ t('queue.applyOverride') }}
            </button>
            <button
              class="btn btn-sm btn-ghost rounded-full"
              @click="overrideOpen[jobKey(item)] = false"
            >
              {{ t('common.cancel') }}
            </button>
          </div>
          <button
            v-else
            type="button"
            class="mt-2 text-xs text-primary/80 hover:text-primary"
            @click="overrideOpen[jobKey(item)] = true"
          >
            {{ t('queue.forceAudio') }}
          </button>
        </template>
      </li>
    </ul>

    <!-- Pagination -->
    <Pagination
      v-if="totalPages > 1"
      v-model="currentPage"
      :total-pages="totalPages"
    />
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted } from 'vue'
import { Icon } from '@iconify/vue'
import Pagination from './Pagination.vue'
import API from '../model/api'
import {
  useProgressTracker,
  useDownloadManager,
  syncQueueFromServer,
} from '../model/download'
import { useI18n } from '../i18n'

const PAGE_SIZE = 10

const { downloadQueue, queueVersion } = useProgressTracker()
const dm = useDownloadManager()
const { t } = useI18n()

const statusFilter = ref('all')
const currentPage = ref(1)
const overrideOpen = reactive({})
const overrideUrls = reactive({})

function jobKey(item) {
  return String(item.song.song_id || item.song.url || '')
}

function queueItemState(item) {
  if (item.isErrored()) return 'failed'
  if (item.isDownloaded()) return 'done'
  if (item.isQueued()) return 'queued'
  return 'active'
}

// queueVersion is bumped on every in-place item change (status, progress),
// so these counts refresh even when the array itself isn't replaced.
function countState(state) {
  queueVersion.value
  return downloadQueue.value.filter((item) => queueItemState(item) === state)
    .length
}

const queueLength = computed(() => {
  queueVersion.value
  return downloadQueue.value.length
})
const activeCount = computed(() => countState('active'))
const queuedCount = computed(() => countState('queued'))
const doneCount = computed(() => countState('done'))
const failedCount = computed(() => countState('failed'))

const filterTabs = computed(() => [
  { id: 'all', label: t('queue.filterAll'), count: queueLength.value },
  { id: 'active', label: t('queue.filterActive'), count: activeCount.value },
  { id: 'queued', label: t('queue.filterQueued'), count: queuedCount.value },
  { id: 'done', label: t('queue.filterDone'), count: doneCount.value },
  { id: 'failed', label: t('queue.filterFailed'), count: failedCount.value },
])

const filteredQueue = computed(() => {
  queueVersion.value
  if (statusFilter.value === 'all') return downloadQueue.value
  return downloadQueue.value.filter(
    (item) => queueItemState(item) === statusFilter.value
  )
})

const totalPages = computed(() =>
  Math.ceil(filteredQueue.value.length / PAGE_SIZE)
)

const paginatedQueue = computed(() => {
  const start = (currentPage.value - 1) * PAGE_SIZE
  return filteredQueue.value.slice(start, start + PAGE_SIZE)
})

watch(statusFilter, () => {
  currentPage.value = 1
})

// Default to "In progress" as soon as something starts downloading, so
// opening the queue (or a new batch kicking off) lands on what's
// actually happening instead of last time's filter.
watch(activeCount, (curr, prev) => {
  if (curr > (prev ?? 0)) {
    statusFilter.value = 'active'
  }
})

watch(
  () => filteredQueue.value.length,
  () => {
    if (currentPage.value > totalPages.value && totalPages.value > 0) {
      currentPage.value = totalPages.value
    }
  }
)

// Jobs started elsewhere (another tab, Playlist Monitor) only reach this
// client through /api/queue.
onMounted(() => {
  syncQueueFromServer().catch(() => {})
})

async function onClearAll() {
  if (!confirm(t('queue.clearAllPrompt'))) return
  await dm.clearAll()
}

function artistsOf(song) {
  if (Array.isArray(song.artists) && song.artists.length) {
    return song.artists.join(', ')
  }
  return song.artist || t('common.unknownArtist')
}

function statusClass(item) {
  if (item.isErrored()) return 'badge-error-soft'
  if (item.isDownloaded()) return 'badge-soft'
  return 'badge-neutral-soft'
}

// Which audio source served the track (backend job field), styled like
// the source badges on the Playlist Monitor page.
const PROVIDERS = {
  'youtube-music': {
    label: 'YouTube Music',
    badge: 'badge-youtube-music',
    icon: 'fa6-brands:youtube',
  },
  youtube: {
    label: 'YouTube',
    badge: 'badge-youtube',
    icon: 'fa6-brands:youtube',
  },
  slskd: {
    label: 'slskd',
    badge: 'badge-slskd',
    icon: 'fa6-solid:share-nodes',
  },
}

function providerOf(item) {
  return PROVIDERS[String(item.provider || '').trim()] || null
}

function parseYoutubeId(url) {
  const m = String(url || '').match(/(?:v=|youtu\.be\/)([A-Za-z0-9_-]{6,})/)
  return m ? m[1] : null
}

function applyOverride(item) {
  const key = jobKey(item)
  const videoId = parseYoutubeId(overrideUrls[key])
  if (!videoId) {
    alert(t('queue.invalidYouTubeURL'))
    return
  }
  overrideOpen[key] = false
  dm.retryWithAudio(item.song, videoId)
}

function forceDownload(url) {
  const a = document.createElement('a')
  a.href = url
  a.download = API.downloadSaveName(url)
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
}
</script>
