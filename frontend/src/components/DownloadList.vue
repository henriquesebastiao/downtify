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
              <svg
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                stroke-width="1.5"
                stroke="currentColor"
                class="size-6"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0"
                />
              </svg>
            </button>
            <a
              v-if="downloadItem.isDownloaded()"
              class="btn btn-square btn-ghost"
              href="javascript:;"
              @click="download(downloadItem.web_download_url)"
              download
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                stroke-width="1.5"
                stroke="currentColor"
                class="size-6"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5M16.5 12 12 16.5m0 0L7.5 12m4.5 4.5V3"
                />
              </svg>
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
