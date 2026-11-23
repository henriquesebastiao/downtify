<template>
  <button
    v-if="src"
    type="button"
    class="relative shrink-0 cursor-zoom-in overflow-hidden rounded-control"
    :class="sizeClass"
    :aria-label="t('doctor.coverOf', { name })"
    :title="name"
    @click="open = true"
  >
    <CoverArt
      :src="src"
      :name="name"
      :thumb="thumb"
      rounded="rounded-control"
      :letter-size="14"
      :icon-size="16"
      class="size-full"
    />
  </button>
  <span
    v-else
    class="flex shrink-0 items-center justify-center rounded-control bg-raised text-muted"
    :class="sizeClass"
  >
    <AppIcon name="music" :size="16" />
  </span>
  <UiModal :open="open" :title="name || ' '" @close="open = false">
    <img
      v-if="open"
      :src="full"
      :alt="name"
      class="mx-auto max-h-[70vh] max-w-full rounded-control object-contain"
    />
  </UiModal>
</template>

<script setup>
// A small cover for a Doctor row: a song's embedded cover (by its library
// file) or a playlist's own sidecar picture (by its M3U). Clicking it
// shows it full size, so two copies can be told apart by their artwork.
import { computed, ref } from 'vue'

import { useI18n } from '/src/i18n'
import { coverURL } from '/src/lib/paths'
import AppIcon from '/src/components/ui/AppIcon.vue'
import CoverArt from '/src/components/ui/CoverArt.vue'
import UiModal from '/src/components/ui/UiModal.vue'
import { playlistCoverOf } from './covers'

const props = defineProps({
  /** A library file: its embedded cover. */
  file: { type: String, default: '' },
  /** Or a playlist's M3U: the picture saved beside it. */
  m3u: { type: String, default: '' },
  /** Changes the URL when the picture may have changed. */
  version: { type: String, default: '' },
  name: { type: String, default: '' },
  /** 'sm' (40 px) or 'md' (48 px). */
  size: { type: String, default: 'md' },
})

const { t } = useI18n()
const open = ref(false)

const sizeClass = computed(() => (props.size === 'sm' ? 'size-10' : 'size-12'))
const thumb = computed(() => (props.file ? 48 : 0))
const full = computed(() =>
  props.file ? coverURL(props.file) : playlistCoverOf(props.m3u, props.version)
)
const src = computed(() => (props.file || props.m3u ? full.value : ''))
</script>
