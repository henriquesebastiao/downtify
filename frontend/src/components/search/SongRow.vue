<template>
  <div
    class="group flex h-16 items-center gap-3 rounded-[12px] px-3 transition-colors hover:bg-surface"
  >
    <span
      v-if="index !== null"
      class="tabular w-6 text-center text-[13px] text-faint max-sm:hidden"
    >
      {{ index + 1 }}
    </span>
    <CoverArt
      :src="song.cover_url"
      :name="song.album_name || song.name"
      rounded="rounded-[8px]"
      :letter-size="14"
      class="size-11"
    />
    <div class="min-w-0 flex-1">
      <p class="flex items-center gap-1.5">
        <span class="truncate text-sm font-semibold">{{ song.name }}</span>
        <span
          v-if="song.explicit"
          class="shrink-0 rounded-[3px] bg-muted px-1 text-[9px] leading-[14px] font-bold text-bg"
          :title="t('search.explicit')"
          >E</span
        >
      </p>
      <p class="truncate text-[13px] text-muted">
        {{ artists
        }}<span v-if="song.album_name" class="lg:hidden">
          · {{ song.album_name }}</span
        >
      </p>
    </div>
    <span class="hidden w-[30%] truncate text-[13px] text-muted lg:block">{{
      song.album_name
    }}</span>
    <span
      class="tabular hidden w-12 text-right text-[13px] text-muted sm:block"
    >
      {{ song.duration ? formatDuration(song.duration) : '' }}
    </span>
    <a
      v-if="sourceUrl"
      :href="sourceUrl"
      target="_blank"
      rel="noopener"
      class="hidden size-8 items-center justify-center rounded-control text-faint hover:bg-surface-2 hover:text-fg sm:flex lg:opacity-0 lg:group-hover:opacity-100"
      :title="t('search.openSource')"
      :aria-label="t('search.openSource')"
    >
      <AppIcon name="arrow-up-right" :size="16" />
    </a>
    <div class="flex w-28 shrink-0 justify-end">
      <DownloadState :song="song" />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import AppIcon from '../ui/AppIcon.vue'
import CoverArt from '../ui/CoverArt.vue'
import DownloadState from './DownloadState.vue'
import { formatDuration } from '/src/lib/format'
import { useI18n } from '/src/i18n'

const props = defineProps({
  song: { type: Object, required: true },
  index: { type: Number, default: null },
})
const { t } = useI18n()

const artists = computed(
  () =>
    (props.song.artists || []).join(', ') ||
    props.song.artist ||
    t('common.unknownArtist')
)
const sourceUrl = computed(() => {
  const url = String(props.song.url || '')
  return /^https?:\/\//.test(url) ? url : ''
})
</script>
