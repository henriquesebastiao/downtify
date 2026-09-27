// Sign-in and pairing helpers. Pure, so they're unit-testable.
import { encode } from 'uqr'

/** Whether the web app has to show the sign-in page. */
export function needsSignIn(status) {
  return Boolean(status?.require_sign_in && !status?.signed_in)
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
