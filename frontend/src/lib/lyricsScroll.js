// Glides `container` alone - never its ancestors, as `scrollIntoView` would,
// which pushes the whole Now playing view up once the last lines of a song
// can't reach the middle - until `el` sits in the middle of it. Offsets, not
// client rects: the view opens scaled, which would throw the rects off.
// `container` must be positioned, so that it's the offset parent of `el`.
export function centerWithin(container, el) {
  if (!container || !el) return
  container.scrollTo({
    top: el.offsetTop - (container.clientHeight - el.offsetHeight) / 2,
    behavior: 'smooth',
  })
}
