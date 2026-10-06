// Instant full-track streaming for songs that aren't downloaded yet.
//
// A tap on such a row doesn't play a 30 s preview anywhere: it resolves
// the song to a YouTube video, asks the backend for that video's current
// direct-audio URL, and plays it in the built-in player as a transient
// track (never stored, never tagged, gone from the queue on reload).
import { ref } from 'vue'

import API from '/src/model/api'
import { usePlayer } from '/src/model/player'

const VIDEO_ID_RE = /^[A-Za-z0-9_-]{11}$/

// `artist|title` of the song whose video id is being resolved right now
// ('' when none) - its row shows a spinner meanwhile.
const resolvingKey = ref('')

export function songArtist(song) {
  return String((song?.artists || [])[0] || song?.artist || '').trim()
}

export function songTitle(song) {
  return String(song?.name || song?.title || '').trim()
}

export function rowKey(song) {
  return `${songArtist(song)}|${songTitle(song)}`.toLowerCase()
}

/** This song's YouTube video id when the row already carries one. */
export function directVideoId(song) {
  const direct = String(song?.youtube_id || '').trim()
  if (VIDEO_ID_RE.test(direct)) return direct
  const sid = String(song?.song_id || '').trim()
  return VIDEO_ID_RE.test(sid) ? sid : ''
}

/** The video id to stream: the row's own, else the first search hit. */
export async function videoIdFor(song) {
  const direct = directVideoId(song)
  if (direct) return direct
  const artist = songArtist(song)
  const title = songTitle(song)
  if (!artist || !title) throw new Error('noartistortitle')
  const res = await API.search(`${artist} ${title}`)
  for (const row of res.data || []) {
    const candidate = directVideoId(row)
    if (candidate) return candidate
  }
  throw new Error('nomatch')
}

/** Whether the player's current track is a stream of `song`. */
export function isStreamingSong(song) {
  const current = usePlayer().currentTrack.value
  if (!current?.stream) return false
  const videoId = directVideoId(song)
  if (videoId) return current.video_id === videoId
  return (
    current.artist === songArtist(song) &&
    current.title === songTitle(song) &&
    !!songTitle(song)
  )
}

/** Whether this row's stream is being resolved right now. */
export function resolvingFor(song) {
  const key = rowKey(song)
  return !!key && resolvingKey.value === key
}

/**
 * Play `song` in full through the built-in player. Resolves `false`
 * when there is nothing to play (the caller toasts); anything else the
 * caller can't fix surfaces the same way.
 */
export async function playStream(song, { context = null } = {}) {
  const key = rowKey(song)
  if (!key) return false
  resolvingKey.value = key
  try {
    const videoId = await videoIdFor(song)
    const res = await API.getStreamUrl(videoId)
    const url = res.data?.url
    if (typeof url !== 'string' || !url.startsWith('https://')) {
      return false
    }
    // Another song started while this one resolved.
    if (resolvingKey.value !== key) return false
    const artist = songArtist(song)
    const title = songTitle(song)
    usePlayer().playList(
      [
        {
          file: '',
          stream: true,
          video_id: videoId,
          title,
          artist,
          album: String(song?.album_name || song?.album || ''),
          albumArtist: artist,
          cover: String(song?.cover_url || ''),
          hasCover: !!song?.cover_url,
          url,
          duration: Number(song?.duration) || 0,
        },
      ],
      { context }
    )
    return true
  } catch {
    return false
  } finally {
    if (resolvingKey.value === key) resolvingKey.value = ''
  }
}

export function useStream() {
  return {
    resolvingKey,
    videoIdFor,
    playStream,
    isStreamingSong,
    resolvingFor,
    songArtist,
    songTitle,
  }
}
