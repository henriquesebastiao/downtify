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

    <div
      v-if="loading"
      class="flex flex-1 flex-col justify-center gap-5 px-2"
      aria-hidden="true"
    >
      <div
        v-for="n in 6"
        :key="n"
        class="h-7 animate-pulse rounded-lg bg-white/10"
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
      ]"
      @wheel.passive="userScrolled"
      @touchmove.passive="userScrolled"
    >
      <button
        v-for="(line, i) in lines"
        :key="i"
        :ref="(el) => (lineEls[i] = el)"
        type="button"
        class="text-display block w-full transition-all duration-300"
        :class="karaoke ? karaokeLineClass(i) : lineClass(i)"
        :tabindex="readonly ? -1 : undefined"
        @click="player.seek(line.time)"
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
import { loadLyrics } from '/src/model/lyrics'
import { activeLineIndex, countInBeats, lineProgress } from '/src/lib/lrc'
import { centerLine } from '/src/lib/lyricsScroll'
import { useI18n } from '/src/i18n'

const COUNT_IN_DOTS = 3

const props = defineProps({
  compact: { type: Boolean, default: false },
  // Stage layout: huge centred lines, the sung part filling in as it goes.
  karaoke: { type: Boolean, default: false },
  // The app's player, or the projected window's read-only copy of it.
  player: { type: Object, required: true },
  // Projected: nothing here to click or scroll.
  readonly: { type: Boolean, default: false },
})

const { t } = useI18n()
const loading = ref(false)
const lines = ref([])
const plain = ref('')
const scroller = ref(null)
const lineEls = ref([])
let manualUntil = 0

watch(
  () => props.player.currentTrack.value?.file,
  async (file) => {
    lines.value = []
    plain.value = ''
    lineEls.value = []
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

const clock = computed(() => props.player.currentTime.value + 0.25)
const active = computed(() => activeLineIndex(lines.value, clock.value))
const countIn = computed(() =>
  props.karaoke ? countInBeats(lines.value, clock.value, COUNT_IN_DOTS) : 0
)

function lineClass(i) {
  return [
    'origin-left py-2 text-left leading-tight font-semibold',
    props.compact ? 'now-playing-lyric-compact' : 'now-playing-lyric',
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
