// Changing the port the server listens on (Settings > Server). Pure, so
// it's unit-testable.

/** The port a page at `location` was loaded from (80/443 when implied). */
export function pagePort(location) {
  if (location?.port) return Number(location.port)
  return location?.protocol === 'https:' ? 443 : 80
}

/**
 * Whether this page talks to the server directly - on the port the
 * server listens on - rather than through a reverse proxy or a Docker
 * mapping to another port. Only then can the page follow a port change.
 */
export function reachesDirectly(location, serverPort) {
  return pagePort(location) === Number(serverPort)
}

/** This page's address with `port` in place of its own. */
export function urlOnPort(location, port) {
  const url = new URL(location.href)
  url.port = String(port)
  return url.toString()
}

/**
 * What the Port field shows for `status` (`GET /api/server/port`): when
 * DOWNTIFY_PORT (or --port) sets the port, the port in use, read-only;
 * otherwise the port the next start uses, editable.
 */
export function portField(status) {
  if (!status) return { value: '', editable: false }
  if (status.locked_by) return { value: String(status.port), editable: false }
  return { value: String(status.next), editable: true }
}

/** Whether `value` is a port Settings accepts (`min`..`max`). */
export function validPort(value, min = 1024, max = 65535) {
  const text = String(value ?? '').trim()
  if (!/^\d+$/.test(text)) return false
  const port = Number(text)
  return port >= min && port <= max
}
