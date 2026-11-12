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
        class="flex flex-wrap items-center gap-x-2 rounded-control bg-surface-2 px-3 py-2"
      >
        <span class="min-w-0 flex-1 truncate text-fg">{{ member.path }}</span>
        <span class="tabular text-muted">
          {{ t('doctor.songsCount', { count: member.songs }) }}
        </span>
        <AppIcon
          v-if="member.cover"
          name="image"
          :size="14"
          class="text-muted"
          :title="t('doctor.hasCover')"
        />
        <UiBadge v-if="member.path === group.keeper" tone="accent">
          {{ t('doctor.keeps') }}
        </UiBadge>
      </li>
    </ul>
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
import { computed } from 'vue'

import { useI18n } from '/src/i18n'
import AppIcon from '/src/components/ui/AppIcon.vue'
import UiBadge from '/src/components/ui/UiBadge.vue'
import UiButton from '/src/components/ui/UiButton.vue'

const props = defineProps({
  group: { type: Object, required: true },
  busy: { type: Boolean, default: false },
})
defineEmits(['merge'])

const { t } = useI18n()

const title = computed(() => {
  const keeper = props.group.keeper || props.group.members[0]?.path || ''
  return keeper
    .split('/')
    .pop()
    .replace(/\.m3u$/i, '')
})
</script>
