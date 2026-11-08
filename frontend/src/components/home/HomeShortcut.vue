<template>
  <div
    class="group relative min-w-0 overflow-hidden rounded-[12px] bg-surface-2"
  >
    <RouterLink
      :to="entry.route || { name: 'Home' }"
      class="flex h-16 min-w-0 items-center gap-2.5 pr-3 transition-colors hover:bg-line-2"
      @click="$emit('open')"
    >
      <CoverArt
        :src="entry.cover"
        :covers="entry.covers"
        :name="entry.title"
        :icon="
          entry.type === 'artist'
            ? 'user'
            : entry.type === 'playlist'
              ? 'playlist'
              : 'disc'
        "
        rounded="rounded-none"
        :letter-size="16"
        :icon-size="20"
        class="size-14 shrink-0"
      />
      <span
        class="flex min-w-0 flex-1 flex-col"
        :class="entry.playlist ? 'pr-5' : ''"
      >
        <span class="truncate text-[13px] font-semibold" :title="entry.title">{{
          entry.title
        }}</span>
        <span class="truncate text-xs text-muted">{{
          entry.subtitle || t(`home.kind.${entry.type}`)
        }}</span>
      </span>
      <EqBars v-if="entry.playing" :size="12" />
    </RouterLink>
    <UiIconButton
      v-if="entry.playlist && entry.playlist.count"
      icon="play"
      :label="t('common.play')"
      class="absolute right-1 top-1/2 -translate-y-1/2 !size-8"
      @click="$emit('play', entry.playlist)"
    />
  </div>
</template>

<script setup>
import CoverArt from '/src/components/ui/CoverArt.vue'
import EqBars from '/src/components/ui/EqBars.vue'
import UiIconButton from '/src/components/ui/UiIconButton.vue'
import { useI18n } from '/src/i18n'

defineProps({ entry: { type: Object, required: true } })
defineEmits(['open', 'play'])
const { t } = useI18n()
</script>
