<template>
  <div>
    <!-- Loading -->
    <div
      v-if="loading"
      class="mx-auto flex max-w-[1680px] flex-col gap-8 px-4 pt-10 sm:px-6 md:flex-row md:items-end lg:px-10"
    >
      <UiSkeleton
        class="size-48 self-center !rounded-[16px] sm:size-56 md:self-auto"
      />
      <div class="flex flex-1 flex-col gap-3">
        <UiSkeleton class="h-3 w-32" />
        <UiSkeleton class="h-12 w-2/3" />
        <p class="flex items-center gap-2 text-sm text-muted">
          <span
            class="size-4 animate-spin rounded-full border-2 border-accent border-r-transparent"
          />
          {{ t('link.resolving') }}
        </p>
      </div>
    </div>

    <div
      v-else-if="error"
      class="mx-auto max-w-[1680px] px-4 pt-10 sm:px-6 lg:px-10"
    >
      <UiEmpty icon="alert" :title="t('link.failed')" :body="error">
        <UiButton icon="refresh" @click="resolve">{{
          t('common.retry')
        }}</UiButton>
      </UiEmpty>
    </div>

    <div v-else-if="details" class="animate-rise">
      <CollectionHero
        :title="details.name || t('link.untitled')"
        :kicker="kicker"
        :cover="details.cover_url"
        :covers="details.cover_url ? [] : mosaic"
        :name="details.name"
        :icon="
          details.kind === 'artist'
            ? 'user'
            : details.kind === 'playlist'
              ? 'playlist'
              : 'disc'
        "
        :round="details.kind === 'artist'"
      >
        <template #subtitle>
          <span v-if="details.subtitle" class="line-clamp-2">{{
            details.subtitle
          }}</span>
          <span v-if="details.tracks.length" class="tabular">
            {{
              [
                details.year,
                t('common.tracks', { count: details.tracks.length }),
                lengthLabel,
              ]
                .filter(Boolean)
                .join(' · ')
            }}
          </span>
          <span v-else-if="details.albums.length">
            {{ t('link.releases', { count: details.albums.length }) }}
          </span>
        </template>
        <template #actions>
          <template v-if="details.tracks.length">
            <UiButton
              v-if="newSongs.length"
              variant="primary"
              size="lg"
              icon="download"
              :loading="submitting"
              @click="download(newSongs)"
            >
              {{
                newSongs.length === details.tracks.length
                  ? t('link.downloadAll', { count: newSongs.length })
                  : t('link.downloadNew', { count: newSongs.length })
              }}
            </UiButton>
            <span
              v-else
              class="inline-flex h-12 items-center gap-2 rounded-control bg-accent/12 px-5 text-[15px] font-semibold text-accent"
            >
              <AppIcon name="check-circle" :size="18" />{{
                t('link.allInLibrary')
              }}
            </span>
            <UiButton
              v-if="newSongs.length && newSongs.length < details.tracks.length"
              variant="ghost"
              size="lg"
              @click="download(details.tracks)"
            >
              {{ t('link.redownloadAll') }}
            </UiButton>
          </template>
          <UiButton
            v-if="watchable"
            variant="ghost"
            size="lg"
            icon="radar"
            :loading="watching"
            @click="watch"
          >
            {{
              details.kind === 'artist'
                ? t('link.watchArtist')
                : t('link.watchPlaylist')
            }}
          </UiButton>
          <UiButton variant="plain" size="lg" icon="arrow-up-right" :href="url">
            <span class="max-sm:sr-only">{{ sourceLabel }}</span>
          </UiButton>
        </template>
      </CollectionHero>

      <div
        class="mx-auto flex max-w-[1680px] flex-col gap-6 px-4 sm:px-6 lg:px-10"
      >
        <!-- Tracks -->
        <template v-if="details.tracks.length">
          <div class="flex flex-wrap items-center gap-3">
            <UiChips v-model="filter" :items="filters" />
            <span v-if="selected.size" class="ml-auto flex items-center gap-2">
              <span class="tabular text-sm text-muted">{{
                t('library.selectedCount', { count: selected.size })
              }}</span>
              <UiButton
                size="sm"
                variant="primary"
                icon="download"
                @click="download(selectedSongs)"
              >
                {{ t('link.downloadSelected') }}
              </UiButton>
              <UiIconButton
                icon="x"
                :label="t('library.clearSelection')"
                size="sm"
                @click="selected = new Set()"
              />
            </span>
          </div>
          <ol class="-mx-3 flex flex-col">
            <li
              v-for="row in visibleRows"
              :key="row.key"
              class="group flex h-16 items-center gap-3 rounded-[12px] px-3 transition-colors hover:bg-surface"
              :class="selected.has(row.key) ? 'bg-accent/8' : ''"
            >
              <button
                type="button"
                role="checkbox"
                :aria-checked="selected.has(row.key)"
                :aria-label="t('library.selectTrack', { title: row.song.name })"
                class="flex size-[18px] shrink-0 items-center justify-center rounded-[5px] border-[1.5px] transition-colors"
                :class="
                  selected.has(row.key)
                    ? 'border-accent bg-accent text-on-accent'
                    : 'border-line-3 hover:border-fg-3'
                "
                @click="toggle(row.key)"
              >
                <AppIcon
                  v-if="selected.has(row.key)"
                  name="check"
                  :size="13"
                  stroke-width="3"
                />
              </button>
              <span
                class="tabular w-6 text-center text-[13px] text-faint max-sm:hidden"
                >{{ row.index + 1 }}</span
              >
              <CoverArt
                :src="row.song.cover_url"
                :name="row.song.album_name || row.song.name"
                rounded="rounded-[8px]"
                :letter-size="14"
                class="size-11"
              />
              <div class="min-w-0 flex-1">
                <p class="truncate text-sm font-semibold">
                  {{ row.song.name }}
                </p>
                <p class="truncate text-[13px] text-muted">
                  {{ (row.song.artists || []).join(', ') || row.song.artist }}
                </p>
              </div>
              <span
                class="hidden w-[28%] truncate text-[13px] text-muted lg:block"
                >{{ row.song.album_name }}</span
              >
              <span
                class="tabular hidden w-12 text-right text-[13px] text-muted sm:block"
              >
                {{ row.song.duration ? formatDuration(row.song.duration) : '' }}
              </span>
              <div class="flex w-28 shrink-0 justify-end">
                <DownloadState :song="row.song" />
              </div>
            </li>
          </ol>
          <p
            v-if="!visibleRows.length"
            class="py-10 text-center text-sm text-muted"
          >
            {{ t('library.noMatches') }}
          </p>
        </template>

        <!-- Artist releases -->
        <div
          v-else-if="details.albums.length"
          class="grid grid-cols-2 gap-x-5 gap-y-7 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 2xl:grid-cols-6"
        >
          <ReleaseCard
            v-for="album in details.albums"
            :key="album.album_id || album.url"
            :release="album"
          />
        </div>

        <UiEmpty v-else icon="search" :title="t('link.empty')" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch as watchValue } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppIcon from '/src/components/ui/AppIcon.vue'
import CoverArt from '/src/components/ui/CoverArt.vue'
import UiButton from '/src/components/ui/UiButton.vue'
import UiChips from '/src/components/ui/UiChips.vue'
import UiEmpty from '/src/components/ui/UiEmpty.vue'
import UiIconButton from '/src/components/ui/UiIconButton.vue'
import UiSkeleton from '/src/components/ui/UiSkeleton.vue'
import CollectionHero from '/src/components/library/CollectionHero.vue'
import DownloadState from '/src/components/search/DownloadState.vue'
import ReleaseCard from '/src/components/search/ReleaseCard.vue'
import API from '/src/model/api'
import monitorAPI from '/src/model/monitor'
import {
  jobSongKey,
  useDownloadManager,
  useProgressTracker,
} from '/src/model/download'
import { useLibrary } from '/src/model/library'
import { useUi } from '/src/model/ui'
import { classifyInput } from '/src/lib/input'
import { formatDuration, splitLength } from '/src/lib/format'
import { useI18n } from '/src/i18n'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const dm = useDownloadManager()
const tracker = useProgressTracker()
const library = useLibrary()
const ui = useUi()

const details = ref(null)
const loading = ref(false)
const error = ref('')
const submitting = ref(false)
const watching = ref(false)
const filter = ref('all')
const selected = ref(new Set())

const url = computed(() => String(route.query.url || ''))
const kind = computed(() => classifyInput(url.value))

async function resolve() {
  if (!url.value) return
  loading.value = true
  error.value = ''
  details.value = null
  selected.value = new Set()
  filter.value = 'all'
  try {
    const res = await API.resolveUrl(url.value)
    details.value = res.data
  } catch (err) {
    error.value = err?.response?.data?.detail || err?.message || ''
  } finally {
    loading.value = false
  }
}

watchValue(url, resolve, { immediate: true })

const sourceLabel = computed(() =>
  kind.value.source === 'spotify'
    ? t('link.openSpotify')
    : t('link.openYoutube')
)

const kicker = computed(() => {
  const source = kind.value.source === 'spotify' ? 'Spotify' : 'YouTube Music'
  return `${source} · ${t(`link.kind.${details.value?.kind || 'track'}`)}`
})

const watchable = computed(
  () => details.value?.kind === 'playlist' || details.value?.kind === 'artist'
)

const mosaic = computed(() =>
  [
    ...new Set(
      (details.value?.tracks || [])
        .map((song) => song.cover_url)
        .filter(Boolean)
    ),
  ].slice(0, 4)
)

const lengthLabel = computed(() => {
  const total = (details.value?.tracks || []).reduce(
    (sum, song) => sum + (song.duration || 0),
    0
  )
  if (!total) return ''
  const { hours, minutes } = splitLength(total)
  return hours
    ? t('common.lengthHours', { hours, minutes })
    : t('common.lengthMinutes', { minutes })
})

function keyOf(song, index) {
  return jobSongKey(song) || `row-${index}`
}

function statusOf(song) {
  tracker.queueVersion.value
  if (tracker.getBySong(song)) return 'queue'
  const artist = (song.artists || [])[0] || song.artist
  return library.hasSong(artist, song.name) ? 'library' : 'new'
}

const rows = computed(() =>
  (details.value?.tracks || []).map((song, index) => ({
    song,
    index,
    key: keyOf(song, index),
    status: statusOf(song),
  }))
)

const newSongs = computed(() =>
  rows.value.filter((row) => row.status === 'new').map((row) => row.song)
)

const filters = computed(() => {
  const count = (status) =>
    rows.value.filter((row) => row.status === status).length
  return [
    { id: 'all', label: t('link.filterAll'), count: rows.value.length },
    { id: 'new', label: t('link.filterNew'), count: count('new') },
    { id: 'library', label: t('link.filterLibrary'), count: count('library') },
    { id: 'queue', label: t('link.filterQueue'), count: count('queue') },
  ].filter((item) => item.id === 'all' || item.count)
})

const visibleRows = computed(() =>
  filter.value === 'all'
    ? rows.value
    : rows.value.filter((row) => row.status === filter.value)
)

const selectedSongs = computed(() =>
  rows.value.filter((row) => selected.value.has(row.key)).map((row) => row.song)
)

function toggle(key) {
  const next = new Set(selected.value)
  if (next.has(key)) next.delete(key)
  else next.add(key)
  selected.value = next
}

async function download(songs) {
  if (!songs.length) return
  submitting.value = true
  try {
    const isPlaylist = details.value.kind === 'playlist'
    // Keep the playlist's own order for the M3U even when only some
    // tracks are sent.
    const withOrder = songs.map((song) => ({
      ...song,
      downtify_track_order: details.value.tracks.indexOf(song),
    }))
    const count = await dm.fromSongs(withOrder, {
      playlistUrl: isPlaylist ? url.value : '',
    })
    selected.value = new Set()
    ui.toast(t('toast.queuedTracks', { count, name: details.value.name }), {
      kind: 'success',
      action: {
        label: t('nav.queue'),
        run: () => router.push({ name: 'Queue' }),
      },
    })
  } catch (err) {
    ui.toast(err?.response?.data?.detail || t('toast.actionFailed'), {
      kind: 'error',
    })
  } finally {
    submitting.value = false
  }
}

async function watch() {
  watching.value = true
  try {
    await monitorAPI.addMonitoredPlaylist(url.value, 360)
    ui.toast(t('toast.watching', { name: details.value.name }), {
      kind: 'success',
      action: {
        label: t('nav.monitor'),
        run: () => router.push({ name: 'Monitor' }),
      },
    })
  } catch (err) {
    ui.toast(err?.response?.data?.detail || t('toast.actionFailed'), {
      kind: 'error',
    })
  } finally {
    watching.value = false
  }
}
</script>
