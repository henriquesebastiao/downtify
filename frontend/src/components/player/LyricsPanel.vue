<template>
  <div class="relative flex h-full min-h-0 flex-col">
    <div
      v-if="countIn"
      class="absolute inset-x-0 top-1 z-10 flex justify-center gap-2.5"
      aria-hidden="true"
    >
      <span
        v-for="n in COUNT_IN_DOTS"
        :key="n"
        class="size-3 rounded-full transition-colors duration-300"
        :class="n <= countIn ? 'bg-white' : 'bg-white/20'"
      />
    </div>

    <button
      v-if="canAdjust"
      type="button"
      class="press transition-press absolute top-0 right-0 z-10 flex size-9 items-center justify-center rounded-full hover:bg-white/10"
      :class="adjusting ? 'bg-white/15 text-white' : 'text-white/55'"
      :aria-label="t('player.lyricsTiming')"
      :title="t('player.lyricsTiming')"
      :aria-pressed="adjusting"
      @click="toggleAdjusting"
    >
      <AppIcon name="timer" :size="18" />
    </button>

    <Transition name="float-bar">
      <div
        v-if="canAdjust && adjusting"
        class="absolute inset-x-0 bottom-2 z-10 flex flex-col items-center gap-2 px-2"
      >
        <p class="max-w-sm text-center text-xs text-white/60">
          {{ t('player.lyricsOffsetHint') }}
        </p>
        <div
          class="flex items-center gap-1 rounded-full border border-white/10 bg-black/45 p-1 backdrop-blur-xl"
          role="group"
          :aria-label="t('player.lyricsTiming')"
        >
          <button
            type="button"
            class="press transition-press flex size-9 items-center justify-center rounded-full text-white hover:bg-white/10"
            :aria-label="t('player.lyricsSooner')"
            :title="t('player.lyricsSooner')"
            :disabled="saving"
            @click="nudge(-OFFSET_STEP)"
          >
            <AppIcon name="minus" :size="18" />
          </button>
          <output
            class="min-w-16 text-center text-sm font-semibold text-white tabular-nums"
            aria-live="polite"
            >{{ offsetLabel }}</output
          >
          <button
            type="button"
            class="press transition-press flex size-9 items-center justify-center rounded-full text-white hover:bg-white/10"
            :aria-label="t('player.lyricsLater')"
            :title="t('player.lyricsLater')"
            :disabled="saving"
            @click="nudge(OFFSET_STEP)"
          >
            <AppIcon name="plus" :size="18" />
          </button>
          <button
            type="button"
            class="press transition-press h-8 rounded-full px-3 text-[13px] font-medium text-white/70 hover:bg-white/10 hover:text-white disabled:opacity-40"
            :disabled="!offset || saving"
            @click="offset = 0"
          >
            {{ t('player.lyricsOffsetReset') }}
          </button>
          <UiButton
            variant="photo"
            size="sm"
            class="!rounded-full"
            :loading="saving"
            :disabled="!offset"
            @click="saveOffset"
          >
            {{ t('player.lyricsOffsetSave') }}
          </UiButton>
        </div>
      </div>
    </Transition>

    <div
      v-if="loading"
      class="flex flex-1 flex-col justify-center gap-5 px-2"
      aria-hidden="true"
    >
      <UiSkeleton
        v-for="n in 6"
        :key="n"
        glass
        class="h-7 !rounded-lg"
        :style="{ width: `${50 + ((n * 37) % 45)}%` }"
      />
    </div>

    <div
      v-else-if="lines.length"
      ref="scroller"
      class="relative flex-1 overflow-y-auto overscroll-contain px-2 [mask-image:linear-gradient(transparent,#000_18%,#000_82%,transparent)] [scrollbar-width:none]"
      :class="[
        karaoke
          ? 'py-[calc(50dvh-140px)] lg:py-[calc(50dvh-66px)]'
          : 'py-[min(30vh,9rem)]',
        { 'pointer-events-none': readonly },
        wide && !karaoke ? 'xl:mx-auto xl:w-full xl:max-w-[46rem]' : '',
      ]"
      @wheel.passive="userScrolled"
      @touchmove.passive="userScrolled"
    >
      <button
        v-for="(line, i) in lines"
        :key="i"
        :ref="(el) => (lineEls[i] = el)"
        type="button"
        class="text-display block w-full transition-[color,opacity,scale] duration-(--dur-slow) ease-out-soft"
        :class="karaoke ? karaokeLineClass(i) : lineClass(i)"
        :tabindex="readonly ? -1 : undefined"
        @click="player.seek(Math.max(0, line.time + offset))"
      >
        <span
          v-if="karaoke"
          class="now-playing-karaoke-fill"
          :style="{ '--karaoke-fill': `${fillPercent(i)}%` }"
          >{{ line.text || '♪' }}</span
        >
        <template v-else>{{ line.text || '♪' }}</template>
      </button>
    </div>

    <div
      v-else-if="plain"
      class="flex-1 overflow-y-auto px-2 py-6 [scrollbar-width:thin]"
      :class="wide && !karaoke ? 'xl:mx-auto xl:w-full xl:max-w-[46rem]' : ''"
    >
      <p
        class="text-display leading-relaxed font-medium whitespace-pre-line text-white/80"
        :class="
          karaoke
            ? 'now-playing-karaoke-plain text-center'
            : 'now-playing-lyric'
        "
      >
        {{ plain }}
      </p>
      <p
        class="mt-6 text-xs text-white/45"
        :class="karaoke ? 'text-center' : ''"
      >
        {{ t('player.lyricsNotSynced') }}
      </p>
    </div>

    <div
      v-else
      class="flex flex-1 flex-col items-center justify-center gap-3 text-center"
    >
      <AppIcon name="lyrics" :size="32" class="text-white/35" />
      <p class="text-sm text-white/60">{{ t('player.noLyrics') }}</p>
      <p class="max-w-xs text-xs text-white/40">
        {{ t('player.noLyricsHint') }}
      </p>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import AppIcon from '../ui/AppIcon.vue'
import UiButton from '../ui/UiButton.vue'
import UiSkeleton from '../ui/UiSkeleton.vue'
import { loadLyrics, shiftLyrics } from '/src/model/lyrics'
import { useUi } from '/src/model/ui'
import { activeLineIndex, countInBeats, lineProgress } from '/src/lib/lrc'
import { centerLine } from '/src/lib/lyricsScroll'
import { useI18n } from '/src/i18n'

const COUNT_IN_DOTS = 3
// Each tap on − / + moves the lyrics this many seconds (issue #663).
const OFFSET_STEP = 0.1
// The server takes at most a minute either way.
const MAX_OFFSET = 60

const props = defineProps({
  compact: { type: Boolean, default: false },
  // Stage layout: huge centred lines, the sung part filling in as it goes.
  karaoke: { type: Boolean, default: false },
  // The app's player, or the projected window's read-only copy of it.
  player: { type: Object, required: true },
  // Projected: nothing here to click or scroll.
  readonly: { type: Boolean, default: false },
  // Nothing beside it (Up next hidden): on wide screens the words sit in
  // a centred column, a size up (issue #679).
  wide: { type: Boolean, default: false },
})

const { t, locale } = useI18n()
const ui = useUi()
const loading = ref(false)
const lines = ref([])
const plain = ref('')
const scroller = ref(null)
const lineEls = ref([])
let manualUntil = 0
// Timing being tried out: lines show `offset` seconds later (sooner when
// negative) until saved into the song's .lrc and tags.
const adjusting = ref(false)
const offset = ref(0)
const saving = ref(false)

watch(
  () => props.player.currentTrack.value?.file,
  async (file) => {
    lines.value = []
    plain.value = ''
    lineEls.value = []
    offset.value = 0
    adjusting.value = false
    if (!file) return
    loading.value = true
    const result = await loadLyrics(file)
    if (props.player.currentTrack.value?.file !== file) return
    lines.value = result.lines
    plain.value = result.plain
    loading.value = false
  },
  { immediate: true }
)

// Library songs only: a stream or podcast has no saved lyrics to fix.
const canAdjust = computed(() => {
  const track = props.player.currentTrack.value
  return (
    !props.readonly &&
    !loading.value &&
    lines.value.length > 0 &&
    !!track?.file &&
    !track.stream &&
    !track.isPodcast
  )
})

const offsetLabel = computed(() =>
  t('player.lyricsOffsetValue', {
    value: new Intl.NumberFormat(locale.value, {
      signDisplay: 'exceptZero',
      minimumFractionDigits: 1,
      maximumFractionDigits: 1,
    }).format(offset.value),
  })
)

// Closing drops a timing that wasn't saved, so what plays is what's saved.
function toggleAdjusting() {
  adjusting.value = !adjusting.value
  if (!adjusting.value) offset.value = 0
}

function nudge(step) {
  const next = Math.round((offset.value + step) * 10) / 10
  offset.value = Math.min(MAX_OFFSET, Math.max(-MAX_OFFSET, next))
}

async function saveOffset() {
  const file = props.player.currentTrack.value?.file
  if (!file || !offset.value || saving.value) return
  saving.value = true
  try {
    const result = await shiftLyrics(file, offset.value * 1000)
    if (props.player.currentTrack.value?.file !== file) return
    lines.value = result.lines
    offset.value = 0
    adjusting.value = false
    ui.toast(t('player.lyricsOffsetSaved'), { kind: 'success' })
  } catch (err) {
    ui.toast(err?.response?.data?.detail || t('player.lyricsOffsetFailed'), {
      kind: 'error',
    })
  } finally {
    saving.value = false
  }
}

// A positive offset shows every line later: the song's clock runs behind.
const clock = computed(
  () => props.player.currentTime.value + 0.25 - offset.value
)
const active = computed(() => activeLineIndex(lines.value, clock.value))
const countIn = computed(() =>
  props.karaoke ? countInBeats(lines.value, clock.value, COUNT_IN_DOTS) : 0
)

function lineClass(i) {
  return [
    'origin-left py-2 text-left leading-tight font-semibold',
    props.compact
      ? 'now-playing-lyric-compact'
      : props.wide
        ? 'now-playing-lyric now-playing-lyric--wide'
        : 'now-playing-lyric',
    i === active.value
      ? 'scale-100 text-white'
      : i < active.value
        ? 'scale-[0.97] text-white/35 hover:text-white/60'
        : 'scale-[0.97] text-white/55 hover:text-white/75',
  ]
}

function karaokeLineClass(i) {
  const base =
    'now-playing-karaoke-lyric origin-center py-[0.18em] text-center leading-[1.12] font-bold text-balance'
  if (i === active.value) return [base, 'scale-100']
  if (i < active.value) return [base, 'scale-[0.8] opacity-25 hover:opacity-50']
  return [
    base,
    i === active.value + 1
      ? 'scale-[0.86]'
      : 'scale-[0.8] opacity-70 hover:opacity-100',
  ]
}

function fillPercent(i) {
  if (i !== active.value) return i < active.value ? 100 : 0
  return lineProgress(lines.value, i, clock.value) * 100
}

function userScrolled() {
  // Leave the user's scroll position alone for a moment.
  manualUntil = Date.now() + 4000
}

async function centerActive() {
  if (Date.now() < manualUntil) return
  await nextTick()
  centerLine(scroller.value, lineEls.value, active.value)
}

watch(active, centerActive)
// Opened mid-song, or switched between the Lyrics and Karaoke layouts.
watch([scroller, () => props.karaoke], centerActive)
</script>
