<template>
  <div
    class="mx-auto flex max-w-[1180px] flex-col gap-6 px-4 pt-6 pb-10 sm:px-6 md:pt-8 lg:px-10"
  >
    <PageHeader
      :title="t('lowBitrate.title')"
      :subtitle="t('lowBitrate.subtitle')"
    >
      <UiButton variant="ghost" icon="wand" :to="{ name: 'Upgrade' }">
        <span class="max-sm:sr-only">{{ t('lowBitrate.backToUpgrade') }}</span>
      </UiButton>
      <UiButton
        v-if="auth.isAdmin.value"
        variant="ghost"
        icon="refresh"
        :loading="loading"
        @click="load"
      >
        <span class="max-sm:sr-only">{{ t('common.refresh') }}</span>
      </UiButton>
    </PageHeader>

    <UiEmpty
      v-if="!auth.isAdmin.value"
      icon="lock"
      :title="t('lowBitrate.adminOnly')"
    />

    <template v-else>
      <p class="text-sm text-pretty text-muted">
        {{ t('lowBitrate.howItWorks') }}
      </p>

      <p
        v-if="report && !report.slskd"
        class="rounded-panel border border-warn/40 bg-warn/8 px-4 py-3 text-sm text-fg"
        role="status"
      >
        {{ t('lowBitrate.slskdOff') }}
      </p>
      <p
        v-if="report && !report.trash"
        class="rounded-panel border border-warn/40 bg-warn/8 px-4 py-3 text-sm text-fg"
        role="status"
      >
        {{ t('lowBitrate.trashOff') }}
      </p>

      <div class="flex flex-wrap items-end gap-3">
        <UiSelect
          v-model="threshold"
          :options="thresholdOptions"
          :label="t('lowBitrate.threshold')"
          icon="filter"
        />
        <UiSwitch
          v-model="includeLossless"
          class="min-w-0 basis-64"
          :label="t('lowBitrate.includeLossless')"
          :description="t('lowBitrate.includeLosslessHint')"
        />
      </div>

      <div class="flex flex-wrap items-center gap-2">
        <label class="flex items-center gap-2 text-sm text-muted">
          <input
            type="checkbox"
            class="size-4 accent-[var(--color-accent)]"
            :checked="allShownSelected"
            :disabled="!shown.length"
            @change="toggleAll($event.target.checked)"
          />
          {{ t('lowBitrate.selectShown') }}
        </label>
        <UiButton
          variant="secondary"
          icon="search"
          :disabled="!searchable.length || !report?.slskd || busy"
          @click="search(searchable)"
        >
          {{ t('lowBitrate.findSelected', { count: searchable.length }) }}
        </UiButton>
        <UiButton
          variant="primary"
          icon="download"
          :disabled="!replaceable.length || !report?.trash || busy"
          @click="replace(replaceable)"
        >
          {{ t('lowBitrate.replaceSelected', { count: replaceable.length }) }}
        </UiButton>
      </div>

      <p v-if="error" class="text-[13px] text-danger" role="alert">
        {{ error }}
      </p>

      <p
        v-if="report"
        class="tabular text-[13px] text-muted"
        aria-live="polite"
      >
        {{
          t('lowBitrate.summary', {
            count: report.total,
            kbps: report.threshold,
            size: formatBytes(report.size),
          })
        }}
      </p>

      <UiEmpty
        v-if="report && !report.tracks.length && !loading"
        icon="check"
        :title="t('lowBitrate.empty', { kbps: report.threshold })"
        :body="t('lowBitrate.emptyHint')"
      />

      <ul
        v-if="shown.length"
        class="flex flex-col divide-y divide-line-2 overflow-hidden rounded-panel border border-line-2 bg-surface"
      >
        <li
          v-for="track in shown"
          :key="track.file"
          class="flex flex-col gap-3 px-4 py-3"
        >
          <div class="flex flex-wrap items-start gap-x-4 gap-y-2">
            <input
              v-model="selected"
              :value="track.file"
              type="checkbox"
              class="mt-1 size-4 shrink-0 accent-[var(--color-accent)]"
              :aria-label="
                t('lowBitrate.select', { title: track.title || track.file })
              "
            />
            <div class="min-w-0 flex-1 basis-60">
              <p class="truncate font-semibold text-fg">
                {{ track.title || track.file }}
              </p>
              <p class="truncate text-sm text-muted">
                {{ track.artist || '—' }}
                <template v-if="track.album"> · {{ track.album }}</template>
              </p>
              <p class="tabular mt-0.5 truncate text-[12px] text-faint">
                {{ t('lowBitrate.kbps', { kbps: track.bitrate }) }} ·
                {{ track.format.toUpperCase() }} ·
                {{ formatBytes(track.size) }}
                <template v-if="sourceKey(track.source)">
                  · {{ t(sourceKey(track.source)) }}
                </template>
                · {{ track.file }}
              </p>
            </div>
            <div class="flex shrink-0 items-center gap-2">
              <UiBadge
                v-if="replacementPhase(track.replacement) === 'working'"
                tone="accent"
              >
                {{ t('lowBitrate.states.' + track.replacement.state) }}
              </UiBadge>
              <UiBadge v-else-if="searching(track)" tone="neutral">
                {{ t('lowBitrate.searching') }}
              </UiBadge>
              <UiButton
                size="sm"
                variant="ghost"
                icon="search"
                :disabled="!canSearch(track) || !report.slskd || busy"
                @click="search([track.file])"
              >
                {{
                  track.search
                    ? t('lowBitrate.searchAgain')
                    : t('lowBitrate.find')
                }}
              </UiButton>
              <UiButton
                v-if="canReplace(track)"
                size="sm"
                icon="download"
                :disabled="!report.trash || busy"
                @click="replace([track.file])"
              >
                {{ t('lowBitrate.replace') }}
              </UiButton>
            </div>
          </div>

          <p
            v-if="replacementPhase(track.replacement) === 'error'"
            class="text-[12px] text-danger"
          >
            {{ t(errorKey(track.replacement.code)) }}
            <template v-if="track.replacement.message">
              ({{ track.replacement.message }})
            </template>
          </p>
          <p
            v-if="track.search?.state === 'error'"
            class="text-[12px] text-danger"
          >
            {{ t(errorKey(track.search.code)) }}
          </p>
          <p
            v-else-if="
              track.search?.state === 'done' && !candidatesOf(track).length
            "
            class="text-[12px] text-muted"
          >
            {{ t('lowBitrate.noneFound') }}
          </p>

          <fieldset
            v-if="candidatesOf(track).length"
            class="flex flex-col gap-1.5 sm:pl-8"
          >
            <legend class="sr-only">
              {{ t('lowBitrate.candidatesFor', { title: track.title }) }}
            </legend>
            <label
              v-for="candidate in candidatesOf(track)"
              :key="candidate.id"
              class="flex cursor-pointer flex-wrap items-center gap-x-3 gap-y-1 rounded-control border px-3 py-2 text-sm"
              :class="
                choiceFor(track, choices) === candidate.id
                  ? 'border-accent bg-accent/6'
                  : 'border-line-2'
              "
            >
              <input
                type="radio"
                class="size-4 accent-[var(--color-accent)]"
                :name="'choice-' + track.file"
                :value="candidate.id"
                :checked="choiceFor(track, choices) === candidate.id"
                @change="choices[track.file] = candidate.id"
              />
              <span class="font-semibold text-fg">
                {{ qualityLabel(candidate, t) }}
              </span>
              <UiBadge v-if="candidate.best" tone="accent">
                {{ t('lowBitrate.best') }}
              </UiBadge>
              <span class="tabular text-[12px] text-muted">
                {{ formatBytes(candidate.size) }}
                <template v-if="lengthDiff(candidate.duration_diff)">
                  · {{ lengthDiff(candidate.duration_diff) }}
                </template>
                ·
                {{ t('lowBitrate.peer', { name: candidate.username }) }}
                <template v-if="!candidate.free_slot">
                  · {{ t('lowBitrate.queued', { count: candidate.queue }) }}
                </template>
              </span>
              <span class="w-full truncate text-[12px] text-faint">
                {{ candidate.folder ? candidate.folder + ' / ' : ''
                }}{{ candidate.name }}
              </span>
            </label>
          </fieldset>
        </li>
      </ul>

      <div v-if="report && report.tracks.length > shown.length">
        <UiButton variant="ghost" @click="limit += PAGE">
          {{
            t('lowBitrate.showMore', {
              count: report.tracks.length - shown.length,
            })
          }}
        </UiButton>
      </div>

      <UiPanel
        v-if="report?.finished?.length"
        :title="t('lowBitrate.finishedTitle')"
        :description="t('lowBitrate.finishedHint')"
      >
        <ul class="flex flex-col gap-2 text-sm">
          <li
            v-for="item in report.finished"
            :key="item.file"
            class="flex flex-wrap items-center gap-x-3 gap-y-1"
          >
            <UiBadge :tone="item.state === 'done' ? 'accent' : 'danger'">
              {{ t('lowBitrate.states.' + item.state) }}
            </UiBadge>
            <span class="min-w-0 truncate text-fg">{{ item.file }}</span>
            <span
              v-if="item.state === 'done'"
              class="tabular text-[12px] text-muted"
            >
              {{
                t('lowBitrate.replacedWith', {
                  before: item.bitrate_before,
                  after: item.bitrate_after,
                  file: item.new_file,
                })
              }}
            </span>
            <span v-else class="text-[12px] text-danger">
              {{ t(errorKey(item.code)) }}
            </span>
          </li>
        </ul>
        <div class="mt-3 flex flex-wrap gap-2">
          <UiButton
            size="sm"
            variant="ghost"
            icon="trash"
            :to="{ name: 'Trash' }"
          >
            {{ t('lowBitrate.openTrash') }}
          </UiButton>
          <UiButton size="sm" variant="ghost" icon="x" @click="forgetFinished">
            {{ t('lowBitrate.clearFinished') }}
          </UiButton>
        </div>
      </UiPanel>
    </template>
  </div>
</template>

<script setup>
// The low-bitrate report (admins): library files under a bitrate, and
// better copies from Soulseek for each. Reading it writes nothing; a
// search writes nothing; only "Replace" (after a confirmation) changes
// the library, and the old file goes to the music trash.
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import UiBadge from '/src/components/ui/UiBadge.vue'
import UiButton from '/src/components/ui/UiButton.vue'
import UiEmpty from '/src/components/ui/UiEmpty.vue'
import UiPanel from '/src/components/ui/UiPanel.vue'
import UiSelect from '/src/components/ui/UiSelect.vue'
import UiSwitch from '/src/components/ui/UiSwitch.vue'
import PageHeader from '/src/components/library/PageHeader.vue'
import API from '/src/model/api'
import { useAuth } from '/src/model/auth'
import { useLibrary } from '/src/model/library'
import { useUi } from '/src/model/ui'
import { formatBytes } from '/src/lib/format'
import { lengthDiff } from '/src/lib/replaceAudio'
import {
  DEFAULT_THRESHOLD,
  THRESHOLDS,
  anyWorking,
  canReplace,
  canSearch,
  candidatesOf,
  choiceFor,
  errorKey,
  qualityLabel,
  replaceItems,
  replacementPhase,
  searching,
  sourceKey,
} from '/src/lib/lowBitrate'
import { useI18n } from '/src/i18n'

const PAGE = 100
const POLL_MS = 3000

const { t } = useI18n()
const auth = useAuth()
const ui = useUi()
const library = useLibrary()

const report = ref(null)
const threshold = ref(DEFAULT_THRESHOLD)
const includeLossless = ref(false)
const selected = ref([])
const choices = reactive({})
const limit = ref(PAGE)
const loading = ref(false)
const busy = ref(false)
const error = ref('')
let timer = null
let disposed = false
let hadWork = false

const thresholdOptions = computed(() =>
  THRESHOLDS.map((kbps) => ({
    value: kbps,
    label: t('lowBitrate.under', { kbps }),
  }))
)
const shown = computed(() => (report.value?.tracks || []).slice(0, limit.value))
const selectedTracks = computed(() => {
  const wanted = new Set(selected.value)
  return (report.value?.tracks || []).filter((track) => wanted.has(track.file))
})
const searchable = computed(() =>
  selectedTracks.value.filter(canSearch).map((track) => track.file)
)
const replaceable = computed(() =>
  selectedTracks.value.filter(canReplace).map((track) => track.file)
)
const allShownSelected = computed(
  () =>
    shown.value.length > 0 &&
    shown.value.every((track) => selected.value.includes(track.file))
)

function message(e) {
  const detail = e?.response?.data?.detail
  if (detail?.code) return t(errorKey(detail.code))
  return typeof detail === 'string' ? detail : t('lowBitrate.errors.failed')
}

async function load() {
  if (loading.value || disposed || !auth.isAdmin.value) return
  loading.value = true
  try {
    const { data } = await API.lowBitrateReport(threshold.value)
    if (disposed) return
    report.value = data
    const files = new Set(data.tracks.map((track) => track.file))
    selected.value = selected.value.filter((file) => files.has(file))
    error.value = ''
    const working = anyWorking(data)
    // A replacement just finished: the library page should see it.
    if (hadWork && !working) library.load({ force: true })
    hadWork = working
  } catch (e) {
    error.value = message(e)
  } finally {
    loading.value = false
  }
}

function toggleAll(on) {
  const files = shown.value.map((track) => track.file)
  selected.value = on
    ? [...new Set([...selected.value, ...files])]
    : selected.value.filter((file) => !files.includes(file))
}

async function search(files) {
  busy.value = true
  error.value = ''
  try {
    // The server takes 50 files a request.
    for (let i = 0; i < files.length; i += 50) {
      await API.lowBitrateSearch(files.slice(i, i + 50), includeLossless.value)
    }
    await load()
  } catch (e) {
    error.value = message(e)
  } finally {
    busy.value = false
  }
}

async function replace(files) {
  const tracks = report.value?.tracks || []
  const items = replaceItems(tracks, files, choices)
  if (!items.length) return
  const ok = await ui.confirm({
    title: t('lowBitrate.confirmTitle', { count: items.length }),
    body: t('lowBitrate.confirmBody'),
    confirmLabel: t('lowBitrate.replace'),
  })
  if (!ok) return
  busy.value = true
  error.value = ''
  try {
    for (let i = 0; i < items.length; i += 50) {
      const { data } = await API.lowBitrateReplace(items.slice(i, i + 50))
      if (data.refused?.length) {
        const first = data.refused[0]
        error.value = t('lowBitrate.refused', {
          count: data.refused.length,
          reason: t(errorKey(first.code)),
        })
      }
    }
    selected.value = selected.value.filter((file) => !files.includes(file))
    await load()
  } catch (e) {
    error.value = message(e)
  } finally {
    busy.value = false
  }
}

async function forgetFinished() {
  const files = (report.value?.finished || []).map((item) => item.file)
  if (!files.length) return
  try {
    for (let i = 0; i < files.length; i += 50) {
      await API.lowBitrateForget(files.slice(i, i + 50))
    }
    await load()
  } catch (e) {
    error.value = message(e)
  }
}

watch(threshold, () => {
  limit.value = PAGE
  load()
})

onMounted(() => {
  load()
  timer = setInterval(() => {
    if (!document.hidden && anyWorking(report.value)) load()
  }, POLL_MS)
})
onUnmounted(() => {
  disposed = true
  clearInterval(timer)
})
</script>
