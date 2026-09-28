<template>
  <div class="flex min-w-0 flex-col gap-8">
    <!-- Now playing -->
    <SettingGroup
      :title="t('activity.nowTitle')"
      :description="t('activity.nowHint')"
    >
      <p v-if="!playing.length" class="px-5 py-4 text-sm text-muted">
        {{ t('activity.nowEmpty') }}
      </p>
      <ul v-else class="flex flex-col">
        <li
          v-for="entry in playing"
          :key="`${entry.user_id}-${entry.client}-${entry.track.file || entry.track.track_id}`"
          class="flex items-center gap-3 px-5 py-3"
        >
          <span
            class="flex size-10 shrink-0 items-center justify-center rounded-full"
            :class="
              entry.paused
                ? 'bg-surface-2 text-muted'
                : 'bg-accent/15 text-accent'
            "
          >
            <AppIcon :name="entry.paused ? 'pause' : 'play'" :size="16" />
          </span>
          <span class="flex min-w-0 flex-1 flex-col">
            <span class="truncate text-sm font-semibold">
              {{ trackText(entry.track) }}
            </span>
            <span class="truncate text-[12px] text-muted">
              {{ entry.username }} · {{ entry.client }}
              <template v-if="entry.track.duration">
                · {{ formatDuration(entry.position) }} /
                {{ formatDuration(entry.track.duration) }}
              </template>
            </span>
          </span>
          <UiBadge v-if="entry.paused">{{ t('activity.paused') }}</UiBadge>
        </li>
      </ul>
    </SettingGroup>

    <!-- History -->
    <SettingGroup
      :title="t('activity.logTitle')"
      :description="t('activity.logHint')"
    >
      <div class="flex flex-wrap items-center gap-2 px-5 py-4">
        <UiSelect
          v-model="userFilter"
          :options="userOptions"
          :label="t('activity.filterUser')"
          icon="user"
          size="sm"
        />
        <UiSelect
          v-model="kindFilter"
          :options="kindOptions"
          :label="t('activity.filterKind')"
          icon="filter"
          size="sm"
        />
        <UiIconButton
          icon="refresh"
          :label="t('common.refresh')"
          class="ml-auto"
          @click="reload"
        />
      </div>
      <p
        v-if="!entries.length && !loading"
        class="px-5 py-4 text-sm text-muted"
      >
        {{ t('activity.logEmpty') }}
      </p>
      <ul class="flex flex-col">
        <li
          v-for="entry in entries"
          :key="entry.id"
          class="flex items-start gap-3 px-5 py-3"
        >
          <span
            class="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-full"
            :class="
              entry.kind === 'login_failed'
                ? 'bg-danger/12 text-danger'
                : 'bg-surface-2 text-muted'
            "
          >
            <AppIcon :name="iconFor(entry.kind)" :size="15" />
          </span>
          <span class="flex min-w-0 flex-1 flex-col">
            <span class="text-sm text-pretty">
              <span class="font-semibold">{{
                entry.username || t('activity.someone')
              }}</span>
              {{ ' ' }}{{ describe(entry) }}
            </span>
            <span class="truncate text-[12px] text-muted">
              <time :datetime="entry.at" :title="exact(entry.at)">{{
                timeAgo(entry.at, locale)
              }}</time>
              <template v-if="entry.client"> · {{ entry.client }}</template>
              <template v-if="entry.ip"> · {{ entry.ip }}</template>
            </span>
          </span>
        </li>
      </ul>
      <div v-if="next" class="flex justify-center px-5 py-4">
        <UiButton variant="ghost" :loading="loading" @click="more">
          {{ t('activity.more') }}
        </UiButton>
      </div>
    </SettingGroup>
  </div>
</template>

<script setup>
// Settings > Activity (admins): who is playing what right now, and the
// history of what everyone did - sign-ins, songs started, downloads,
// changes. See downtify/activity.py.
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import AppIcon from '../ui/AppIcon.vue'
import UiBadge from '../ui/UiBadge.vue'
import UiButton from '../ui/UiButton.vue'
import UiIconButton from '../ui/UiIconButton.vue'
import UiSelect from '../ui/UiSelect.vue'
import SettingGroup from './SettingGroup.vue'
import API from '/src/model/api'
import { formatDuration, timeAgo } from '/src/lib/format'
import { ACTIVITY_KINDS, activityIcon } from '/src/lib/activity'
import { useI18n } from '/src/i18n'

const { t, locale } = useI18n()

const playing = ref([])
const entries = ref([])
const next = ref(0)
const loading = ref(false)
const users = ref([])
const userFilter = ref(0)
const kindFilter = ref('')

const userOptions = computed(() => [
  { value: 0, label: t('activity.allUsers') },
  ...users.value.map((u) => ({ value: u.id, label: u.username })),
])
const kindOptions = computed(() => [
  { value: '', label: t('activity.allKinds') },
  ...ACTIVITY_KINDS.map((kind) => ({
    value: kind,
    label: t(`activity.kinds.${kind}`),
  })),
])

function trackText(track) {
  return [track.artist, track.title].filter(Boolean).join(' – ') || track.file
}

function iconFor(kind) {
  return activityIcon(kind)
}

function describe(entry) {
  const text = t(`activity.did.${entry.kind}`, {
    what: entry.summary,
    count: entry.detail?.songs || 0,
  })
  return text
}

function exact(when) {
  try {
    return new Date(when).toLocaleString(locale.value)
  } catch {
    return when
  }
}

async function loadPlaying() {
  try {
    playing.value = (await API.getNowPlaying()).data || []
  } catch {
    // Kept as it was; the next tick tries again.
  }
}

async function loadEntries(before = 0) {
  loading.value = true
  try {
    const params = { limit: 50, before }
    if (userFilter.value) params.user_id = userFilter.value
    if (kindFilter.value) params.kind = kindFilter.value
    const { data } = await API.getActivity(params)
    entries.value = before ? [...entries.value, ...data.entries] : data.entries
    next.value = data.next
  } catch {
    if (!before) entries.value = []
  } finally {
    loading.value = false
  }
}

function reload() {
  loadPlaying()
  loadEntries()
}

function more() {
  if (next.value) loadEntries(next.value)
}

watch([userFilter, kindFilter], () => loadEntries())

let timer = null
onMounted(async () => {
  reload()
  try {
    users.value = (await API.listUsers()).data || []
  } catch {
    users.value = []
  }
  // What's playing changes all the time; the history on request.
  timer = setInterval(loadPlaying, 10000)
})

onBeforeUnmount(() => clearInterval(timer))
</script>
