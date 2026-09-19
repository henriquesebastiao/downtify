<template>
  <Transition name="now-playing">
    <div
      v-if="count"
      class="sticky top-[76px] z-20 flex flex-wrap items-center gap-2 rounded-[14px] border border-line-3 bg-surface-2/95 p-2 pl-4 shadow-float backdrop-blur-xl md:top-[84px]"
    >
      <span class="tabular text-sm font-semibold">{{
        t('library.selectedCount', { count })
      }}</span>
      <button
        v-if="count < total"
        type="button"
        class="rounded-control px-2 py-1 text-[13px] font-semibold text-accent hover:bg-accent/10"
        @click="$emit('select-all')"
      >
        {{ t('library.selectAllCount', { count: total }) }}
      </button>
      <div class="ml-auto flex flex-wrap items-center gap-1.5">
        <UiButton
          size="sm"
          variant="secondary"
          icon="play"
          @click="$emit('play')"
        >
          <span class="max-sm:sr-only">{{ t('actions.play') }}</span>
        </UiButton>
        <UiButton
          size="sm"
          variant="secondary"
          icon="queue"
          @click="$emit('enqueue')"
        >
          <span class="max-sm:sr-only">{{ t('actions.addToQueue') }}</span>
        </UiButton>
        <UiButton
          size="sm"
          variant="secondary"
          icon="zip"
          :loading="zipping"
          @click="$emit('zip')"
        >
          <span class="max-sm:sr-only">{{ t('library.downloadZip') }}</span>
        </UiButton>
        <UiButton
          size="sm"
          variant="danger"
          icon="trash"
          @click="$emit('delete')"
        >
          <span class="max-sm:sr-only">{{ t('actions.delete') }}</span>
        </UiButton>
        <UiIconButton
          icon="x"
          :label="t('library.clearSelection')"
          size="sm"
          @click="$emit('clear')"
        />
      </div>
    </div>
  </Transition>
</template>

<script setup>
import UiButton from '../ui/UiButton.vue'
import UiIconButton from '../ui/UiIconButton.vue'
import { useI18n } from '/src/i18n'

defineProps({
  count: { type: Number, default: 0 },
  total: { type: Number, default: 0 },
  zipping: { type: Boolean, default: false },
})
defineEmits(['select-all', 'play', 'enqueue', 'zip', 'delete', 'clear'])
const { t } = useI18n()
</script>
