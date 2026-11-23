// Motion helpers the CSS can't do alone (styles/motion.css has the rest).
import { computed } from 'vue'
import { usePreferredReducedMotion } from '@vueuse/core'

/**
 * The `:duration` of a <Transition> whose root doesn't move itself, only
 * its children do (a modal: the overlay stays, its backdrop and panel
 * animate) — Vue only reads the root's own transition, so it has to be
 * told how long the children take. Nothing to wait for when the person
 * asked for less motion: the CSS ends every transition at once then.
 */
export function motionDuration(reduced, enter, leave = enter) {
  return reduced ? 0 : { enter, leave }
}

/** `motionDuration`, following the system's reduced-motion setting. */
export function useMotionDuration(enter, leave = enter) {
  const preference = usePreferredReducedMotion()
  return computed(() =>
    motionDuration(preference.value === 'reduce', enter, leave)
  )
}

/** Whether the system asks for reduced motion, as a ref. */
export function useReducedMotion() {
  const preference = usePreferredReducedMotion()
  return computed(() => preference.value === 'reduce')
}

/**
 * Where a popover grows from: the corner of it that touches its trigger,
 * so it unfolds out of the button instead of from its own middle.
 * `menu` and `anchor` are rects ({ left, top, width, height }); the
 * anchor of a right-click menu is the pointer (width and height 0).
 */
export function popoverOrigin(menu, anchor) {
  const below = menu.top >= anchor.top + anchor.height / 2
  const anchorMiddle = anchor.left + anchor.width / 2
  const x = Math.min(Math.max(anchorMiddle - menu.left, 0), menu.width)
  // Snap to the edge it is next to: a menu aligned with its trigger's end
  // grows from that end's corner.
  const side =
    x <= menu.width * 0.2
      ? 'left'
      : x >= menu.width * 0.8
        ? 'right'
        : `${Math.round(x)}px`
  return `${below ? 'top' : 'bottom'} ${side}`
}
