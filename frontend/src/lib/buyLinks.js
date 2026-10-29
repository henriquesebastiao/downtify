// Where to buy music to support the artist (see downtify/buy_links.py):
// what to ask the server for, and how to show what it answers. Pure, so
// it's unit-testable.

/**
 * The store country for the iTunes lookup: the region of the first browser
 * language that has one (`pt-BR` → `BR`), else the US store.
 */
export function storeCountry(languages) {
  for (const tag of languages || []) {
    const match = /^[a-z]{2,3}[-_]([a-z]{2})\b/i.exec(String(tag || ''))
    if (match) return match[1].toUpperCase()
  }
  return 'US'
}

const firstArtist = (artists, fallback) =>
  String((artists || [])[0] || fallback || '').trim()

/** What to buy for a search result / chart row (`name`, `artists`). */
export function buyTargetForSong(song) {
  return {
    artist: firstArtist(song?.artists, song?.artist),
    title: String(song?.name || song?.title || '').trim(),
    album: String(song?.album_name || '').trim(),
  }
}

/** What to buy for a library track (`title`, `artists`, `album`). */
export function buyTargetForTrack(track) {
  return {
    artist: firstArtist(track?.artists, track?.artist),
    title: String(track?.title || '').trim(),
    album: String(track?.album || '').trim(),
  }
}

/** A price as the store shows it (`R$ 2,90`); `''` without one. */
export function formatPrice(price, currency, locale) {
  const amount = Number(price)
  if (!amount || amount <= 0 || !currency) return ''
  try {
    return new Intl.NumberFormat(locale || undefined, {
      style: 'currency',
      currency,
    }).format(amount)
  } catch {
    return `${amount} ${currency}`
  }
}

const ICONS = {
  itunes: 'apple-music',
  bandcamp: 'bandcamp',
  qobuz: 'disc',
  website: 'globe',
}

/** The icon of a store link. */
export function storeIcon(store) {
  return ICONS[store] || 'tag'
}
