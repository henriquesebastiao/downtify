<template>
  <span
    v-if="meta"
    class="inline-flex h-[22px] shrink-0 items-center gap-1.5 rounded-full border text-[11px] font-semibold whitespace-nowrap"
    :class="[meta.classes, compact ? 'w-[22px] justify-center' : 'px-2']"
    :title="t('source.from', { source: meta.label })"
  >
    <AppIcon :name="meta.icon" :size="11" />
    <span v-if="!compact">{{ meta.label }}</span>
  </span>
</template>

<script setup>
import { computed } from 'vue'
import AppIcon from './AppIcon.vue'
import { useI18n } from '/src/i18n'

const props = defineProps({
  source: { type: String, default: '' },
  compact: { type: Boolean, default: false },
})
const { t } = useI18n()

// The audio source a track was downloaded from (backend job `provider`).
const SOURCES = {
  'youtube-music': {
    label: 'YouTube Music',
    icon: 'youtube',
    classes: 'border-src-ytm/25 bg-src-ytm/15 text-src-ytm',
  },
  youtube: {
    label: 'YouTube',
    icon: 'youtube',
    classes: 'border-src-yt/20 bg-src-yt/10 text-src-yt',
  },
  slskd: {
    label: 'slskd',
    icon: 'share',
    classes: 'border-src-slskd/25 bg-src-slskd/15 text-src-slskd',
  },
}

const meta = computed(() => SOURCES[props.source] || null)
</script>
