// An artist's profile links (see downtify/artist_profile.py): the social
// networks they filled in and the streaming platforms they were found on.
// Pure, so it's unit-testable. Used by the artist page's Links tab and by the
// icons on its banner.

const SOCIAL = {
  twitter: { icon: 'twitter', label: 'Twitter/X' },
  instagram: { icon: 'instagram', label: 'Instagram' },
  facebook: { icon: 'facebook', label: 'Facebook' },
  youtube: { icon: 'youtube', label: 'YouTube' },
  website: { icon: 'globe', label: 'Website' },
}

// Base URL each platform's saved id is appended to. The backend resolves all
// four automatically (see downtify/artist_profile.py) and a hand-edit of the
// profile JSON can set any of them. Unrecognized keys are skipped rather than
// erroring, so this grows without a change needed elsewhere.
const PLATFORMS = {
  spotify: {
    icon: 'spotify',
    label: 'Spotify',
    prefix: 'https://open.spotify.com/artist/',
  },
  youtubemusic: {
    icon: 'youtube-music',
    label: 'YouTube Music',
    prefix: 'https://music.youtube.com/channel/',
  },
  deezer: {
    icon: 'deezer',
    label: 'Deezer',
    prefix: 'https://www.deezer.com/artist/',
  },
  // Stored as 'slug/numeric-id' (e.g. 'evanescence/42102393', straight from
  // Apple's own `url` field) - the 'us' storefront in this prefix is just a
  // stable link target, not tied to the artist's real catalog availability
  // elsewhere.
  applemusic: {
    icon: 'apple-music',
    label: 'Apple Music',
    prefix: 'https://music.apple.com/us/artist/',
  },
}

/**
 * A link's address as something safe to put in an `href`: an http(s) URL as
 * it is, a bare `twitter.com/x` made https, and `''` for anything with
 * another scheme (`javascript:`...) or nothing at all. Social links are typed
 * by hand or come from a third party, so nothing else is passed on.
 */
export function safeLinkUrl(raw) {
  const text = String(raw || '').trim()
  if (!text) return ''
  if (/^https?:\/\//i.test(text)) return text
  if (/^[a-z][a-z0-9+.-]*:/i.test(text)) return ''
  return `https://${text}`
}

/** The site a link points to, for showing under its name: `open.spotify.com`. */
export function linkHost(url) {
  try {
    return new URL(url).hostname.replace(/^www\./, '')
  } catch {
    return String(url || '')
  }
}

/** `[{ key, url, icon, label }]` for the social fields that are filled in. */
export function artistSocialLinks(social) {
  return Object.keys(SOCIAL)
    .map((key) => ({
      key,
      url: safeLinkUrl(social?.[key]),
      icon: SOCIAL[key].icon,
      label: SOCIAL[key].label,
    }))
    .filter((link) => link.url)
}

/** Same for the streaming platforms whose artist id is known. */
export function artistPlatformLinks(platformsId) {
  return Object.keys(PLATFORMS)
    .filter((key) => String(platformsId?.[key] || '').trim())
    .map((key) => ({
      key,
      url: `${PLATFORMS[key].prefix}${String(platformsId[key]).trim()}`,
      icon: PLATFORMS[key].icon,
      label: PLATFORMS[key].label,
    }))
}
