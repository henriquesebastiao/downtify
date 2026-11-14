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
                  [release.year, sourceNames(release)]
                    .filter(Boolean)
                    .join(' · ')
                }}
              </span>
              <span class="mt-0.5 flex flex-wrap items-center gap-1.5">
                <UiBadge :tone="stateTone(release.state)">
                  {{ stateLabel(release) }}
                </UiBadge>
                <span v-if="release.choice" class="text-[11.5px] text-faint">{{
                  t('artistReleases.byYou')
                }}</span>
              </span>
            </span>
            <UiSwitch
              v-if="canSwitch(release)"
              :model-value="isOn(release)"
              :aria-label="t('artistReleases.switch', { name: release.name })"
              :disabled="busy.has(release.id)"
              @update:model-value="(on) => toggle(release, on)"
            />
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
import { computed, onMounted, ref, watch } from 'vue'
import AppIcon from '../ui/AppIcon.vue'
import CoverArt from '../ui/CoverArt.vue'
import UiBadge from '../ui/UiBadge.vue'
import UiChips from '../ui/UiChips.vue'
import UiEmpty from '../ui/UiEmpty.vue'
import UiPanel from '../ui/UiPanel.vue'
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
  stateTone,
} from '/src/lib/artistReleases'
import { useI18n } from '/src/i18n'

const props = defineProps({
  watchId: { type: Number, required: true },
})

const { t } = useI18n()
const ui = useUi()

const data = ref(null)
const loading = ref(false)
const error = ref('')
const filter = ref('all')
const busy = ref(new Set())
const savingKinds = ref(false)

const releases = computed(() => data.value?.releases || [])
const kinds = computed(() => data.value?.kinds || [])
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
  if (release.state === 'complete' || release.state === 'partly') {
    return t(`artistReleases.state.${release.state}`, {
      have: release.have,
      total: release.total || '?',
    })
  }
  return t(`artistReleases.state.${release.state}`)
}

function errorOf(err) {
  return err?.response?.data?.detail || t('toast.actionFailed')
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const { data: body } = await monitorAPI.getArtistReleases(props.watchId)
    data.value = body
  } catch (err) {
    error.value = errorOf(err)
  } finally {
    loading.value = false
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
watch(() => props.watchId, load)

defineExpose({ load })
</script>
