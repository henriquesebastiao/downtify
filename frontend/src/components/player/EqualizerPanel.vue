<template>
  <section
    class="flex h-full min-h-0 flex-col gap-4 overflow-y-auto px-1 lg:justify-center"
    :aria-label="t('player.equalizer')"
  >
    <header class="flex flex-wrap items-center gap-x-4 gap-y-3">
      <div class="mr-auto flex items-center gap-2.5">
        <h2 class="text-display text-xl font-semibold">
          {{ t('player.equalizer') }}
        </h2>
        <span
          class="cursor-help rounded-full border border-warn/60 bg-warn/15 px-2 py-0.5 text-[11px] font-semibold tracking-wide text-warn uppercase"
          :title="t('player.experimentalHint')"
          :aria-label="`${t('player.experimental')}: ${t('player.experimentalHint')}`"
          role="note"
          >{{ t('player.experimental') }}</span
        >
      </div>
      <button
        type="button"
        role="switch"
        :aria-checked="eq.enabled.value"
        :aria-label="t('player.equalizer')"
        :disabled="!eq.supported"
        class="flex h-9 items-center gap-2.5 rounded-full bg-white/10 pr-3 pl-1.5 text-[13px] font-semibold transition-colors hover:bg-white/15 disabled:opacity-40"
        @click="eq.setEnabled(!eq.enabled.value)"
      >
        <span
          class="relative h-6 w-10 rounded-full transition-colors duration-200"
          :style="{
            backgroundColor: eq.enabled.value
              ? color
              : 'rgb(255 255 255 / 0.2)',
          }"
          aria-hidden="true"
        >
          <span
            class="absolute top-1 size-4 rounded-full bg-white shadow transition-[left] duration-200 ease-out-soft"
            :class="eq.enabled.value ? 'left-5' : 'left-1'"
          />
        </span>
        {{
          eq.enabled.value ? t('player.equalizerOn') : t('player.equalizerOff')
        }}
      </button>
    </header>

    <div class="flex flex-wrap items-center gap-2">
      <UiMenu :items="presetMenu" :label="t('player.preset')" align="start">
        <template #trigger>
          <button
            type="button"
            class="flex h-9 items-center gap-2 rounded-full bg-white/10 pr-3 pl-3.5 text-[13px] font-semibold transition-colors hover:bg-white/15"
            :aria-label="`${t('player.preset')}: ${presetLabel(eq.preset.value)}`"
          >
            <span class="text-white/55">{{ t('player.preset') }}</span>
            {{ presetLabel(eq.preset.value) }}
            <AppIcon name="chevron-down" :size="16" class="text-white/60" />
          </button>
        </template>
      </UiMenu>
      <button
        type="button"
        class="flex h-9 items-center gap-2 rounded-full px-3 text-[13px] font-semibold text-white/70 transition-colors hover:bg-white/10 hover:text-white disabled:opacity-40"
        :disabled="isDefault"
        @click="eq.reset()"
      >
        <AppIcon name="refresh" :size="15" />{{ t('player.resetEqualizer') }}
      </button>
    </div>

    <p
      v-if="!eq.supported || eq.graphState.value === 'error'"
      class="flex items-center gap-2 text-sm text-white/70"
    >
      <AppIcon name="alert" :size="16" />
      {{
        eq.supported
          ? t('player.equalizerError')
          : t('player.equalizerUnsupported')
      }}
    </p>

    <div
      class="group/eq rounded-panel border border-white/10 bg-white/6 px-2 pt-3 pb-3 backdrop-blur-xl transition-opacity sm:px-4"
      :class="eq.enabled.value ? '' : 'opacity-60'"
    >
      <div class="flex items-stretch gap-1 sm:gap-2">
        <EqBandSlider
          :model-value="eq.preamp.value"
          :limit="PREAMP_LIMIT"
          :label="t('player.preamp')"
          :caption="t('player.preampShort')"
          :color="color"
          :height="height"
          class="shrink-0"
          @update:model-value="eq.setPreamp"
        />
        <div class="w-px shrink-0 bg-white/10" aria-hidden="true" />
        <div ref="bandsEl" class="relative min-w-0 flex-1">
          <!-- Response curve, aligned with the slider tracks. -->
          <svg
            class="pointer-events-none absolute inset-x-0 top-6 overflow-hidden"
            :width="bandsWidth"
            :height="height"
            :viewBox="`0 0 ${bandsWidth} ${height}`"
            aria-hidden="true"
          >
            <defs>
              <linearGradient :id="gradientId" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0" :stop-color="color" stop-opacity="0.35" />
                <stop offset="0.5" :stop-color="color" stop-opacity="0.08" />
                <stop offset="1" :stop-color="color" stop-opacity="0.35" />
              </linearGradient>
            </defs>
            <path
              v-if="curve"
              :d="`${curve} L${bandsWidth} ${height / 2} L0 ${height / 2} Z`"
              :fill="`url(#${gradientId})`"
            />
            <path
              v-if="curve"
              :d="curve"
              fill="none"
              :stroke="color"
              stroke-width="2"
              stroke-linejoin="round"
              stroke-opacity="0.9"
            />
          </svg>
          <div class="relative grid grid-cols-10">
            <EqBandSlider
              v-for="(band, i) in BANDS"
              :key="band.frequency"
              :model-value="eq.gains.value[i]"
              :limit="GAIN_LIMIT"
              :label="t('player.bandLabel', { frequency: band.frequency })"
              :caption="formatFrequency(band.frequency)"
              :color="color"
              :height="height"
              @update:model-value="(v) => eq.setGain(i, v)"
            />
          </div>
        </div>
      </div>
    </div>

    <p class="min-h-5 text-[13px] text-white/55" aria-live="polite">
      <template v-if="eq.enabled.value && eq.preamp.value > 0">
        {{ t('player.clipWarning') }}
      </template>
      <template v-else-if="eq.enabled.value && eq.headroom.value < -0.05">
        {{
          t('player.headroomHint', {
            amount: Math.round(-eq.headroom.value * 10) / 10,
          })
        }}
      </template>
      <template v-else>{{ t('player.equalizerHint') }}</template>
    </p>
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, useId } from 'vue'
import { useMediaQuery } from '@vueuse/core'
import AppIcon from '../ui/AppIcon.vue'
import UiMenu from '../ui/UiMenu.vue'
import EqBandSlider from './EqBandSlider.vue'
import { useEqualizer } from '/src/model/equalizer'
import {
  BANDS,
  GAIN_LIMIT,
  PREAMP_LIMIT,
  PRESETS,
  formatFrequency,
  responsePath,
} from '/src/lib/equalizer'
import { useI18n } from '/src/i18n'

const props = defineProps({
  // Cover palette from useCoverPalette, or null.
  palette: { type: Object, default: null },
})

const { t } = useI18n()
const eq = useEqualizer()
const gradientId = `eq-fill-${useId()}`

const color = computed(() => props.palette?.primary || '#ffffff')
const short = useMediaQuery('(max-height: 760px)')
const height = computed(() => (short.value ? 140 : 180))

const bandsEl = ref(null)
const bandsWidth = ref(0)
let observer = null
onMounted(() => {
  observer = new ResizeObserver(([entry]) => {
    bandsWidth.value = Math.round(entry.contentRect.width)
  })
  observer.observe(bandsEl.value)
})
onBeforeUnmount(() => observer?.disconnect())

const curve = computed(() =>
  bandsWidth.value
    ? responsePath(eq.gains.value, {
        width: bandsWidth.value,
        height: height.value,
      })
    : ''
)

const isDefault = computed(
  () => !eq.enabled.value && eq.preset.value === 'flat' && eq.preamp.value === 0
)

function presetLabel(id) {
  return t(`player.presets.${id}`)
}

const presetMenu = computed(() => [
  ...PRESETS.map((preset) => ({
    label: presetLabel(preset.id),
    checked: eq.preset.value === preset.id,
    action: () => eq.selectPreset(preset.id),
  })),
  { divider: true, hidden: !eq.isCustom.value },
  {
    label: presetLabel('custom'),
    checked: true,
    disabled: true,
    hidden: !eq.isCustom.value,
  },
])
</script>
