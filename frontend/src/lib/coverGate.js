// When a cover may ask for its picture. Scrolling fast through a long list
// mounts dozens of tiles a second, and a browser only opens a few connections
// to the server: the covers of rows already gone stayed in the queue ahead of
// the ones on screen, which took half a minute to appear. So while the page
// is scrolling a tile waits a moment first, and one that scrolls away in the
// meantime never asks at all. Pure but for the scroll listener below.

/** How long a tile stays mounted before asking, while scrolling. */
export const COVER_DWELL_MS = 150

let lastScroll = -Infinity

// Capture, to hear scrolling inside any element as well as the window.
if (typeof window !== 'undefined') {
  window.addEventListener(
    'scroll',
    () => {
      lastScroll = performance.now()
    },
    { capture: true, passive: true }
  )
}

/** How long a tile mounted at *now* waits; 0 once the page is at rest. */
export function coverDelay(now, scrolledAt = lastScroll) {
  return now - scrolledAt < COVER_DWELL_MS ? COVER_DWELL_MS : 0
}

/**
 * Drop the request of every image in *root* still loading, so it stops taking
 * up a connection. Finished ones are left alone: they may fade out with the
 * page leaving, and the browser keeps them for when they come back.
 */
export function cancelUnfinishedImages(root) {
  for (const image of root?.querySelectorAll?.('img') || []) {
    if (image.complete) continue
    image.removeAttribute('srcset')
    image.removeAttribute('src')
  }
}
