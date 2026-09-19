<template>
  <div class="flex h-full min-h-0 flex-col">
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
      class="relative flex-1 overflow-y-auto overscroll-contain px-2 py-[30vh] [mask-image:linear-gradient(transparent,#000_18%,#000_82%,transparent)] [scrollbar-width:none]"
      @wheel.passive="userScrolled"
      @touchmove.passive="userScrolled"
    >
      <button
        v-for="(line, i) in lines"
        :key="i"
        :ref="(el) => (lineEls[i] = el)"
        type="button"
        class="text-display block w-full origin-left py-2 text-left leading-tight font-semibold transition-all duration-300"
        :class="[
          sizeClass,
          i === active
            ? 'scale-100 text-white'
            : i < active
              ? 'scale-[0.97] text-white/35 hover:text-white/60'
              : 'scale-[0.97] text-white/55 hover:text-white/75',
        ]"
        @click="player.seek(line.time)"
      >
        {{ line.text || '♪' }}
      </button>
    </div>

    <div
      v-else-if="plain"
      class="flex-1 overflow-y-auto px-2 py-6 [scrollbar-width:thin]"
    >
      <p
        class="text-display text-xl leading-relaxed font-medium whitespace-pre-line text-white/80"
      >
        {{ plain }}
      </p>
      <p class="mt-6 text-xs text-white/45">
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
import { usePlayer } from '/src/model/player'
import { loadLyrics } from '/src/model/lyrics'
import { activeLineIndex } from '/src/lib/lrc'
import { useI18n } from '/src/i18n'

const props = defineProps({
  compact: { type: Boolean, default: false },
})

const player = usePlayer()
const { t } = useI18n()
const loading = ref(false)
const lines = ref([])
const plain = ref('')
const scroller = ref(null)
const lineEls = ref([])
let manualUntil = 0

const sizeClass = computed(() =>
  props.compact ? 'text-xl sm:text-2xl' : 'text-2xl xl:text-[34px]'
)

watch(
  () => player.currentTrack.value?.file,
  async (file) => {
    lines.value = []
    plain.value = ''
    lineEls.value = []
    if (!file) return
    loading.value = true
    const result = await loadLyrics(file)
    if (player.currentTrack.value?.file !== file) return
    lines.value = result.lines
    plain.value = result.plain
    loading.value = false
  },
  { immediate: true }
)

const active = computed(() =>
  activeLineIndex(lines.value, player.currentTime.value + 0.25)
)

function userScrolled() {
  // Leave the user's scroll position alone for a moment.
  manualUntil = Date.now() + 4000
}

watch(active, async (index) => {
  if (index < 0 || Date.now() < manualUntil) return
  await nextTick()
  lineEls.value[index]?.scrollIntoView({ block: 'center', behavior: 'smooth' })
})
</script>
