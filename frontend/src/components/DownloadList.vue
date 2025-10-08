<template>
  <div class="min-h-screen m-2">
    <h1 class="m-4 text-xl">Queue</h1>
    <div v-if="pt.downloadQueue.value.length === 0">
      <div class="alert alert-error shadow-lg">
        <svg
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
          class="stroke-current flex-shrink-0 w-6 h-6"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
          ></path>
        </svg>
        <span>No downloads are queued. Search for a song to begin.</span>
      </div>
    </div>
    <div v-else>
      <div class="carousel carousel-end bg-base-200 rounded-box shadow-lg">
        <div
          v-for="(downloadItem, index) in pt.downloadQueue.value"
          :key="index"
          class="carousel-item h-48"
        >
          <img :src="downloadItem.song.cover_url" />
        </div>
      </div>

      <div class="card card-bordered my-2 shadow-lg card-compact bg-base-100">
        <div
          v-for="(downloadItem, index) in pt.downloadQueue.value"
          :key="index"
          class="card-body grid grid-rows-1"
        >
          <h2 class="card-title">
            {{ downloadItem.song.name }} - {{ downloadItem.song.artist }}
          </h2>

          <p>
            {{ downloadItem.song.album_name }}
          </p>
          <div class="stat-figure text-primary flex space-x-2 items-center">
            <div
              v-if="downloadItem.isErrored()"
              class="badge badge-error gap-2"
            >
              error
            </div>
            <!-- // If Websocket connection exists, set status using descriptive events (message), else, fallback to simple statuses. -->
            <span class="badge">{{
              downloadItem.message || downloadItem.web_status
            }}</span>
            <button
              class="btn btn-error btn-outline btn-square"
              @click="dm.remove(downloadItem.song)"
            >
              <Icon icon="clarity:trash-line" class="h-6 w-6" />
            </button>
            <a
              v-if="downloadItem.isDownloaded()"
              class="btn btn-square btn-ghost"
              href="javascript:;"
              @click="download(downloadItem.web_download_url)"
              download
            >
              <Icon icon="clarity:download-line" class="h-6 w-6" />
            </a>
            <button
              v-else-if="downloadItem.progress === 0"
              class="btn btn-square btn-ghost loading"
            ></button>
            <div
              v-else
              class="radial-progress bg-primary text-primary-content border-4 border-primary"
              :style="`--value: ${downloadItem.progress}; --size: 2.5rem`"
            >
              {{ Math.round(downloadItem.progress) }}%
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { Icon } from '@iconify/vue'

import { useProgressTracker, useDownloadManager } from '../model/download'

const props = defineProps({
  data: Object,
})

const pt = useProgressTracker()
const dm = useDownloadManager()

function download(url) {
  const a = document.createElement('a')
  a.href = url
  a.download = url.split('/').pop()
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
}
</script>

<style scoped></style>
