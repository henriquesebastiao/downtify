// Podcasts: pure helpers shared by the Podcasts page and the player.
// Kept free of the API client and Vue reactivity so they're plain,
// unit-testable functions — the same split as lib/library.js.
import { coverURL, fileURL } from './paths'

/** A downloaded episode as a player track: same shape normalizeTrack()
 * builds for a library file, plus what the player needs to tell a
 * podcast episode apart from a song (see model/player.js's toTrack,
 * which accepts a ready-made object exactly like this one). */
export function episodeToTrack(episode, show) {
  const file = String(episode.filename || '')
  return {
    file,
    title: episode.title || 'Untitled episode',
    artist: show?.name || '',
    artists: show?.name ? [show.name] : [],
    album: show?.name || '',
    albumArtist: show?.name || '',
    trackNumber: episode.episode_number || 0,
    year: (episode.published_at || '').slice(0, 4),
    duration: Number(episode.duration_seconds) || 0,
    added: 0,
    size: 0,
    hasCover: true,
    playlists: [],
    format: (file.split('.').pop() || '').toUpperCase(),
    url: fileURL(file),
    cover: coverURL(file),
    isPodcast: true,
    podcastEpisodeId: episode.id,
    podcastShowId: episode.show_id,
  }
}

/** 0 means "every new episode, forever"; anything else is a rolling
 * window of that many downloaded episodes. */
export function isKeepAll(retention) {
  return !retention
}

/** A resume position worth acting on: not the very start, and not
 * already basically finished (which counts as played, not resumable). */
export function hasResumePosition(episode) {
  const position = Number(episode?.position_seconds) || 0
  const duration = Number(episode?.duration_seconds) || 0
  if (position < 5) return false
  if (duration && position >= duration - 5) return false
  return true
}

/** True once an episode is close enough to its end to count as played,
 * even if the player never fires an explicit "ended" event for it (a
 * seek past the end, a stream cut short by a couple of seconds). */
export function isNearlyDone(positionSeconds, durationSeconds) {
  const duration = Number(durationSeconds) || 0
  if (!duration) return false
  const position = Number(positionSeconds) || 0
  return position >= duration - 3
}

/** Sort episodes newest-published first — the API already does this,
 * but a client-side merge (search results, retried loads) shouldn't
 * assume the order survived. */
export function sortEpisodesByDate(episodes) {
  return [...(episodes || [])].sort((a, b) =>
    String(b.published_at || '').localeCompare(String(a.published_at || ''))
  )
}
