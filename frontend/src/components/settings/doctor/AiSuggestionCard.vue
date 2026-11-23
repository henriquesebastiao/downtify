<template>
  <div class="flex flex-col" :data-suggestion="item.id">
    <div class="flex flex-wrap items-center gap-2 px-5 pt-4 text-[13px]">
      <UiBadge :tone="decisionTone">{{ decisionLabel }}</UiBadge>
      <UiBadge :tone="stateTone">
        {{ t(`doctor.ai.state.${item.state}`) }}
      </UiBadge>
    </div>

    <!-- Duplicate playlists: covers, song counts, the kept file. -->
    <PlaylistGroupCard
      v-if="item.kind === 'playlists'"
      :group="item.group"
      :cover-version="item.created_at"
      readonly
      :apart="item.decision === 'apart'"
    />

    <!-- Duplicate songs: every copy with a player, the kept one marked. -->
    <template v-else-if="item.kind === 'songs'">
      <DuplicateGroupCard
        :group="item.group"
        readonly
        :keep-file="item.decision === 'keep' ? item.keep : ''"
      />
      <p
        v-if="item.decision === 'keep'"
        class="mx-5 -mt-2 mb-2 text-[13px]"
        :class="item.permanent ? 'text-warn' : 'text-muted'"
      >
        {{
          item.permanent
            ? t('doctor.ai.songsForGood')
            : t('doctor.ai.songsTrash')
        }}
      </p>
    </template>

    <!-- slskd leftovers: what goes, and the library copy it matches. -->
    <div
      v-else-if="item.kind === 'slskd'"
      class="flex flex-col gap-2 px-5 py-4 text-[13px]"
    >
      <p class="text-fg">
        {{
          t('doctor.ai.slskdSummary', {
            count: item.count,
            size: formatBytes(item.bytes),
          })
        }}
      </p>
      <ul class="flex flex-col gap-1.5">
        <li
          v-for="file in item.preview"
          :key="file.file"
          class="flex items-center gap-3 rounded-control bg-surface-2 px-3 py-2"
        >
          <DoctorCover :file="file.match || file.file" size="sm" />
          <span class="flex min-w-0 flex-1 flex-col">
            <span class="text-fg [overflow-wrap:anywhere]">{{
              file.file
            }}</span>
            <span class="text-muted [overflow-wrap:anywhere]">
              = {{ file.match }} · {{ formatBytes(file.bytes) }}
            </span>
          </span>
        </li>
      </ul>
      <p v-if="item.count > item.preview.length" class="text-muted">
        {{
          t('doctor.ai.andMore', { count: item.count - item.preview.length })
        }}
      </p>
    </div>

    <!-- Navidrome: the playlists that go, and what kind each is. -->
    <div
      v-else-if="item.kind === 'navidrome'"
      class="flex flex-col gap-2 px-5 py-4 text-[13px]"
    >
      <ul class="flex flex-col gap-1.5">
        <li
          v-for="playlist in item.playlists"
          :key="playlist.id"
          class="flex flex-wrap items-center gap-x-3 gap-y-1 rounded-control bg-surface-2 px-3 py-2"
        >
          <DoctorCover
            :m3u="playlist.m3u_exists ? playlist.m3u : ''"
            :name="playlist.name"
            :version="item.created_at"
            size="sm"
          />
          <span class="min-w-0 flex-1 truncate text-fg">
            {{ playlist.name || playlist.id }}
          </span>
          <span class="tabular text-muted">
            {{ t('doctor.songsCount', { count: playlist.songs || 0 }) }}
          </span>
          <UiBadge tone="neutral">
            {{ t(`doctor.ai.ndKind.${playlist.kind || 'other'}`) }}
          </UiBadge>
          <UiBadge tone="danger">{{ t('doctor.ai.ndRemoved') }}</UiBadge>
        </li>
      </ul>
      <p v-if="item.enable_m3u_import" class="text-muted">
        {{ t('doctor.ai.ndImport') }}
      </p>
    </div>

    <div class="flex flex-col gap-2 px-5 pb-4 text-[13px]">
      <p class="rounded-control bg-accent/6 px-3 py-2 text-fg">
        <span class="font-semibold">{{ t('doctor.ai.why') }}</span>
        {{ item.reason }}
      </p>
      <p v-if="item.error" class="text-danger">{{ errorText }}</p>
      <div v-if="item.state === 'waiting'" class="flex flex-wrap gap-2">
        <UiButton
          size="sm"
          variant="primary"
          icon="check"
          :disabled="busy || locked"
          @click="$emit('apply', [item.id])"
        >
          {{ t('doctor.ai.apply') }}
        </UiButton>
        <UiButton
          size="sm"
          variant="ghost"
          icon="x"
          :disabled="busy"
          @click="$emit('dismiss', [item.id])"
        >
          {{ t('doctor.ai.dismiss') }}
        </UiButton>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

import { useI18n } from '/src/i18n'
import { formatBytes } from '/src/lib/format'
import UiBadge from '/src/components/ui/UiBadge.vue'
import UiButton from '/src/components/ui/UiButton.vue'
import DoctorCover from './DoctorCover.vue'
import DuplicateGroupCard from './DuplicateGroupCard.vue'
import PlaylistGroupCard from './PlaylistGroupCard.vue'

const props = defineProps({
  item: { type: Object, required: true },
  busy: { type: Boolean, default: false },
  /** Its Doctor section is out of date: apply after checking again. */
  locked: { type: Boolean, default: false },
})
defineEmits(['apply', 'dismiss'])

const { t } = useI18n()

const decisionLabel = computed(() => {
  const { kind, decision } = props.item
  if (kind === 'songs')
    return decision === 'keep'
      ? t('doctor.ai.decisionKeep')
      : t('doctor.ai.decisionSongsApart')
  if (kind === 'slskd') return t('doctor.ai.decisionClean')
  if (kind === 'navidrome') return t('doctor.ai.decisionNavidrome')
  return decision === 'merge'
    ? t('doctor.ai.decisionMerge')
    : t('doctor.ai.decisionApart')
})

const decisionTone = computed(() =>
  props.item.decision === 'apart' ? 'neutral' : 'accent'
)

// The Doctor's own message for its error code, else the server's text.
const errorText = computed(() => {
  const code = props.item.error_code
  const key = `doctor.error.${code}`
  const text = code ? t(key) : ''
  return text && text !== key ? text : props.item.error
})

const stateTone = computed(() => {
  if (props.item.state === 'applied') return 'accent'
  if (props.item.state === 'failed') return 'danger'
  return 'neutral'
})
</script>
