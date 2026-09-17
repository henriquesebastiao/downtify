// Pointer and keyboard handling shared by the player's sliders.
import { computed, ref } from 'vue'

/**
 * `props`: { modelValue, max, step, min? }. Emits `update:modelValue`
 * while dragging and `commit` on release or key press.
 *
 * `options.vertical`: the value grows upwards.
 * `options.snap`: values are rounded to `step` while dragging too.
 */
export function useSlider(props, emit, options = {}) {
  const track = ref(null)
  const dragging = ref(false)
  const dragValue = ref(0)

  const min = () => props.min ?? 0

  const shown = computed(() =>
    dragging.value ? dragValue.value : props.modelValue
  )
  const percent = computed(() => {
    const span = props.max - min()
    return span > 0
      ? Math.max(0, Math.min(100, ((shown.value - min()) / span) * 100))
      : 0
  })

  function clampValue(value) {
    const snapped =
      options.snap && props.step
        ? min() + Math.round((value - min()) / props.step) * props.step
        : value
    return Math.max(min(), Math.min(props.max, snapped))
  }

  function valueAt(event) {
    const rect = track.value.getBoundingClientRect()
    const raw = options.vertical
      ? (rect.bottom - event.clientY) / rect.height
      : (event.clientX - rect.left) / rect.width
    const ratio = Math.max(0, Math.min(1, raw))
    return clampValue(min() + ratio * (props.max - min()))
  }

  function onDown(event) {
    if (event.button !== 0) return
    dragging.value = true
    dragValue.value = valueAt(event)
    emit('update:modelValue', dragValue.value)
    track.value.setPointerCapture(event.pointerId)
    const move = (e) => {
      dragValue.value = valueAt(e)
      emit('update:modelValue', dragValue.value)
    }
    const up = () => {
      dragging.value = false
      emit('commit', dragValue.value)
      track.value.removeEventListener('pointermove', move)
      track.value.removeEventListener('pointerup', up)
      track.value.removeEventListener('pointercancel', up)
    }
    track.value.addEventListener('pointermove', move)
    track.value.addEventListener('pointerup', up)
    track.value.addEventListener('pointercancel', up)
  }

  function onKey(event) {
    let next
    const delta = {
      ArrowRight: 1,
      ArrowUp: 1,
      PageUp: 2,
      ArrowLeft: -1,
      ArrowDown: -1,
      PageDown: -2,
    }[event.key]
    if (delta) next = props.modelValue + delta * props.step
    else if (event.key === 'Home') next = min()
    else if (event.key === 'End') next = props.max
    else return
    event.preventDefault()
    event.stopPropagation()
    next = clampValue(next)
    emit('update:modelValue', next)
    emit('commit', next)
  }

  return { track, dragging, percent, onDown, onKey }
}
