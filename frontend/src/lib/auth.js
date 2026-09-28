// Sign-in and pairing helpers. Pure, so they're unit-testable.
import { encode } from 'uqr'

/**
 * Whether the web app has to show the sign-in page: the server answered
 * and this browser isn't signed in. An unreachable server (no status)
 * doesn't lock the page - that's shown elsewhere.
 */
export function needsSignIn(status) {
  return Boolean(status && !status.signed_in)
}

export const ROLE_ADMIN = 'admin'

/** The Settings sections a user may open: everything for an admin. */
export function settingsSectionsFor(role, sections) {
  if (role === ROLE_ADMIN) return sections
  return sections.filter((section) => !section.admin)
}

/**
 * What a player sends to `POST /api/activity/playback` about `track`
 * (a player track: `{ file, title, artists, album, duration, ... }`).
 * `null` for nothing worth reporting (no track, a preview, a podcast).
 */
export function playbackReport(track, { player, state, position = 0 }) {
  if (state === 'stopped') return { player, state, track: {}, position: 0 }
  if (!track?.file || track.isPodcast || track.isPreview) return null
  return {
    player,
    state,
    position: Math.max(0, Math.round(Number(position) || 0)),
    track: {
      file: track.file,
      title: track.title || '',
      artist: (track.artists || []).join(', ') || track.artist || '',
      album: track.album || '',
      duration: Number(track.duration) || 0,
    },
  }
}

/**
 * What the pairing QR code carries: the address the app should use, the
 * server's id (so the app knows it reached the right one) and the code.
 * `origin` is this page's own (`window.location.origin`): the address the
 * phone has to reach, unless a better one is given.
 */
export function pairingUri({ origin, serverId, code }) {
  const params = new URLSearchParams({
    url: String(origin || '').replace(/\/+$/, ''),
    sid: String(serverId || ''),
    code: String(code || ''),
  })
  return `downtify://pair?${params.toString()}`
}

/**
 * A QR code for `text` as one SVG path (`d`) on a `size`×`size` grid,
 * dark modules only. Drawn by the page itself: no image, no `v-html`.
 */
export function qrPath(text) {
  const { size, data } = encode(String(text || ''), { ecc: 'M', border: 0 })
  let d = ''
  for (let y = 0; y < size; y += 1) {
    for (let x = 0; x < size; x += 1) {
      if (data[y][x]) d += `M${x} ${y}h1v1h-1z`
    }
  }
  return { size, d }
}

/** `125` → `2:05`; never negative. */
export function formatCountdown(seconds) {
  const total = Math.max(0, Math.floor(Number(seconds) || 0))
  const minutes = Math.floor(total / 60)
  return `${minutes}:${String(total % 60).padStart(2, '0')}`
}
