// Instant full-track streaming for songs that aren't downloaded yet.
//
// A tap on such a row doesn't download anything: it resolves the song
// to a YouTube video and hands it to the player, which plays it piece
// by piece (20-second chunks, see model/chunked.js) as a transient
// track - never stored, never tagged, gone from the queue on reload.
// The player keeps one track ahead prepared (see model/player.js), so
// the next song starts without waiting too.
import { ref } from 'vue'

import { usePlayer } from '/src/model/player'
import {
  directVideoId,
  rowKey,
  songArtist,
  songTitle,
  videoIdFor,
} from '/src/model/streamResolve'

// `artist|title` of the song whose video id is being resolved right
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

/**
 * Play `song` in full through the built-in player. Only the video id
 * resolves up front; the pieces load as the player asks for them.
 * Resolves `false` when there is nothing to play (the caller toasts);
 * anything else the caller can't fix surfaces the same way.
 */
export async function playStream(song, { context = null } = {}) {
  const key = rowKey(song)
  if (!key) return false
  resolvingKey.value = key
  try {
    const videoId = await videoIdFor(song)
    // Another song started while this resolved.
    if (resolvingKey.value !== key) return false
    usePlayer().playList(
      [
        {
          file: '',
          stream: true,
          video_id: videoId,
          title: songTitle(song),
          artist: songArtist(song),
          album: String(song?.album_name || song?.album || ''),
          albumArtist: songArtist(song),
          cover: String(song?.cover_url || ''),
          hasCover: !!song?.cover_url,
          url: '',
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
    playStream,
    isStreamingSong,
    resolvingFor,
    songArtist,
    songTitle,
  }
}
