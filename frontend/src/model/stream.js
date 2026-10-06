// Instant full-track streaming for songs that aren't downloaded yet.
//
// A tap on such a row doesn't download anything: it resolves the song
// to a YouTube video, asks the backend for that video's current
// direct-audio URL, and plays it in the built-in player as a transient
// track (never stored, never tagged, gone from the queue on reload).
// The player keeps one track ahead resolved (see model/player.js), so
// the next song starts without waiting too.
import { ref } from 'vue'

import { usePlayer } from '/src/model/player'
import {
  directVideoId,
  resolveTrackUrl,
  rowKey,
  songArtist,
  songTitle,
} from '/src/model/streamResolve'

// `artist|title` of the song whose stream URL is being resolved right
// now ('' when none) - its row shows a spinner meanwhile.
const resolvingKey = ref('')

/** Whether the player's current track is a stream of `song`. */
export function isStreamingSong(song) {
  const current = usePlayer().currentTrack.value
  if (!current?.stream) return false
  const videoId = directVideoId(song)
  if (videoId) return current.video_id === videoId
  const artist = songArtist(song)
  const title = songTitle(song)
  if (!artist || !title) return false
  return current.artist === artist && current.title === title
}

/** Whether this row's stream is being resolved right now. */
export function resolvingFor(song) {
  const key = rowKey(song)
  return !!key && resolvingKey.value === key
}

/** A player track streaming `song` once `url` is known. */
export function streamTrack(song, url, videoId) {
  return {
    file: '',
    stream: true,
    video_id: videoId,
    title: songTitle(song),
    artist: songArtist(song),
    album: String(song?.album_name || song?.album || ''),
    albumArtist: songArtist(song),
    cover: String(song?.cover_url || ''),
    hasCover: !!song?.cover_url,
    url,
    duration: Number(song?.duration) || 0,
  }
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
    const { url, videoId } = await resolveTrackUrl(song)
    // Another song started while this one resolved.
    if (resolvingKey.value !== key) return false
    usePlayer().playList([streamTrack(song, url, videoId)], { context })
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
    playStream,
    isStreamingSong,
    resolvingFor,
    songArtist,
    songTitle,
  }
}
