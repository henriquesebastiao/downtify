<template>
  <div class="min-h-dvh overflow-x-hidden">
    <Navbar />
    <Settings />

    <div class="mx-auto max-w-4xl px-4 py-8 sm:px-6">
      <div class="mb-8">
        <h1 class="text-2xl font-bold tracking-tight">
          {{ t('monitor.title') }}
        </h1>
        <p class="mt-1 text-sm text-base-content/60">
          {{ t('monitor.subtitle') }}
        </p>
      </div>

      <div
        v-if="loadError"
        class="surface rounded-2xl p-4 mb-6 text-sm text-error flex gap-2 items-center"
      >
        <Icon icon="clarity:exclamation-circle-line" class="h-5 w-5 shrink-0" />
        <span>{{ loadError }}</span>
      </div>

      <div v-if="loading" class="space-y-3">
        <div v-for="n in 3" :key="n" class="skeleton h-24 rounded-2xl" />
      </div>

      <div
        v-else-if="playlists.length === 0"
        class="surface rounded-2xl p-12 flex flex-col items-center text-center"
      >
        <Icon
          icon="clarity:music-note-line"
          class="h-12 w-12 text-base-content/20 mb-4"
        />
        <p class="text-base-content/50 text-sm">
          {{ t('monitor.empty') }}
        </p>
        <p class="text-base-content/40 text-xs mt-1">
          {{ t('monitor.emptyHint') }}
        </p>
      </div>

      <ul v-else class="space-y-3">
        <li
          v-for="pl in playlists"
          :key="pl.spotify_playlist_id"
          class="surface rounded-2xl p-4 sm:p-5 flex flex-col gap-4"
        >
          <div class="flex flex-col sm:flex-row sm:items-start gap-4">
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 mb-1">
                <span class="font-semibold truncate">{{
                  pl.playlist_name
                }}</span>
                <span
                  v-if="isWatched(pl)"
                  class="pill shrink-0"
                  :class="
                    pl.monitor?.enabled ? 'badge-soft' : 'badge-neutral-soft'
                  "
                >
                  {{
                    pl.monitor?.enabled
                      ? t('monitor.active')
                      : t('monitor.paused')
                  }}
                </span>
              </div>
              <p class="text-xs text-base-content/50">
                {{ playlistSummary(pl) }}
              </p>
              <div
                v-if="pl.monitor?.enabled"
                class="flex flex-wrap gap-x-4 gap-y-0.5 text-xs text-base-content/50 mt-1"
              >
                <span>
                  <Icon
                    icon="clarity:refresh-line"
                    class="inline h-3 w-3 mr-0.5"
                  />
                  {{ scheduleLabel(pl) }}
                </span>
                <span v-if="pl.monitor.last_checked">
                  <Icon
                    icon="clarity:clock-line"
                    class="inline h-3 w-3 mr-0.5"
                  />
                  {{
                    t('monitor.checked', {
                      when: timeAgo(pl.monitor.last_checked),
                    })
                  }}
                </span>
              </div>
            </div>

            <div class="flex flex-wrap items-center gap-2 shrink-0">
              <label
                class="flex items-center gap-2 cursor-pointer select-none"
                :title="t('monitor.watchNew')"
              >
                <input
                  type="checkbox"
                  class="toggle toggle-primary toggle-sm"
                  :checked="!!pl.monitor?.enabled"
                  :disabled="!!toggling[pl.spotify_playlist_id]"
                  @change="onToggleWatch(pl, $event)"
                />
                <span class="text-xs text-base-content/70">{{
                  t('monitor.watchNew')
                }}</span>
              </label>

              <select
                :value="scheduleFor(pl).interval_minutes"
                class="filter-select-xs"
                @change="onChangeInterval(pl, $event)"
              >
                <option :value="15">{{ t('monitor.short15') }}</option>
                <option :value="30">{{ t('monitor.short30') }}</option>
                <option :value="60">{{ t('monitor.short1h') }}</option>
                <option :value="180">{{ t('monitor.short3h') }}</option>
                <option :value="360">{{ t('monitor.short6h') }}</option>
                <option :value="720">{{ t('monitor.short12h') }}</option>
                <option :value="1440">{{ t('monitor.short1d') }}</option>
                <option :value="10080">{{ t('monitor.short1w') }}</option>
                <option :value="20160">{{ t('monitor.short2w') }}</option>
                <option :value="43200">{{ t('monitor.short1mo') }}</option>
              </select>

              <input
                v-if="usesCheckTime(scheduleFor(pl).interval_minutes)"
                type="time"
                class="filter-select-xs w-[5.5rem]"
                :value="scheduleFor(pl).check_time"
                :title="t('monitor.checkTimeHint')"
                @change="onChangeCheckTime(pl, $event)"
              />

              <button
                v-if="pl.monitor?.enabled"
                class="icon-btn"
                :title="t('monitor.checkNow')"
                :disabled="!!checking[pl.spotify_playlist_id]"
                @click="onCheck(pl)"
              >
                <span
                  v-if="checking[pl.spotify_playlist_id]"
                  class="loading loading-spinner loading-xs"
                />
                <Icon v-else icon="clarity:refresh-line" class="h-4 w-4" />
              </button>

              <a
                v-if="pl.playlist_url"
                class="icon-btn"
                :href="pl.playlist_url"
                target="_blank"
                rel="noopener noreferrer"
                :title="t('search.openPlaylistOnSpotify')"
              >
                <Icon icon="clarity:pop-out-line" class="h-4 w-4" />
              </a>

              <button
                v-if="pl.missing_count > 0"
                type="button"
                class="icon-btn text-primary hover:bg-primary/10"
                :disabled="!!downloading[pl.spotify_playlist_id]"
                :title="
                  t('search.downloadMissing', { count: pl.missing_count })
                "
                @click="onDownloadMissing(pl)"
              >
                <Icon icon="clarity:download-line" class="h-4 w-4" />
              </button>
            </div>
          </div>
        </li>
      </ul>

      <div
        class="mt-8 surface rounded-2xl p-4 flex gap-3 text-sm text-base-content/60"
      >
        <Icon
          icon="clarity:info-standard-line"
          class="h-5 w-5 shrink-0 mt-0.5 text-primary/70"
        />
        <p>{{ t('monitor.info') }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { Icon } from '@iconify/vue'
import Navbar from '/src/components/Navbar.vue'
import Settings from '/src/components/Settings.vue'
import API from '/src/model/api.js'
import monitorAPI from '/src/model/monitor.js'
import { useI18n } from '/src/i18n'

const { t } = useI18n()

const CALENDAR_INTERVAL_MINUTES = 1440
const DEFAULT_DAILY_CHECK_TIME = '03:00'

const playlists = ref([])
const loading = ref(false)
const loadError = ref('')
const toggling = ref({})
const checking = ref({})
const downloading = ref({})
const preferredSchedule = ref({})

function isWatched(pl) {
  return pl.monitor != null
}

function usesCheckTime(intervalMinutes) {
  return intervalMinutes >= CALENDAR_INTERVAL_MINUTES
}

function scheduleFor(pl) {
  const sid = pl.spotify_playlist_id
  const mon = pl.monitor
  const preferred = preferredSchedule.value[sid] || {}
  const interval = mon?.interval_minutes ?? preferred.interval_minutes ?? 60
  let checkTime = mon?.check_time ?? preferred.check_time ?? ''
  if (usesCheckTime(interval) && !checkTime) {
    checkTime = DEFAULT_DAILY_CHECK_TIME
  }
  return { interval_minutes: interval, check_time: checkTime }
}

function rememberSchedule(sid, { interval_minutes, check_time }) {
  preferredSchedule.value = {
    ...preferredSchedule.value,
    [sid]: { interval_minutes, check_time },
  }
}

function playlistSummary(pl) {
  return t('search.incompleteSummary', {
    downloaded: pl.downloaded_count,
    expected: pl.expected_count,
    missing: pl.missing_count,
  })
}

function scheduleLabel(pl) {
  const { interval_minutes, check_time } = scheduleFor(pl)
  const interval = formatInterval(interval_minutes)
  if (usesCheckTime(interval_minutes) && check_time) {
    return t('monitor.everyIntervalAt', { interval, time: check_time })
  }
  return t('monitor.everyInterval', { interval })
}

async function load() {
  loading.value = true
  loadError.value = ''
  try {
    const res = await API.getPlaylistBatches()
    playlists.value = res.data?.playlists || []
  } catch {
    loadError.value = t('monitor.failedAdd')
  } finally {
    loading.value = false
  }
}

function monitorPayload(pl, { enabled, interval_minutes, check_time }) {
  const payload = {
    spotify_playlist_id: pl.spotify_playlist_id,
    enabled,
    interval_minutes,
  }
  if (usesCheckTime(interval_minutes) && check_time) {
    payload.check_time = check_time
    payload.check_timezone =
      pl.monitor?.check_timezone || monitorAPI.browserTimezone()
  }
  return payload
}

async function onToggleWatch(pl, event) {
  const enabled = event.target.checked
  const sid = pl.spotify_playlist_id
  const schedule = scheduleFor(pl)
  toggling.value = { ...toggling.value, [sid]: true }
  try {
    const res = await monitorAPI.upsertMonitoredPlaylist(
      monitorPayload(pl, { enabled, ...schedule })
    )
    pl.monitor = res.data
    rememberSchedule(sid, schedule)
  } catch {
    event.target.checked = !enabled
  } finally {
    toggling.value = { ...toggling.value, [sid]: false }
  }
}

async function onChangeInterval(pl, event) {
  const val = parseInt(event.target.value, 10)
  const sid = pl.spotify_playlist_id
  const prev = scheduleFor(pl)
  const check_time = usesCheckTime(val)
    ? prev.check_time || DEFAULT_DAILY_CHECK_TIME
    : ''
  rememberSchedule(sid, { interval_minutes: val, check_time })
  if (!pl.monitor?.id) return
  try {
    const res = await monitorAPI.updateMonitoredPlaylist(
      pl.monitor.id,
      monitorPayload(pl, {
        enabled: true,
        interval_minutes: val,
        check_time,
      })
    )
    pl.monitor = res.data
  } catch {
    // silently ignore
  }
}

async function onChangeCheckTime(pl, event) {
  const check_time = event.target.value
  const sid = pl.spotify_playlist_id
  const { interval_minutes } = scheduleFor(pl)
  rememberSchedule(sid, { interval_minutes, check_time })
  if (!pl.monitor?.id) return
  try {
    const res = await monitorAPI.updateMonitoredPlaylist(
      pl.monitor.id,
      monitorPayload(pl, {
        enabled: true,
        interval_minutes,
        check_time,
      })
    )
    pl.monitor = res.data
  } catch {
    // silently ignore
  }
}

async function onCheck(pl) {
  const id = pl.monitor?.id
  if (!id) return
  const sid = pl.spotify_playlist_id
  checking.value = { ...checking.value, [sid]: true }
  try {
    await monitorAPI.checkMonitoredPlaylist(id)
    setTimeout(load, 3000)
  } finally {
    checking.value = { ...checking.value, [sid]: false }
  }
}

async function onDownloadMissing(pl) {
  const sid = pl.spotify_playlist_id
  downloading.value = { ...downloading.value, [sid]: true }
  try {
    await API.downloadMissingPlaylistTracks({
      spotify_playlist_id: sid,
      playlist_url: pl.playlist_url,
    })
    setTimeout(load, 2000)
  } finally {
    downloading.value = { ...downloading.value, [sid]: false }
  }
}

function formatInterval(minutes) {
  if (minutes < 60) return `${minutes} ${t('monitor.minSuffix')}`
  if (minutes < 1440) return `${minutes / 60} ${t('monitor.hourSuffix')}`
  if (minutes < 10080) {
    const days = minutes / 1440
    return `${days} ${days === 1 ? t('monitor.daySuffix') : t('monitor.daysSuffix')}`
  }
  if (minutes < 43200) {
    const weeks = minutes / 10080
    return `${weeks} ${weeks === 1 ? t('monitor.weekSuffix') : t('monitor.weeksSuffix')}`
  }
  const months = Math.round(minutes / 43200)
  return `${months} ${months === 1 ? t('monitor.monthSuffix') : t('monitor.monthsSuffix')}`
}

function timeAgo(isoString) {
  try {
    const diff = Date.now() - new Date(isoString).getTime()
    const mins = Math.floor(diff / 60000)
    if (mins < 1) return t('monitor.timeJustNow')
    if (mins < 60) return t('monitor.timeMinAgo', { n: mins })
    const hrs = Math.floor(mins / 60)
    if (hrs < 24) return t('monitor.timeHourAgo', { n: hrs })
    return t('monitor.timeDayAgo', { n: Math.floor(hrs / 24) })
  } catch {
    return ''
  }
}

onMounted(load)
</script>
