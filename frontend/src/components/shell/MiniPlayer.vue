<template>
  <Transition name="float-bar">
    <!-- The wrapper lets the seek bar's hit area and time tooltip reach
         past the player's clipped top edge. -->
    <div v-if="visible" class="relative">
      <div
        ref="bar"
        class="relative flex h-16 items-center gap-3 overflow-hidden rounded-[16px] border border-line-3 bg-glass pr-2 pl-2 shadow-float backdrop-blur-xl md:h-[76px] md:gap-5 md:rounded-[18px] md:pr-5 md:pl-3"
        :class="{ 'adjustable-player': wide }"
        :style="grid"
        @keydown.esc="onEscape"
      >
        <!-- Progress: a hairline on phones; desktop's scrubber is below. -->
        <div class="absolute inset-x-3 bottom-0 h-0.5 bg-line-2 md:hidden">
          <div
            class="h-full origin-left bg-accent"
            :style="{ transform: `scaleX(${smoothPercent / 100})` }"
          />
        </div>

        <!-- The heart sits beside the button that opens Now playing, not
           inside it, so tapping it never opens the overlay. -->
        <div
          id="mini-player-track"
          class="track-section flex min-w-0 flex-1 items-center gap-1 md:min-w-[200px] md:basis-0"
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
            <!-- The next song's name comes into focus over the last one. -->
            <Transition name="text-swap" mode="out-in">
              <span
                :key="track.file || track.title"
                class="flex min-w-0 flex-col"
              >
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
            </Transition>
          </button>
          <!-- Moves into the More menu when the bar runs out of room. -->
          <LikeButton
            v-if="fits('like')"
            class="track-like"
            :file="track.file"
          />
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
          class="transport-section flex shrink-0 items-center justify-center gap-1 md:gap-3"
          :style="sectionStyle(1)"
        >
          <UiIconButton
            v-if="fits('similar')"
            icon="wand"
            :label="t('similar.findSimilar')"
            @click="goSimilar"
          />
          <UiIconButton
            v-if="fits('shuffle')"
            icon="shuffle"
            :label="t('player.shuffle')"
            :active="player.shuffle.value"
            toggle
            @click="player.toggleShuffle()"
          />
          <UiIconButton
            icon="prev"
            :label="t('player.previous')"
            @click="player.prev()"
          />
          <button
            type="button"
            class="play-button press flex size-11 items-center justify-center rounded-full text-fg transition-[scale] duration-(--dur-fast) ease-out-soft md:bg-invert md:text-on-invert md:hover:scale-105"
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
            v-if="fits('repeat')"
            :icon="player.repeatMode.value === 'one' ? 'repeat-one' : 'repeat'"
            :label="repeatLabel"
            :active="player.repeatMode.value !== 'off'"
            toggle
            @click="player.cycleRepeat()"
          />
          <UiIconButton
            v-if="showMiniDownload && fits('library')"
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
            v-if="showDownloadedCheck && fits('library')"
            class="downloaded-check inline-flex size-10 shrink-0 items-center justify-center text-accent"
            :title="t('search.inLibrary')"
            aria-hidden="true"
          >
            <AppIcon name="check" :size="18" />
          </span>
          <!-- Phones have no utility section: the close button and the
             More menu end this row there. -->
          <UiIconButton
            v-if="isPhone && fits('close')"
            icon="x"
            :label="t('common.close')"
            size="sm"
            @click="player.stop()"
          />
          <UiMenu
            v-if="isPhone && moreItems.length"
            :items="moreItems"
            :label="t('player.moreControls')"
            size="sm"
          />
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
          class="utility-section hidden items-center justify-end gap-1 md:flex md:flex-1 md:basis-0"
          :style="sectionStyle(2)"
        >
          <!-- Never wraps, and keeps one width for the whole track: the
             invisible copy is the widest the text will get, so the
             controls beside it don't shift as it ticks past 10:00. -->
          <span
            v-if="fits('clock')"
            class="player-clock tabular mr-2 inline-grid shrink-0 text-xs whitespace-nowrap text-muted"
          >
            <span
              class="invisible col-start-1 row-start-1"
              aria-hidden="true"
              >{{ clockSizer }}</span
            >
            <span class="col-start-1 row-start-1 text-right"
              >{{ formatDuration(player.currentTime.value) }} /
              {{ formatDuration(player.duration.value) }}</span
            >
          </span>
          <UiIconButton
            v-if="fits('lyrics')"
            icon="lyrics"
            :label="t('player.lyrics')"
            size="sm"
            @click="nowPlaying.open('lyrics')"
          />
          <UiIconButton
            v-if="fits('nowPlaying')"
            icon="queue"
            :label="t('player.upNext')"
            size="sm"
            @click="nowPlaying.open('queue')"
          />
          <!-- Always here: a slider while there's room for one, else a
             button that opens it. -->
          <VolumeControl
            class="player-volume min-w-0"
            :compact="plan.volume === 'compact'"
            :width="wide ? 'min-w-8 flex-1' : 'w-20 min-w-8'"
          />
          <UiIconButton
            v-if="fits('nowPlaying')"
            icon="expand"
            :label="t('player.openNowPlaying')"
            size="sm"
            @click="nowPlaying.open()"
          />
          <!-- Stops playback and forgets the queue, so the bar stays closed
             after a reload until something plays again. -->
          <UiIconButton
            v-if="fits('close')"
            icon="x"
            :label="t('common.close')"
            size="sm"
            @click="player.stop()"
          />
          <!-- What the bar had no room for (issue #552). -->
          <UiMenu
            v-if="moreItems.length"
            :items="moreItems"
            :label="t('player.moreControls')"
            size="sm"
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
      <SeekBar
        class="hidden md:block"
        :model-value="scrub ?? player.currentTime.value"
        :max="player.duration.value || 1"
        :label="t('player.seek')"
        :value-text="formatDuration(player.currentTime.value)"
        :playing="player.isPlaying.value"
        @update:model-value="(v) => (scrub = v)"
        @commit="commitSeek"
      />
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
import UiMenu from '../ui/UiMenu.vue'
import LikeButton from '../player/LikeButton.vue'
import SeekBar from '../player/SeekBar.vue'
import { useSmoothTime } from '../player/useSmoothTime'
import VolumeControl from '../player/VolumeControl.vue'
import PlayerDivider from './PlayerDivider.vue'
import { useMiniPlayerLayout } from './miniPlayerLayout'
import { CONTROL_PRIORITY, planControls } from './playerControls'
import { usePlayer } from '/src/model/player'
import { useDownloadManager, useProgressTracker } from '/src/model/download'
import { useLibrary } from '/src/model/library'
import { useLikes } from '/src/model/likes'
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
  width,
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

// Which controls this track has; which of them the bar has room for
// (issue #552). The adjustable wide layout keeps them all on the bar.
const likes = useLikes()
const canLike = computed(() => !track.value?.isPodcast && !track.value?.stream)
const available = computed(() =>
  CONTROL_PRIORITY.filter(
    (id) =>
      ({
        like: canLike.value,
        lyrics: showLyrics.value,
        library: showMiniDownload.value || showDownloadedCheck.value,
        similar: canSimilar.value,
      })[id] ?? true
  )
)
const plan = computed(() =>
  wide.value
    ? { shown: new Set(available.value), overflow: [], volume: 'inline' }
    : planControls(width.value, available.value, { phone: isPhone.value })
)

function fits(id) {
  return plan.value.shown.has(id)
}

const moreItems = computed(() => {
  const items = []
  for (const id of plan.value.overflow) {
    if (id === 'clock') {
      items.push({
        heading: `${formatDuration(player.currentTime.value)} / ${formatDuration(player.duration.value)}`,
      })
    } else if (id === 'repeat') {
      items.push({
        label: repeatLabel.value,
        icon: player.repeatMode.value === 'one' ? 'repeat-one' : 'repeat',
        checked: player.repeatMode.value !== 'off',
        action: () => player.cycleRepeat(),
      })
    } else if (id === 'shuffle') {
      items.push({
        label: t('player.shuffle'),
        icon: 'shuffle',
        checked: player.shuffle.value,
        action: () => player.toggleShuffle(),
      })
    } else if (id === 'like') {
      const liked = likes.isLiked(track.value?.file)
      items.push({
        label: liked ? t('likes.unlike') : t('likes.like'),
        icon: liked ? 'heart' : 'heart-outline',
        disabled: !track.value?.file,
        action: () => likes.toggle(track.value.file),
      })
    } else if (id === 'nowPlaying') {
      items.push(
        {
          label: t('player.upNext'),
          icon: 'queue',
          action: () => nowPlaying.open('queue'),
        },
        {
          label: t('player.openNowPlaying'),
          icon: 'expand',
          action: () => nowPlaying.open(),
        }
      )
    } else if (id === 'lyrics') {
      items.push({
        label: t('player.lyrics'),
        icon: 'lyrics',
        action: () => nowPlaying.open('lyrics'),
      })
    } else if (id === 'library' && showMiniDownload.value) {
      items.push({
        label: t('actions.downloadItem', { name: trackTitle.value }),
        icon: 'download',
        disabled: downloadBusy.value,
        action: downloadCurrent,
      })
    } else if (id === 'library') {
      items.push({
        label: t('search.inLibrary'),
        icon: 'check',
        disabled: true,
      })
    } else if (id === 'similar') {
      items.push({
        label: t('similar.findSimilar'),
        icon: 'wand',
        action: goSimilar,
      })
    } else if (id === 'close') {
      if (items.length) items.push({ divider: true })
      items.push({
        label: t('player.closePlayer'),
        icon: 'x',
        action: () => player.stop(),
      })
    }
  }
  return items
})

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

.adjustable-player
  :is(.transport-section, .utility-section, .track-section)
  :deep(button > svg),
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
