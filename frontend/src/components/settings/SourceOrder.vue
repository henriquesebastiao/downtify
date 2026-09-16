<template>
  <ol class="flex flex-col gap-2 p-4">
    <li
      v-for="(source, i) in rows"
      :key="source.id"
      class="flex items-center gap-3 rounded-[12px] border bg-bg px-3 py-2.5 transition-colors"
      :class="[
        source.enabled ? 'border-line-3' : 'border-line-2 opacity-60',
        dragOver === i ? 'border-accent' : '',
      ]"
      :draggable="source.enabled"
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
          source.enabled
            ? 'bg-accent/12 text-accent'
            : 'bg-surface-2 text-faint'
        "
        >{{ source.enabled ? source.position : '–' }}</span
      >
      <SourceBadge :source="source.id" />
      <div class="min-w-0 flex-1">
        <p class="truncate text-sm font-semibold">{{ source.title }}</p>
        <p class="truncate text-xs text-muted">{{ source.description }}</p>
      </div>
      <div class="flex items-center">
        <UiIconButton
          icon="chevron-up"
          :label="t('settings.moveUp')"
          size="sm"
          :disabled="!source.enabled || source.position === 1"
          @click="move(source.id, -1)"
        />
        <UiIconButton
          icon="chevron-down"
          :label="t('settings.moveDown')"
          size="sm"
          :disabled="!source.enabled || source.position === enabled.length"
          @click="move(source.id, 1)"
        />
      </div>
      <UiSwitch
        :model-value="source.enabled"
        :aria-label="source.title"
        @update:model-value="(on) => toggle(source.id, on)"
      />
    </li>
  </ol>
</template>

<script setup>
import { computed, ref } from 'vue'
import AppIcon from '../ui/AppIcon.vue'
import SourceBadge from '../ui/SourceBadge.vue'
import UiIconButton from '../ui/UiIconButton.vue'
import UiSwitch from '../ui/UiSwitch.vue'
import { useI18n } from '/src/i18n'

const props = defineProps({
  modelValue: { type: Array, required: true },
})
const emit = defineEmits(['update:modelValue', 'enable-slskd'])
const { t } = useI18n()
const dragOver = ref(-1)
const dragFrom = ref(-1)

const ALL = ['slskd', 'youtube-music', 'youtube']

const enabled = computed(() =>
  props.modelValue.filter((id) => ALL.includes(id))
)

const info = computed(() => ({
  slskd: {
    title: t('settings.sourceSlskd'),
    description: t('settings.sourceSlskdHint'),
  },
  'youtube-music': {
    title: t('settings.sourceYtm'),
    description: t('settings.sourceYtmHint'),
  },
  youtube: {
    title: t('settings.sourceYt'),
    description: t('settings.sourceYtHint'),
  },
}))

// Enabled sources in fallback order, then the disabled ones.
const rows = computed(() => [
  ...enabled.value.map((id, i) => ({
    id,
    enabled: true,
    position: i + 1,
    ...info.value[id],
  })),
  ...ALL.filter((id) => !enabled.value.includes(id)).map((id) => ({
    id,
    enabled: false,
    position: 0,
    ...info.value[id],
  })),
])

function toggle(id, on) {
  let next = enabled.value.filter((item) => item !== id)
  if (on) {
    next = id === 'slskd' ? [id, ...next] : [...next, id]
    if (id === 'slskd') emit('enable-slskd')
  }
  if (!next.length) return
  emit('update:modelValue', next)
}

function move(id, delta) {
  const next = enabled.value.slice()
  const from = next.indexOf(id)
  const to = from + delta
  if (from < 0 || to < 0 || to >= next.length) return
  ;[next[from], next[to]] = [next[to], next[from]]
  emit('update:modelValue', next)
}

function drop(index) {
  const fromRow = rows.value[dragFrom.value]
  const toRow = rows.value[index]
  dragOver.value = -1
  if (!fromRow?.enabled || !toRow?.enabled || fromRow.id === toRow.id) return
  const next = enabled.value.slice()
  next.splice(next.indexOf(fromRow.id), 1)
  next.splice(toRow.position - 1, 0, fromRow.id)
  emit('update:modelValue', next)
}
</script>
