<template>
  <div class="flex flex-col gap-2 px-5 py-4 text-[13px]">
    <div class="flex flex-wrap items-center gap-2">
      <p class="min-w-0 font-semibold text-fg">
        {{ group.artist }} — {{ group.title }}
      </p>
      <UiBadge :tone="group.kind === 'exact' ? 'accent' : 'neutral'">
        {{
          group.kind === 'exact'
            ? t('doctor.duplicatesExact')
            : t('doctor.duplicatesLikely')
        }}
      </UiBadge>
    </div>
    <ul class="flex flex-col gap-1.5">
      <li
        v-for="file in group.files"
        :key="file.file"
        class="flex flex-col gap-1.5 rounded-control border px-3 py-2"
        :class="
          file.file === keep
            ? 'border-accent bg-accent/8'
            : 'border-transparent bg-surface-2'
        "
      >
        <label class="flex min-w-0 cursor-pointer items-start gap-2">
          <input
            v-model="keep"
            type="radio"
            class="mt-0.5 accent-[var(--color-accent)]"
            :name="radioName"
            :value="file.file"
            :disabled="busy"
          />
          <span class="flex min-w-0 flex-1 flex-col">
            <span class="text-fg [overflow-wrap:anywhere]">
              {{ file.file }}
            </span>
            <span class="tabular text-muted">{{ details(file) }}</span>
            <span v-if="ownTags(file)" class="text-muted">
              {{ ownTags(file) }}
            </span>
            <span class="text-muted">
              {{
                file.playlists?.length
                  ? t('doctor.dupeIn', { playlists: file.playlists.join(', ') })
                  : t('doctor.dupeInNone')
              }}
            </span>
          </span>
          <UiBadge v-if="file.file === keep" tone="accent">
            {{ t('doctor.dupeKeep') }}
          </UiBadge>
        </label>
        <!-- Listen before deciding: the same file the player streams,
             with seeking; one copy plays at a time. -->
        <audio
          class="h-8 w-full"
          controls
          preload="none"
          :src="fileURL(file.file)"
          @play="onlyThis"
        />
      </li>
    </ul>
    <div class="flex flex-wrap gap-2">
      <UiButton
        size="sm"
        variant="primary"
        icon="check"
        :disabled="busy || !keep"
        @click="$emit('merge', { keep, remove: others })"
      >
        {{ t('doctor.dupeMerge') }}
      </UiButton>
      <UiButton
        size="sm"
        variant="ghost"
        :disabled="busy"
        @click="
          $emit(
            'keep-all',
            group.files.map((f) => f.file)
          )
        "
      >
        {{ t('doctor.dupeKeepAll') }}
      </UiButton>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'

import { useI18n } from '/src/i18n'
import { fileURL } from '/src/lib/paths'
import { formatBytes, formatDuration } from '/src/lib/format'
import { usePlayer } from '/src/model/player'
import UiBadge from '/src/components/ui/UiBadge.vue'
import UiButton from '/src/components/ui/UiButton.vue'

const props = defineProps({
  group: { type: Object, required: true },
  busy: { type: Boolean, default: false },
})
defineEmits(['merge', 'keep-all'])

const { t } = useI18n()
const player = usePlayer()

// Suggested: the copy in the most playlists, then the biggest (usually
// the best quality; the list is sorted biggest first).
const suggested = [...props.group.files].sort(
  (a, b) => (b.playlists?.length || 0) - (a.playlists?.length || 0)
)[0]
const keep = ref(suggested?.file || '')
const radioName = `keep-${Math.random().toString(36).slice(2)}`
const others = computed(() =>
  props.group.files.map((f) => f.file).filter((f) => f !== keep.value)
)

function details(file) {
  const parts = []
  // The library reads bitrates in bits per second.
  const kbps = Math.round((file.bitrate || 0) / 1000)
  const format = [file.codec?.toUpperCase(), kbps && `${kbps} kbps`]
    .filter(Boolean)
    .join(' ')
  if (format) parts.push(format)
  parts.push(formatBytes(file.bytes))
  if (file.duration) parts.push(formatDuration(file.duration))
  if (file.provider && file.provider !== 'unknown') parts.push(file.provider)
  return parts.join(' · ')
}

// Each copy's own tags: a look-alike can be another recording uploaded
// under the original's name (a parody, a sped-up edit).
function ownTags(file) {
  if (!file.title && !file.album) return ''
  return t('doctor.dupeTags', {
    title: file.title || props.group.title,
    album: file.album || '—',
  })
}

// One copy plays at a time, and the main player stops for it.
function onlyThis(event) {
  if (player.isPlaying.value) player.pause()
  for (const audio of document.querySelectorAll('audio')) {
    if (audio !== event.target && !audio.paused) audio.pause()
  }
}
</script>
