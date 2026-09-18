<template>
  <ProviderOrder
    :model-value="modelValue"
    :providers="providers"
    dense
    @update:model-value="(value) => $emit('update:modelValue', value)"
  />
</template>

<script setup>
import { computed } from 'vue'
import ProviderOrder from './ProviderOrder.vue'
import { useI18n } from '/src/i18n'

defineProps({ modelValue: { type: Array, required: true } })
defineEmits(['update:modelValue'])
const { t } = useI18n()

const providers = computed(() => [
  {
    id: 'lrclib',
    title: 'LRCLIB',
    description: t('settings.lyricsLrclibHint'),
  },
  {
    id: 'netease',
    title: t('settings.lyricsNetease'),
    description: t('settings.lyricsNeteaseHint'),
  },
])
</script>
