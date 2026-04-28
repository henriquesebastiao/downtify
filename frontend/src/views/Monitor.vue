<template>
  <div class="min-h-screen">
    <Navbar />
    <Settings />

    <div class="mx-auto max-w-4xl px-4 py-8 sm:px-6">
      <!-- Header -->
      <div class="mb-8">
        <h1 class="text-2xl font-bold tracking-tight">Playlist Monitor</h1>
        <p class="mt-1 text-sm text-base-content/60">
          Add Spotify playlists to watch. New tracks added to those playlists
          will be downloaded automatically.
        </p>
      </div>

      <!-- Add playlist form -->
      <div class="surface rounded-2xl p-5 mb-8">
        <h2
          class="text-sm font-semibold uppercase tracking-wider text-base-content/50 mb-4"
        >
          Watch a new playlist
        </h2>
        <form @submit.prevent="onAdd" class="flex flex-col sm:flex-row gap-3">
          <input
            v-model="newUrl"
            type="text"
            placeholder="Paste a Spotify playlist URL…"
            class="input-modern flex-1 h-11 text-sm"
            :disabled="adding"
          />
          <div class="flex items-center gap-2 shrink-0">
            <select
              v-model="newInterval"
              class="select select-sm rounded-full border border-white/10 bg-base-100/85 focus:border-primary/60 h-11 px-3 text-sm"
              :disabled="adding"
            >
              <option :value="15">Every 15 min</option>
              <option :value="30">Every 30 min</option>
              <option :value="60">Every hour</option>
              <option :value="180">Every 3 h</option>
              <option :value="360">Every 6 h</option>
              <option :value="720">Every 12 h</option>
              <option :value="1440">Every day</option>
            </select>
            <button
              type="submit"
              class="btn btn-primary btn-sm h-11 px-5 rounded-full"
              :disabled="adding || !newUrl.trim()"
            >
              <span v-if="adding" class="loading loading-spinner loading-xs" />
              <span v-else>Watch</span>
            </button>
          </div>
        </form>
        <p v-if="addError" class="mt-2 text-xs text-error">{{ addError }}</p>
      </div>

      <!-- Loading skeleton -->
      <div v-if="loading" class="space-y-3">
        <div v-for="n in 3" :key="n" class="skeleton h-24 rounded-2xl" />
      </div>

      <!-- Empty state -->
      <div
        v-else-if="playlists.length === 0"
        class="surface rounded-2xl p-12 flex flex-col items-center text-center"
      >
        <Icon
          icon="clarity:music-note-line"
          class="h-12 w-12 text-base-content/20 mb-4"
        />
        <p class="text-base-content/50 text-sm">
          No playlists being monitored yet.
        </p>
        <p class="text-base-content/40 text-xs mt-1">
          Paste a Spotify playlist link above to get started.
        </p>
      </div>

      <!-- Playlist cards -->
      <ul v-else class="space-y-3">
        <li
          v-for="pl in playlists"
          :key="pl.id"
          class="surface rounded-2xl p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center gap-4"
        >
          <!-- Info -->
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2 mb-1">
              <span class="font-semibold truncate">{{ pl.name }}</span>
              <span
                class="pill shrink-0"
                :class="pl.enabled ? 'badge-soft' : 'badge-neutral-soft'"
              >
                {{ pl.enabled ? 'Active' : 'Paused' }}
              </span>
            </div>
            <div
              class="flex flex-wrap gap-x-4 gap-y-0.5 text-xs text-base-content/50"
            >
              <span>
                <Icon
                  icon="clarity:refresh-line"
                  class="inline h-3 w-3 mr-0.5"
                />
                Every {{ formatInterval(pl.interval_minutes) }}
              </span>
              <span>
                <Icon
                  icon="clarity:music-note-line"
                  class="inline h-3 w-3 mr-0.5"
                />
                {{ pl.last_track_count }} track{{
                  pl.last_track_count !== 1 ? 's' : ''
                }}
              </span>
              <span v-if="pl.last_checked">
                <Icon icon="clarity:clock-line" class="inline h-3 w-3 mr-0.5" />
                Checked {{ timeAgo(pl.last_checked) }}
              </span>
              <span v-else class="italic">Not checked yet</span>
            </div>
          </div>

          <!-- Actions -->
          <div class="flex items-center gap-2 shrink-0">
            <!-- Interval selector -->
            <select
              :value="pl.interval_minutes"
              @change="onChangeInterval(pl, $event)"
              class="select select-xs rounded-full border border-white/10 bg-base-100/60 text-xs focus:border-primary/60"
            >
              <option :value="15">15 min</option>
              <option :value="30">30 min</option>
              <option :value="60">1 h</option>
              <option :value="180">3 h</option>
              <option :value="360">6 h</option>
              <option :value="720">12 h</option>
              <option :value="1440">1 day</option>
            </select>

            <!-- Toggle enabled -->
            <button
              class="icon-btn"
              :title="pl.enabled ? 'Pause monitoring' : 'Resume monitoring'"
              @click="onToggle(pl)"
            >
              <Icon
                :icon="pl.enabled ? 'clarity:pause-line' : 'clarity:play-line'"
                class="h-4 w-4"
              />
            </button>

            <!-- Manual check -->
            <button
              class="icon-btn"
              title="Check now"
              :disabled="checking[pl.id]"
              @click="onCheck(pl)"
            >
              <span
                v-if="checking[pl.id]"
                class="loading loading-spinner loading-xs"
              />
              <Icon v-else icon="clarity:refresh-line" class="h-4 w-4" />
            </button>

            <!-- Delete -->
            <button
              class="icon-btn text-error/70 hover:text-error hover:bg-error/10"
              title="Stop monitoring"
              @click="onDelete(pl)"
            >
              <Icon icon="clarity:trash-line" class="h-4 w-4" />
            </button>
          </div>
        </li>
      </ul>

      <!-- Info banner -->
      <div
        class="mt-8 surface rounded-2xl p-4 flex gap-3 text-sm text-base-content/60"
      >
        <Icon
          icon="clarity:info-standard-line"
          class="h-5 w-5 shrink-0 mt-0.5 text-primary/70"
        />
        <p>
          When you add a playlist, Downtify downloads every track it currently
          contains and then keeps watching it. Any songs added later on Spotify
          are detected and downloaded automatically on the next scheduled check.
        </p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { Icon } from '@iconify/vue'
import Navbar from '/src/components/Navbar.vue'
import Settings from '/src/components/Settings.vue'
import monitorAPI from '/src/model/monitor.js'

const playlists = ref([])
const loading = ref(false)
const adding = ref(false)
const addError = ref('')
const newUrl = ref('')
const newInterval = ref(60)
const checking = ref({})

async function load() {
  loading.value = true
  try {
    const res = await monitorAPI.listMonitoredPlaylists()
    playlists.value = res.data || []
  } finally {
    loading.value = false
  }
}

async function onAdd() {
  addError.value = ''
  adding.value = true
  try {
    const res = await monitorAPI.addMonitoredPlaylist(
      newUrl.value.trim(),
      newInterval.value
    )
    playlists.value.unshift(res.data)
    newUrl.value = ''
  } catch (e) {
    addError.value =
      e?.response?.data?.detail ||
      'Failed to add playlist. Check the URL and try again.'
  } finally {
    adding.value = false
  }
}

async function onToggle(pl) {
  try {
    const res = await monitorAPI.updateMonitoredPlaylist(pl.id, {
      enabled: !pl.enabled,
    })
    Object.assign(pl, res.data)
  } catch {
    // silently ignore
  }
}

async function onChangeInterval(pl, event) {
  const val = parseInt(event.target.value, 10)
  try {
    const res = await monitorAPI.updateMonitoredPlaylist(pl.id, {
      interval_minutes: val,
    })
    Object.assign(pl, res.data)
  } catch {
    // silently ignore
  }
}

async function onCheck(pl) {
  checking.value = { ...checking.value, [pl.id]: true }
  try {
    await monitorAPI.checkMonitoredPlaylist(pl.id)
    // Refresh after a short delay to pick up updated last_checked
    setTimeout(async () => {
      try {
        const res = await monitorAPI.listMonitoredPlaylists()
        playlists.value = res.data || []
      } finally {
        checking.value = { ...checking.value, [pl.id]: false }
      }
    }, 3000)
  } catch {
    checking.value = { ...checking.value, [pl.id]: false }
  }
}

async function onDelete(pl) {
  if (!confirm(`Stop monitoring "${pl.name}"?`)) return
  try {
    await monitorAPI.deleteMonitoredPlaylist(pl.id)
    playlists.value = playlists.value.filter((p) => p.id !== pl.id)
  } catch {
    // silently ignore
  }
}

function formatInterval(minutes) {
  if (minutes < 60) return `${minutes} min`
  if (minutes < 1440) return `${minutes / 60} h`
  return `${minutes / 1440} day${minutes / 1440 !== 1 ? 's' : ''}`
}

function timeAgo(isoString) {
  try {
    const diff = Date.now() - new Date(isoString).getTime()
    const mins = Math.floor(diff / 60000)
    if (mins < 1) return 'just now'
    if (mins < 60) return `${mins} min ago`
    const hrs = Math.floor(mins / 60)
    if (hrs < 24) return `${hrs} h ago`
    return `${Math.floor(hrs / 24)} day(s) ago`
  } catch {
    return ''
  }
}

onMounted(load)
</script>
