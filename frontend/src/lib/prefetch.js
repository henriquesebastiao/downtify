// Pages are loaded on demand (router/index.js). Once the app is idle, the
// ones people go to most are fetched ahead, one at a time, so opening them
// later is instant - unless the connection asks to save data.

/** Whether to fetch ahead on this connection (navigator.connection). */
export function shouldPrefetch(connection) {
  if (!connection) return true
  if (connection.saveData) return false
  return !/(^|-)2g$/.test(connection.effectiveType || '')
}

/** The loaders (`() => import(...)`) of the named routes, in that order. */
export function routeLoaders(routes, names) {
  return names
    .map((name) => routes.find((route) => route.name === name))
    .map((route) => route?.components?.default)
    .filter((component) => typeof component === 'function')
}

function idle(callback) {
  if (typeof requestIdleCallback === 'function') {
    requestIdleCallback(callback, { timeout: 4000 })
  } else {
    setTimeout(callback, 200)
  }
}

/**
 * Fetch the named routes' code in idle moments, one after the other, so it
 * never competes with what the page on screen is loading.
 */
export function prefetchRoutes(
  router,
  names,
  { schedule = idle, extra = [] } = {}
) {
  const connection =
    typeof navigator === 'undefined' ? null : navigator.connection
  if (!shouldPrefetch(connection)) return
  // `extra`: other on-demand code worth having ahead (Now playing), first.
  const queue = [...extra, ...routeLoaders(router.getRoutes(), names)]
  const next = () => {
    const load = queue.shift()
    if (!load) return
    Promise.resolve()
      .then(load)
      .catch(() => {})
      .finally(() => schedule(next))
  }
  schedule(next)
}
