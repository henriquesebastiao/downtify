// Pointer and keyboard handling shared by the seek/volume sliders.
import { computed, ref } from 'vue'

/**
 * `props`: { modelValue, max, step }. Emits `update:modelValue` while
 * dragging and `commit` on release or key press.
 */
export function useSlider(props, emit) {
  const track = ref(null)
  const dragging = ref(false)
  const dragValue = ref(0)

  const shown = computed(() =>
    dragging.value ? dragValue.value : props.modelValue
  )
  const percent = computed(() =>
    props.max > 0
      ? Math.max(0, Math.min(100, (shown.value / props.max) * 100))
      : 0
  )

  function valueAt(event) {
    const rect = track.value.getBoundingClientRect()
    const ratio = Math.max(
      0,
      Math.min(1, (event.clientX - rect.left) / rect.width)
    )
    return ratio * props.max
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
    const delta = {
      ArrowRight: 1,
      ArrowUp: 1,
      ArrowLeft: -1,
      ArrowDown: -1,
    }[event.key]
    if (!delta) return
    event.preventDefault()
    event.stopPropagation()
    const next = Math.max(
      0,
      Math.min(props.max, props.modelValue + delta * props.step)
    )
    emit('update:modelValue', next)
    emit('commit', next)
  }

  return { track, dragging, percent, onDown, onKey }
}
