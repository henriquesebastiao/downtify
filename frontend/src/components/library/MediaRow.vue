<template>
  <div
    class="group flex h-[72px] items-center gap-4 rounded-[12px] px-3 transition-colors hover:bg-surface"
  >
    <RouterLink :to="to" class="flex min-w-0 flex-1 items-center gap-4">
      <CoverArt
        :src="cover"
        :covers="covers"
        :name="name || title"
        :round="round"
        :icon="icon"
        rounded="rounded-[8px]"
        :letter-size="20"
        :icon-size="20"
        class="size-[52px]"
      />
      <span class="flex min-w-0 flex-1 flex-col gap-0.5">
        <span class="flex items-center gap-2">
          <span class="truncate text-[15px] font-semibold text-fg">{{
            title
          }}</span>
          <EqBars v-if="playing" :size="10" />
        </span>
        <span class="truncate text-[13px] text-muted">{{ subtitle }}</span>
      </span>
    </RouterLink>
    <div class="hidden min-w-0 items-center gap-2 md:flex">
      <slot name="meta" />
    </div>
    <span
      v-if="aside"
      class="tabular hidden w-24 text-right text-[13px] text-muted sm:block"
    >
      {{ aside }}
    </span>
    <div class="flex items-center gap-1">
      <slot name="actions" />
      <UiIconButton
        v-if="playable"
        icon="play"
        :label="t('actions.playItem', { name: title })"
        size="sm"
        class="opacity-100 lg:opacity-0 lg:group-hover:opacity-100 lg:focus-visible:opacity-100"
        @click="$emit('play')"
      />
    </div>
  </div>
</template>

<script setup>
import CoverArt from '../ui/CoverArt.vue'
import EqBars from '../ui/EqBars.vue'
import UiIconButton from '../ui/UiIconButton.vue'
import { useI18n } from '/src/i18n'

defineProps({
  to: { type: [String, Object], required: true },
  title: { type: String, required: true },
  subtitle: { type: String, default: '' },
  aside: { type: String, default: '' },
  name: { type: String, default: '' },
  cover: { type: String, default: '' },
  covers: { type: Array, default: () => [] },
  icon: { type: String, default: 'disc' },
  round: { type: Boolean, default: false },
  playing: { type: Boolean, default: false },
  playable: { type: Boolean, default: true },
})
defineEmits(['play'])
const { t } = useI18n()
</script>
