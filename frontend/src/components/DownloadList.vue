<template>
  <div class="mx-auto max-w-4xl px-4 py-8 sm:px-6">
    <!-- Header -->
    <div class="mb-8">
      <h1 class="text-2xl font-bold tracking-tight">Download Queue</h1>
      <p class="mt-1 text-sm text-base-content/60">
        Songs you've queued. Progress, status and quick actions live here.
      </p>
    </div>

    <!-- Empty state -->
    <div
      v-if="pt.downloadQueue.value.length === 0"
      class="surface rounded-2xl p-12 flex flex-col items-center text-center"
    >
      <Icon
        icon="clarity:download-line"
        class="h-12 w-12 text-base-content/20 mb-4"
      />
      <p class="text-base-content/50 text-sm">Nothing queued right now.</p>
      <p class="text-base-content/40 text-xs mt-1">
        Search for a song and hit download to start.
      </p>
    </div>

    <!-- Queue items -->
    <ul v-else class="space-y-3">
      <li
        v-for="(item, index) in pt.downloadQueue.value"
        :key="index"
        class="surface rounded-2xl p-3 sm:p-4 flex items-center gap-4"
      >
        <!-- Cover -->
        <div class="track-cover h-16 w-16 sm:h-20 sm:w-20">
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
          <div class="flex items-center gap-2 mb-0.5">
            <span class="font-semibold truncate">{{ item.song.name }}</span>
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
          <a
            v-if="item.isDownloaded()"
            class="icon-btn text-primary hover:bg-primary/10"
            href="javascript:;"
            @click="forceDownload(item.web_download_url)"
            title="Save to device"
          >
            <Icon icon="clarity:download-line" class="h-4 w-4" />
          </a>
          <div
            v-else-if="item.progress > 0 && !item.isErrored()"
            class="radial-progress text-primary"
            :style="`--value:${item.progress}; --size:2.75rem; --thickness:3px`"
          >
            <span class="text-[10px] font-semibold">
              {{ Math.round(item.progress) }}%
            </span>
          </div>
          <span
            v-else-if="!item.isErrored()"
            class="loading loading-spinner loading-sm text-primary"
          />

          <button
            class="icon-btn text-error/70 hover:text-error hover:bg-error/10"
            @click="dm.remove(item.song)"
            title="Remove from queue"
          >
            <Icon icon="clarity:trash-line" class="h-4 w-4" />
          </button>
        </div>
      </li>
    </ul>
  </div>
</template>

<script setup>
import { Icon } from '@iconify/vue'
import { useProgressTracker, useDownloadManager } from '../model/download'

const pt = useProgressTracker()
const dm = useDownloadManager()

function artistsOf(song) {
  if (Array.isArray(song.artists) && song.artists.length) {
    return song.artists.join(', ')
  }
  return song.artist || 'Unknown artist'
}

function statusClass(item) {
  if (item.isErrored()) return 'badge-error-soft'
  if (item.isDownloaded()) return 'badge-soft'
  return 'badge-neutral-soft'
}

function forceDownload(url) {
  const a = document.createElement('a')
  a.href = url
  a.download = url.split('/').pop()
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
}
</script>
