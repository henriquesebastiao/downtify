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
          <UiButton
            v-if="artist.songs.length"
            variant="primary"
            size="lg"
            icon="download"
            :loading="submitting"
            :disabled="!selectedSongs.length"
            @click="download"
          >
            {{ t('link.downloadSelected') }}
          </UiButton>
          <UiButton
            variant="ghost"
            size="lg"
            icon="arrow-left"
            :to="{ name: 'Link', query: { url } }"
          >
            {{ artist.name }}
          </UiButton>
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

          <div class="flex flex-wrap items-center gap-2">
            <UiButton size="sm" variant="ghost" @click="selectAll">
              {{ t('link.selectAll') }}
            </UiButton>
            <UiButton
              v-if="selected.size"
              size="sm"
              variant="ghost"
              @click="selected = new Set()"
            >
              {{ t('library.clearSelection') }}
            </UiButton>
            <span class="tabular ml-auto text-sm text-muted">{{
              t('library.selectedCount', { count: selected.size })
            }}</span>
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
import UiButton from '/src/components/ui/UiButton.vue'
import UiEmpty from '/src/components/ui/UiEmpty.vue'
import UiSkeleton from '/src/components/ui/UiSkeleton.vue'
import UiSwitch from '/src/components/ui/UiSwitch.vue'
import CollectionHero from '/src/components/library/CollectionHero.vue'
import DownloadState from '/src/components/search/DownloadState.vue'
import API from '/src/model/api'
import { jobSongKey, useDownloadManager } from '/src/model/download'
import { useUi } from '/src/model/ui'
import { classifyInput } from '/src/lib/input'
import { formatDuration, splitLength } from '/src/lib/format'
import { useI18n } from '/src/i18n'

// How many of the top songs start out selected.
const PRESELECTED = 5

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const dm = useDownloadManager()
const ui = useUi()

const artist = ref(null)
const loading = ref(false)
const error = ref('')
const submitting = ref(false)
const selected = ref(new Set())
const createPlaylist = ref(false)

const url = computed(() => String(route.query.url || ''))
const kind = computed(() => classifyInput(url.value))

function keyOf(song, index) {
  return jobSongKey(song) || `row-${index}`
}

const rows = computed(() =>
  (artist.value?.songs || []).map((song, index) => ({
    song,
    index,
    key: keyOf(song, index),
  }))
)

async function load() {
  if (!url.value) return
  loading.value = true
  error.value = ''
  artist.value = null
  selected.value = new Set()
  createPlaylist.value = false
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

async function download() {
  const songs = selectedSongs.value
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
    const count = await dm.fromSongs(ranked, {
      playlistName: `Top Songs of ${artist.value.name}`,
      coverUrl: createPlaylist.value ? artist.value.cover_url : '',
      m3u: createPlaylist.value,
    })
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
