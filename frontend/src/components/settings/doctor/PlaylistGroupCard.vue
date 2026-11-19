<template>
  <div class="flex flex-col gap-2 px-5 py-4 text-[13px]">
    <div class="flex flex-wrap items-center gap-2">
      <p class="font-semibold text-fg">{{ title }}</p>
      <UiBadge :tone="group.safe ? 'accent' : 'warn'">
        {{ t(`doctor.groupReason.${group.reason}`) }}
      </UiBadge>
    </div>
    <ul class="flex flex-col gap-1">
      <li
        v-for="member in group.members"
        :key="member.path"
        class="flex flex-wrap items-center gap-x-3 rounded-control bg-surface-2 px-3 py-2"
      >
        <img
          v-if="member.cover"
          :src="playlistCoverOf(member.path, coverVersion)"
          :alt="t('doctor.coverOf', { name: member.path })"
          loading="lazy"
          class="size-12 shrink-0 cursor-zoom-in rounded-control object-cover"
          @click="zoomed = member.path"
        />
        <span
          v-else
          class="flex size-12 shrink-0 items-center justify-center rounded-control bg-raised text-muted"
          :title="t('doctor.noCover')"
        >
          <AppIcon name="music" :size="18" />
        </span>
        <span class="min-w-0 flex-1 truncate text-fg">{{ member.path }}</span>
        <span class="tabular text-muted">
          {{ t('doctor.songsCount', { count: member.songs }) }}
        </span>
        <UiBadge v-if="member.path === group.keeper" tone="accent">
          {{ t('doctor.keeps') }}
        </UiBadge>
      </li>
    </ul>
    <figure
      v-if="zoomed"
      class="flex flex-col items-start gap-2 rounded-control bg-surface-2 p-3"
    >
      <img
        :src="playlistCoverOf(zoomed, coverVersion)"
        :alt="t('doctor.coverOf', { name: zoomed })"
        class="max-h-80 max-w-full rounded-control object-contain"
      />
      <figcaption class="flex w-full items-center justify-between gap-2">
        <span class="truncate text-muted">{{ zoomed }}</span>
        <UiButton size="sm" variant="ghost" @click="zoomed = ''">
          {{ t('common.close') }}
        </UiButton>
      </figcaption>
    </figure>
    <p class="text-muted">
      {{
        group.safe
          ? t('doctor.mergePlan', {
              songs: group.songs_after,
              overlap: Math.round(group.overlap * 100),
            })
          : t('doctor.mergeUnsafe', {
              overlap: Math.round(group.overlap * 100),
            })
      }}
    </p>
    <div>
      <UiButton
        size="sm"
        icon="check"
        :disabled="busy || !group.safe"
        @click="$emit('merge', group)"
      >
        {{ t('doctor.merge') }}
      </UiButton>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'

import { useI18n } from '/src/i18n'
import AppIcon from '/src/components/ui/AppIcon.vue'
import UiBadge from '/src/components/ui/UiBadge.vue'
import UiButton from '/src/components/ui/UiButton.vue'
import { playlistCoverOf } from './covers'

const props = defineProps({
  group: { type: Object, required: true },
  busy: { type: Boolean, default: false },
  /** Changes when the covers may have changed (the last check's time). */
  coverVersion: { type: String, default: '' },
})
defineEmits(['merge'])

const { t } = useI18n()
const zoomed = ref('')

const title = computed(() => {
  const keeper = props.group.keeper || props.group.members[0]?.path || ''
  return keeper
    .split('/')
    .pop()
    .replace(/\.m3u$/i, '')
})
</script>
