<template>
  <section
    class="flex flex-col rounded-panel border border-line-2 bg-surface"
    :data-section="id"
  >
    <button
      type="button"
      class="flex w-full items-center gap-3 rounded-panel px-5 py-4 text-left hover:bg-surface-2"
      :aria-expanded="open"
      :aria-controls="`doctor-section-${id}`"
      @click="toggle"
    >
      <span class="flex min-w-0 flex-1 flex-col gap-0.5">
        <span class="text-display text-base font-semibold text-fg">
          {{ title }}
        </span>
        <span
          v-if="description && open"
          class="text-[13px] text-pretty text-muted"
        >
          {{ description }}
        </span>
      </span>
      <UiBadge v-if="stale" tone="warn">{{ t('doctor.outOfDate') }}</UiBadge>
      <UiBadge v-else-if="status" :tone="statusTone">{{ status }}</UiBadge>
      <AppIcon
        :name="open ? 'chevron-up' : 'chevron-down'"
        :size="16"
        class="shrink-0 text-muted"
      />
    </button>
    <div
      v-show="open"
      :id="`doctor-section-${id}`"
      class="flex flex-col divide-y divide-line border-t border-line"
    >
      <div
        v-if="stale"
        class="flex flex-wrap items-center justify-between gap-3 bg-warn/8 px-5 py-3 text-[13px] text-warn"
        role="status"
      >
        <span class="min-w-0 flex-1">{{ t('doctor.staleHint') }}</span>
        <UiButton
          size="sm"
          icon="refresh"
          :disabled="busy"
          @click="$emit('recheck')"
        >
          {{ t('doctor.checkAgain') }}
        </UiButton>
      </div>
      <slot />
    </div>
  </section>
</template>

<script setup>
import { ref } from 'vue'

import { useI18n } from '/src/i18n'
import AppIcon from '/src/components/ui/AppIcon.vue'
import UiBadge from '/src/components/ui/UiBadge.vue'
import UiButton from '/src/components/ui/UiButton.vue'

const props = defineProps({
  id: { type: String, required: true },
  title: { type: String, required: true },
  description: { type: String, default: '' },
  /** Short summary shown on the closed header, e.g. "3 to merge". */
  status: { type: String, default: '' },
  statusTone: { type: String, default: 'neutral' },
  /** A repair elsewhere may have changed these findings. */
  stale: { type: Boolean, default: false },
  busy: { type: Boolean, default: false },
})
defineEmits(['recheck'])

const { t } = useI18n()

// Which sections are open is a per-browser convenience, so it lives in
// localStorage; without it every section starts closed.
const STORE_KEY = 'downtify.doctor.open'

function readOpen() {
  try {
    return JSON.parse(localStorage.getItem(STORE_KEY) || '{}') || {}
  } catch {
    return {}
  }
}

const open = ref(Boolean(readOpen()[props.id]))

function toggle() {
  open.value = !open.value
  try {
    const all = readOpen()
    all[props.id] = open.value
    localStorage.setItem(STORE_KEY, JSON.stringify(all))
  } catch {
    // Storage blocked: the section just won't remember it.
  }
}
</script>
