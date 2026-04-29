<template>
  <div class="min-h-screen">
    <Navbar />
    <Settings />

    <div class="mx-auto max-w-5xl px-4 py-8 sm:px-6">
      <!-- Header -->
      <div class="mb-8">
        <h1 class="text-2xl font-bold tracking-tight">
          {{ t('player.title') }}
        </h1>
        <p class="mt-1 text-sm text-base-content/60">
          {{ t('player.subtitle') }}
        </p>
      </div>

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
      <div v-else class="grid gap-6 lg:grid-cols-[1fr_360px]">
        <!-- Player card -->
        <section
          class="surface rounded-3xl p-6 sm:p-8 flex flex-col items-center text-center"
        >
          <!-- Cover -->
          <div
            class="relative h-56 w-56 sm:h-64 sm:w-64 rounded-3xl bg-primary/10 text-primary flex items-center justify-center overflow-hidden shadow-glow"
            :class="{ 'pulse-glow': player.isPlaying.value }"
          >
            <img
              v-if="
                player.currentTrack.value &&
                player.currentTrack.value.cover &&
                !coverFailed[player.currentTrack.value.file]
              "
              :src="player.currentTrack.value.cover"
              :alt="player.currentTrack.value.title"
              class="absolute inset-0 h-full w-full object-cover"
              @error="markCoverFailed(player.currentTrack.value.file)"
            />
            <Icon v-else icon="clarity:music-note-line" class="h-24 w-24" />
            <div
              v-if="player.isPlaying.value"
              class="absolute bottom-3 right-3 equalizer h-5"
              aria-hidden="true"
            >
              <span></span><span></span><span></span>
            </div>
          </div>

          <!-- Title / artist -->
          <div class="mt-6 w-full">
            <p class="text-xl font-bold tracking-tight truncate">
              {{ trackTitle }}
            </p>
            <p class="text-sm text-base-content/60 truncate mt-0.5">
              {{ trackArtist }}
            </p>
          </div>

          <!-- Progress -->
          <div class="mt-6 w-full">
            <div
              class="relative h-2 rounded-full bg-white/10 overflow-hidden cursor-pointer group"
              ref="progressBar"
              @click="onSeekClick"
              @pointerdown="onSeekStart"
            >
              <div
                class="h-full bg-primary transition-[width] duration-150"
                :style="`width: ${player.progressPct.value}%`"
              />
              <div
                class="absolute top-1/2 -translate-y-1/2 h-3.5 w-3.5 rounded-full bg-primary shadow-glow-sm transition-all duration-150 opacity-0 group-hover:opacity-100"
                :style="`left: calc(${player.progressPct.value}% - 7px)`"
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
          <div class="mt-5 flex items-center justify-center gap-3">
            <button
              class="icon-btn"
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
              class="icon-btn"
              @click="player.prev()"
              :title="t('player.previous')"
              :disabled="files.length === 0"
            >
              <Icon
                icon="clarity:step-forward-2-line"
                class="h-5 w-5 -scale-x-100"
              />
            </button>
            <button
              class="inline-flex h-14 w-14 items-center justify-center rounded-full bg-primary text-primary-content shadow-glow-sm hover:scale-105 active:scale-95 transition disabled:opacity-50"
              @click="player.toggle()"
              :disabled="files.length === 0"
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
              class="icon-btn"
              @click="player.next()"
              :title="t('player.next')"
              :disabled="files.length === 0"
            >
              <Icon icon="clarity:step-forward-2-line" class="h-5 w-5" />
            </button>
            <button
              class="icon-btn relative"
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
          <div class="mt-6 w-full max-w-xs flex items-center gap-3">
            <button
              class="icon-btn"
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
        </section>

        <!-- Queue list -->
        <aside
          class="surface rounded-3xl p-4 sm:p-5 lg:max-h-[640px] lg:overflow-y-auto"
        >
          <div class="flex items-center justify-between mb-3 px-1">
            <h2
              class="text-xs font-semibold uppercase tracking-wider text-base-content/50"
            >
              {{ t('player.queue') }}
            </h2>
            <span class="text-[11px] text-base-content/40">
              {{
                files.length === 1
                  ? t('player.countOne', { count: files.length })
                  : t('player.countMany', { count: files.length })
              }}
            </span>
          </div>

          <ul v-if="files.length > 0" class="space-y-1">
            <li
              v-for="(file, idx) in files"
              :key="file"
              class="rounded-xl px-2 py-2 flex items-center gap-3 cursor-pointer transition-colors"
              :class="
                idx === player.currentIndex.value
                  ? 'bg-primary/10 text-primary'
                  : 'hover:bg-white/5'
              "
              @click="onPick(idx)"
            >
              <div
                class="relative h-9 w-9 shrink-0 rounded-lg overflow-hidden flex items-center justify-center"
                :class="
                  idx === player.currentIndex.value
                    ? 'bg-primary/15'
                    : 'bg-base-100/60'
                "
              >
                <img
                  v-if="!coverFailed[file]"
                  :src="coverUrlFor(file)"
                  :alt="trackInfo(file).title"
                  class="absolute inset-0 h-full w-full object-cover"
                  loading="lazy"
                  @error="markCoverFailed(file)"
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
                  v-else-if="coverFailed[file]"
                  icon="clarity:music-note-line"
                  class="h-4 w-4 text-base-content/50"
                />
              </div>
              <div class="flex-1 min-w-0">
                <p class="text-sm truncate font-medium">
                  {{ trackInfo(file).title }}
                </p>
                <p class="text-[11px] truncate text-base-content/50">
                  {{ trackInfo(file).artist || t('common.unknownArtist') }}
                </p>
              </div>
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
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { Icon } from '@iconify/vue'
import Navbar from '/src/components/Navbar.vue'
import Settings from '/src/components/Settings.vue'
import API from '/src/model/api'
import { usePlayer, formatTime, trackInfoFromFile } from '/src/model/player'
import { useI18n } from '/src/i18n'

const { t } = useI18n()
const player = usePlayer()

const files = ref([])
const loading = ref(false)
const progressBar = ref(null)
const coverFailed = ref({})
let dragging = false

function coverUrlFor(file) {
  return API.coverFileURL(file)
}

function markCoverFailed(file) {
  coverFailed.value = { ...coverFailed.value, [file]: true }
}

async function load() {
  loading.value = true
  try {
    const res = await API.listDownloads()
    files.value = res.data || []
    // If the player was empty (direct nav to /player), seed the queue
    // with the library so the user has something to play.
    if (player.playlist.value.length === 0 && files.value.length > 0) {
      player.setPlaylist(files.value)
    }
  } finally {
    loading.value = false
  }
}

function onPick(idx) {
  if (
    player.playlist.value.length !== files.value.length ||
    player.playlist.value[idx]?.file !== files.value[idx]
  ) {
    player.setPlaylist(files.value, { startIndex: idx })
  } else {
    player.playAt(idx)
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
