<template>
  <section
    class="flex min-w-0 flex-col gap-4 rounded-panel border border-line-2 bg-surface p-4 sm:p-5"
    :data-home-shelf="kind"
  >
    <div class="flex items-baseline justify-between gap-3">
      <h2 class="text-display text-lg font-semibold">{{ title }}</h2>
      <button
        type="button"
        class="shrink-0 text-[13px] font-semibold text-accent hover:text-accent-hi"
        @click="expanded = true"
      >
        {{ t('common.seeAll') }}
      </button>
    </div>
    <div class="grid grid-cols-2 gap-2.5 sm:grid-cols-3" data-home-preview>
      <HomeShortcut
        v-for="entry in entries.slice(0, 6)"
        :key="entry.id"
        :entry="entry"
        @play="$emit('play', $event)"
      />
    </div>
    <UiModal
      :open="expanded"
      :title="title"
      width="sm:max-w-4xl"
      @close="expanded = false"
    >
      <div class="grid gap-2.5 sm:grid-cols-2 lg:grid-cols-3">
        <HomeShortcut
          v-for="entry in entries"
          :key="entry.id"
          :entry="entry"
          @open="expanded = false"
          @play="$emit('play', $event)"
        />
      </div>
    </UiModal>
  </section>
</template>

<script setup>
import { ref } from 'vue'
import UiModal from '/src/components/ui/UiModal.vue'
import HomeShortcut from './HomeShortcut.vue'
import { useI18n } from '/src/i18n'

defineProps({
  title: { type: String, required: true },
  kind: { type: String, required: true },
  entries: { type: Array, required: true },
})
defineEmits(['play'])
const { t } = useI18n()
const expanded = ref(false)
</script>
