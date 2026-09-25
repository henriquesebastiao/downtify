<template>
  <div
    role="row"
    class="flex h-9 items-center gap-3 border-b border-line px-3 text-[11px] font-semibold tracking-[0.06em] text-faint uppercase max-sm:hidden"
  >
    <span role="columnheader" class="w-6 text-center">#</span>
    <span class="size-11 shrink-0" aria-hidden="true" />
    <span role="columnheader" class="min-w-0 flex-1">{{
      t('track.title')
    }}</span>
    <span role="columnheader" class="w-[30%] max-lg:hidden">{{
      t('track.album')
    }}</span>
    <span role="columnheader" class="w-12 text-right">
      <AppIcon name="clock" :size="14" class="inline" />
    </span>
    <span class="w-28 shrink-0" aria-hidden="true" />
  </div>
</template>

<script setup>
// The column headings for a list of TrackDownPlay rows, in the style of
// TrackList's. Its columns are the row's, so the two have to change together
// (widths, and what is hidden at which breakpoint).
import AppIcon from '../ui/AppIcon.vue'
import { useI18n } from '/src/i18n'

const { t } = useI18n()
</script>
