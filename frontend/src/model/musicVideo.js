// Which library song has a music video (GET /api/music-video). A video
// found is remembered for the session; "none yet" only for a little
// while, since a song's video arrives after the song itself (the server
// fetches videos one at a time, after the downloads).
import { getCurrentScope, onScopeDispose, ref, watch } from 'vue'
import API from '/src/model/api'

/** How long (ms) a "no video" answer is trusted before asking again. */
export const MISS_TTL_MS = 30000

const known = new Map()

/** The stream URL of *file*'s video, or '' when it has none (yet). */
export async function musicVideoURL(file, now = Date.now()) {
  if (!file) return ''
  const cached = known.get(file)
  if (cached && (cached.url || now - cached.at < MISS_TTL_MS)) return cached.url
  let url = ''
  let crop = null
  try {
    const data = (await API.getMusicVideo(file)).data || {}
    url = data.url || ''
    crop = data.crop || null
  } catch {
    url = ''
  }
  known.set(file, { url, crop, at: now })
  return url
}

/** The picture box of *file*'s video when black bars are burnt into it
 * (`{width, height, x, y, video_width, video_height}`), else null. Only
 * known once musicVideoURL found the video. */
export function musicVideoCrop(file) {
  return known.get(file)?.crop || null
}

/** Forget what was learnt (a video may have arrived since). */
export function forgetMusicVideos() {
  known.clear()
}

/**
 * The video URL of the playing track, while `enabled()` says videos are
 * wanted; '' otherwise (streams and podcasts have none). While the track
 * has none it asks again every MISS_TTL_MS, so a video that arrives
 * while the song plays still shows up.
 */
export function useMusicVideo(track, enabled) {
  const url = ref('')
  let timer = null
  let lookup = 0

  function stop() {
    if (timer) clearTimeout(timer)
    timer = null
  }

  async function check(file) {
    stop()
    const mine = ++lookup
    const found = await musicVideoURL(file)
    if (mine !== lookup || track.value?.file !== file || !enabled()) return
    url.value = found
    if (!found) timer = setTimeout(() => check(file), MISS_TTL_MS + 50)
  }

  watch(
    () => [
      track.value?.file,
      track.value?.stream,
      track.value?.isPodcast,
      enabled(),
    ],
    ([file, stream, podcast, on]) => {
      stop()
      lookup += 1
      url.value = ''
      if (!on || !file || stream || podcast) return
      check(file)
    },
    { immediate: true }
  )
  if (getCurrentScope()) onScopeDispose(stop)
  return url
}
