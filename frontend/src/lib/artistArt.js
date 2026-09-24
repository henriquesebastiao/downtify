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

/**
 * A saved artist photo/banner URL with its version in it. The file keeps
 * the same `/downloads/...` URL however often it is replaced, so a browser
 * that already has it never asks again; the backend's `*_version` (the
 * file's modified time) changes exactly when the file does, which makes
 * this URL change with it - a replaced image shows up at once, an untouched
 * one stays cached. `''` when there is no image.
 */
export function versionedArtUrl(url, version) {
  if (!url) return ''
  if (version === undefined || version === null) return url
  return `${url}${url.includes('?') ? '&' : '?'}v=${version}`
}

/**
 * What names an artist image apart from the CDN that serves it: the path of
 * its URL, without host, query, or the size the CDN was asked for. A saved
 * photo records the path of the URL it came from (`current_cover` /
 * `current_cover_banner`), and a candidate in the picker is the photo in use
 * when the two keys match - so the same image from another CDN host, or at
 * another size, still matches. `''` for anything that isn't a URL or a path
 * (an old profile's `spotify`, an `upload`), which matches nothing.
 */
export function artImageKey(value) {
  let path = String(value || '').trim()
  if (/^https?:\/\//i.test(path)) {
    try {
      path = new URL(path).pathname
    } catch {
      return ''
    }
  }
  if (!path.startsWith('/')) return ''
  return (
    path
      // YouTube Music: '/<id>=w600-h600-l90-rj' - the size is after the '='.
      .replace(/=[^/]*$/, '')
      // Deezer: '/images/artist/<hash>/1000x1000-000000-80-0-0.jpg'.
      .replace(/\/\d+x\d+[^/]*$/, '')
  )
}

/** Whether *candidate* (a picker card) is the image saved as *current*. */
export function isCurrentArt(candidate, current) {
  const key = artImageKey(current)
  return !!key && artImageKey(candidate?.image_url) === key
}
