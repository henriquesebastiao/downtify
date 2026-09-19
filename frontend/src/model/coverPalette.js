// Palette of the cover art currently playing (see lib/palette.js).
// Covers are served same-origin by /cover, so the canvas can read them.
import { ref, watch } from 'vue'
import { extractPalette } from '/src/lib/palette'

const SIZE = 48
const cache = new Map()

function loadPalette(url) {
  if (!cache.has(url)) {
    const job = new Promise((resolve) => {
      const img = new Image()
      img.decoding = 'async'
      img.onload = () => {
        try {
          const canvas = document.createElement('canvas')
          canvas.width = SIZE
          canvas.height = SIZE
          const ctx = canvas.getContext('2d', { willReadFrequently: true })
          ctx.drawImage(img, 0, 0, SIZE, SIZE)
          resolve(extractPalette(ctx.getImageData(0, 0, SIZE, SIZE).data))
        } catch {
          resolve(null)
        }
      }
      img.onerror = () => resolve(null)
      img.src = url
    })
    cache.set(url, job)
  }
  return cache.get(url)
}

/**
 * Reactive palette for a track ref: null until the cover is read, and
 * whenever the track has no cover.
 */
export function useCoverPalette(track) {
  const palette = ref(null)
  watch(
    () => (track.value?.hasCover ? track.value.cover : null),
    async (url) => {
      if (!url) {
        palette.value = null
        return
      }
      const result = await loadPalette(url)
      // Ignore a slow cover that finished after the track changed.
      if (track.value?.cover === url) palette.value = result
    },
    { immediate: true }
  )
  return palette
}
