<template>
  <Teleport to="body">
    <Transition name="fade">
      <div
        v-if="open"
        class="fixed inset-0 z-[80] flex items-center justify-center bg-black/55 p-4 backdrop-blur-sm"
        @click.self="$emit('update:open', false)"
      >
        <div
          role="dialog"
          aria-modal="true"
          class="w-full max-w-lg animate-rise rounded-panel border border-line-3 bg-surface p-6 shadow-float"
        >
          <div class="mb-4 flex items-center justify-between">
            <h2 class="text-display text-lg font-semibold">
              {{ t('shortcuts.title') }}
            </h2>
            <UiIconButton
              ref="closeButton"
              icon="x"
              :label="t('common.close')"
              @click="$emit('update:open', false)"
            />
          </div>
          <ul class="grid gap-x-8 gap-y-2.5 sm:grid-cols-2">
            <li
              v-for="item in shortcuts"
              :key="item.label"
              class="flex items-center justify-between gap-4 text-sm"
            >
              <span class="text-fg-3">{{ t(item.label) }}</span>
              <span class="flex gap-1">
                <kbd
                  v-for="key in item.keys"
                  :key="key"
                  class="min-w-6 rounded-md border border-line-3 bg-surface-2 px-1.5 py-0.5 text-center font-sans text-xs text-muted"
                  >{{ key }}</kbd
                >
              </span>
            </li>
          </ul>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import UiIconButton from '../ui/UiIconButton.vue'
import { visibleShortcuts } from './shortcuts'
import { usePlayerPrefs } from '/src/model/playerPrefs'
import { useI18n } from '/src/i18n'

const props = defineProps({ open: { type: Boolean, default: false } })
defineEmits(['update:open'])
const { t } = useI18n()
const { showLyrics } = usePlayerPrefs()
const closeButton = ref(null)
const shortcuts = computed(() => visibleShortcuts({ lyrics: showLyrics.value }))

watch(
  () => props.open,
  async (open) => {
    if (!open) return
    await nextTick()
    closeButton.value?.$el?.focus()
  }
)
</script>
