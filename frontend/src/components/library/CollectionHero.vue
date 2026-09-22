<template>
  <header
    class="relative isolate flex flex-col justify-end overflow-hidden"
    :class="banner ? 'min-h-[300px] sm:min-h-[380px] lg:min-h-[440px]' : ''"
  >
    <img
      v-if="banner"
      :src="banner"
      alt=""
      class="absolute inset-0 -z-20 size-full object-cover"
    />
    <div
      class="absolute inset-0 -z-10"
      :class="banner ? '' : 'opacity-70'"
      :style="{
        background: banner
          ? 'linear-gradient(180deg, rgba(11,12,14,0.05) 0%, rgba(11,12,14,0.55) 65%, rgba(11,12,14,0.92) 100%)'
          : `linear-gradient(180deg, ${tint} 0%, transparent 100%)`,
      }"
      aria-hidden="true"
    />
    <button
      v-if="bannerEditable"
      type="button"
      :title="t('artistArt.editBanner')"
      :aria-label="t('artistArt.editBanner')"
      class="absolute top-4 right-4 z-10 flex size-10 items-center justify-center rounded-full border border-line-2 bg-black/55 text-white backdrop-blur transition-colors hover:bg-black/70"
      @click="$emit('edit-banner')"
    >
      <AppIcon name="pencil" :size="16" />
    </button>
    <div
      class="mr-auto flex max-w-[1680px] flex-col gap-6 px-4 pt-6 pb-6 sm:px-6 md:flex-row md:items-end md:gap-8 md:pt-10 lg:px-10"
    >
      <div
        class="group/cover relative size-48 shrink-0 self-center sm:size-56 md:self-auto lg:size-[232px]"
      >
        <CoverArt
          :src="cover"
          :covers="covers"
          :name="name || title"
          :round="round"
          :icon="icon"
          :symbol="symbol"
          shadow
          :letter-size="96"
          :icon-size="64"
          rounded="rounded-[16px]"
          class="size-full shadow-[0_24px_60px_rgba(0,0,0,0.45)]"
        />
        <button
          v-if="photoEditable"
          type="button"
          class="absolute inset-0 flex items-center justify-center rounded-[16px] bg-black/0 text-white opacity-0 transition-all group-hover/cover:bg-black/45 group-hover/cover:opacity-100"
          :class="round ? 'rounded-full' : ''"
          @click="$emit('edit-photo')"
        >
          <span class="flex items-center gap-2 text-base font-semibold">
            <AppIcon name="pencil" :size="17" />{{ t('artistArt.editPhoto') }}
          </span>
        </button>
      </div>
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
import AppIcon from '../ui/AppIcon.vue'
import CoverArt from '../ui/CoverArt.vue'
import { hueFor } from '/src/lib/format'
import { useI18n } from '/src/i18n'

const props = defineProps({
  title: { type: String, required: true },
  kicker: { type: String, default: '' },
  name: { type: String, default: '' },
  cover: { type: String, default: '' },
  covers: { type: Array, default: () => [] },
  icon: { type: String, default: 'disc' },
  symbol: { type: Boolean, default: false },
  round: { type: Boolean, default: false },
  // Optional background photo (artist page only - see ArtistView) and
  // whether each hover "edit photo/banner" affordance is shown at all -
  // each mirrors its own settings toggle independently.
  banner: { type: String, default: '' },
  photoEditable: { type: Boolean, default: false },
  bannerEditable: { type: Boolean, default: false },
})
defineEmits(['edit-photo', 'edit-banner'])

const { t } = useI18n()

const tint = computed(
  () => `oklch(0.45 0.08 ${hueFor(props.name || props.title)} / 0.55)`
)
</script>
