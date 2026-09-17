// Keeps Tab / Shift+Tab inside a dialog.
const FOCUSABLE =
  'a[href], button:not([disabled]), input:not([disabled]), [tabindex]:not([tabindex="-1"])'

export function trapTab(event, container) {
  if (event.key !== 'Tab' || !container) return
  const items = [...container.querySelectorAll(FOCUSABLE)].filter(
    (el) => el.offsetParent !== null
  )
  if (!items.length) return
  const first = items[0]
  const last = items[items.length - 1]
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault()
    last.focus()
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault()
    first.focus()
  }
}
