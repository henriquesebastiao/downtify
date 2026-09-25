<template>
  <Teleport to="body">
    <Transition name="fade">
      <!-- Above UiModal's z-[80]: ui.confirm() is routinely called from
           inside an already-open modal (e.g. a delete confirmation), so
           this has to win the stack regardless of DOM/mount order. -->
      <div
        v-if="dialog"
        class="fixed inset-0 z-[90] flex items-end justify-center bg-black/55 p-4 backdrop-blur-sm sm:items-center"
        @click.self="closeDialog(false)"
      >
        <div
          role="alertdialog"
          aria-modal="true"
          :aria-labelledby="titleId"
          class="w-full max-w-md animate-rise rounded-panel border border-line-3 bg-surface p-6 shadow-float"
        >
          <h2 :id="titleId" class="text-display text-lg font-semibold text-fg">
            {{ dialog.title }}
          </h2>
          <p
            v-if="dialog.body"
            class="mt-2 text-sm text-pretty whitespace-pre-line text-muted"
          >
            {{ dialog.body }}
          </p>
          <div
            class="mt-6 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end"
          >
            <UiButton variant="ghost" @click="closeDialog(false)">
              {{ dialog.cancelLabel || t('common.cancel') }}
            </UiButton>
            <UiButton
              ref="confirmButton"
              :variant="dialog.danger ? 'danger' : 'primary'"
              @click="closeDialog(true)"
            >
              {{ dialog.confirmLabel || t('common.confirm') }}
            </UiButton>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { nextTick, ref, watch } from 'vue'
import UiButton from './UiButton.vue'
import { useUi } from '/src/model/ui'
import { useI18n } from '/src/i18n'

const { dialog, closeDialog } = useUi()
const { t } = useI18n()
const titleId = 'dialog-title'
const confirmButton = ref(null)

watch(dialog, async (value) => {
  if (!value) return
  await nextTick()
  confirmButton.value?.$el?.focus()
})
</script>
