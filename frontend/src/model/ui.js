// App-wide UI state: toasts, the confirm dialog and the Now playing
// overlay.
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const toasts = ref([])
let toastId = 0

/**
 * Show a short message. `kind`: 'info' | 'success' | 'error'.
 * `action`: optional { label, run }.
 */
function toast(text, { kind = 'info', action = null, timeout = 4500 } = {}) {
  const id = ++toastId
  toasts.value = [...toasts.value, { id, text, kind, action }]
  if (timeout) setTimeout(() => dismiss(id), timeout)
  return id
}

function dismiss(id) {
  toasts.value = toasts.value.filter((item) => item.id !== id)
}

const dialog = ref(null)

/**
 * Ask before doing something destructive. Resolves true when confirmed.
 * `options`: { title, body, confirmLabel, cancelLabel, danger }
 */
function confirm(options) {
  return new Promise((resolve) => {
    dialog.value = { ...options, resolve }
  })
}

function closeDialog(result) {
  const current = dialog.value
  dialog.value = null
  current?.resolve(result)
}

// The global search box registers a focus function here (Ctrl/Cmd+K).
let focusSearchFn = null
function registerSearchFocus(fn) {
  focusSearchFn = fn
}
function focusSearch() {
  focusSearchFn?.()
}

export function useUi() {
  return {
    toasts,
    toast,
    dismiss,
    dialog,
    confirm,
    closeDialog,
    registerSearchFocus,
    focusSearch,
  }
}

/**
 * The Now playing view is an overlay tied to `?np=1`, so the browser's
 * back button (and the phone's back gesture) closes it.
 */
export function useNowPlaying() {
  const route = useRoute()
  const router = useRouter()
  const isOpen = computed(() => route.query.np === '1')
  function open(panel) {
    if (isOpen.value) {
      // Already open: just switch to the requested panel.
      if (panel && route.query.panel !== panel) {
        router.replace({ query: { ...route.query, panel } })
      }
      return
    }
    router.push({
      query: { ...route.query, np: '1', ...(panel ? { panel } : {}) },
    })
  }
  function close() {
    if (!isOpen.value) return
    if (window.history.state?.back) router.back()
    else {
      const { np: _np, panel: _panel, ...query } = route.query
      router.replace({ query })
    }
  }
  return { isOpen, open, close }
}
