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
        <button
          class="btn btn-sm h-11 px-5 rounded-full border-white/10 bg-base-100/85 hover:bg-base-100"
          @click="refresh"
          :disabled="loading"
        >
          <span v-if="loading" class="loading loading-spinner loading-xs mr-2" />
          <Icon v-else icon="clarity:refresh-line" class="h-4 w-4 mr-2" />
          {{ t('common.refresh') }}
        </button>
      </div>

      <!-- Search bar -->
      <div class="mb-4 relative">
        <Icon
          icon="clarity:search-line"
          class="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-base-content/40 pointer-events-none"
        />
        <input
          v-model="searchInput"
          type="text"
          :placeholder="t('library.search')"
          class="w-full rounded-xl bg-base-100/85 border border-white/10 focus:border-primary/60 focus:outline-none pl-10 pr-4 py-2.5 text-sm"
        />
      </div>

      <!-- Error -->
      <div
        v-if="error"
        class="surface rounded-2xl p-4 mb-4 flex gap-3 items-center text-sm text-error"
      >
        <Icon icon="clarity:exclamation-circle-line" class="h-5 w-5 shrink-0" />
        <span>{{ error }}</span>
      </div>

      <!-- Success toast -->
      <Transition name="toast">
        <div
          v-if="successMsg"
          class="surface rounded-2xl p-4 mb-4 flex gap-3 items-center text-sm text-primary"
        >
          <Icon icon="clarity:check-circle-line" class="h-5 w-5 shrink-0" />
          <span>{{ successMsg }}</span>
        </div>
      </Transition>

      <!-- Loading skeleton -->
      <div v-if="loading && items.length === 0" class="space-y-3">
        <div v-for="n in 5" :key="n" class="skeleton h-16 rounded-2xl" />
      </div>

      <!-- Empty state -->
      <div
        v-else-if="!loading && items.length === 0"
        class="surface rounded-2xl p-12 flex flex-col items-center text-center"
      >
        <Icon
          icon="clarity:list-line"
          class="h-12 w-12 text-base-content/20 mb-4"
        />
        <p class="text-base-content/50 text-sm">{{ t('library.empty') }}</p>
        <p class="text-base-content/40 text-xs mt-1">
          {{ t('library.emptyHint') }}
        </p>
      </div>

      <!-- Track list -->
      <ul v-else class="space-y-2">
        <li
          v-for="item in items"
          :key="item.id"
          class="surface rounded-2xl p-3 sm:p-4 flex items-center gap-3"
        >
          <!-- Icon -->
          <div
            class="h-11 w-11 shrink-0 rounded-xl bg-primary/10 text-primary flex items-center justify-center"
          >
            <Icon icon="clarity:music-note-line" class="h-5 w-5" />
          </div>

          <!-- Info -->
          <div class="flex-1 min-w-0">
            <span class="text-sm font-medium truncate block">
              {{ displayFilename(item.filename) || item.track_spotify_id }}
            </span>
            <span class="text-xs text-base-content/40 flex items-center gap-2 mt-0.5 flex-wrap">
              <span v-if="item.playlist_name" class="text-primary/70">
                <Icon
                  icon="clarity:playlist-line"
                  class="inline h-3 w-3 mr-0.5 align-text-top"
                />{{ item.playlist_name }}
              </span>
              <span v-else class="text-base-content/30">
                {{ t('library.direct') }}
              </span>
              <span>·</span>
              <span>{{ relativeDate(item.downloaded_at) }}</span>
              <span v-if="item.filename" class="text-base-content/30">
                {{ fileExt(item.filename) }}
              </span>
            </span>
          </div>

          <!-- Delete -->
          <button
            class="icon-btn text-error/70 hover:text-error hover:bg-error/10 shrink-0"
            :disabled="deleting[item.id] === true"
            @click="onDelete(item)"
            :title="t('library.deleteFile')"
          >
            <span
              v-if="deleting[item.id] === true"
              class="loading loading-spinner loading-xs"
            />
            <Icon v-else icon="clarity:trash-line" class="h-4 w-4" />
          </button>
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
          @click="goToPage(currentPage - 1)"
          :title="t('common.previousPage')"
        >
          <Icon icon="clarity:angle-line" class="h-4 w-4 rotate-[-90deg]" />
        </button>
        <button
          v-for="page in visiblePages"
          :key="page"
          class="h-10 min-w-[2.5rem] rounded-full px-3 text-sm font-medium transition-colors"
          :class="
            page === currentPage
              ? 'bg-primary text-primary-content shadow-glow-sm'
              : 'text-base-content/70 hover:text-base-content hover:bg-white/10'
          "
          @click="goToPage(page)"
        >
          {{ page }}
        </button>
        <button
          class="icon-btn"
          :disabled="currentPage === totalPages"
          @click="goToPage(currentPage + 1)"
          :title="t('common.nextPage')"
        >
          <Icon icon="clarity:angle-line" class="h-4 w-4 rotate-90" />
        </button>
      </nav>

      <!-- Count footer -->
      <p
        v-if="total > 0"
        class="mt-6 text-xs text-base-content/40 text-center"
      >
        {{
          total === 1
            ? t('library.countOne', { count: total })
            : t('library.countMany', { count: total })
        }}
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { Icon } from '@iconify/vue'
import Navbar from '/src/components/Navbar.vue'
import Settings from '/src/components/Settings.vue'
import API from '/src/model/api'
import { useI18n } from '/src/i18n'

const PAGE_SIZE = 20

const { t } = useI18n()

const items = ref([])
const total = ref(0)
const totalPages = ref(1)
const currentPage = ref(1)
const searchInput = ref('')
const loading = ref(false)
const error = ref('')
const successMsg = ref('')
const deleting = ref({})

let searchTimeout = null

const visiblePages = computed(() => {
  const pages = []
  const max = totalPages.value
  const cur = currentPage.value
  const delta = 2
  for (let i = Math.max(1, cur - delta); i <= Math.min(max, cur + delta); i++) {
    pages.push(i)
  }
  return pages
})

watch(searchInput, (val) => {
  clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => {
    currentPage.value = 1
    loadTruth()
  }, 300)
})

async function loadTruth() {
  loading.value = true
  error.value = ''
  try {
    const res = await API.listTruth(searchInput.value, currentPage.value, PAGE_SIZE)
    items.value = res.data.items || []
    total.value = res.data.total || 0
    totalPages.value = res.data.pages || 1
  } catch {
    error.value = t('library.failedLoad')
  } finally {
    loading.value = false
  }
}

function refresh() {
  loadTruth()
}

function goToPage(page) {
  currentPage.value = page
  loadTruth()
}

async function onDelete(item) {
  if (!confirm(t('library.deletePrompt'))) return
  deleting.value = { ...deleting.value, [item.id]: true }
  try {
    await API.deleteTruth(item.id)
    items.value = items.value.filter((i) => i.id !== item.id)
    total.value = Math.max(0, total.value - 1)
    showSuccess(t('library.deleteSuccess'))
  } catch {
    error.value = t('library.failedDelete')
  } finally {
    deleting.value = { ...deleting.value, [item.id]: false }
  }
}

function showSuccess(msg) {
  successMsg.value = msg
  setTimeout(() => {
    successMsg.value = ''
  }, 3000)
}

function displayFilename(filename) {
  if (!filename) return ''
  const slash = filename.lastIndexOf('/')
  const name = slash >= 0 ? filename.slice(slash + 1) : filename
  const dot = name.lastIndexOf('.')
  return dot > 0 ? name.slice(0, dot) : name
}

function fileExt(filename) {
  if (!filename) return ''
  const dot = filename.lastIndexOf('.')
  return dot > 0 ? filename.slice(dot + 1).toUpperCase() : ''
}

function relativeDate(isoStr) {
  if (!isoStr) return ''
  try {
    const d = new Date(isoStr)
    const diff = (Date.now() - d.getTime()) / 1000
    if (diff < 60) return 'just now'
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
    if (diff < 2592000) return `${Math.floor(diff / 86400)}d ago`
    return d.toLocaleDateString()
  } catch {
    return isoStr
  }
}

onMounted(loadTruth)
</script>

<style scoped>
.toast-enter-active,
.toast-leave-active {
  transition: opacity 0.3s, transform 0.3s;
}
.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}
</style>
