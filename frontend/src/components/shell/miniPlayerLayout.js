import { computed, ref, shallowRef, watch } from 'vue'
import { useResizeObserver } from '@vueuse/core'

const defaultLayout = [0.3, 0.4, 0.3]
const minimums = [156, 288, 300]
const gutter = 16
const utilityWidth = 72
const fixedWidth =
  minimums.reduce((sum, width) => sum + width, 0) + 2 * gutter + utilityWidth

function resizeSections(widths, index, delta) {
  const min = minimums[index]
  const max = widths[index] + widths[index + 1] - minimums[index + 1]
  const resized = [...widths]
  resized[index] = Math.max(min, Math.min(max, widths[index] + delta))
  resized[index + 1] += widths[index] - resized[index]
  return resized
}

export function useMiniPlayerLayout(bar, visible, preference) {
  const width = ref(0)
  const unlocked = ref(false)
  const preview = shallowRef(null)
  let drag = null

  const wide = computed(() => visible.value && width.value >= 900)
  const spare = computed(() => Math.max(0, width.value - fixedWidth))
  const widths = computed(() => {
    const proportions = preference.value ?? defaultLayout
    return (
      preview.value ??
      minimums.map((min, i) => min + proportions[i] * spare.value)
    )
  })
  const grid = computed(() => {
    if (!wide.value) return undefined
    const [track, transport, utility] = widths.value
    const columns = [track, gutter, transport, gutter, utility, utilityWidth]
    return { gridTemplateColumns: columns.map((size) => `${size}px`).join(' ') }
  })

  function sectionStyle(index) {
    if (!wide.value) return undefined
    const rate = index === 1 ? 10 : 6
    const growth = Math.min(12, (widths.value[index] - minimums[index]) / rate)
    return { '--control-growth': `${Math.max(0, growth)}px` }
  }

  function limits(index) {
    return {
      min: minimums[index],
      max: Math.round(
        widths.value[index] + widths.value[index + 1] - minimums[index + 1]
      ),
      current: Math.round(widths.value[index]),
    }
  }

  function save(next) {
    const extra = next.map((size, index) => Math.max(0, size - minimums[index]))
    const total = extra.reduce((sum, size) => sum + size, 0)
    preference.value = extra.map((size) => size / total)
  }

  function cancelDrag() {
    const active = drag
    drag = null
    preview.value = null
    if (active?.element.hasPointerCapture(active.id)) {
      active.element.releasePointerCapture(active.id)
    }
  }

  function startDrag(event, index) {
    if (drag || !unlocked.value || event.button !== 0 || !event.isPrimary)
      return
    const element = event.currentTarget
    element.focus()
    element.setPointerCapture(event.pointerId)
    drag = {
      element,
      id: event.pointerId,
      x: event.clientX,
      widths: widths.value,
      index,
    }
    event.preventDefault()
  }

  function moveDrag(event) {
    if (drag?.id !== event.pointerId) return
    preview.value = resizeSections(
      drag.widths,
      drag.index,
      event.clientX - drag.x
    )
  }

  function endDrag(event) {
    if (drag?.id !== event.pointerId) return
    moveDrag(event)
    if (preview.value[drag.index] !== drag.widths[drag.index])
      save(preview.value)
    cancelDrag()
  }

  function cancelPointer(event) {
    if (drag?.id === event.pointerId) cancelDrag()
  }

  function onKeydown(event, index) {
    const deltas = {
      ArrowLeft: -8,
      ArrowRight: 8,
      Home: -Infinity,
      End: Infinity,
    }
    if (!Object.hasOwn(deltas, event.key)) return
    event.preventDefault()
    event.stopPropagation()
    if (drag) return
    const next = resizeSections(widths.value, index, deltas[event.key])
    if (next[index] !== widths.value[index]) save(next)
  }

  function onEscape(event) {
    if (!drag) return
    event.preventDefault()
    event.stopPropagation()
    cancelDrag()
  }

  function toggle() {
    cancelDrag()
    unlocked.value = !unlocked.value
  }

  function reset() {
    cancelDrag()
    preference.value = null
  }

  useResizeObserver(bar, ([entry]) => {
    if (!visible.value || entry.target !== bar.value) return
    if (entry.contentRect.width === width.value) return
    cancelDrag()
    width.value = entry.contentRect.width
  })
  watch(
    visible,
    (shown) => {
      if (!shown) width.value = 0
    },
    { flush: 'sync' }
  )
  watch(
    wide,
    (enabled) => {
      if (enabled) return
      cancelDrag()
      unlocked.value = false
    },
    { flush: 'sync' }
  )

  return {
    wide,
    unlocked,
    grid,
    sectionStyle,
    limits,
    startDrag,
    moveDrag,
    endDrag,
    cancelPointer,
    onKeydown,
    onEscape,
    toggle,
    reset,
  }
}
