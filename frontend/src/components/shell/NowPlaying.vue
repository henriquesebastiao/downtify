<template>
  <Teleport to="body">
    <Transition name="now-playing">
      <div
        v-if="nowPlaying.isOpen.value && track"
        class="fixed inset-0 z-50 flex flex-col overflow-hidden bg-[#07080b] text-white"
        role="dialog"
        aria-modal="true"
        :aria-label="t('player.nowPlaying')"
      >
        <NowPlayingBackdrop
          :track="track"
          :palette="palette"
          :karaoke="isKaraoke"
          :playing="player.isPlaying.value"
        />

        <div
          class="relative flex h-full flex-col px-5 lg:px-10"
          :class="
            isKaraoke
              ? 'pt-[max(0.5rem,env(safe-area-inset-top))] pb-[max(0.5rem,env(safe-area-inset-bottom))] lg:pt-3 lg:pb-2'
              : 'pt-[max(1rem,env(safe-area-inset-top))] pb-[max(1.25rem,env(safe-area-inset-bottom))] lg:pt-6 lg:pb-8'
          "
        >
          <!-- Header -->
          <header class="relative z-10 flex h-12 shrink-0 items-center gap-3">
            <button
              ref="closeButton"
              type="button"
              class="flex size-10 items-center justify-center rounded-full bg-white/10 transition-colors hover:bg-white/20"
              :aria-label="t('player.closeNowPlaying')"
              @click="nowPlaying.close()"
            >
              <AppIcon name="chevron-down" :size="22" />
            </button>
            <!-- Karaoke gives the body to the words: what's playing moves
                 up here, instead of the "Playing from" label. -->
            <div
              v-if="isKaraoke"
              class="flex min-w-0 flex-1 items-center gap-3"
            >
              <CoverArt
                :src="track.hasCover ? track.cover : ''"
                :name="track.album || track.title"
                rounded="rounded-[9px]"
                :letter-size="18"
                :icon-size="20"
                class="size-11 shrink-0"
              />
              <NowPlayingTrackInfo
                :track="track"
                compact
                @navigate="nowPlaying.close()"
              />
              <LikeButton :file="track.file" size="lg" />
              <span
                v-if="player.playError.value"
                class="flex shrink-0 items-center gap-2 text-sm text-danger"
                :title="t('player.cannotPlay')"
              >
                <AppIcon name="alert" :size="16" />
                <span class="max-xl:sr-only">{{ t('player.cannotPlay') }}</span>
              </span>
            </div>
            <component
              v-else
              :is="contextRoute ? RouterLink : 'div'"
              :to="contextRoute || undefined"
              class="flex min-w-0 items-center gap-2 max-lg:flex-1 max-lg:justify-center"
              @click="contextRoute && nowPlaying.close()"
            >
              <CoverArt
                v-if="
                  context?.type === 'playlist' &&
                  (context.cover || context.covers?.length)
                "
                :src="context.cover || ''"
                :covers="context.covers || []"
                :name="context.title"
                rounded="rounded-[5px]"
                :letter-size="10"
                :icon-size="12"
                class="size-8 shrink-0"
              />
              <span class="flex min-w-0 flex-col">
                <span class="eyebrow !text-white/55">{{ contextLabel }}</span>
                <span class="max-w-full truncate text-sm font-semibold">{{
                  contextTitle
                }}</span>
              </span>
            </component>
            <KaraokeUpNext
              v-if="isKaraoke && nextTrack"
              :track="nextTrack"
              class="hidden xl:block"
            />
            <button
              v-if="isKaraoke"
              type="button"
              class="hidden size-10 shrink-0 items-center justify-center rounded-full bg-white/10 transition-colors hover:bg-white/20 lg:flex"
              :class="{ 'text-accent': karaokeStage.connected.value }"
              :aria-label="t('player.karaokeWindow')"
              :title="t('player.karaokeWindow')"
              @click="openKaraokeWindow"
            >
              <AppIcon name="screen-share" :size="20" />
            </button>
            <div
              class="ml-auto hidden gap-1 rounded-[12px] p-1 lg:flex"
              :class="isKaraoke ? 'bg-black/40' : 'bg-white/8'"
              role="tablist"
            >
              <button
                v-for="tab in panels"
                :key="tab.id"
                type="button"
                role="tab"
                :aria-selected="panel === tab.id"
                class="flex h-9 items-center gap-2 rounded-[9px] px-3.5 text-[13px] transition-colors"
                :class="
                  panel === tab.id
                    ? 'bg-white/15 font-semibold text-white'
                    : 'font-medium text-white/65 hover:text-white'
                "
                @click="setPanel(tab.id)"
              >
                <AppIcon :name="tab.icon" :size="16" />{{ tab.label }}
              </button>
            </div>
            <UiMenu
              :items="trackMenu"
              :label="t('common.more')"
              class="lg:hidden"
            >
              <template #trigger>
                <button
                  type="button"
                  class="flex size-10 items-center justify-center rounded-full hover:bg-white/10"
                  :aria-label="t('common.more')"
                >
                  <AppIcon name="more" :size="22" />
                </button>
              </template>
            </UiMenu>
          </header>

          <!-- Body -->
          <div
            class="grid min-h-0 flex-1 grid-cols-[minmax(0,1fr)] overflow-hidden"
            :class="
              isKaraoke
                ? 'grid-rows-[minmax(0,1fr)] py-1'
                : 'gap-6 py-4 lg:grid-cols-[auto_minmax(0,1fr)] lg:items-stretch lg:gap-10 lg:py-4 xl:grid-cols-[auto_minmax(0,1fr)_minmax(220px,340px)] xl:gap-12'
            "
          >
            <!-- Artwork + title (hidden on phones while a panel is open) -->
            <div
              v-if="!isKaraoke"
              class="now-playing-stage flex h-full min-h-0 w-full min-w-0 max-w-full flex-col justify-center gap-4 overflow-hidden lg:gap-5"
              :class="mobilePanel ? 'max-lg:hidden' : ''"
            >
              <div class="now-playing-cover mx-auto">
                <CoverArt
                  :src="track.hasCover ? track.cover : ''"
                  :name="track.album || track.title"
                  rounded="rounded-[20px]"
                  :letter-size="140"
                  :icon-size="72"
                  class="aspect-square w-full min-h-0 min-w-0 transition-transform duration-500 ease-out-soft"
                  :class="player.isPlaying.value ? 'scale-100' : 'scale-[0.94]'"
                />
              </div>
              <div
                class="flex w-full min-w-0 shrink-0 items-end justify-between gap-4"
              >
                <NowPlayingTrackInfo
                  :track="track"
                  class="flex-1"
                  @navigate="nowPlaying.close()"
                />
                <div class="flex shrink-0 items-center gap-1">
                  <LikeButton
                    v-if="!track?.isPodcast && !track?.stream"
                    :file="track.file"
                    size="lg"
                  />
                  <UiMenu
                    :items="trackMenu"
                    :label="t('common.more')"
                    class="hidden lg:inline-flex"
                  >
                    <template #trigger>
                      <button
                        type="button"
                        class="flex size-10 items-center justify-center rounded-full hover:bg-white/10"
                        :aria-label="t('common.more')"
                      >
                        <AppIcon name="more" :size="22" />
                      </button>
                    </template>
                  </UiMenu>
                </div>
              </div>
              <p
                v-if="player.playError.value"
                class="flex items-center gap-2 text-sm text-danger"
              >
                <AppIcon name="alert" :size="16" />{{ t('player.cannotPlay') }}
              </p>
            </div>

            <!-- Main panel -->
            <div
              class="min-h-0 lg:h-full"
              :class="mobilePanel ? '' : 'max-lg:hidden'"
            >
              <LyricsPanel
                v-if="panel === 'lyrics' || isKaraoke"
                :compact="isMobile"
                :karaoke="isKaraoke"
                :player="player"
              />
              <UpNextPanel v-else-if="panel === 'queue'" />
              <TrackDetails v-else-if="panel === 'details'" class="lg:pt-10" />
              <EqualizerPanel
                v-else-if="panel === 'equalizer'"
                :palette="palette"
              />
            </div>

            <!-- Up next always visible on wide screens -->
            <aside
              v-if="panel !== 'queue' && !isKaraoke"
              class="hidden h-full min-h-0 max-h-full rounded-panel border border-white/10 bg-white/6 p-3 backdrop-blur-xl xl:block"
            >
              <UpNextPanel />
            </aside>
          </div>

          <!-- Transport -->
          <footer
            class="relative z-10 shrink-0"
            :class="{ 'now-playing-footer--karaoke': isKaraoke }"
          >
            <div class="now-playing-seek flex items-center gap-3">
              <span class="tabular w-12 text-xs text-white/65">{{
                formatDuration(scrub ?? player.currentTime.value)
              }}</span>
              <WaveSeekBar
                class="flex-1"
                :model-value="scrub ?? player.currentTime.value"
                :max="player.duration.value || 1"
                :label="t('player.seek')"
                :value-text="formatDuration(player.currentTime.value)"
                :playing="player.isPlaying.value"
                :palette="palette"
                @update:model-value="(v) => (scrub = v)"
                @commit="commitSeek"
              />
              <span class="tabular w-12 text-right text-xs text-white/65">{{
                formatDuration(player.duration.value)
              }}</span>
            </div>

            <div class="now-playing-transport mt-3 flex items-center lg:mt-4">
              <div
                class="now-playing-file hidden flex-1 items-center gap-2 lg:flex"
              >
                <span
                  v-if="track.format"
                  class="rounded-md border border-white/20 px-1.5 py-0.5 text-[11px] font-semibold tracking-wide text-white/75"
                  >{{ track.format }}</span
                >
                <span v-if="track.size" class="text-xs text-white/55">
                  {{ formatBytes(track.size) }}
                </span>
              </div>

              <div
                class="now-playing-controls flex flex-1 items-center justify-between lg:flex-none lg:justify-center lg:gap-7"
              >
                <button
                  v-if="track?.isPodcast"
                  type="button"
                  class="flex size-11 items-center justify-center rounded-full text-white/80 transition-colors hover:bg-white/10"
                  :aria-label="t('podcasts.skipBack')"
                  @click="player.seekBy(-15)"
                >
                  <AppIcon name="skip-back" :size="22" />
                </button>
                <!-- Left of shuffle: tracks like this one
                     (podcasts have none). -->
                <button
                  v-if="similarArtist && similarTitle"
                  type="button"
                  class="flex size-11 items-center justify-center rounded-full text-white/80 transition-colors hover:bg-white/10"
                  :aria-label="t('similar.findSimilar')"
                  @click="goSimilar"
                >
                  <AppIcon name="wand" :size="22" />
                </button>
                <button
                  type="button"
                  class="flex size-11 items-center justify-center rounded-full transition-colors hover:bg-white/10"
                  :class="
                    player.shuffle.value ? 'text-accent' : 'text-white/80'
                  "
                  :aria-label="t('player.shuffle')"
                  :aria-pressed="player.shuffle.value"
                  @click="player.toggleShuffle()"
                >
                  <AppIcon name="shuffle" :size="22" />
                </button>
                <button
                  type="button"
                  class="flex size-13 items-center justify-center rounded-full hover:bg-white/10"
                  :aria-label="t('player.previous')"
                  @click="player.prev()"
                >
                  <AppIcon name="prev" :size="28" />
                </button>
                <button
                  type="button"
                  class="now-playing-play flex items-center justify-center rounded-full bg-white text-[#0b0c0e] shadow-[0_12px_30px_rgba(0,0,0,0.35)] transition-transform hover:scale-105 active:scale-95"
                  :aria-label="
                    player.isPlaying.value
                      ? t('player.pause')
                      : t('player.play')
                  "
                  @click="player.toggle()"
                >
                  <AppIcon
                    :name="player.isPlaying.value ? 'pause' : 'play'"
                    :size="26"
                  />
                </button>
                <button
                  type="button"
                  class="flex size-13 items-center justify-center rounded-full hover:bg-white/10"
                  :aria-label="t('player.next')"
                  @click="player.next()"
                >
                  <AppIcon name="next" :size="28" />
                </button>
                <button
                  v-if="track?.isPodcast"
                  type="button"
                  class="flex size-11 items-center justify-center rounded-full text-white/80 transition-colors hover:bg-white/10"
                  :aria-label="t('podcasts.skipForward')"
                  @click="player.seekBy(30)"
                >
                  <AppIcon name="skip-forward" :size="22" />
                </button>
                <button
                  v-else
                  type="button"
                  class="relative flex size-11 items-center justify-center rounded-full transition-colors hover:bg-white/10"
                  :class="
                    player.repeatMode.value !== 'off'
                      ? 'text-accent'
                      : 'text-white/80'
                  "
                  :aria-label="repeatLabel"
                  @click="player.cycleRepeat()"
                >
                  <AppIcon
                    :name="
                      player.repeatMode.value === 'one'
                        ? 'repeat-one'
                        : 'repeat'
                    "
                    :size="22"
                  />
                </button>
                <!-- Right of repeat: a stream queues its download (once -
                     while queued it spins instead), a downloaded track
                     shows a static check that does nothing. -->
                <button
                  v-if="showPlayerDownload"
                  type="button"
                  class="flex size-11 items-center justify-center rounded-full text-white/80 transition-colors hover:bg-white/10 disabled:opacity-50"
                  :aria-label="t('actions.downloadItem', { name: track.title })"
                  :disabled="downloadBusy"
                  @click="downloadCurrent"
                >
                  <AppIcon
                    :name="downloadBusy ? 'refresh' : 'download'"
                    :size="22"
                    :class="downloadBusy ? 'animate-spin' : ''"
                  />
                </button>
                <span
                  v-else-if="showDownloadedCheck"
                  class="flex size-11 items-center justify-center rounded-full text-accent"
                  :title="t('search.inLibrary')"
                  aria-hidden="true"
                >
                  <AppIcon name="check" :size="22" />
                </span>
              </div>

              <div
                class="now-playing-extras hidden flex-1 items-center justify-end gap-2 lg:flex"
              >
                <UiMenu
                  v-if="track?.isPodcast"
                  :items="speedMenu"
                  :label="t('podcasts.playbackSpeed')"
                >
                  <template #trigger>
                    <button
                      type="button"
                      class="flex h-10 items-center gap-2 rounded-full px-3 text-xs font-semibold text-white/75 transition-colors hover:bg-white/10"
                      :aria-label="t('podcasts.playbackSpeed')"
                    >
                      <AppIcon name="gauge" :size="20" />
                      <span class="tabular">{{ speedLabel }}</span>
                    </button>
                  </template>
                </UiMenu>
                <UiMenu :items="sleepMenu" :label="t('player.sleepTimer')">
                  <template #trigger>
                    <button
                      type="button"
                      class="flex h-10 items-center gap-2 rounded-full px-3 text-xs font-semibold transition-colors hover:bg-white/10"
                      :class="
                        player.sleepAt.value ? 'text-accent' : 'text-white/75'
                      "
                      :aria-label="t('player.sleepTimer')"
                    >
                      <AppIcon name="timer" :size="20" />
                      <span v-if="sleepLabel" class="tabular">{{
                        sleepLabel
                      }}</span>
                    </button>
                  </template>
                </UiMenu>
                <VolumeControl
                  width="w-28"
                  track-class="bg-white/20"
                  fill-class="bg-white"
                  thumb-class="bg-white"
                  class="text-white [&_button]:text-white/80 [&_button:hover]:bg-white/10"
                />
              </div>
            </div>

            <!-- Phone extras -->
            <div
              class="now-playing-phone-extras mt-4 flex items-center justify-between lg:hidden"
            >
              <div class="flex items-center gap-1">
                <UiMenu
                  v-if="track?.isPodcast"
                  :items="speedMenu"
                  :label="t('podcasts.playbackSpeed')"
                  align="start"
                >
                  <template #trigger>
                    <button
                      type="button"
                      class="flex h-10 items-center gap-2 rounded-full px-3 text-xs font-semibold text-white/75"
                      :aria-label="t('podcasts.playbackSpeed')"
                    >
                      <AppIcon name="gauge" :size="20" />
                      <span class="tabular">{{ speedLabel }}</span>
                    </button>
                  </template>
                </UiMenu>
                <UiMenu
                  :items="sleepMenu"
                  :label="t('player.sleepTimer')"
                  align="start"
                >
                  <template #trigger>
                    <button
                      type="button"
                      class="flex h-10 items-center gap-2 rounded-full px-3 text-xs font-semibold"
                      :class="
                        player.sleepAt.value ? 'text-accent' : 'text-white/75'
                      "
                      :aria-label="t('player.sleepTimer')"
                    >
                      <AppIcon name="timer" :size="20" />
                      <span v-if="sleepLabel" class="tabular">{{
                        sleepLabel
                      }}</span>
                    </button>
                  </template>
                </UiMenu>
              </div>
              <div class="flex gap-2">
                <button
                  v-for="tab in panels"
                  :key="tab.id"
                  type="button"
                  class="flex h-10 items-center gap-2 rounded-full px-3.5 text-[13px] font-semibold transition-colors"
                  :class="
                    panel === tab.id && mobilePanel
                      ? 'bg-white text-[#0b0c0e]'
                      : 'bg-white/12 text-white'
                  "
                  :aria-pressed="panel === tab.id && mobilePanel"
                  @click="toggleMobilePanel(tab.id)"
                >
                  <AppIcon :name="tab.icon" :size="16" />
                  <!-- Five tabs don't fit with every label: only the open
                       one keeps it on narrow screens. -->
                  <span
                    :class="
                      panel === tab.id && mobilePanel
                        ? 'max-xs:sr-only'
                        : 'max-md:sr-only'
                    "
                    >{{ tab.label }}</span
                  >
                </button>
              </div>
            </div>
          </footer>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { useMediaQuery, useNow } from '@vueuse/core'
import AppIcon from '../ui/AppIcon.vue'
import CoverArt from '../ui/CoverArt.vue'
import UiMenu from '../ui/UiMenu.vue'
import WaveSeekBar from '../player/WaveSeekBar.vue'
import VolumeControl from '../player/VolumeControl.vue'
import LikeButton from '../player/LikeButton.vue'
import LyricsPanel from '../player/LyricsPanel.vue'
import UpNextPanel from '../player/UpNextPanel.vue'
import TrackDetails from '../player/TrackDetails.vue'
import NowPlayingTrackInfo from '../player/NowPlayingTrackInfo.vue'
import EqualizerPanel from '../player/EqualizerPanel.vue'
import KaraokeUpNext from '../player/KaraokeUpNext.vue'
import NowPlayingBackdrop from '../player/NowPlayingBackdrop.vue'
import { usePlayer } from '/src/model/player'
import { useKaraokeStage } from '/src/model/karaokeStage'
import { useDownloadManager, useProgressTracker } from '/src/model/download'
import { useLibrary } from '/src/model/library'
import { useUi } from '/src/model/ui'
import { usePlayerPrefs } from '/src/model/playerPrefs'
import { useNowPlaying } from '/src/model/ui'
import { formatBytes, formatDuration } from '/src/lib/format'
import { availablePanels, defaultPanel, requestedPanel } from '/src/lib/panels'
import { useCoverPalette } from '/src/model/coverPalette'
import { groupingArtistName } from '/src/lib/library'
import { saveName } from '/src/lib/paths'
import { useBuyLinks } from '/src/model/buyLinks'
import { buyTargetForTrack } from '/src/lib/buyLinks'
import { useI18n } from '/src/i18n'

const player = usePlayer()
const library = useLibrary()
const dm = useDownloadManager()
const tracker = useProgressTracker()
const ui = useUi()
const { showLyrics } = usePlayerPrefs()
const nowPlaying = useNowPlaying()
const buyLinks = useBuyLinks()
const route = useRoute()
const router = useRouter()
const { t } = useI18n()
const isMobile = useMediaQuery('(max-width: 1023px)')
const now = useNow({ interval: 15000 })
const scrub = ref(null)
const closeButton = ref(null)

const track = computed(() => player.currentTrack.value)

// Tracks like this one (podcasts have none): left of shuffle.
const similarArtist = computed(() => {
  if (track.value?.isPodcast) return ''
  return (track.value?.artists || [])[0] || track.value?.artist || ''
})
const similarTitle = computed(
  () => track.value?.name || track.value?.title || ''
)

function goSimilar() {
  const artist = (
    (track.value?.artists || [])[0] ||
    track.value?.artist ||
    ''
  ).trim()
  const title = (track.value?.name || track.value?.title || '').trim()
  if (!artist || !title) return
  router.push({ name: 'Similar', query: { artist, track: title } })
}
const palette = useCoverPalette(track)

const PANEL_TABS = {
  lyrics: { icon: 'lyrics', label: 'player.lyrics' },
  karaoke: { icon: 'mic-vocal', label: 'player.karaoke' },
  queue: { icon: 'queue', label: 'player.upNext' },
  details: { icon: 'info', label: 'player.details' },
  equalizer: { icon: 'equalizer', label: 'player.equalizer' },
}

const panels = computed(() =>
  availablePanels({
    lyrics: showLyrics.value,
    isPodcast: track.value?.isPodcast,
    isStream: track.value?.stream,
  }).map((id) => ({
    id,
    icon: PANEL_TABS[id].icon,
    label: t(PANEL_TABS[id].label),
  }))
)

// ?panel= picks the side panel; phones show it instead of the artwork.
const requested = computed(() =>
  requestedPanel(
    route.query.panel,
    panels.value.map((tab) => tab.id)
  )
)
const panel = computed(
  () =>
    requested.value ||
    defaultPanel({
      lyrics: showLyrics.value,
      isPodcast: track.value?.isPodcast,
      isStream: track.value?.stream,
    })
)
const mobilePanel = computed(() => isMobile.value && !!requested.value)
const isKaraoke = computed(() => panel.value === 'karaoke')
const nextTrack = computed(() => player.upcoming.value[0]?.track || null)
const karaokeStage = useKaraokeStage()

// The words go to the other screen; this one is free to pick the next song.
function openKaraokeWindow() {
  if (karaokeStage.open()) nowPlaying.close()
  else ui.toast(t('player.karaokeWindowBlocked'), { kind: 'error' })
}

function setPanel(id) {
  router.replace({ query: { ...route.query, panel: id } })
}

function toggleMobilePanel(id) {
  if (mobilePanel.value && panel.value === id) {
    const { panel: _panel, ...query } = route.query
    router.replace({ query })
  } else {
    setPanel(id)
  }
}

const context = computed(() => player.context.value)
const contextLabel = computed(() => {
  const type = context.value?.type
  return type ? t(`player.playingFrom.${type}`) : t('player.nowPlaying')
})
const contextTitle = computed(
  () => context.value?.title || track.value?.album || t('player.queue')
)
const contextRoute = computed(() => context.value?.route || null)

const repeatLabel = computed(
  () =>
    ({
      off: t('player.repeatOff'),
      all: t('player.repeatAll'),
      one: t('player.repeatOne'),
    })[player.repeatMode.value]
)

const sleepLabel = computed(() => {
  const at = player.sleepAt.value
  if (!at) return ''
  if (at === 'track') return t('player.sleepEndOfTrackShort')
  const minutes = Math.max(1, Math.ceil((at - now.value.getTime()) / 60000))
  return t('player.minutesLeft', { count: minutes })
})

const SPEEDS = [0.75, 1, 1.25, 1.5, 1.75, 2]
const speedLabel = computed(() => `${player.playbackRate.value}×`)
const speedMenu = computed(() =>
  SPEEDS.map((rate) => ({
    label: `${rate}×`,
    checked: player.playbackRate.value === rate,
    action: () => player.setPlaybackRate(rate),
  }))
)

const sleepMenu = computed(() => [
  { heading: t('player.sleepTimer') },
  ...[15, 30, 45, 60, 90].map((minutes) => ({
    label: t('player.sleepMinutes', { count: minutes }),
    action: () => player.setSleepTimer(minutes),
  })),
  {
    label: t('player.sleepEndOfTrack'),
    checked: player.sleepAt.value === 'track',
    action: () => player.setSleepTimer('track'),
  },
  { divider: true, hidden: !player.sleepAt.value },
  {
    label: t('player.sleepOff'),
    icon: 'x',
    hidden: !player.sleepAt.value,
    action: () => player.setSleepTimer(null),
  },
])

const trackMenu = computed(() => {
  const tr = track.value
  if (!tr) return []
  return [
    {
      label: t('player.goToAlbum'),
      icon: 'disc',
      hidden: !tr.album || tr.isPodcast,
      action: () =>
        navigate({
          name: 'Album',
          query: { artist: tr.albumArtist, title: tr.album },
        }),
    },
    {
      label: t('player.goToArtist'),
      icon: 'user',
      hidden: !groupingArtistName(tr) || tr.isPodcast,
      action: () =>
        navigate({ name: 'Artist', query: { name: groupingArtistName(tr) } }),
    },
    {
      label: t('buy.menu'),
      icon: 'tag',
      hidden: !tr.artist || tr.isPodcast,
      action: () => buyLinks.open(buyTargetForTrack(tr)),
    },
    {
      label: t('library.saveToDevice'),
      icon: 'download',
      hidden: !!tr.stream,
      action: () => saveFile(tr),
    },
    { divider: true },
    {
      label: t('player.details'),
      icon: 'info',
      action: () =>
        isMobile.value ? toggleMobilePanel('details') : setPanel('details'),
    },
  ]
})

function navigate(to) {
  // Leave the overlay first so the new page isn't opened "under" it.
  router.replace({ query: {} }).then(() => router.push(to))
}

function saveFile(tr) {
  const a = document.createElement('a')
  a.href = tr.url
  a.download = saveName(tr.file)
  document.body.appendChild(a)
  a.click()
  a.remove()
}

// A stream that landed in the library while playing (downloaded from
// anywhere) offers deletion instead of another download.
const streamDownloaded = computed(
  () =>
    !!track.value?.stream &&
    library.hasSong(track.value.artist, track.value.title)
)

const showPlayerDownload = computed(
  () => !!track.value?.stream && !streamDownloaded.value
)
// A downloaded track shows a static check where the download button
// was; deleting happens from the library rows.
const showDownloadedCheck = computed(
  () =>
    !!track.value &&
    !track.value.isPodcast &&
    (!track.value.stream || streamDownloaded.value)
)

// The playing stream as a downloadable song: the watch URL is the
// download key (so it can't be queued twice) and the known video id
// pins the exact version, like a resolved search row.
const pendingSong = computed(() => {
  const tr = track.value
  if (!tr?.stream || !tr.video_id) return null
  return {
    name: tr.title,
    artists: tr.artist ? [tr.artist] : [],
    artist: tr.artist || '',
    album_name: tr.album || '',
    cover_url: tr.cover && String(tr.cover).startsWith('http') ? tr.cover : '',
    duration: tr.duration || 0,
    url: `https://music.youtube.com/watch?v=${tr.video_id}`,
    youtube_id: tr.video_id,
  }
})

// The queued/finished job behind the button, if any - while one exists
// the button spins instead of queueing a duplicate.
const downloadJob = computed(() => {
  tracker.queueVersion.value
  return pendingSong.value ? tracker.getBySong(pendingSong.value) : null
})
const downloadBusy = computed(() => {
  const state = downloadJob.value?.state
  return state === 'queued' || state === 'active'
})

/** Queue the playing stream as a download (it keeps streaming). */
function downloadCurrent() {
  const song = pendingSong.value
  if (!song || downloadBusy.value) return
  if (downloadJob.value?.state === 'failed') dm.retry(song)
  else {
    dm.queue(song)
    ui.toast(t('toast.queuedTracks', { count: 1, name: song.name }), {
      kind: 'success',
    })
  }
}

function commitSeek(value) {
  player.seek(value)
  scrub.value = null
}

// Nothing to show once the queue empties.
watch(track, (value) => {
  if (!value && nowPlaying.isOpen.value) nowPlaying.close()
})

watch(
  () => nowPlaying.isOpen.value,
  async (open) => {
    document.documentElement.style.overflow = open ? 'hidden' : ''
    if (open) {
      await nextTick()
      closeButton.value?.focus()
    }
  },
  { immediate: true }
)

onBeforeUnmount(() => {
  document.documentElement.style.overflow = ''
})
</script>
