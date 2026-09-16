<template>
  <header class="relative isolate overflow-hidden">
    <div
      class="absolute inset-0 -z-10 opacity-70"
      :style="{
        background: `linear-gradient(180deg, ${tint} 0%, transparent 100%)`,
      }"
      aria-hidden="true"
    />
    <div
      class="mx-auto flex max-w-[1680px] flex-col gap-6 px-4 pt-6 pb-6 sm:px-6 md:flex-row md:items-end md:gap-8 md:pt-10 lg:px-10"
    >
      <CoverArt
        :src="cover"
        :covers="covers"
        :name="name || title"
        :round="round"
        :icon="icon"
        shadow
        :letter-size="96"
        :icon-size="64"
        rounded="rounded-[16px]"
        class="size-48 self-center shadow-[0_24px_60px_rgba(0,0,0,0.45)] sm:size-56 md:self-auto lg:size-[232px]"
      />
      <div
        class="flex min-w-0 flex-col gap-3 max-md:items-center max-md:text-center"
      >
        <span class="eyebrow !text-fg-3">{{ kicker }}</span>
        <h1
          class="text-display line-clamp-2 text-4xl leading-[1.05] font-bold text-balance break-words sm:text-5xl xl:text-[64px]"
        >
          {{ title }}
        </h1>
        <p class="text-[15px] text-fg-3">
          <slot name="subtitle" />
        </p>
        <div
          class="mt-3 flex flex-wrap items-center gap-2.5 max-md:justify-center"
        >
          <slot name="actions" />
        </div>
      </div>
    </div>
  </header>
</template>

<script setup>
import { computed } from 'vue'
import CoverArt from '../ui/CoverArt.vue'
import { hueFor } from '/src/lib/format'

const props = defineProps({
  title: { type: String, required: true },
  kicker: { type: String, default: '' },
  name: { type: String, default: '' },
  cover: { type: String, default: '' },
  covers: { type: Array, default: () => [] },
  icon: { type: String, default: 'disc' },
  round: { type: Boolean, default: false },
})

const tint = computed(
  () => `oklch(0.45 0.08 ${hueFor(props.name || props.title)} / 0.55)`
)
</script>
