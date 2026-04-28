<template>
  <div class="min-h-screen">
    <Navbar />
    <Settings />

    <div class="mx-auto max-w-4xl px-4 py-8 sm:px-6">
      <!-- Header -->
      <div class="mb-8 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 class="text-2xl font-bold tracking-tight">Library</h1>
          <p class="mt-1 text-sm text-base-content/60">
            Music you've already downloaded. Listen, re-download or remove.
          </p>
        </div>
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
          Refresh
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

      <!-- Empty state -->
      <div
        v-else-if="files.length === 0"
        class="surface rounded-2xl p-12 flex flex-col items-center text-center"
      >
        <Icon
          icon="clarity:library-line"
          class="h-12 w-12 text-base-content/20 mb-4"
        />
        <p class="text-base-content/50 text-sm">No downloads yet.</p>
        <p class="text-base-content/40 text-xs mt-1">
          Find a song to start filling your library.
        </p>
      </div>

      <!-- File list -->
      <ul v-else class="space-y-2">
        <li
          v-for="file in files"
          :key="file"
          class="surface rounded-2xl p-3 sm:p-4 flex items-center gap-3"
        >
          <!-- Audio icon thumb -->
          <div
            class="h-11 w-11 shrink-0 rounded-xl bg-primary/10 text-primary flex items-center justify-center"
          >
            <Icon icon="clarity:music-note-line" class="h-5 w-5" />
          </div>

          <!-- Filename -->
          <div class="flex-1 min-w-0">
            <span class="text-sm font-medium truncate block">{{ file }}</span>
            <span class="text-xs text-base-content/40">
              {{ formatExt(file) }}
            </span>
          </div>

          <!-- Actions -->
          <div class="flex items-center gap-1 shrink-0">
            <a
              class="icon-btn"
              :href="`/downloads/${encodeURIComponent(file)}`"
              download
              title="Download to device"
            >
              <Icon icon="clarity:download-line" class="h-4 w-4" />
            </a>
            <button
              class="icon-btn text-error/70 hover:text-error hover:bg-error/10"
              :disabled="deleting[file] === true"
              @click="onDelete(file)"
              title="Delete file"
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

      <!-- Count footer -->
      <p
        v-if="files.length > 0"
        class="mt-6 text-xs text-base-content/40 text-center"
      >
        {{ files.length }} file{{ files.length !== 1 ? 's' : '' }} in your
        library
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { Icon } from '@iconify/vue'
import Navbar from '/src/components/Navbar.vue'
import Settings from '/src/components/Settings.vue'
import API from '/src/model/api'

const files = ref([])
const loading = ref(false)
const error = ref('')
const deleting = ref({})

async function refresh() {
  loading.value = true
  error.value = ''
  try {
    const res = await API.listDownloads()
    files.value = res.data || []
  } catch {
    error.value = 'Failed to load downloads.'
  } finally {
    loading.value = false
  }
}

async function onDelete(file) {
  if (!confirm(`Delete "${file}"?`)) return
  deleting.value = { ...deleting.value, [file]: true }
  try {
    await API.deleteDownload(file)
    files.value = files.value.filter((f) => f !== file)
  } catch {
    error.value = `Failed to delete ${file}`
  } finally {
    deleting.value = { ...deleting.value, [file]: false }
  }
}

function formatExt(file) {
  const dot = file.lastIndexOf('.')
  return dot > 0 ? file.slice(dot + 1).toUpperCase() : ''
}

onMounted(refresh)
</script>
