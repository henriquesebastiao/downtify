// Playing one song from a list of songs that may or may not be downloaded
// yet - a link's album or playlist, an artist's top songs. The whole list
// goes to the player as one queue: downloaded songs play from the
// library, the rest stream in full from YouTube (see model/stream.js),
// always shown in the player - there are no 30 s preview clips anywhere.
// The player resolves a stream's URL when its turn comes and keeps one
// track ahead resolved, so playback never waits on the network.
//
// Shared by TrackDownPlay (the artist page's Top songs) and SongPlayCell
// (the number cell of the selectable lists), so both behave the same.
import { computed } from 'vue'

import { useLibrary } from '/src/model/library'
import { usePlayer } from '/src/model/player'
import { isStreamingSong, playStream, resolvingFor } from '/src/model/stream'
import {
  directVideoId,
  rowKey,
  songArtist,
  songTitle,
} from '/src/model/streamResolve'
import { useTrackActions } from '/src/model/trackActions'
import { useUi } from '/src/model/ui'
import { useI18n } from '/src/i18n'

/** The player track behind a song: the library's, else an unstored one. */
export function songToPlayerTrack(song, findTrack) {
  const found = findTrack(songArtist(song), songTitle(song))
  if (found) return found
  return {
    file: '',
    stream: true,
    video_id: directVideoId(song),
    title: songTitle(song),
    artist: songArtist(song),
    album: String(song?.album_name || song?.album || ''),
    albumArtist: songArtist(song),
    cover: String(song?.cover_url || ''),
    hasCover: !!song?.cover_url,
    url: '',
    duration: Number(song?.duration) || 0,
  }
}

/**
 * `start(song, { queue, context, songs })`: make sure `song` plays - from
 * the library once it's downloaded (with `queue` after it), else as one
 * row of a mixed queue (`songs`: the whole list, downloaded or
 * streamed) the player works through to the end. What a double click on
 * a song's row does, for a caller holding the song but not its row (the
 * Finder, starting the popular track it was just asked for). Call it
 * during setup, like any composable; `start` itself can then be called
 * any time.
 */
export function useSongStarter() {
  const { t } = useI18n()
  const library = useLibrary()
  const player = usePlayer()
  const actions = useTrackActions()
  const ui = useUi()

  return function start(
    song,
    { queue = [], context = null, songs = null } = {}
  ) {
    if (Array.isArray(songs) && songs.length) {
      const key = rowKey(song)
      const at = Math.max(
        0,
        songs.findIndex((s) => s === song || rowKey(s) === key)
      )
      actions.play(
        songs.map((s) => songToPlayerTrack(s, library.findTrack)),
        at,
        context
      )
      return
    }
    const track = library.findTrack(songArtist(song), songTitle(song))
    if (track) {
      const index = (queue || []).findIndex((item) => item.file === track.file)
      if (index < 0) actions.play([track], 0, context)
      else actions.play(queue, index, context)
      return
    }
    if (isStreamingSong(song) && player.isPlaying.value) return
    Promise.resolve(playStream(song, { context })).then((ok) => {
      if (!ok) ui.toast(t('stream.failed', { name: songTitle(song) }))
    })
  }
}

/**
 * `props`: `{ song, queue, context, songs }` - the song (a search/link
 * result), the library tracks playing it starts a queue from, the
 * player's "playing from" for them, and the whole song list for a mixed
 * queue (downloaded rows from the library, the rest streamed).
 */
export function useSongPlay(props) {
  const { t } = useI18n()
  const library = useLibrary()
  const player = usePlayer()
  const actions = useTrackActions()
  const ui = useUi()
  const start = useSongStarter()

  // The library track behind the song once it's downloaded - the library
  // refreshes itself shortly after a download finishes, and this follows.
  const track = computed(() =>
    library.findTrack(songArtist(props.song), songTitle(props.song))
  )
  const streaming = computed(() => isStreamingSong(props.song))
  const isCurrent = computed(
    () =>
      (!!track.value && player.currentTrack.value?.file === track.value.file) ||
      streaming.value
  )

  // Resolving the stream URL right now (direct tap, or the player working
  // through the queue): the row spins meanwhile.
  const loading = computed(
    () =>
      resolvingFor(props.song) ||
      (player.resolving.value != null &&
        rowKey(player.resolving.value) === rowKey(props.song))
  )
  // Anything with an artist and a title plays: from the library, else
  // streamed in full.
  const playable = computed(
    () => !!track.value || (!!songArtist(props.song) && !!songTitle(props.song))
  )
  const highlighted = computed(() => isCurrent.value)
  const playLabel = computed(() =>
    isCurrent.value && player.isPlaying.value
      ? t('player.pause')
      : t('actions.playItem', { name: songTitle(props.song) })
  )

  function play() {
    if (!track.value) return
    const queue = props.queue || []
    const start = queue.findIndex((item) => item.file === track.value.file)
    if (start < 0) actions.play([track.value], 0, props.context)
    else actions.play(queue, start, props.context)
  }

  // The play button: the song from the library, or - not downloaded yet -
  // its full stream (as one row of the whole list when the caller passes
  // it, so the player works through to the end even past undownloaded
  // rows), which the same button pauses again.
  function toggle() {
    if (track.value) play()
    else if (streaming.value) player.toggle()
    else
      start(props.song, {
        queue: props.queue,
        context: props.context,
        songs: props.songs,
      })
  }

  // A double click makes sure the song plays; it never pauses a stream.
  function ensurePlaying() {
    start(props.song, {
      queue: props.queue,
      context: props.context,
      songs: props.songs,
    })
  }

  return {
    track,
    isCurrent,
    loading,
    playable,
    highlighted,
    playLabel,
    toggle,
    ensurePlaying,
  }
}
