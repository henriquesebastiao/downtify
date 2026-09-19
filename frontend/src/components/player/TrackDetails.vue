<template>
  <div
    v-if="track"
    class="flex h-full min-h-0 flex-col gap-5 overflow-y-auto px-2"
  >
    <dl class="grid grid-cols-[auto_1fr] gap-x-6 gap-y-3 text-sm">
      <template v-for="row in rows" :key="row.label">
        <dt class="text-white/50">{{ row.label }}</dt>
        <dd class="min-w-0 break-words text-white/90">{{ row.value }}</dd>
      </template>
    </dl>
    <div class="flex flex-wrap gap-2">
      <RouterLink
        v-if="track.album"
        :to="{
          name: 'Album',
          query: { artist: track.albumArtist, title: track.album },
        }"
        class="flex h-9 items-center gap-2 rounded-full bg-white/10 px-3.5 text-[13px] font-semibold text-white hover:bg-white/15"
      >
        <AppIcon name="disc" :size="15" />{{ t('player.goToAlbum') }}
      </RouterLink>
      <RouterLink
        v-if="track.albumArtist"
        :to="{ name: 'Artist', query: { name: track.albumArtist } }"
        class="flex h-9 items-center gap-2 rounded-full bg-white/10 px-3.5 text-[13px] font-semibold text-white hover:bg-white/15"
      >
        <AppIcon name="user" :size="15" />{{ t('player.goToArtist') }}
      </RouterLink>
      <a
        :href="track.url"
        :download="saveName(track.file)"
        class="flex h-9 items-center gap-2 rounded-full bg-white/10 px-3.5 text-[13px] font-semibold text-white hover:bg-white/15"
      >
        <AppIcon name="download" :size="15" />{{ t('library.saveToDevice') }}
      </a>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import AppIcon from '../ui/AppIcon.vue'
import { usePlayer } from '/src/model/player'
import { formatBytes, formatDuration, timeAgo } from '/src/lib/format'
import { saveName } from '/src/lib/paths'
import { useI18n } from '/src/i18n'

const player = usePlayer()
const { t, locale } = useI18n()
const track = computed(() => player.currentTrack.value)

const rows = computed(() => {
  const tr = track.value
  if (!tr) return []
  return [
    { label: t('track.title'), value: tr.title },
    { label: t('track.artist'), value: tr.artist },
    { label: t('track.album'), value: tr.album },
    { label: t('track.trackNumber'), value: tr.trackNumber || '' },
    { label: t('track.year'), value: tr.year },
    {
      label: t('track.length'),
      value: tr.duration ? formatDuration(tr.duration) : '',
    },
    { label: t('track.format'), value: tr.format },
    { label: t('track.size'), value: tr.size ? formatBytes(tr.size) : '' },
    {
      label: t('track.added'),
      value: tr.added ? timeAgo(tr.added, locale.value) : '',
    },
    { label: t('track.file'), value: tr.file },
  ].filter((row) => row.value !== '' && row.value !== undefined)
})
</script>
