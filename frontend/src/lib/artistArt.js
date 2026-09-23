// Pure helpers for the artist photo/banner picker (ArtistArtModal.vue).

/** Whether a modal query looks like a direct image link rather than a name. */
export function isImageUrlQuery(text) {
  return /^https?:\/\//i.test(String(text || '').trim())
}

const SOURCE_NAMES = {
  spotify: 'Spotify',
  youtube: 'YouTube Music',
  deezer: 'Deezer',
}

/** Display label for a candidate's source; `linkLabel` covers a pasted URL. */
export function sourceLabel(source, linkLabel) {
  if (source === 'link') return linkLabel
  return SOURCE_NAMES[source] ?? source
}

const SOURCE_ICONS = {
  spotify: 'spotify',
  youtube: 'youtube',
  deezer: 'deezer',
  link: 'link',
  upload: 'upload',
}

/** Icon name for a candidate's source badge. */
export function sourceIcon(source) {
  return SOURCE_ICONS[source] ?? 'link'
}

/**
 * Candidate cards for the results grid: the auto-detected Spotify photo
 * (if any) first, then whatever the name/URL search turned up.
 */
export function artCandidates(spotifyCandidate, searchResults) {
  const results = Array.isArray(searchResults) ? searchResults : []
  return spotifyCandidate ? [spotifyCandidate, ...results] : results
}
