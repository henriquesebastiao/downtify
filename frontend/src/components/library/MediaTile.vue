<template>
  <article class="tile group relative flex min-w-0 flex-col gap-2.5">
    <RouterLink :to="to" class="relative block" :aria-label="title">
      <CoverArt
        :src="cover"
        :covers="covers"
        :name="name || title"
        :round="round"
        :icon="icon"
        :symbol="symbol"
        shadow
        :letter-size="round ? 40 : 56"
        class="aspect-square w-full"
      >
        <span
          v-if="playing"
          class="absolute top-2.5 left-2.5 flex h-6 items-center gap-1.5 rounded-full bg-black/55 px-2 text-[11px] font-semibold text-white backdrop-blur"
        >
          <EqBars :size="10" />{{ t('player.playing') }}
        </span>
        <slot name="badge" />
      </CoverArt>
    </RouterLink>
    <button
      v-if="playable"
      type="button"
      class="tile-play absolute flex size-11 items-center justify-center rounded-full bg-accent text-on-accent shadow-[0_8px_24px_color-mix(in_srgb,var(--c-accent)_40%,transparent)] transition-transform hover:scale-105"
      :class="round ? 'right-1 bottom-[4.25rem]' : 'right-3 bottom-[4.25rem]'"
      :aria-label="t('actions.playItem', { name: title })"
      @click="$emit('play')"
    >
      <AppIcon name="play" :size="16" />
    </button>
    <RouterLink
      :to="to"
      class="flex min-w-0 flex-col gap-0.5"
      :class="round ? 'items-center text-center' : ''"
    >
      <span class="w-full truncate text-sm font-semibold text-fg">{{
        title
      }}</span>
      <span class="w-full truncate text-[13px] text-muted">{{ subtitle }}</span>
    </RouterLink>
  </article>
</template>

<script setup>
import AppIcon from '../ui/AppIcon.vue'
import CoverArt from '../ui/CoverArt.vue'
import EqBars from '../ui/EqBars.vue'
import { useI18n } from '/src/i18n'

defineProps({
  to: { type: [String, Object], required: true },
  title: { type: String, required: true },
  subtitle: { type: String, default: '' },
  name: { type: String, default: '' },
  cover: { type: String, default: '' },
  covers: { type: Array, default: () => [] },
  icon: { type: String, default: 'disc' },
  symbol: { type: Boolean, default: false },
  round: { type: Boolean, default: false },
  playing: { type: Boolean, default: false },
  playable: { type: Boolean, default: true },
})
defineEmits(['play'])
const { t } = useI18n()
</script>
