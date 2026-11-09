<template>
  <Transition name="now-playing">
    <div
      v-if="visible"
      ref="bar"
      class="relative flex h-16 items-center gap-3 overflow-hidden rounded-[16px] border border-line-3 bg-glass pr-2 pl-2 shadow-float backdrop-blur-xl md:h-[76px] md:gap-5 md:rounded-[18px] md:pr-5 md:pl-3"
      :class="{ 'adjustable-player': wide }"
      :style="grid"
      @keydown.esc="onEscape"
    >
      <!-- Progress: a hairline on phones, a scrubber on desktop. -->
      <div class="absolute inset-x-3 bottom-0 h-0.5 bg-line-2 md:hidden">
        <div class="h-full bg-accent" :style="{ width: `${smoothPercent}%` }" />
      </div>
      <div class="absolute inset-x-0 -top-2 hidden md:block">
        <SliderBar
          :model-value="scrub ?? player.currentTime.value"
          :max="player.duration.value || 1"
          :label="t('player.seek')"
          :value-text="formatDuration(player.currentTime.value)"
          :hit-height="16"
          :playing="player.isPlaying.value"
          track-class="bg-transparent"
          fill-class="bg-accent"
          thumb-class="bg-accent"
          @update:model-value="(v) => (scrub = v)"
          @commit="commitSeek"
        />
      </div>

      <!-- The heart sits beside the button that opens Now playing, not
           inside it, so tapping it never opens the overlay. -->
      <div
        id="mini-player-track"
        class="track-section flex min-w-0 flex-1 items-center gap-1 md:w-[300px] md:flex-none"
        :style="sectionStyle(0)"
      >
        <button
          type="button"
          class="flex min-w-0 flex-1 items-center gap-3 text-left"
          :aria-label="t('player.openNowPlaying')"
          @click="nowPlaying.open()"
        >
          <CoverArt
            :thumb="150"
            :src="track.hasCover ? track.cover : ''"
            :name="track.album || track.title"
            rounded="rounded-[10px]"
            :letter-size="18"
            :icon-size="18"
            class="track-art size-11 md:size-[52px]"
          />
          <span class="flex min-w-0 flex-col">
            <span class="flex items-center gap-2">
              <span class="truncate text-sm font-semibold">{{
                track.title
              }}</span>
              <ExplicitBadge v-if="track.explicit" />
              <EqBars
                v-if="player.isPlaying.value"
                :size="10"
                class="hidden md:inline-flex"
              />
            </span>
            <span class="truncate text-xs text-muted">
              {{ [track.artist, track.album].filter(Boolean).join(' · ') }}
            </span>
          </span>
        </button>
        <!-- Phones have no room for it beside the transport buttons;
             the rows and the full player carry the heart there. -->
        <span
          v-if="!track?.isPodcast && !track?.stream"
          class="hidden sm:contents"
          ><LikeButton class="track-like" :file="track.file"
        /></span>
      </div>

      <PlayerDivider
        v-if="wide"
        :editable="unlocked"
        :label="t('player.resizeTrackSection')"
        controls="mini-player-track"
        :limits="limits(0)"
        @pointerdown="startDrag($event, 0)"
        @pointermove="moveDrag"
        @pointerup="endDrag"
        @pointercancel="cancelPointer"
        @lostpointercapture="cancelPointer"
        @keydown="resizeOnKey($event, 0)"
      />

      <div
        id="mini-player-transport"
        class="transport-section flex items-center justify-center gap-1 md:flex-1 md:gap-3"
        :style="sectionStyle(1)"
      >
        <UiIconButton
          v-if="canSimilar"
          icon="wand"
          :label="t('similar.findSimilar')"
          @click="goSimilar"
        />
        <UiIconButton
          icon="shuffle"
          :label="t('player.shuffle')"
          :active="player.shuffle.value"
          toggle
          class="hidden md:inline-flex"
          @click="player.toggleShuffle()"
        />
        <UiIconButton
          icon="prev"
          :label="t('player.previous')"
          class="hidden md:inline-flex"
          @click="player.prev()"
        />
        <button
          type="button"
          class="play-button flex size-11 items-center justify-center rounded-full text-fg md:bg-invert md:text-on-invert md:transition-transform md:hover:scale-105"
          :aria-label="
            player.isPlaying.value ? t('player.pause') : t('player.play')
          "
          @click="player.toggle()"
        >
          <span
            v-if="player.isBuffering.value && player.isPlaying.value"
            class="size-4 animate-spin rounded-full border-2 border-current border-r-transparent"
          />
          <AppIcon
            v-else
            :name="player.isPlaying.value ? 'pause' : 'play'"
            :size="18"
          />
        </button>
        <UiIconButton
          icon="next"
          :label="t('player.next')"
          @click="player.next()"
        />
        <UiIconButton
          :icon="player.repeatMode.value === 'one' ? 'repeat-one' : 'repeat'"
          :label="repeatLabel"
          :active="player.repeatMode.value !== 'off'"
          toggle
          class="hidden md:inline-flex"
          @click="player.cycleRepeat()"
        />
        <UiIconButton
          v-if="showMiniDownload"
          :icon="downloadBusy ? 'refresh' : 'download'"
          :label="t('actions.downloadItem', { name: trackTitle })"
          :disabled="downloadBusy"
          :class="downloadBusy ? '[&_svg]:animate-spin' : ''"
          @click="downloadCurrent"
        />
        <!-- Downloaded tracks show a static check in the download
             button's slot: it does nothing, deleting happens from the
             library rows. -->
        <span
          v-if="showDownloadedCheck"
          class="downloaded-check inline-flex size-10 shrink-0 items-center justify-center text-accent"
          :title="t('search.inLibrary')"
          aria-hidden="true"
        >
          <AppIcon name="check" :size="18" />
        </span>
      </div>

      <PlayerDivider
        v-if="wide"
        :editable="unlocked"
        :label="t('player.resizeTransportSection')"
        controls="mini-player-transport"
        :limits="limits(1)"
        @pointerdown="startDrag($event, 1)"
        @pointermove="moveDrag"
        @pointerup="endDrag"
        @pointercancel="cancelPointer"
        @lostpointercapture="cancelPointer"
        @keydown="resizeOnKey($event, 1)"
      />

      <div
        class="utility-section hidden items-center justify-end gap-1 md:flex md:w-[300px]"
        :style="sectionStyle(2)"
      >
        <!-- Never wraps, and keeps one width for the whole track: the
             invisible copy is the widest the text will get, so the
             controls beside it don't shift as it ticks past 10:00. -->
        <span
          class="player-clock tabular mr-2 hidden shrink-0 text-xs whitespace-nowrap text-muted lg:inline-grid"
        >
          <span class="invisible col-start-1 row-start-1" aria-hidden="true">{{
            clockSizer
          }}</span>
          <span class="col-start-1 row-start-1 text-right"
            >{{ formatDuration(player.currentTime.value) }} /
            {{ formatDuration(player.duration.value) }}</span
          >
        </span>
        <UiIconButton
          v-if="showLyrics"
          icon="lyrics"
          :label="t('player.lyrics')"
          size="sm"
          @click="nowPlaying.open('lyrics')"
        />
        <UiIconButton
          icon="queue"
          :label="t('player.upNext')"
          size="sm"
          @click="nowPlaying.open('queue')"
        />
        <!-- The slider is what gives when the row is tight, so the time
             next to it never has to. -->
        <VolumeControl
          class="player-volume hidden min-w-0 lg:flex"
          :width="wide ? 'min-w-8 flex-1' : 'w-20 min-w-8'"
        />
        <UiIconButton
          icon="expand"
          :label="t('player.openNowPlaying')"
          size="sm"
          @click="nowPlaying.open()"
        />
      </div>

      <div v-if="wide" class="flex items-center gap-1 pl-1">
        <UiIconButton
          :icon="unlocked ? 'unlock' : 'lock'"
          :label="t(unlocked ? 'player.lockLayout' : 'player.unlockLayout')"
          :active="unlocked"
          size="sm"
          @click="toggleLayout"
        />
        <UiIconButton
          v-if="unlocked"
          icon="refresh"
          :label="t('player.resetLayout')"
          size="sm"
          @click="reset"
        />
      </div>
    </div>
  </Transition>
</template>

<script setup>
import { computed, nextTick, ref } from 'vue'
import { useMediaQuery } from '@vueuse/core'
import { useRouter } from 'vue-router'
import AppIcon from '../ui/AppIcon.vue'
import CoverArt from '../ui/CoverArt.vue'
import EqBars from '../ui/EqBars.vue'
import ExplicitBadge from '../ui/ExplicitBadge.vue'
import UiIconButton from '../ui/UiIconButton.vue'
import LikeButton from '../player/LikeButton.vue'
import SliderBar from '../player/SliderBar.vue'
import { useSmoothTime } from '../player/useSmoothTime'
import VolumeControl from '../player/VolumeControl.vue'
import PlayerDivider from './PlayerDivider.vue'
import { useMiniPlayerLayout } from './miniPlayerLayout'
import { usePlayer } from '/src/model/player'
import { useDownloadManager, useProgressTracker } from '/src/model/download'
import { useLibrary } from '/src/model/library'
import { usePlayerPrefs } from '/src/model/playerPrefs'
import { useNowPlaying, useUi } from '/src/model/ui'
import { formatDuration, widestClock } from '/src/lib/format'
import { useI18n } from '/src/i18n'

const player = usePlayer()
const { showLyrics, miniPlayerLayout } = usePlayerPrefs()
const nowPlaying = useNowPlaying()
const { t } = useI18n()
const router = useRouter()
const library = useLibrary()
const dm = useDownloadManager()
const tracker = useProgressTracker()
const ui = useUi()
const scrub = ref(null)

const track = computed(() => player.currentTrack.value)
const visible = computed(() => !!track.value && !nowPlaying.isOpen.value)
const bar = ref(null)
const {
  wide,
  unlocked,
  grid,
  sectionStyle,
  limits,
  startDrag,
  moveDrag,
  endDrag,
  cancelPointer,
  onKeydown: resizeOnKey,
  onEscape,
  toggle,
  reset,
} = useMiniPlayerLayout(bar, visible, miniPlayerLayout)

async function toggleLayout(event) {
  toggle()
  if (unlocked.value && event.detail === 0) {
    await nextTick()
    bar.value?.querySelector('[role="separator"]')?.focus()
  }
}

const trackArtist = computed(
  () =>
    (track.value?.artists || [])[0] ||
    track.value?.artist ||
    t('common.unknownArtist')
)
const trackTitle = computed(() => track.value?.name || track.value?.title || '')

const canSimilar = computed(() => {
  if (track.value?.isPodcast) return false
  const artist = (track.value?.artists || [])[0] || track.value?.artist || ''
  const title = track.value?.name || track.value?.title || ''
  return !!artist.trim() && !!title.trim()
})

function goSimilar() {
  const artist = (track.value?.artists || [])[0] || track.value?.artist || ''
  const title = track.value?.name || track.value?.title || ''
  if (!artist.trim() || !title.trim()) return
  router.push({ name: 'Similar', query: { artist, track: title } })
}

// A stream that isn't in the library yet can be queued from here; while
// queued it spins instead of queueing a duplicate.
const streamDownloadable = computed(
  () =>
    !!track.value?.stream &&
    !!track.value.video_id &&
    !library.hasSong(trackArtist.value, trackTitle.value)
)
const pendingSong = computed(() => {
  if (!streamDownloadable.value) return null
  const tr = track.value
  return {
    name: trackTitle.value,
    artists: tr.artist ? [tr.artist] : [],
    artist: tr.artist || '',
    album_name: tr.album || '',
    cover_url: tr.cover && String(tr.cover).startsWith('http') ? tr.cover : '',
    duration: tr.duration || 0,
    url: `https://music.youtube.com/watch?v=${tr.video_id}`,
    youtube_id: tr.video_id,
  }
})
const downloadJob = computed(() => {
  tracker.queueVersion.value
  return pendingSong.value ? tracker.getBySong(pendingSong.value) : null
})
const downloadBusy = computed(() => {
  const state = downloadJob.value?.state
  return state === 'queued' || state === 'active'
})
const showMiniDownload = computed(() => !!streamDownloadable.value)

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

// A downloaded track (or a stream that landed in the library while
// playing) shows a static check where the download button was.
const showDownloadedCheck = computed(
  () =>
    !!track.value &&
    !track.value.isPodcast &&
    (!track.value.stream ||
      library.hasSong(trackArtist.value, trackTitle.value))
)

// The phone hairline glides like the desktop scrubber (only animated
// while it's the one on screen).
const isPhone = useMediaQuery('(max-width: 767px)')
const smoothTime = useSmoothTime(
  () => player.currentTime.value,
  () => isPhone.value && player.isPlaying.value,
  () => player.duration.value || 0
)
const smoothPercent = computed(() =>
  isPhone.value && player.duration.value
    ? Math.min(100, (smoothTime.value / player.duration.value) * 100)
    : player.progressPct.value
)

const clockSizer = computed(() => widestClock(player.duration.value))

const repeatLabel = computed(
  () =>
    ({
      off: t('player.repeatOff'),
      all: t('player.repeatAll'),
      one: t('player.repeatOne'),
    })[player.repeatMode.value]
)

function commitSeek(value) {
  player.seek(value)
  scrub.value = null
}
</script>

<style scoped>
.adjustable-player {
  display: grid;
  gap: 0;
}

.adjustable-player .track-section,
.adjustable-player .utility-section {
  width: auto;
}

.adjustable-player .track-art {
  width: calc(44px + var(--control-growth));
  height: calc(44px + var(--control-growth));
}

.adjustable-player .transport-section {
  --button-size: calc(36px + var(--control-growth));
  gap: calc(4px + var(--control-growth) / 3);
}

.adjustable-player .track-section,
.adjustable-player .utility-section {
  --button-size: calc(32px + var(--control-growth));
}

.adjustable-player :is(.transport-section, .utility-section) :deep(button),
.adjustable-player .track-section :deep(.track-like),
.adjustable-player .downloaded-check {
  width: var(--button-size);
  height: var(--button-size);
}

.adjustable-player .transport-section .play-button {
  flex-shrink: 0;
  width: calc(40px + var(--control-growth));
  height: calc(40px + var(--control-growth));
}

.adjustable-player :is(.transport-section, .utility-section, .track-section) :deep(button > svg),
.adjustable-player .downloaded-check :deep(svg) {
  width: calc(16px + var(--control-growth) / 2);
  height: calc(16px + var(--control-growth) / 2);
}

.adjustable-player .utility-section,
.adjustable-player .player-volume {
  display: flex;
}

.adjustable-player .player-volume {
  flex: 1;
  gap: 4px;
}

.adjustable-player .player-clock {
  display: inline-grid;
  grid-template-columns: minmax(0, 1fr);
  width: 112px;
  margin-right: 0;
}

.adjustable-player .player-clock > :last-child {
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
