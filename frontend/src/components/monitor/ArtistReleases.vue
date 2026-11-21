<template>
  <!-- An artist watch's whole catalogue (YouTube Music, Deezer and
       MusicBrainz, from its last check): what the library has of each
       release, a switch per release, and the MusicBrainz release kinds
       the watch downloads. GET/PATCH /api/monitor/playlists/{id}/releases -->
  <UiPanel
    :title="t('artistReleases.title')"
    :description="t('artistReleases.hint')"
  >
    <div v-if="loading && !data" class="flex flex-col gap-2">
      <UiSkeleton v-for="n in 4" :key="n" class="h-12 w-full" />
    </div>
    <p v-else-if="error" class="text-[13px] text-danger" role="alert">
      {{ error }}
    </p>
    <UiEmpty
      v-else-if="!releases.length"
      icon="disc"
      :title="t('artistReleases.empty')"
      :body="t('artistReleases.emptyHint')"
    />
    <div v-else class="flex flex-col gap-4">
      <p class="text-sm text-muted">{{ summary }}</p>

      <!-- "Check what I have": read every release's tracklist (slowly)
           and compare it with the library; downloads nothing. -->
      <div class="flex flex-col gap-1.5">
        <div class="flex flex-wrap items-center gap-x-3 gap-y-1.5">
          <UiButton
            size="sm"
            variant="secondary"
            icon="search"
            :loading="starting"
            :disabled="Boolean(inventory?.running)"
            @click="checkHave"
          >
            {{ t('artistReleases.check') }}
          </UiButton>
          <UiButton
            size="sm"
            variant="secondary"
            icon="download"
            :loading="fetching"
            :disabled="!canDownloadMissing"
            @click="downloadMissing"
          >
            {{
              missing.tracks
                ? t('artistReleases.downloadMissingCount', {
                    count: missing.tracks,
                  })
                : t('artistReleases.downloadMissing')
            }}
          </UiButton>
          <span
            v-if="inventory?.running"
            class="tabular text-[13px] text-muted"
            aria-live="polite"
            >{{
              t('artistReleases.checking', {
                done: inventory.done,
                total: inventory.total || '…',
              })
            }}</span
          >
          <span
            v-else-if="inventory?.finished_at"
            class="text-[13px] text-muted"
            >{{
              t('artistReleases.checkDone', {
                count: inventory.checked || 0,
                failed: inventory.failed || 0,
              })
            }}</span
          >
        </div>
        <UiProgress
          v-if="inventory?.running"
          :value="
            inventory.total ? (inventory.done / inventory.total) * 100 : 0
          "
          :indeterminate="!inventory.total"
        />
        <p
          v-if="data.checking"
          class="text-[13px] text-pretty text-muted"
          aria-live="polite"
        >
          {{ t('artistReleases.busy') }}
        </p>
        <p class="text-[12px] text-pretty text-muted">
          {{ t('artistReleases.checkHint') }}
          {{ t('artistReleases.missingHint') }}
        </p>
      </div>

      <div v-if="data.musicbrainz" class="flex flex-col gap-1.5">
        <div class="flex flex-wrap items-center gap-2">
          <span class="text-[13px] font-semibold text-fg-3">{{
            t('artistReleases.kinds')
          }}</span>
          <button
            v-for="kind in data.available_kinds"
            :key="kind"
            type="button"
            class="inline-flex h-8 items-center gap-1.5 rounded-full px-3 text-[13px] font-medium transition-colors disabled:opacity-60"
            :class="
              kinds.includes(kind)
                ? 'bg-fg text-bg'
                : 'bg-surface-2 text-fg-3 hover:bg-raised'
            "
            :aria-pressed="kinds.includes(kind)"
            :disabled="savingKinds"
            @click="toggleKind(kind)"
          >
            <AppIcon v-if="kinds.includes(kind)" name="check" :size="14" />
            {{ t(`artistReleases.kind.${kind}`) }}
          </button>
        </div>
        <p class="text-[12px] text-pretty text-muted">
          {{ t('artistReleases.kindsHint') }}
        </p>
      </div>

      <UiChips v-model="filter" :items="chips" />

      <section
        v-for="section in sections"
        :key="section.id"
        class="flex flex-col gap-1"
      >
        <h3
          class="text-[11px] font-semibold tracking-[0.06em] text-faint uppercase"
        >
          {{ t(`artistReleases.section.${section.id}`) }}
          <span class="tabular">· {{ section.releases.length }}</span>
        </h3>
        <ul class="flex flex-col divide-y divide-line-2">
          <li
            v-for="release in section.releases"
            :key="release.id"
            class="flex flex-col py-2"
          >
            <div class="flex items-center gap-3">
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
                    [release.year, sourceNames(release)]
                      .filter(Boolean)
                      .join(' · ')
                  }}
                </span>
                <span class="mt-0.5 flex flex-wrap items-center gap-1.5">
                  <UiBadge :tone="stateTone(release.state)">
                    {{ stateLabel(release) }}
                  </UiBadge>
                  <span
                    v-if="release.choice"
                    class="text-[11.5px] text-faint"
                    >{{ t('artistReleases.byYou') }}</span
                  >
                </span>
              </span>
              <button
                type="button"
                class="flex size-8 shrink-0 items-center justify-center rounded-control text-muted hover:bg-raised hover:text-fg"
                :aria-expanded="Boolean(tracks[release.id])"
                :aria-label="t('artistReleases.tracks', { name: release.name })"
                :title="t('artistReleases.tracks', { name: release.name })"
                @click="toggleTracks(release)"
              >
                <AppIcon
                  :name="tracks[release.id] ? 'chevron-up' : 'chevron-down'"
                  :size="16"
                />
              </button>
              <UiSwitch
                v-if="canSwitch(release)"
                :model-value="isOn(release)"
                :aria-label="t('artistReleases.switch', { name: release.name })"
                :disabled="busy.has(release.id)"
                @update:model-value="(on) => toggle(release, on)"
              />
            </div>
            <!-- Its tracks, and which the library has. -->
            <div v-if="tracks[release.id]" class="pt-2 pl-14 text-[13px]">
              <p v-if="tracks[release.id] === 'loading'" class="text-muted">
                …
              </p>
              <p
                v-else-if="!tracks[release.id].length"
                class="text-pretty text-muted"
              >
                {{ t('artistReleases.tracksNotRead') }}
              </p>
              <ol v-else class="flex flex-col gap-1">
                <li
                  v-for="track in tracks[release.id]"
                  :key="track.position"
                  class="flex items-center gap-2"
                >
                  <span class="tabular w-5 shrink-0 text-right text-faint">{{
                    track.position
                  }}</span>
                  <span class="min-w-0 flex-1 truncate">{{ track.name }}</span>
                  <span
                    class="flex shrink-0 items-center gap-1"
                    :class="track.file ? 'text-accent' : 'text-muted'"
                    :title="track.file || ''"
                  >
                    <AppIcon v-if="track.file" name="check" :size="14" />
                    {{
                      track.file
                        ? t('artistReleases.trackHave')
                        : t('artistReleases.trackMissing')
                    }}
                  </span>
                </li>
              </ol>
            </div>
          </li>
        </ul>
      </section>
      <p v-if="!sections.length" class="text-sm text-muted">
        {{ t('artistReleases.noneHere') }}
      </p>
    </div>
  </UiPanel>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import AppIcon from '../ui/AppIcon.vue'
import CoverArt from '../ui/CoverArt.vue'
import UiBadge from '../ui/UiBadge.vue'
import UiButton from '../ui/UiButton.vue'
import UiChips from '../ui/UiChips.vue'
import UiEmpty from '../ui/UiEmpty.vue'
import UiPanel from '../ui/UiPanel.vue'
import UiProgress from '../ui/UiProgress.vue'
import UiSkeleton from '../ui/UiSkeleton.vue'
import UiSwitch from '../ui/UiSwitch.vue'
import monitorAPI from '/src/model/monitor'
import { useUi } from '/src/model/ui'
import {
  FILTERS,
  canSwitch,
  filterCounts,
  isOn,
  sectioned,
  sourceNames,
  stateLabel as releaseStateLabel,
  stateTone,
} from '/src/lib/artistReleases'
import { useI18n } from '/src/i18n'

const props = defineProps({
  watchId: { type: Number, required: true },
})

const { t, locale } = useI18n()
const ui = useUi()

const data = ref(null)
const loading = ref(false)
const error = ref('')
const filter = ref('all')
const busy = ref(new Set())
const savingKinds = ref(false)
const starting = ref(false)
const fetching = ref(false)
// Each opened release's tracks: 'loading', or the list.
const tracks = ref({})
let poll = null

const releases = computed(() => data.value?.releases || [])
const kinds = computed(() => data.value?.kinds || [])
const inventory = computed(() => data.value?.inventory || null)
const missing = computed(
  () => data.value?.missing || { tracks: 0, releases: 0, unread: 0 }
)
const canDownloadMissing = computed(
  () =>
    Boolean(missing.value.tracks || missing.value.unread) &&
    !data.value?.checking &&
    !inventory.value?.running
)
const sections = computed(() => sectioned(releases.value, filter.value))
const counts = computed(() => filterCounts(releases.value))
const chips = computed(() =>
  FILTERS.filter((id) => id === 'all' || counts.value[id]).map((id) => ({
    id,
    label: t(`artistReleases.filter.${id}`),
    count: counts.value[id],
  }))
)

const summary = computed(() => {
  const c = data.value?.counts || {}
  return t('artistReleases.summary', {
    complete: c.complete || 0,
    partly: c.partly || 0,
    missing: c.missing || 0,
  })
})

function stateLabel(release) {
  return releaseStateLabel(release, t, locale.value)
}

function errorOf(err) {
  return err?.response?.data?.detail || t('toast.actionFailed')
}

async function load() {
  loading.value = true
  error.value = ''
  clearTimeout(poll)
  try {
    const { data: body } = await monitorAPI.getArtistReleases(props.watchId)
    data.value = body
    // Follow a running check (or download) until it is done.
    if (body.inventory?.running || body.checking) {
      poll = setTimeout(load, body.checking ? 5000 : 3000)
    }
  } catch (err) {
    error.value = errorOf(err)
  } finally {
    loading.value = false
  }
}

async function checkHave() {
  starting.value = true
  try {
    const { data: body } = await monitorAPI.checkArtistInventory(props.watchId)
    data.value = { ...data.value, inventory: body.inventory }
    clearTimeout(poll)
    poll = setTimeout(load, 1500)
  } catch (err) {
    ui.toast(errorOf(err), { kind: 'error' })
  } finally {
    starting.value = false
  }
}

async function downloadMissing() {
  const { tracks, releases: count, unread } = missing.value
  const ok = await ui.confirm({
    title: t('artistReleases.missingTitle'),
    body: unread
      ? t('artistReleases.missingBodyUnread', { tracks, count, unread })
      : t('artistReleases.missingBody', { tracks, count }),
    confirmLabel: t('artistReleases.missingConfirm'),
  })
  if (!ok) return
  fetching.value = true
  try {
    await monitorAPI.downloadArtistMissing(props.watchId)
    data.value = { ...data.value, checking: true }
    ui.toast(t('artistReleases.missingStarted'), { kind: 'success' })
    clearTimeout(poll)
    poll = setTimeout(load, 3000)
  } catch (err) {
    ui.toast(errorOf(err), { kind: 'error' })
  } finally {
    fetching.value = false
  }
}

async function toggleTracks(release) {
  if (tracks.value[release.id]) {
    const next = { ...tracks.value }
    delete next[release.id]
    tracks.value = next
    return
  }
  tracks.value = { ...tracks.value, [release.id]: 'loading' }
  try {
    const { data: body } = await monitorAPI.getArtistReleaseTracks(
      props.watchId,
      release.album_ids
    )
    tracks.value = { ...tracks.value, [release.id]: body.tracks }
  } catch (err) {
    const next = { ...tracks.value }
    delete next[release.id]
    tracks.value = next
    ui.toast(errorOf(err), { kind: 'error' })
  }
}

async function toggle(release, on) {
  busy.value = new Set([...busy.value, release.id])
  try {
    const { data: body } = await monitorAPI.switchArtistReleases(
      props.watchId,
      release.album_ids,
      on ? 'on' : 'off'
    )
    data.value = body
    ui.toast(
      on
        ? t('artistReleases.switchedOn', { name: release.name })
        : t('artistReleases.switchedOff', { name: release.name }),
      { kind: 'success' }
    )
  } catch (err) {
    ui.toast(errorOf(err), { kind: 'error' })
  } finally {
    const next = new Set(busy.value)
    next.delete(release.id)
    busy.value = next
  }
}

async function toggleKind(kind) {
  const next = kinds.value.includes(kind)
    ? kinds.value.filter((k) => k !== kind)
    : [...kinds.value, kind]
  savingKinds.value = true
  try {
    await monitorAPI.updateMonitoredPlaylist(props.watchId, {
      musicbrainz_kinds: next,
    })
    await load()
  } catch (err) {
    ui.toast(errorOf(err), { kind: 'error' })
  } finally {
    savingKinds.value = false
  }
}

onMounted(load)
onBeforeUnmount(() => clearTimeout(poll))
watch(
  () => props.watchId,
  () => {
    tracks.value = {}
    load()
  }
)

defineExpose({ load })
</script>
