<template>
  <ProviderOrder
    :model-value="modelValue"
    :providers="providers"
    :first-when-enabled="['slskd', 'deemix']"
    @update:model-value="(value) => $emit('update:modelValue', value)"
    @enabled="(id) => $emit(`enable-${id}`)"
  >
    <template #badge="{ row }">
      <SourceBadge :source="row.id" />
    </template>
  </ProviderOrder>
</template>

<script setup>
import { computed } from 'vue'
import ProviderOrder from './ProviderOrder.vue'
import SourceBadge from '../ui/SourceBadge.vue'
import { useI18n } from '/src/i18n'

defineProps({ modelValue: { type: Array, required: true } })
defineEmits(['update:modelValue', 'enable-slskd', 'enable-deemix'])
const { t } = useI18n()

// Optional local services lead only when explicitly enabled.
const providers = computed(() => [
  {
    id: 'deemix',
    title: t('settings.deemixTitle'),
    description: t('settings.deemixHint'),
  },
  {
    id: 'slskd',
    title: t('settings.sourceSlskd'),
    description: t('settings.sourceSlskdHint'),
  },
  {
    id: 'youtube-music',
    title: t('settings.sourceYtm'),
    description: t('settings.sourceYtmHint'),
  },
  {
    id: 'youtube',
    title: t('settings.sourceYt'),
    description: t('settings.sourceYtHint'),
  },
  {
    id: 'soundcloud',
    title: t('settings.sourceSoundcloud'),
    description: t('settings.sourceSoundcloudHint'),
  },
])
</script>
