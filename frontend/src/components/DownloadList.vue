<template>
  <div class="mx-auto max-w-4xl px-4 py-8 sm:px-6">
    <!-- Header -->
    <div class="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 class="text-2xl font-bold tracking-tight">
          {{ t('queue.title') }}
        </h1>
      </div>
      <div v-if="queueLength > 0" class="flex flex-wrap gap-2 justify-end">
        <button
          v-if="failedCount > 0"
          class="btn btn-sm h-11 px-4 rounded-full border-white/10 bg-base-100/85 hover:bg-base-100"
          @click="onRetryAllFailed"
        >
          <Icon icon="clarity:refresh-line" class="h-4 w-4 mr-1.5" />
          {{ t('queue.retryAllFailed', { count: failedCount }) }}
        </button>
        <button
          v-if="doneCount > 0"
          class="btn btn-sm h-11 px-4 rounded-full border-white/10 bg-base-100/85 hover:bg-base-100"
          @click="onClearCompleted"
        >
          {{ t('queue.clearCompleted', { count: doneCount }) }}
        </button>
        <button
          class="btn btn-sm h-11 px-5 rounded-full border-white/10 bg-base-100/85 hover:bg-base-100 text-error/70 hover:text-error"
          @click="onClearAll"
          :title="t('queue.clearAll')"
        >
          <Icon icon="clarity:trash-line" class="h-4 w-4 mr-1.5" />
          {{ t('queue.clearAll') }}
        </button>
      </div>
    </div>

    <!-- Filters -->
    <div
      v-if="queueLength > 0"
      class="mb-6 flex flex-wrap gap-2"
      role="tablist"
    >
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

    <!-- Empty state (no queue at all) -->
    <div
      v-if="queueLength === 0"
      class="surface rounded-2xl p-12 flex flex-col items-center text-center"
    >
      <Icon
        icon="clarity:download-line"
        class="h-12 w-12 text-base-content/20 mb-4"
      />
      <p class="text-base-content/50 text-sm">{{ t('queue.empty') }}</p>
      <p class="text-base-content/40 text-xs mt-1">
        {{ t('queue.emptyHint') }}
      </p>
    </div>

    <!-- Filtered empty -->
    <div
      v-else-if="filteredQueue.length === 0"
      class="surface rounded-2xl p-8 text-center text-sm text-base-content/50"
    >
      <p v-if="statusFilter === 'active' && queuedCount > 0">
        {{ t('queue.emptyActiveWithWaiting', { count: queuedCount }) }}
      </p>
      <p v-else>{{ t('queue.emptyFilter') }}</p>
    </div>

    <!-- Queue items -->
    <ul v-else class="space-y-3">
      <li
        v-for="(item, index) in paginatedQueue"
        :key="item.song.song_id || item.song.url || index"
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
              <Icon icon="clarity:music-note-line" class="h-6 w-6" />
            </div>
          </div>

          <!-- Title + status -->
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2 mb-0.5 flex-wrap">
              <span class="font-semibold truncate">{{ item.song.name }}</span>
              <span
                v-if="providerLabel(item)"
                class="badge badge-xs badge-outline opacity-80 shrink-0"
              >
                {{ providerLabel(item) }}
              </span>
              <span :class="statusClass(item)" class="shrink-0">
                {{ statusLabel(item) }}
              </span>
            </div>
            <p class="text-xs text-base-content/60 truncate">
              {{ artistsOf(item.song) }}
            </p>
            <p
              v-if="queueItemState(item) === 'active' && item.message"
              class="text-xs text-base-content/50 mt-0.5 line-clamp-2"
            >
              {{ item.message }}
            </p>
            <p
              v-if="item.song.album_name"
              class="text-xs text-base-content/40 truncate"
            >
              {{ item.song.album_name }}
            </p>
            <p
              v-if="item.isErrored() && item.message"
              class="text-xs text-error/80 mt-1 line-clamp-2"
            >
              {{ item.message }}
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
              <Icon icon="clarity:refresh-line" class="h-4 w-4" />
            </button>
            <a
              v-if="item.isDownloaded()"
              class="icon-btn text-primary hover:bg-primary/10"
              href="javascript:;"
              @click="forceDownload(item.web_download_url)"
              :title="t('queue.saveToDevice')"
            >
              <Icon icon="clarity:download-line" class="h-4 w-4" />
            </a>
            <div
              v-else-if="queueItemState(item) === 'active'"
              class="radial-progress text-primary"
              :style="`--value:${Math.max(0, item.progress)}; --size:2.75rem; --thickness:3px`"
            >
              <span class="text-[10px] font-semibold">
                {{ Math.round(item.progress) }}%
              </span>
            </div>

            <button
              class="icon-btn text-error/70 hover:text-error hover:bg-error/10"
              @click="dm.remove(item.song)"
              :title="t('queue.removeFromQueue')"
            >
              <Icon icon="clarity:trash-line" class="h-4 w-4" />
            </button>
          </div>
        </div>

        <!-- Manual source override for failed tracks -->
        <div
          v-if="item.isErrored() && overrideMode[item.song.song_id]"
          class="mt-3 pt-3 border-t border-white/10 space-y-2"
        >
          <p class="text-[11px] text-base-content/50 leading-snug">
            {{
              overrideMode[item.song.song_id] === 'slskd'
                ? t('queue.slskdOverrideHint')
                : t('queue.youtubeOverrideHint')
            }}
          </p>
          <div class="flex flex-wrap gap-2 items-center">
            <input
              v-model="overrideText[item.song.song_id]"
              type="text"
              class="input input-sm flex-1 min-w-[12rem] rounded-xl bg-base-100/80 font-mono text-xs"
              :placeholder="
                overrideMode[item.song.song_id] === 'slskd'
                  ? t('queue.slskdOverridePlaceholder')
                  : t('queue.overridePlaceholder')
              "
            />
            <button
              class="btn btn-sm btn-primary rounded-full"
              @click="applyOverride(item)"
            >
              {{ t('queue.applyOverride') }}
            </button>
            <button
              class="btn btn-sm btn-ghost rounded-full"
              @click="closeOverride(item.song.song_id)"
            >
              {{ t('common.cancel') }}
            </button>
          </div>
        </div>
        <div
          v-else-if="item.isErrored()"
          class="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-xs"
        >
          <button
            type="button"
            class="text-primary/80 hover:text-primary"
            @click="openOverride(item.song.song_id, 'youtube')"
          >
            {{ t('queue.forceAudio') }}
          </button>
          <button
            type="button"
            class="text-primary/80 hover:text-primary"
            @click="openOverride(item.song.song_id, 'slskd')"
          >
            {{ t('queue.forceSlskd') }}
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
  </div>
</template>

<script setup>
import { ref, computed, watch, reactive, onMounted, onUnmounted } from 'vue'
import { Icon } from '@iconify/vue'
import API from '../model/api'
import {
  useProgressTracker,
  useDownloadManager,
  syncQueueFromServer,
} from '../model/download'
import { parseSlskdOverride } from '../model/slskdOverride'
import { useI18n } from '../i18n'

const PAGE_SIZE = 10

const { downloadQueue, queueVersion } = useProgressTracker()
const dm = useDownloadManager()
const { t } = useI18n()

const statusFilter = ref('active')
const currentPage = ref(1)
const overrideMode = reactive({})
const overrideText = reactive({})

function queueItemState(item) {
  if (item.isErrored()) return 'failed'
  if (item.isDownloaded()) return 'done'
  if (item.isQueued()) return 'queued'
  return 'active'
}

const queueLength = computed(() => {
  queueVersion.value
  return downloadQueue.value.length
})

const doneCount = computed(() => {
  queueVersion.value
  return downloadQueue.value.filter((item) => queueItemState(item) === 'done')
    .length
})

const failedCount = computed(() => {
  queueVersion.value
  return downloadQueue.value.filter((item) => queueItemState(item) === 'failed')
    .length
})

const activeCount = computed(() => {
  queueVersion.value
  return downloadQueue.value.filter((item) => queueItemState(item) === 'active')
    .length
})

const queuedCount = computed(() => {
  queueVersion.value
  return downloadQueue.value.filter((item) => queueItemState(item) === 'queued')
    .length
})

const filterTabs = computed(() => [
  {
    id: 'active',
    label: t('queue.filterActive'),
    count: activeCount.value,
  },
  {
    id: 'queued',
    label: t('queue.filterQueued'),
    count: queuedCount.value,
  },
  {
    id: 'all',
    label: t('queue.filterAll'),
    count: queueLength.value,
  },
  {
    id: 'done',
    label: t('queue.filterDone'),
    count: doneCount.value,
  },
  {
    id: 'failed',
    label: t('queue.filterFailed'),
    count: failedCount.value,
  },
])

const filteredQueue = computed(() => {
  queueVersion.value
  const q = downloadQueue.value
  switch (statusFilter.value) {
    case 'all':
      return q
    case 'active':
      return q.filter((item) => queueItemState(item) === 'active')
    case 'queued':
      return q.filter((item) => queueItemState(item) === 'queued')
    case 'done':
      return q.filter((item) => queueItemState(item) === 'done')
    case 'failed':
      return q.filter((item) => queueItemState(item) === 'failed')
    default:
      return q
  }
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

watch(
  () => filteredQueue.value.length,
  () => {
    if (currentPage.value > totalPages.value && totalPages.value > 0) {
      currentPage.value = totalPages.value
    }
    if (currentPage.value < 1) currentPage.value = 1
  }
)

const pendingCount = computed(() => activeCount.value + queuedCount.value)

watch(queueLength, (len) => {
  if (len === 0) statusFilter.value = 'active'
})

watch(pendingCount, (pending, prev) => {
  if (pending > (prev ?? 0)) {
    statusFilter.value = 'active'
  }
})

let queueRefreshTimer = null

onMounted(() => {
  syncQueueFromServer().catch(() => {})
  queueRefreshTimer = setInterval(() => {
    syncQueueFromServer().catch(() => {})
  }, 2000)
})

onUnmounted(() => {
  if (queueRefreshTimer) {
    clearInterval(queueRefreshTimer)
    queueRefreshTimer = null
  }
})

async function onClearAll() {
  if (!confirm(t('queue.clearAllPrompt'))) return
  await dm.clearAll()
}

async function onClearCompleted() {
  await dm.clearCompleted()
}

function onRetryAllFailed() {
  dm.retryAllFailed()
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
  if (queueItemState(item) === 'active') return 'badge-soft'
  return 'badge-neutral-soft'
}

function statusLabel(item) {
  const state = queueItemState(item)
  if (state === 'active' && item.message) {
    return t('queue.statusActive')
  }
  if (item.isErrored()) return t('queue.statusFailed')
  if (item.isDownloaded()) return t('queue.statusDone')
  if (state === 'active') return t('queue.statusActive')
  return t('queue.statusQueued')
}

function providerLabel(item) {
  const raw = String(item.provider || '').trim()
  if (raw === 'youtube-music') return 'YouTube Music'
  if (raw === 'youtube') return 'YouTube'
  if (raw === 'slskd') return 'slskd'
  return ''
}

function parseYoutubeId(url) {
  const m = String(url || '').match(/(?:v=|youtu\.be\/)([A-Za-z0-9_-]{6,})/)
  return m ? m[1] : null
}

function openOverride(id, mode) {
  overrideMode[id] = mode
  if (overrideText[id] === undefined) {
    overrideText[id] = ''
  }
}

function closeOverride(id) {
  delete overrideMode[id]
}

function applyOverride(item) {
  const id = item.song.song_id
  const mode = overrideMode[id]
  const text = overrideText[id]
  if (mode === 'slskd') {
    const parsed = parseSlskdOverride(text)
    if (!parsed) {
      alert(t('queue.invalidSlskdOverride'))
      return
    }
    closeOverride(id)
    dm.retryWithSlskd(item.song, parsed)
    return
  }
  const videoId = parseYoutubeId(text)
  if (!videoId) {
    alert(t('queue.invalidYouTubeURL'))
    return
  }
  closeOverride(id)
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
