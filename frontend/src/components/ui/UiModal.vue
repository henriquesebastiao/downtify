<template>
  <Teleport to="body">
    <Transition name="fade">
      <div
        v-if="open"
        class="fixed inset-0 z-[80] flex items-end justify-center bg-black/55 backdrop-blur-sm sm:items-center sm:p-4"
        @pointerdown.self="pressedBackdrop = true"
        @click.self="onBackdrop"
      >
        <div
          ref="panel"
          role="dialog"
          aria-modal="true"
          :aria-labelledby="titleId"
          tabindex="-1"
          class="flex max-h-[92dvh] outline-none w-full animate-rise flex-col overflow-hidden rounded-t-[22px] border border-line-3 bg-surface shadow-float sm:rounded-panel"
          :class="width"
          @keydown="onKeydown"
        >
          <header
            class="flex shrink-0 items-start gap-3 border-b border-line-2 px-5 py-4 sm:px-6"
          >
            <div class="min-w-0 flex-1">
              <h2
                :id="titleId"
                class="text-display text-lg font-semibold text-fg"
              >
                {{ title }}
              </h2>
              <p v-if="description" class="mt-0.5 text-[13px] text-muted">
                {{ description }}
              </p>
            </div>
            <UiIconButton
              icon="x"
              :label="t('common.close')"
              class="-mr-2 -mt-1"
              @click="$emit('close')"
            />
          </header>
          <div class="min-h-0 flex-1 overflow-y-auto px-5 py-5 sm:px-6">
            <slot />
          </div>
          <footer
            v-if="$slots.footer"
            class="flex shrink-0 flex-col-reverse gap-2 border-t border-line-2 px-5 py-4 pb-[max(1rem,env(safe-area-inset-bottom))] sm:flex-row sm:justify-end sm:px-6"
          >
            <slot name="footer" />
          </footer>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { nextTick, onBeforeUnmount, ref, useId, watch } from 'vue'
import UiIconButton from './UiIconButton.vue'
import { useUi } from '/src/model/ui'
import { useI18n } from '/src/i18n'

const props = defineProps({
  open: { type: Boolean, default: false },
  title: { type: String, required: true },
  description: { type: String, default: '' },
  width: { type: String, default: 'sm:max-w-lg' },
})
const emit = defineEmits(['close'])

const { t } = useI18n()
const ui = useUi()
const titleId = `modal-${useId()}`
const panel = ref(null)
// Only a click that also started on the backdrop closes the dialog, so
// selecting text in a field and releasing outside doesn't.
const pressedBackdrop = ref(false)
let modalId = null
let returnFocus = null

const FOCUSABLE =
  'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'

function focusables() {
  return [...(panel.value?.querySelectorAll(FOCUSABLE) || [])].filter(
    (el) => el.offsetParent !== null
  )
}

function onBackdrop() {
  if (pressedBackdrop.value) emit('close')
  pressedBackdrop.value = false
}

function onKeydown(event) {
  if (event.key === 'Escape') {
    event.preventDefault()
    event.stopPropagation()
    emit('close')
    return
  }
  if (event.key !== 'Tab') return
  const items = focusables()
  if (!items.length) return
  const first = items[0]
  const last = items.at(-1)
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault()
    last.focus()
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault()
    first.focus()
  }
}

function release() {
  if (modalId === null) return
  ui.popModal(modalId)
  modalId = null
  document.documentElement.style.overflow = ''
  returnFocus?.focus?.()
  returnFocus = null
}

watch(
  () => props.open,
  async (open) => {
    if (!open) {
      release()
      return
    }
    returnFocus = document.activeElement
    modalId = ui.pushModal(() => emit('close'))
    document.documentElement.style.overflow = 'hidden'
    await nextTick()
    // First field, else the first button after the close button. On touch
    // screens focus the dialog itself, so the keyboard doesn't pop up.
    const touch = window.matchMedia?.('(pointer: coarse)').matches
    const items = focusables()
    const target = touch
      ? panel.value
      : panel.value?.querySelector('input, select, textarea') ||
        items[1] ||
        items[0]
    target?.focus()
  },
  { immediate: true }
)

onBeforeUnmount(release)
</script>
