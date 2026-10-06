// Playing one song from a list of songs that may or may not be downloaded
// yet - a link's album or playlist, an artist's top songs. Once the song is
// in the library it plays through the built-in player (with the list's
// other downloaded songs queued after it); until then the same controls
// stream it in full from YouTube (see model/stream.js), always shown in
// the player - there are no 30 s preview clips anywhere.
//
// Shared by TrackDownPlay (the artist page's Top songs) and SongPlayCell
// (the number cell of the selectable lists), so both behave the same.
import { computed } from 'vue'

import { useLibrary } from '/src/model/library'
import { usePlayer } from '/src/model/player'
import {
  isStreamingSong,
  playStream,
  resolvingFor,
  songArtist,
  songTitle,
} from '/src/model/stream'
import { useTrackActions } from '/src/model/trackActions'
import { useUi } from '/src/model/ui'
import { useI18n } from '/src/i18n'

/**
 * `start(song, { queue, context })`: make sure `song` plays - the library
 * track once it's downloaded (with `queue` after it), else its full
 * stream, never pausing one already playing. What a double click on a
 * song's row does, for a caller holding the song but not its row (the
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

  return function start(song, { queue = [], context = null } = {}) {
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
 * `props`: `{ song, queue, context }` - the song (a search/link result),
 * the library tracks playing it starts a queue from, and the player's
 * "playing from" for them.
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
  const isCurrent = computed(
    () =>
      (!!track.value && player.currentTrack.value?.file === track.value.file) ||
      isStreamingSong(props.song)
  )

  // Resolving the stream URL right now (the row spins meanwhile).
  const loading = computed(() => resolvingFor(props.song))
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
  // its full stream, which the same button pauses again.
  function toggle() {
    if (track.value) play()
    else if (isStreamingSong(props.song)) player.toggle()
    else start(props.song, { queue: props.queue, context: props.context })
  }

  // A double click makes sure the song plays; it never pauses a stream.
  function ensurePlaying() {
    start(props.song, { queue: props.queue, context: props.context })
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
