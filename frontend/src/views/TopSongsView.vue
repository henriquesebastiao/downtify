<template>
  <div>
    <!-- Loading -->
    <div
      v-if="loading"
      class="mx-auto flex max-w-[1680px] flex-col gap-8 px-4 pt-10 sm:px-6 md:flex-row md:items-end lg:px-10"
    >
      <UiSkeleton
        class="size-48 self-center !rounded-full sm:size-56 md:self-auto"
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
        <UiButton icon="refresh" @click="load">{{
          t('common.retry')
        }}</UiButton>
      </UiEmpty>
    </div>

    <div v-else-if="artist" class="animate-rise">
      <CollectionHero
        :title="t('link.topSongsOf', { artist: artist.name })"
        :kicker="kicker"
        :cover="artist.cover_url"
        :name="artist.name"
        icon="user"
        round
      >
        <template #subtitle>
          <span v-if="artist.songs.length" class="tabular">
            {{
              [t('common.tracks', { count: artist.songs.length }), lengthLabel]
                .filter(Boolean)
                .join(' · ')
            }}
          </span>
        </template>
        <template #actions>
          <template v-if="artist.songs.length">
            <UiButton
              v-if="newSongs.length"
              variant="primary"
              size="lg"
              icon="download"
              :loading="submitting"
              @click="download(newSongs)"
            >
              {{
                newSongs.length === artist.songs.length
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
              v-if="newSongs.length && newSongs.length < artist.songs.length"
              variant="ghost"
              size="lg"
              @click="download(artist.songs)"
            >
              {{ t('link.redownloadAll') }}
            </UiButton>
          </template>
          <UiButton variant="plain" size="lg" icon="arrow-up-right" :href="url">
            <span class="max-sm:sr-only">{{ sourceLabel }}</span>
          </UiButton>
        </template>
      </CollectionHero>

      <div
        class="mx-auto flex max-w-[1680px] flex-col gap-6 px-4 sm:px-6 lg:px-10"
      >
        <template v-if="artist.songs.length">
          <div class="rounded-[12px] bg-surface p-4">
            <UiSwitch
              v-model="createPlaylist"
              class="flex-row-reverse"
              :label="t('link.createPlaylist')"
              :description="t('link.createPlaylistHint')"
            />
          </div>

          <div class="flex flex-wrap items-center gap-3">
            <UiChips
              :model-value="allSelected ? 'all' : ''"
              :items="selectionChips"
              @update:model-value="onSelectionChip"
            />
            <span class="ml-auto flex items-center gap-2">
              <span class="tabular text-sm text-muted">{{
                t('library.selectedCount', { count: selected.size })
              }}</span>
              <UiButton
                v-if="selected.size"
                size="sm"
                variant="primary"
                icon="download"
                @click="download(selectedSongs)"
              >
                {{ t('link.downloadSelected') }}
              </UiButton>
            </span>
          </div>

          <ol class="-mx-3 flex flex-col">
            <li
              v-for="row in rows"
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
              <div
                v-if="hasPlays"
                class="hidden w-40 shrink-0 justify-end md:flex"
              >
                <UiBadge
                  v-if="row.song.play_count"
                  :tone="playsBadge(row.song).tone"
                  icon="eye"
                  class="tabular"
                  :title="t(playsBadge(row.song).title)"
                >
                  {{ formatPlayCount(row.song.play_count, locale) }}
                </UiBadge>
              </div>
              <div class="flex w-28 shrink-0 justify-end">
                <DownloadState :song="row.song" />
              </div>
            </li>
          </ol>
        </template>

        <UiEmpty v-else icon="music" :title="t('link.topSongsEmpty')" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppIcon from '/src/components/ui/AppIcon.vue'
import CoverArt from '/src/components/ui/CoverArt.vue'
import UiBadge from '/src/components/ui/UiBadge.vue'
import UiButton from '/src/components/ui/UiButton.vue'
import UiChips from '/src/components/ui/UiChips.vue'
import UiEmpty from '/src/components/ui/UiEmpty.vue'
import UiSkeleton from '/src/components/ui/UiSkeleton.vue'
import UiSwitch from '/src/components/ui/UiSwitch.vue'
import CollectionHero from '/src/components/library/CollectionHero.vue'
import DownloadState from '/src/components/search/DownloadState.vue'
import API from '/src/model/api'
import {
  jobSongKey,
  useDownloadManager,
  useProgressTracker,
} from '/src/model/download'
import { useLibrary } from '/src/model/library'
import { useUi } from '/src/model/ui'
import { classifyInput } from '/src/lib/input'
import { formatPlayCount, formatDuration, splitLength } from '/src/lib/format'
import { topSongsBatchOptions, topSongsPlaylistName } from '/src/lib/topSongs'
import { useI18n } from '/src/i18n'

// How many of the top songs start out selected.
const PRESELECTED = 5

const { t, locale } = useI18n()
const route = useRoute()
const router = useRouter()
const dm = useDownloadManager()
const tracker = useProgressTracker()
const library = useLibrary()
const ui = useUi()

const artist = ref(null)
const loading = ref(false)
const error = ref('')
const submitting = ref(false)
const selected = ref(new Set())
// Off for a first visit; on when this artist's top-songs playlist already
// exists, so later downloads keep feeding it. Once the switch is touched,
// that choice wins.
const playlistChoice = ref(null)
const playlistExists = computed(
  () =>
    !!artist.value && !!library.findPlaylist(topSongsPlaylistName(artist.value))
)
const createPlaylist = computed({
  get: () => playlistChoice.value ?? playlistExists.value,
  set: (value) => {
    playlistChoice.value = value
  },
})

const url = computed(() => String(route.query.url || ''))
const kind = computed(() => classifyInput(url.value))

// The plays column only appears when the list has counts to show.
const hasPlays = computed(() =>
  (artist.value?.songs || []).some((song) => song.play_count)
)

// Spotify reports an exact play count, YouTube Music a rounded one; each
// gets its own colour and tooltip.
function playsBadge(song) {
  return song.source === 'youtube'
    ? { tone: 'ytm', title: 'link.playCountYoutubeMusic' }
    : { tone: 'spotify', title: 'link.playCountSpotify' }
}

function keyOf(song, index) {
  return jobSongKey(song) || `row-${index}`
}

function statusOf(song) {
  tracker.queueVersion.value
  if (tracker.getBySong(song)) return 'queue'
  const name = (song.artists || [])[0] || song.artist
  return library.hasSong(name, song.name) ? 'library' : 'new'
}

const rows = computed(() =>
  (artist.value?.songs || []).map((song, index) => ({
    song,
    index,
    key: keyOf(song, index),
    status: statusOf(song),
  }))
)

// What "Download all" sends: everything not already in the library or the
// queue, in ranking order.
const newSongs = computed(() =>
  rows.value.filter((row) => row.status === 'new').map((row) => row.song)
)

async function load() {
  if (!url.value) return
  loading.value = true
  error.value = ''
  artist.value = null
  selected.value = new Set()
  playlistChoice.value = null
  try {
    const res = await API.artistTopSongs(url.value)
    artist.value = res.data
    selected.value = new Set(
      rows.value.slice(0, PRESELECTED).map((row) => row.key)
    )
  } catch (err) {
    error.value = err?.response?.data?.detail || err?.message || ''
  } finally {
    loading.value = false
  }
}

watch(url, load, { immediate: true })

const sourceLabel = computed(() =>
  kind.value.source === 'spotify'
    ? t('link.openSpotify')
    : t('link.openYoutube')
)

const kicker = computed(() => {
  const source = kind.value.source === 'spotify' ? 'Spotify' : 'YouTube Music'
  return `${source} · ${t('link.topSongs')}`
})

const lengthLabel = computed(() => {
  const total = (artist.value?.songs || []).reduce(
    (sum, song) => sum + (song.duration || 0),
    0
  )
  if (!total) return ''
  const { hours, minutes } = splitLength(total)
  return hours
    ? t('common.lengthHours', { hours, minutes })
    : t('common.lengthMinutes', { minutes })
})

const selectedSongs = computed(() =>
  rows.value.filter((row) => selected.value.has(row.key)).map((row) => row.song)
)

function toggle(key) {
  const next = new Set(selected.value)
  if (next.has(key)) next.delete(key)
  else next.add(key)
  selected.value = next
}

function selectAll() {
  selected.value = new Set(rows.value.map((row) => row.key))
}

const allSelected = computed(
  () => rows.value.length > 0 && selected.value.size === rows.value.length
)

// "Select all" reads as pressed once everything is ticked, like the filter
// chips on the album and playlist pages; "Clear selection" is an action, so
// it only shows up while something is selected.
const selectionChips = computed(() => [
  { id: 'all', label: t('link.selectAll'), count: rows.value.length },
  ...(selected.value.size
    ? [{ id: 'none', label: t('library.clearSelection') }]
    : []),
])

function onSelectionChip(id) {
  if (id === 'all') selectAll()
  else selected.value = new Set()
}

async function download(songs) {
  if (!songs.length) return
  submitting.value = true
  try {
    // The songs go out in ranking order with their rank as the track
    // order, so the M3U keeps the artist's own order even when only some
    // of them are picked.
    const ranked = songs.map((song) => ({
      ...song,
      downtify_track_order: artist.value.songs.indexOf(song),
    }))
    const count = await dm.fromSongs(
      ranked,
      topSongsBatchOptions(artist.value, createPlaylist.value)
    )
    selected.value = new Set()
    ui.toast(t('toast.queuedTracks', { count, name: artist.value.name }), {
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
</script>
