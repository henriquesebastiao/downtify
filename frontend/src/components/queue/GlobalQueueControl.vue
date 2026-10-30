<template>
  <div
    v-if="state.status?.global_pause_supported && state.status?.can_control"
    :class="
      compact ? 'min-w-0' : 'rounded-panel border border-line-2 bg-surface p-4'
    "
  >
    <p v-if="!compact" class="mb-3 text-sm font-semibold">
      {{ t('queue.globalTitle') }}
    </p>
    <UiButton
      :variant="state.status.paused ? 'primary' : 'secondary'"
      :icon="state.error ? 'retry' : state.status.paused ? 'play' : 'pause'"
      :loading="state.busy"
      :title="t('queue.globalHint')"
      @click="change"
    >
      {{
        state.error
          ? t('queue.globalRetry')
          : state.status.paused
            ? t('queue.globalResume')
            : t('queue.globalPause')
      }}
    </UiButton>
    <p v-if="state.error" role="alert" class="mt-2 text-[13px] text-danger">
      {{
        t(
          state.error === 401
            ? 'queue.globalExpired'
            : state.error === 403
              ? 'queue.globalAdmin'
              : 'queue.globalFailed'
        )
      }}
    </p>
    <p
      v-else-if="state.status.paused"
      role="status"
      class="mt-2 text-[13px] text-muted"
    >
      {{
        t(state.status.active ? 'queue.globalDraining' : 'queue.globalPaused')
      }}
    </p>
    <p v-else-if="!compact" class="mt-2 text-[13px] text-muted">
      {{ t('queue.globalHint') }}
    </p>
  </div>
</template>

<script>
import config from '/src/config'
import { createQueueControl } from '/src/model/globalQueueControls'

const control = createQueueControl(
  (...args) => fetch(...args),
  new URL(
    `${config.PROTOCOL}//${config.BACKEND}:${config.PORT}${config.BASEURL}/api/queue/`
  )
)
</script>

<script setup>
import { onMounted, onUnmounted, shallowRef } from 'vue'
import UiButton from '/src/components/ui/UiButton.vue'
import { useI18n } from '/src/i18n'

defineProps({ compact: { type: Boolean, default: false } })
const { t } = useI18n()
const state = shallowRef({ ...control.state })
const unsubscribe = control.subscribe((value) => {
  state.value = { ...value }
})
let timer
function refresh() {
  if (!document.hidden) return control.refresh()
}
function poll() {
  refresh()
  timer = setTimeout(
    poll,
    control.state.status?.paused && control.state.status.active ? 1500 : 15000
  )
}
function change() {
  return state.value.error
    ? control.refresh()
    : control.change(!state.value.status.paused)
}
onMounted(() => {
  poll()
  window.addEventListener('focus', refresh)
})
onUnmounted(() => {
  clearTimeout(timer)
  unsubscribe()
  window.removeEventListener('focus', refresh)
})
</script>
