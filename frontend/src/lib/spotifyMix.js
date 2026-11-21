// Spotify's "made for you" playlists - Daily Mix, Discover Weekly, Release
// Radar, the mood, genre, decade and artist mixes, radios, On Repeat - are
// built for one listener. Their link opens that listener's version only
// when they are signed in; Downtify reads Spotify without an account, so
// it gets the version Spotify shows someone who isn't signed in, which can
// hold completely different songs (issue #489).
//
// Spotify gives these playlists ids with their own prefixes: `37i9dQZF1E…`
// for the mixes and radios, `37i9dQZEVX…` for Discover Weekly and Release
// Radar. Editorial playlists (`37i9dQZF1DX…`, "This Is" `37i9dQZF1DZ…`)
// are the same for everyone and aren't flagged.

const PERSONAL_PREFIXES = ['37i9dQZF1E', '37i9dQZEVX']
const PLAYLIST_ID =
  /open\.spotify\.com\/(?:intl-[a-z-]+\/)?playlist\/([A-Za-z0-9]+)|^spotify:playlist:([A-Za-z0-9]+)/i

/** True for a link to (or the id of) a Spotify playlist made for one listener. */
export function isPersonalMix(linkOrId) {
  const text = String(linkOrId || '').trim()
  const match = PLAYLIST_ID.exec(text)
  const id = match
    ? match[1] || match[2]
    : /^[A-Za-z0-9]{22}$/.test(text)
      ? text
      : ''
  return PERSONAL_PREFIXES.some((prefix) => id.startsWith(prefix))
}

/**
 * Before watching `url`: true to go on. A personal mix asks first, since
 * the watch would follow the signed-out version (see above).
 */
export async function confirmWatchMix(url, { ui, t }) {
  if (!isPersonalMix(url)) return true
  return ui.confirm({
    title: t('monitor.personalMixTitle'),
    body: t('monitor.personalMixBody'),
    confirmLabel: t('monitor.personalMixWatch'),
  })
}
