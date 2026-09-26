// Playing one song from a list of songs that may or may not be downloaded
// yet - a link's album or playlist, an artist's top songs. Once the song is
// in the library it plays through the built-in player (with the list's
// other downloaded songs queued after it); until then the same controls
// play its 30 s preview clip on the row itself (see model/preview.js).
//
// Shared by TrackDownPlay (the artist page's Top songs) and SongPlayCell
// (the number cell of the selectable lists), so both behave the same.
import { computed, onBeforeUnmount, watch } from 'vue'

import { useLibrary } from '/src/model/library'
import { usePlayer } from '/src/model/player'
import { usePreview } from '/src/model/preview'
import { useTrackActions } from '/src/model/trackActions'
import { useUi } from '/src/model/ui'
import { previewKey } from '/src/lib/preview'
import { useI18n } from '/src/i18n'

/**
 * `props`: `{ song, queue, context }` - the song (a search/link result),
 * the library tracks playing it starts a queue from, and the player's
 * "playing from" for them.
 */
export function useSongPlay(props) {
  const { t } = useI18n()
  const library = useLibrary()
  const player = usePlayer()
  const preview = usePreview()
  const actions = useTrackActions()
  const ui = useUi()

  // The library track behind the song once it's downloaded - the library
  // refreshes itself shortly after a download finishes, and this follows.
  const track = computed(() =>
    library.findTrack(
      (props.song.artists || [])[0] || props.song.artist,
      props.song.name
    )
  )
  const isCurrent = computed(
    () => !!track.value && player.currentTrack.value?.file === track.value.file
  )

  // A song that isn't in the library but has (or may have) a clip.
  const previewable = computed(
    () => !track.value && preview.canPreview(props.song)
  )
  const songId = computed(() => previewKey(props.song))
  const previewActive = computed(
    () =>
      !track.value && !!songId.value && preview.activeId.value === songId.value
  )
  const previewPlaying = computed(
    () => previewActive.value && preview.isPlaying.value
  )
  const previewLoading = computed(
    () => previewActive.value && preview.isLoading.value
  )
  // Something on this row plays: the downloaded song, or its clip.
  const playable = computed(() => !!track.value || previewable.value)
  const highlighted = computed(() => isCurrent.value || previewActive.value)
  const playLabel = computed(() =>
    t(
      track.value
        ? 'actions.playItem'
        : previewPlaying.value
          ? 'actions.pausePreview'
          : 'actions.playPreview',
      { name: props.song.name }
    )
  )

  function play() {
    if (!track.value) return
    const queue = props.queue || []
    const start = queue.findIndex((item) => item.file === track.value.file)
    if (start < 0) actions.play([track.value], 0, props.context)
    else actions.play(queue, start, props.context)
  }

  async function playPreview() {
    const ok = await preview.toggle(props.song)
    if (!ok) ui.toast(t('actions.noPreview', { name: props.song.name }))
  }

  // The play button: the song from the library, or - not downloaded yet -
  // its clip, which the same button pauses again.
  function toggle() {
    if (track.value) play()
    else if (previewable.value) playPreview()
  }

  // A double click makes sure the song plays; it never pauses a clip.
  function ensurePlaying() {
    if (track.value) play()
    else if (previewable.value && !previewPlaying.value) playPreview()
  }

  // Once the song has been downloaded the row plays the real thing, so the
  // clip ends; a row that goes away takes its clip with it.
  watch(track, (found) => {
    if (found) preview.stopFor(songId.value)
  })
  onBeforeUnmount(() => preview.stopFor(songId.value))

  return {
    track,
    isCurrent,
    previewable,
    previewActive,
    previewPlaying,
    previewLoading,
    playable,
    highlighted,
    playLabel,
    progress: preview.progress,
    toggle,
    ensurePlaying,
  }
}
