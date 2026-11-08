<template>
  <UiSelect
    :model-value="name"
    :options="options"
    :label="t('library.sortBy')"
    icon="sort"
    @update:model-value="$emit('update:modelValue', trackSortByName($event))"
  />
</template>

<script setup>
// Picks how a list of tracks is ordered. The column headers sort too, but
// they're hidden on a phone and don't say which way "added" goes.
import { computed } from 'vue'
import UiSelect from '../ui/UiSelect.vue'
import { TRACK_SORTS, trackSortByName, trackSortName } from '/src/lib/library'
import { useI18n } from '/src/i18n'

const props = defineProps({
  // `{ key, dir }`
  modelValue: { type: Object, required: true },
  // Offer "Playlist order" (a playlist's own order).
  playlistOrder: { type: Boolean, default: false },
})
defineEmits(['update:modelValue'])

const { t } = useI18n()

const name = computed(() => trackSortName(props.modelValue))
const options = computed(() =>
  TRACK_SORTS.filter(([id]) => props.playlistOrder || id !== 'order').map(
    ([id]) => ({ value: id, label: t(`library.trackSort.${id}`) })
  )
)
</script>
