<template>
  <!-- An artist watch's filters: which kinds of release to download, and
       whether to skip what's already out. Used when adding a watch and in
       its edit dialog. -->
  <div class="flex flex-col gap-3">
    <div class="flex flex-wrap items-center gap-2">
      <span class="text-[13px] font-semibold text-fg-3">{{
        t('monitor.releaseTypes')
      }}</span>
      <button
        v-for="type in RELEASE_TYPES"
        :key="type"
        type="button"
        class="inline-flex h-8 items-center gap-1.5 rounded-full px-3 text-[13px] font-medium transition-colors disabled:cursor-not-allowed"
        :class="
          types.includes(type)
            ? 'bg-fg text-bg'
            : 'bg-surface-2 text-fg-3 hover:bg-raised'
        "
        :aria-pressed="types.includes(type)"
        :disabled="types.length === 1 && types.includes(type)"
        :title="
          types.length === 1 && types.includes(type)
            ? t('monitor.releaseTypesAtLeastOne')
            : ''
        "
        @click="$emit('update:types', toggleReleaseType(types, type))"
      >
        <AppIcon v-if="types.includes(type)" name="check" :size="14" />
        {{ t(`monitor.release.${type}`) }}
      </button>
    </div>
    <UiSwitch
      :model-value="newOnly"
      :label="t('monitor.newOnly')"
      :description="hint"
      @update:model-value="(value) => $emit('update:newOnly', value)"
    />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import AppIcon from '../ui/AppIcon.vue'
import UiSwitch from '../ui/UiSwitch.vue'
import { RELEASE_TYPES, toggleReleaseType } from '/src/lib/watches'
import { useI18n } from '/src/i18n'

const props = defineProps({
  types: { type: Array, required: true },
  newOnly: { type: Boolean, default: false },
  // The watch already exists: say what switching "new releases only"
  // does to it, rather than what it does for a new one.
  existing: { type: Boolean, default: false },
  // ...and whether it was on when the dialog opened.
  wasNewOnly: { type: Boolean, default: false },
})
defineEmits(['update:types', 'update:newOnly'])

const { t } = useI18n()

const hint = computed(() => {
  if (!props.existing) return t('monitor.newOnlyHint')
  if (props.newOnly && !props.wasNewOnly) return t('monitor.newOnlyTurnOn')
  if (!props.newOnly && props.wasNewOnly) return t('monitor.newOnlyTurnOff')
  return t('monitor.newOnlyHint')
})
</script>
