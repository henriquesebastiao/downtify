// What the global search box should do with what was typed.

import { isYouTubePlaylistURL, normalizeSpotifyURL } from '../model/url'

const SPOTIFY_ENTITY =
  /open\.spotify\.com\/(track|album|playlist|artist|show|episode)\//

// `deezer.com/track/123`, with or without `www.` or a two-letter locale
// segment (`deezer.com/br/track/123`, as Deezer's own share links carry).
// Short `deezer.page.link` share links aren't recognized here.
const DEEZER_ENTITY =
  /deezer\.com\/(?:[a-z]{2}\/)?(track|album|playlist|artist)\//i

function youtubeKind(text) {
  if (!/(?:youtube\.com|youtu\.be)\//.test(text)) return null
  if (/\/channel\/UC|youtube\.com\/@/.test(text)) return 'artist'
  if (/\/browse\/MPREb_/.test(text)) return 'album'
  if (text.includes('/playlist?') && /list=OLAK5uy_/.test(text)) {
    return 'album'
  }
  if (isYouTubePlaylistURL(text)) return 'playlist'
  if (/[?&]v=/.test(text) || text.includes('youtu.be/')) return 'track'
  return null
}

/**
 * Classify the search box contents:
 * - `{ type: 'empty' }`
 * - `{ type: 'link', source: 'spotify' | 'youtube' | 'deezer', kind, url }`
 *   for links Downtify can download (`kind`: track, album, playlist, artist)
 * - `{ type: 'unsupported', source, kind }` for other links
 * - `{ type: 'search', query }` for everything else
 */
export function classifyInput(raw) {
  const text = normalizeSpotifyURL(String(raw || '').trim())
  if (!text) return { type: 'empty' }
  const spotify = SPOTIFY_ENTITY.exec(text)
  if (spotify) {
    const kind = spotify[1]
    if (['track', 'album', 'playlist', 'artist'].includes(kind)) {
      return { type: 'link', source: 'spotify', kind, url: text }
    }
    return { type: 'unsupported', source: 'spotify', kind }
  }
  const deezer = DEEZER_ENTITY.exec(text)
  if (deezer) {
    return { type: 'link', source: 'deezer', kind: deezer[1], url: text }
  }
  const looksLikeURL =
    /^https?:\/\//i.test(text) || /(?:youtube\.com|youtu\.be)\//.test(text)
  if (looksLikeURL) {
    const kind = youtubeKind(text)
    if (kind) return { type: 'link', source: 'youtube', kind, url: text }
    return { type: 'unsupported', source: 'web', kind: null }
  }
  return { type: 'search', query: text }
}
