<template>
  <ProviderOrder
    :model-value="modelValue"
    :providers="providers"
    :first-when-enabled="['slskd']"
    @update:model-value="(value) => $emit('update:modelValue', value)"
    @enabled="(id) => id === 'slskd' && $emit('enable-slskd')"
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
defineEmits(['update:modelValue', 'enable-slskd'])
const { t } = useI18n()

// slskd first: it's the only lossless source, so when it's on it leads.
const providers = computed(() => [
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
])
</script>
