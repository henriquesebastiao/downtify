<template>
  <ol class="flex flex-col gap-2" :class="dense ? '' : 'p-4'">
    <li
      v-for="(row, i) in rows"
      :key="row.id"
      class="flex flex-wrap items-center gap-x-3 gap-y-2 rounded-[12px] border bg-bg px-3 py-2.5 transition-colors"
      :class="[
        row.enabled ? 'border-line-3' : 'border-line-2 opacity-60',
        dragOver === i ? 'border-accent' : '',
      ]"
      :draggable="row.enabled"
      @dragstart="dragFrom = i"
      @dragover.prevent="dragOver = i"
      @dragleave="dragOver = -1"
      @drop.prevent="drop(i)"
      @dragend="dragOver = -1"
    >
      <AppIcon
        name="grip"
        :size="18"
        class="hidden cursor-grab text-faint sm:block"
      />
      <span
        class="text-display tabular flex size-6 shrink-0 items-center justify-center rounded-full text-xs font-semibold"
        :class="
          row.enabled ? 'bg-accent/12 text-accent' : 'bg-surface-2 text-faint'
        "
        >{{ row.enabled ? row.position : '–' }}</span
      >
      <slot name="badge" :row="row" />
      <div class="min-w-0 flex-1 basis-40">
        <p class="truncate text-sm font-semibold">{{ row.title }}</p>
        <p class="text-xs text-pretty text-muted">{{ row.description }}</p>
      </div>
      <div class="ml-auto flex items-center">
        <UiIconButton
          icon="chevron-up"
          :label="t('settings.moveUp')"
          size="sm"
          :disabled="!row.enabled || row.position === 1"
          @click="apply(moveProvider(enabled, row.id, -1))"
        />
        <UiIconButton
          icon="chevron-down"
          :label="t('settings.moveDown')"
          size="sm"
          :disabled="!row.enabled || row.position === enabled.length"
          @click="apply(moveProvider(enabled, row.id, 1))"
        />
      </div>
      <UiSwitch
        :model-value="row.enabled"
        :aria-label="row.title"
        @update:model-value="(on) => toggle(row.id, on)"
      />
    </li>
  </ol>
</template>

<script setup>
import { computed, ref } from 'vue'
import AppIcon from '../ui/AppIcon.vue'
import UiIconButton from '../ui/UiIconButton.vue'
import UiSwitch from '../ui/UiSwitch.vue'
import {
  dropProvider,
  moveProvider,
  providerRows,
  toggleProvider,
} from '/src/lib/providerOrder'
import { useI18n } from '/src/i18n'

const props = defineProps({
  // Enabled provider ids, in the order they're tried.
  modelValue: { type: Array, required: true },
  // Every provider: [{ id, title, description }]
  providers: { type: Array, required: true },
  // Ids that belong at the top of the list when switched on.
  firstWhenEnabled: { type: Array, default: () => [] },
  // No padding of its own: for use inside a setting row.
  dense: { type: Boolean, default: false },
})
const emit = defineEmits(['update:modelValue', 'enabled'])
const { t } = useI18n()
const dragOver = ref(-1)
const dragFrom = ref(-1)

const all = computed(() => props.providers.map((provider) => provider.id))
const info = computed(() =>
  Object.fromEntries(props.providers.map((provider) => [provider.id, provider]))
)
const enabled = computed(() =>
  props.modelValue.filter((id) => all.value.includes(id))
)
const rows = computed(() => providerRows(all.value, enabled.value, info.value))

function apply(next) {
  if (next) emit('update:modelValue', next)
}

function toggle(id, on) {
  apply(
    toggleProvider(enabled.value, id, on, {
      first: props.firstWhenEnabled.includes(id),
    })
  )
  if (on) emit('enabled', id)
}

function drop(index) {
  const from = rows.value[dragFrom.value]
  const to = rows.value[index]
  dragOver.value = -1
  if (!from?.enabled || !to?.enabled) return
  apply(dropProvider(enabled.value, from.id, to.id))
}
</script>
