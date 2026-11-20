<template>
  <!-- The Wanted tab: what every artist you watch is still missing, with
       Check all / Download all jobs that go one artist at a time.
       GET /api/monitor/wanted (and .../job to follow a run) and POST
       /api/monitor/wanted/* -->
  <div class="flex flex-col gap-4">
    <div v-if="loading && !data" class="flex flex-col gap-2">
      <UiSkeleton v-for="n in 4" :key="n" class="h-12 w-full" />
    </div>
    <p v-else-if="error && !data" class="text-[13px] text-danger" role="alert">
      {{ error }}
    </p>
    <template v-else-if="data">
      <div class="flex flex-col gap-2">
        <p class="text-sm text-muted">
          <template v-if="totals.tracks > 0">
            {{ summaryLine }}
          </template>
          <template v-if="data.totals?.upcoming > 0">
            <template v-if="totals.tracks > 0"> · </template>
            {{ t('monitor.wantedUpcoming', { count: data.totals.upcoming }) }}
          </template>
          <template v-if="totals.uncheckedReleases > 0">
            <template v-if="totals.tracks > 0 || data.totals?.upcoming > 0">
              ·
            </template>
            {{
              t('monitor.wantedUnchecked', { count: totals.uncheckedReleases })
            }}
          </template>
        </p>
        <div class="flex flex-wrap items-center gap-x-3 gap-y-2">
          <UiButton
            v-if="totals.unchecked > 0"
            size="sm"
            variant="secondary"
            icon="search"
            :loading="starting === 'check'"
            :disabled="running || Boolean(starting)"
            @click="checkAll"
          >
            {{ t('monitor.wantedCheckAll') }}
          </UiButton>
          <UiButton
            size="sm"
            variant="secondary"
            icon="download"
            :loading="starting === 'download'"
            :disabled="!hasWork || running || Boolean(starting)"
            @click="downloadAll"
          >
            {{ t('monitor.wantedDownloadAll') }}
          </UiButton>
          <UiButton
            v-if="running"
            size="sm"
            variant="ghost"
            icon="x"
            :loading="stopping"
            :disabled="Boolean(job?.stopping)"
            @click="stop"
          >
            {{ t('monitor.wantedStop') }}
          </UiButton>
        </div>
        <template v-if="job">
          <p
            class="text-[13px] text-pretty text-muted"
            :aria-live="running ? 'polite' : undefined"
          >
            {{ jobLine }}
          </p>
          <UiProgress
            v-if="running"
            :value="job.total ? (job.done / job.total) * 100 : 0"
            :indeterminate="!job.total"
          />
        </template>
      </div>

      <UiEmpty
        v-if="!data.artists.length"
        icon="disc"
        :title="t('monitor.wantedEmpty')"
      />
      <template v-else>
        <div class="flex flex-col gap-2 sm:flex-row sm:items-center">
          <label
            class="flex h-10 min-w-0 flex-1 items-center gap-2 rounded-control border border-line-2 px-3 focus-within:border-accent"
          >
            <AppIcon name="search" :size="15" class="text-muted" />
            <span class="sr-only">{{ t('monitor.wantedSearch') }}</span>
            <input
              v-model="query"
              type="search"
              :placeholder="t('monitor.wantedSearch')"
              class="h-full min-w-0 flex-1 bg-transparent text-[13px] outline-none placeholder:text-faint"
            />
          </label>
          <UiSelect
            v-model="type"
            :options="typeOptions"
            :label="t('monitor.wantedAllTypes')"
            class="sm:w-48"
            block
          />
        </div>

        <p v-if="notChecked.length" class="text-[13px] text-pretty text-muted">
          {{ t('monitor.wantedNotChecked', { names: notCheckedLine }) }}
        </p>

        <section
          v-for="entry in shown"
          :key="entry.watch.id"
          class="flex flex-col gap-1"
        >
          <div class="flex flex-wrap items-center gap-x-3 gap-y-1">
            <RouterLink
              :to="`/monitor/watch/${entry.watch.id}`"
              class="min-w-0 flex-1 truncate text-sm font-semibold hover:underline"
              >{{ entry.watch.name }}</RouterLink
            >
            <UiButton
              size="sm"
              variant="secondary"
              icon="download"
              :loading="fetching.has(entry.watch.id)"
              :disabled="
                entry.checking ||
                running ||
                (entry.missing.tracks === 0 && !entry.unchecked)
              "
              @click="downloadArtist(entry)"
            >
              {{ t('artistReleases.downloadMissing') }}
            </UiButton>
          </div>
          <ul class="flex flex-col divide-y divide-line-2">
            <li
              v-for="release in entry.releases"
              :key="release.id"
              class="flex items-center gap-3 py-2"
            >
              <CoverArt
                :src="release.cover_url"
                :name="release.name"
                class="size-11 shrink-0"
                rounded="rounded-[6px]"
                :letter-size="15"
                :icon-size="16"
              />
              <span class="flex min-w-0 flex-1 flex-col">
                <a
                  v-if="release.url"
                  :href="release.url"
                  target="_blank"
                  rel="noopener"
                  class="truncate text-sm font-medium hover:underline"
                  >{{ release.name }}</a
                >
                <span v-else class="truncate text-sm font-medium">{{
                  release.name
                }}</span>
                <span class="truncate text-[12px] text-muted">
                  {{
                    [typeLabel(release), release.year]
                      .filter(Boolean)
                      .join(' · ')
                  }}
                </span>
                <span class="mt-0.5 flex">
                  <UiBadge v-if="release.checked === false" tone="neutral">
                    {{ t('monitor.wantedUncheckedBadge') }}
                  </UiBadge>
                  <UiBadge v-else :tone="stateTone(release.state)">
                    {{ stateLabel(release) }}
                  </UiBadge>
                </span>
              </span>
              <UiSwitch
                v-if="canSwitch(release)"
                :model-value="isOn(release)"
                :aria-label="t('artistReleases.switch', { name: release.name })"
                :disabled="busy.has(release.id)"
                @update:model-value="(on) => toggle(entry, release, on)"
              />
            </li>
          </ul>
        </section>
        <p v-if="!shown.length" class="text-sm text-muted">
          {{ t('artistReleases.noneHere') }}
        </p>
      </template>
    </template>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import AppIcon from '../ui/AppIcon.vue'
import CoverArt from '../ui/CoverArt.vue'
import UiBadge from '../ui/UiBadge.vue'
import UiButton from '../ui/UiButton.vue'
import UiEmpty from '../ui/UiEmpty.vue'
import UiProgress from '../ui/UiProgress.vue'
import UiSelect from '../ui/UiSelect.vue'
import UiSkeleton from '../ui/UiSkeleton.vue'
import UiSwitch from '../ui/UiSwitch.vue'
import monitorAPI from '/src/model/monitor'
import { useUi } from '/src/model/ui'
import {
  canSwitch,
  isOn,
  stateLabel as releaseStateLabel,
  stateTone,
} from '/src/lib/artistReleases'
import {
  TYPES,
  filterWanted,
  jobText,
  listedReleases,
  namesText,
  summary,
  summaryText,
  uncheckedNames,
} from '/src/lib/wantedReleases'
import { useI18n } from '/src/i18n'

// The releases listed (read or not), for the tab's count badge.
const emit = defineEmits(['totals'])

const { t, locale } = useI18n()
const ui = useUi()

const data = ref(null)
const loading = ref(true)
const error = ref('')
const query = ref('')
const type = ref('')
const starting = ref('')
const stopping = ref(false)
const busy = ref(new Set())
const fetching = ref(new Set())
let poll = null
// False once the tab is left: a request still in flight must not poll on.
let alive = true

const totals = computed(() => summary(data.value?.totals))
const job = computed(() => data.value?.job || null)
const running = computed(() => Boolean(job.value?.running))
const jobLine = computed(() => jobText(job.value, t))
const summaryLine = computed(() => summaryText(totals.value, t))
// Something to download: songs known missing, or releases not read yet.
const hasWork = computed(
  () => totals.value.tracks > 0 || totals.value.uncheckedReleases > 0
)
const shown = computed(() =>
  filterWanted(data.value?.artists || [], {
    query: query.value,
    type: type.value,
  })
)
// A type filter hides releases, not the fact that an artist wasn't read.
const notChecked = computed(() =>
  uncheckedNames(
    filterWanted(data.value?.artists || [], { query: query.value })
  )
)
const notCheckedLine = computed(() => namesText(notChecked.value, t))
const typeOptions = computed(() => [
  { value: '', label: t('monitor.wantedAllTypes') },
  ...TYPES.map((id) => ({
    value: id,
    label: t(`artistReleases.section.${id}`),
  })),
])

function typeLabel(release) {
  const id = TYPES.includes(release.section) ? release.section : 'album'
  return t(`artistReleases.section.${id}`)
}

// Same wording as an artist's own page.
function stateLabel(release) {
  return releaseStateLabel(release, t, locale.value)
}

function errorOf(err) {
  const detail = err?.response?.data?.detail
  if (typeof detail === 'string' && detail) return detail
  if (detail?.code === 'wanted_busy') return t('monitor.wantedBusy')
  return t('toast.actionFailed')
}

// The whole list. A poll's reload (`polled`) fails quietly and tries again.
async function load(polled = false) {
  clearTimeout(poll)
  try {
    const { data: body } = await monitorAPI.getWanted()
    if (!alive) return
    data.value = body
    error.value = ''
    emit('totals', listedReleases(body.artists || []))
  } catch (err) {
    if (!alive) return
    if (polled) {
      // keep following the job we last knew about
    } else if (data.value) ui.toast(errorOf(err), { kind: 'error' })
    else error.value = errorOf(err)
  } finally {
    loading.value = false
  }
  schedulePoll()
}

// Follow a running job (only while the tab is open) by its light endpoint;
// the full list is read again when an artist is done and when the job ends.
function schedulePoll() {
  clearTimeout(poll)
  if (alive && data.value?.job?.running) {
    poll = setTimeout(pollJob, 2000)
  }
}

async function pollJob() {
  try {
    const { data: body } = await monitorAPI.getWantedJob()
    if (!alive) return
    const before = data.value?.job
    const next = body?.job || null
    data.value = { ...data.value, job: next }
    if (!next?.running || next.done !== before?.done) {
      await load(true)
      return
    }
  } catch {
    // quiet: the next poll tries again
  }
  schedulePoll()
}

async function start(kind, call) {
  starting.value = kind
  try {
    const { data: body } = await call()
    data.value = { ...data.value, job: body }
    await load()
  } catch (err) {
    ui.toast(errorOf(err), { kind: 'error' })
    await load()
  } finally {
    starting.value = ''
  }
}

function checkAll() {
  return start('check', monitorAPI.wantedCheckAll)
}

async function downloadAll() {
  const { tracks, uncheckedReleases } = totals.value
  // Releases not read yet are downloaded too, but their size is unknown.
  const body = [
    t('monitor.wantedConfirmBody'),
    uncheckedReleases > 0
      ? t('monitor.wantedConfirmUnchecked', { count: uncheckedReleases })
      : '',
  ]
    .filter(Boolean)
    .join(' ')
  const ok = await ui.confirm({
    title:
      tracks > 0
        ? t('monitor.wantedConfirmTitle', { count: tracks })
        : t('artistReleases.missingTitle'),
    body,
    confirmLabel: t('monitor.wantedDownloadAll'),
  })
  if (!ok) return
  await start('download', monitorAPI.wantedDownloadAll)
}

async function stop() {
  stopping.value = true
  try {
    const { data: body } = await monitorAPI.wantedStop()
    data.value = { ...data.value, job: body }
  } catch (err) {
    // No job to stop: it has already finished.
    if (err?.response?.data?.detail?.code !== 'no_job') {
      ui.toast(errorOf(err), { kind: 'error' })
    }
  } finally {
    stopping.value = false
    await load()
  }
}

async function downloadArtist(entry) {
  const { tracks, releases: count } = entry.missing
  const unread = entry.unchecked
  const ok = await ui.confirm({
    title: t('artistReleases.missingTitle'),
    body: unread
      ? t('artistReleases.missingBodyUnread', { tracks, count, unread })
      : t('artistReleases.missingBody', { tracks, count }),
    confirmLabel: t('artistReleases.missingConfirm'),
  })
  if (!ok) return
  fetching.value = new Set([...fetching.value, entry.watch.id])
  try {
    await monitorAPI.downloadArtistMissing(entry.watch.id)
    ui.toast(t('artistReleases.missingStarted'), { kind: 'success' })
  } catch (err) {
    ui.toast(errorOf(err), { kind: 'error' })
  } finally {
    const next = new Set(fetching.value)
    next.delete(entry.watch.id)
    fetching.value = next
    await load()
  }
}

async function toggle(entry, release, on) {
  busy.value = new Set([...busy.value, release.id])
  try {
    await monitorAPI.switchArtistReleases(
      entry.watch.id,
      release.album_ids,
      on ? 'on' : 'off'
    )
    ui.toast(
      on
        ? t('artistReleases.switchedOn', { name: release.name })
        : t('artistReleases.switchedOff', { name: release.name }),
      { kind: 'success' }
    )
    await load()
  } catch (err) {
    ui.toast(errorOf(err), { kind: 'error' })
  } finally {
    const next = new Set(busy.value)
    next.delete(release.id)
    busy.value = next
  }
}

onMounted(() => load())
onBeforeUnmount(() => {
  alive = false
  clearTimeout(poll)
})
</script>
