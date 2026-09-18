<template>
  <div
    class="mx-auto flex max-w-[1680px] flex-col gap-10 px-4 pt-6 sm:px-6 md:pt-8 lg:px-10"
  >
    <!-- Hero: paste or search -->
    <div
      class="grid gap-4 animate-rise lg:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)]"
    >
      <section
        class="relative flex flex-col gap-5 overflow-hidden rounded-panel border border-line-2 bg-surface p-6 sm:p-8"
      >
        <div
          class="pointer-events-none absolute -top-24 -right-24 size-72 rounded-full bg-accent/10 blur-3xl"
          aria-hidden="true"
        />
        <div class="relative flex flex-col gap-1.5">
          <h1 class="text-display text-3xl font-bold sm:text-[32px]">
            {{ greeting }}
          </h1>
          <p class="text-[15px] text-muted">{{ t('home.lead') }}</p>
        </div>
        <form
          class="relative flex flex-col gap-2 sm:flex-row"
          @submit.prevent="submit"
        >
          <label
            class="flex h-14 min-w-0 flex-none items-center gap-3 rounded-[14px] sm:flex-1 border bg-bg px-4 transition-colors focus-within:border-accent"
            :class="kind.type === 'link' ? 'border-accent/60' : 'border-line-3'"
          >
            <AppIcon
              :name="kind.type === 'link' ? 'link' : 'search'"
              :size="20"
              :class="kind.type === 'link' ? 'text-accent' : 'text-faint'"
            />
            <span class="sr-only">{{ t('home.inputLabel') }}</span>
            <input
              v-model="text"
              type="text"
              enterkeyhint="go"
              autocomplete="off"
              :placeholder="t('home.inputPlaceholder')"
              class="h-full min-w-0 flex-1 bg-transparent text-[15px] outline-none placeholder:text-faint"
            />
          </label>
          <UiButton
            type="submit"
            variant="primary"
            size="lg"
            class="!h-14 sm:!px-6"
            :icon="kind.type === 'link' ? 'download' : 'search'"
            :disabled="kind.type === 'empty'"
          >
            {{
              kind.type === 'link' ? t('home.getIt') : t('search.searchButton')
            }}
          </UiButton>
        </form>
        <p v-if="unsupported" class="relative -mt-2 text-[13px] text-danger">
          {{ unsupported }}
        </p>
        <div
          class="relative flex flex-wrap items-center gap-x-5 gap-y-2 text-xs text-faint"
        >
          <span class="flex items-center gap-1.5">
            <AppIcon name="spotify" :size="14" class="text-spotify" />{{
              t('home.hintSpotify')
            }}
          </span>
          <span class="flex items-center gap-1.5">
            <AppIcon name="youtube" :size="14" class="text-src-ytm" />{{
              t('home.hintYoutube')
            }}
          </span>
          <button
            type="button"
            class="flex items-center gap-1.5 hover:text-fg"
            @click="csvPicker?.click()"
          >
            <AppIcon name="file-music" :size="14" />{{ t('home.hintCsv') }}
          </button>
          <input
            ref="csvPicker"
            type="file"
            accept=".csv,text/csv"
            class="hidden"
            @change="importCsv"
          />
        </div>
      </section>

      <section
        class="flex flex-col gap-4 rounded-panel border border-line-2 bg-surface p-6"
      >
        <div class="flex items-center justify-between">
          <h2 class="text-[15px] font-semibold">
            {{ pending ? t('home.downloading') : t('home.yourLibrary') }}
          </h2>
          <RouterLink
            :to="{ name: pending ? 'Queue' : 'Library' }"
            class="text-[13px] font-semibold text-accent hover:text-accent-hi"
            >{{
              pending ? t('home.openQueue') : t('home.openLibrary')
            }}</RouterLink
          >
        </div>

        <template v-if="pending">
          <ul class="flex flex-col gap-3">
            <li
              v-for="item in activeItems"
              :key="item.key"
              class="flex items-center gap-3"
            >
              <CoverArt
                :src="item.song.cover_url"
                :name="item.song.album_name || item.song.name"
                rounded="rounded-[8px]"
                :letter-size="13"
                class="size-11"
              />
              <div class="min-w-0 flex-1">
                <div class="flex items-center justify-between gap-2">
                  <span class="truncate text-[13px] font-semibold">{{
                    item.song.name
                  }}</span>
                  <SourceBadge
                    v-if="item.provider"
                    :source="item.provider"
                    compact
                  />
                </div>
                <UiProgress
                  class="mt-2"
                  :value="item.progress"
                  :indeterminate="!item.progress"
                />
              </div>
            </li>
          </ul>
          <p
            v-if="waiting"
            class="border-t border-line pt-3 text-[13px] text-muted"
          >
            {{ t('home.waiting', { count: waiting }) }}
          </p>
        </template>

        <dl v-else class="grid grid-cols-2 gap-4">
          <div
            v-for="stat in stats"
            :key="stat.label"
            class="flex flex-col gap-0.5"
          >
            <dt class="text-xs text-muted">{{ stat.label }}</dt>
            <dd class="text-display tabular text-2xl font-semibold">
              {{ stat.value }}
            </dd>
          </div>
        </dl>
      </section>
    </div>

    <!-- Jump back in -->
    <section
      v-if="history.recent.value.length"
      class="flex flex-col gap-4 animate-rise [animation-delay:80ms]"
    >
      <h2 class="text-display text-xl font-semibold">
        {{ t('home.jumpBackIn') }}
      </h2>
      <div class="grid gap-2.5 sm:grid-cols-2 xl:grid-cols-3">
        <RouterLink
          v-for="entry in history.recent.value.slice(0, 6)"
          :key="entry.id"
          :to="entry.route || { name: 'Home' }"
          class="group flex h-16 items-center gap-3 overflow-hidden rounded-[12px] bg-surface pr-3 transition-colors hover:bg-surface-2"
        >
          <CoverArt
            :src="entry.cover"
            :name="entry.title"
            :icon="
              entry.type === 'artist'
                ? 'user'
                : entry.type === 'playlist'
                  ? 'playlist'
                  : 'disc'
            "
            rounded="rounded-none"
            :letter-size="18"
            :icon-size="20"
            class="size-16"
          />
          <span class="flex min-w-0 flex-1 flex-col">
            <span class="truncate text-sm font-semibold">{{
              entry.title
            }}</span>
            <span class="truncate text-xs text-muted">
              {{ t(`home.kind.${entry.type}`)
              }}<template v-if="entry.subtitle">
                · {{ entry.subtitle }}</template
              >
            </span>
          </span>
          <EqBars v-if="isPlaying(entry)" :size="12" />
        </RouterLink>
      </div>
    </section>

    <!-- Recently added -->
    <section
      v-if="recentAlbums.length"
      class="flex flex-col gap-4 animate-rise [animation-delay:160ms]"
    >
      <div class="flex items-baseline justify-between gap-4">
        <h2 class="text-display text-xl font-semibold">
          {{ t('home.recentlyAdded') }}
        </h2>
        <RouterLink
          :to="{ name: 'Library', params: { tab: 'albums' } }"
          class="text-[13px] font-semibold text-muted hover:text-fg"
          >{{ t('common.seeAll') }}</RouterLink
        >
      </div>
      <div
        class="grid grid-cols-2 gap-x-5 gap-y-7 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 2xl:grid-cols-6"
      >
        <MediaTile
          v-for="album in recentAlbums"
          :key="album.key"
          :to="{
            name: 'Album',
            query: { artist: album.artist, title: album.title },
          }"
          :title="album.title"
          :subtitle="[album.artist, album.year].filter(Boolean).join(' · ')"
          :cover="album.cover"
          :name="album.title"
          @play="playAlbum(album)"
        />
      </div>
    </section>

    <!-- Playlists -->
    <section
      v-if="recentPlaylists.length"
      class="flex flex-col gap-4 animate-rise [animation-delay:240ms]"
    >
      <div class="flex items-baseline justify-between gap-4">
        <h2 class="text-display text-xl font-semibold">
          {{ t('home.playlists') }}
        </h2>
        <RouterLink
          :to="{ name: 'Library', params: { tab: 'playlists' } }"
          class="text-[13px] font-semibold text-muted hover:text-fg"
          >{{ t('common.seeAll') }}</RouterLink
        >
      </div>
      <div
        class="grid grid-cols-2 gap-x-5 gap-y-7 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 2xl:grid-cols-6"
      >
        <MediaTile
          v-for="playlist in recentPlaylists"
          :key="playlist.key"
          :to="{ name: 'Playlist', query: { name: playlist.name } }"
          :title="playlist.name"
          :subtitle="t('common.tracks', { count: playlist.tracks.length })"
          :cover="playlist.cover"
          :covers="playlist.covers"
          :name="playlist.name"
          icon="playlist"
          @play="playlistActions.play(playlist)"
        />
      </div>
    </section>

    <!-- First run -->
    <section
      v-if="library.loaded.value && !library.tracks.value.length"
      class="grid gap-4 md:grid-cols-3"
    >
      <div
        v-for="(step, i) in onboarding"
        :key="step.title"
        class="flex flex-col gap-2 rounded-panel border border-dashed border-line-3 p-5"
      >
        <span class="text-display tabular text-sm font-semibold text-accent"
          >0{{ i + 1 }}</span
        >
        <p class="text-[15px] font-semibold">{{ step.title }}</p>
        <p class="text-[13px] text-pretty text-muted">{{ step.body }}</p>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import AppIcon from '/src/components/ui/AppIcon.vue'
import CoverArt from '/src/components/ui/CoverArt.vue'
import EqBars from '/src/components/ui/EqBars.vue'
import SourceBadge from '/src/components/ui/SourceBadge.vue'
import UiButton from '/src/components/ui/UiButton.vue'
import UiProgress from '/src/components/ui/UiProgress.vue'
import MediaTile from '/src/components/library/MediaTile.vue'
import { useDownloadManager, useProgressTracker } from '/src/model/download'
import { useHistory } from '/src/model/history'
import { useLibrary } from '/src/model/library'
import { usePlayer } from '/src/model/player'
import { usePlaylistActions } from '/src/model/playlistActions'
import { useTrackActions } from '/src/model/trackActions'
import { useUi } from '/src/model/ui'
import { classifyInput } from '/src/lib/input'
import { formatBytes } from '/src/lib/format'
import { useI18n } from '/src/i18n'

const { t } = useI18n()
const router = useRouter()
const library = useLibrary()
const history = useHistory()
const player = usePlayer()
const tracker = useProgressTracker()
const dm = useDownloadManager()
const actions = useTrackActions()
const playlistActions = usePlaylistActions()
const ui = useUi()

const text = ref('')
const unsupported = ref('')
const csvPicker = ref(null)
const kind = computed(() => classifyInput(text.value))

const greeting = computed(() => {
  const hour = new Date().getHours()
  if (hour < 5) return t('home.greetingNight')
  if (hour < 12) return t('home.greetingMorning')
  if (hour < 18) return t('home.greetingAfternoon')
  return t('home.greetingEvening')
})

function submit() {
  unsupported.value = ''
  const result = kind.value
  if (result.type === 'link') {
    router.push({ name: 'Link', query: { url: result.url } })
  } else if (result.type === 'search') {
    router.push({ name: 'Search', params: { query: result.query } })
  } else if (result.type === 'unsupported') {
    unsupported.value =
      result.kind === 'artist' && result.source === 'spotify'
        ? t('search.spotifyArtistUnsupported')
        : t('search.unsupportedLink')
  }
}

async function importCsv(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) return
  try {
    const result = await dm.fromCsvFile(file, file.name.replace(/\.csv$/i, ''))
    ui.toast(t('toast.csvQueued', { count: result?.count ?? 0 }), {
      kind: 'success',
    })
    router.push({ name: 'Queue', params: { tab: 'queued' } })
  } catch (err) {
    ui.toast(err?.response?.data?.detail || t('queue.importFailed'), {
      kind: 'error',
    })
  }
}

const queueItems = computed(() => {
  tracker.queueVersion.value
  return tracker.downloadQueue.value
})
const activeItems = computed(() =>
  queueItems.value.filter((item) => item.state === 'active').slice(0, 3)
)
const waiting = computed(
  () => queueItems.value.filter((item) => item.state === 'queued').length
)
const pending = computed(() => activeItems.value.length + waiting.value)

const stats = computed(() => [
  {
    label: t('library.tracks'),
    value: library.tracks.value.length.toLocaleString(),
  },
  {
    label: t('library.albums'),
    value: library.albums.value.length.toLocaleString(),
  },
  {
    label: t('library.artists'),
    value: library.artists.value.length.toLocaleString(),
  },
  { label: t('home.size'), value: formatBytes(library.totalSize.value) },
])

const recentAlbums = computed(() =>
  [...library.albums.value].sort((a, b) => b.added - a.added).slice(0, 12)
)
const recentPlaylists = computed(() =>
  [...library.playlists.value]
    .filter((playlist) => playlist.tracks.length)
    .sort((a, b) => b.added - a.added)
    .slice(0, 6)
)

function isPlaying(entry) {
  const ctx = player.context.value
  return (
    player.isPlaying.value &&
    ctx?.type === entry.type &&
    ctx?.title === entry.title
  )
}

function playAlbum(album) {
  actions.play(album.tracks, 0, {
    type: 'album',
    title: album.title,
    subtitle: album.artist,
    cover: album.cover,
    route: {
      name: 'Album',
      query: { artist: album.artist, title: album.title },
    },
  })
}

const onboarding = computed(() => [
  { title: t('home.step1Title'), body: t('home.step1Body') },
  { title: t('home.step2Title'), body: t('home.step2Body') },
  { title: t('home.step3Title'), body: t('home.step3Body') },
])
</script>
