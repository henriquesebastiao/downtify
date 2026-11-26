// The Downtify Spotify companion: the parts that don't need the browser,
// so they can be tested (frontend/src/__tests__/companionExtension.test.js).
//
// How a read works: the Spotify web player, open in a tab of this
// browser, sends its own access token with every request it makes. The
// extension notes the latest one (it never stores your password or
// cookies) and uses it to ask Spotify's web-player API for one playlist,
// exactly the request the player makes when you open that playlist. A
// token from a signed-in player gets *your* version of a personal mix.

export const PATHFINDER = 'https://api-partner.spotify.com/pathfinder/v1/query'

/** A header's value from a webRequest header list (case-insensitive). */
export function headerValue(headers, name) {
  const wanted = name.toLowerCase()
  for (const header of headers || []) {
    if (String(header.name).toLowerCase() === wanted) return header.value || ''
  }
  return ''
}

/**
 * What a request of the web player tells us: its token, client token
 * and app version. `null` for requests that aren't the player's own
 * (the extension's requests come from no tab).
 */
export function captureFromRequest(details) {
  if (!details || details.tabId === undefined || details.tabId < 0) return null
  const auth = headerValue(details.requestHeaders, 'authorization')
  const match = /^Bearer\s+(\S+)$/i.exec(auth)
  if (!match) return null
  return {
    token: match[1],
    clientToken: headerValue(details.requestHeaders, 'client-token'),
    appVersion: headerValue(details.requestHeaders, 'spotify-app-version'),
  }
}

function decodeBody(details) {
  const raw = details?.requestBody?.raw
  if (!Array.isArray(raw) || !raw.length || !raw[0].bytes) return ''
  try {
    return new TextDecoder().decode(raw[0].bytes)
  } catch {
    return ''
  }
}

/**
 * `{operation, hash}` of a web-player API request (GET with the query in
 * the address, or POST with it in the body), or `null`.
 */
export function queryFromRequest(details) {
  if (!details || details.tabId === undefined || details.tabId < 0) return null
  let operation = ''
  let extensions = null
  try {
    const url = new URL(details.url)
    operation = url.searchParams.get('operationName') || ''
    const ext = url.searchParams.get('extensions')
    if (ext) extensions = JSON.parse(ext)
  } catch {
    return null
  }
  if (!operation || !extensions) {
    try {
      const body = JSON.parse(decodeBody(details) || 'null')
      if (body) {
        operation = operation || body.operationName || ''
        extensions = extensions || body.extensions || null
      }
    } catch {
      return null
    }
  }
  const hash = extensions?.persistedQuery?.sha256Hash
  if (!operation || !/^[0-9a-f]{64}$/.test(hash || '')) return null
  return { operation, hash }
}

/** The address of one page of a playlist. */
export function playlistPageUrl(playlistId, offset, limit, hash) {
  const params = new URLSearchParams({
    operationName: 'fetchPlaylist',
    variables: JSON.stringify({
      uri: `spotify:playlist:${playlistId}`,
      offset,
      limit,
      enableWatchFeedEntrypoint: false,
      includeEpisodeContentRatingsV2: false,
    }),
    extensions: JSON.stringify({
      persistedQuery: { version: 1, sha256Hash: hash },
    }),
  })
  return `${PATHFINDER}?${params}`
}

/** Headers for a request to Spotify, the way the web player sends them. */
export function spotifyHeaders(session) {
  const headers = {
    Accept: 'application/json',
    Authorization: `Bearer ${session.token}`,
    'app-platform': 'WebPlayer',
  }
  if (session.clientToken) headers['client-token'] = session.clientToken
  if (session.appVersion) headers['spotify-app-version'] = session.appVersion
  return headers
}

export class ReadError extends Error {
  /** `code`: signed_out, not_found, rate_limited, query or failed. */
  constructor(code, message) {
    super(message || code)
    this.code = code
  }
}

function statusError(status) {
  if (status === 401) return new ReadError('signed_out', 'Spotify said 401')
  if (status === 429)
    return new ReadError('rate_limited', 'Spotify asked to slow down')
  if (status === 404) return new ReadError('not_found', 'Playlist not found')
  return new ReadError('failed', `Spotify answered HTTP ${status}`)
}

/**
 * Every item of a playlist, one page after another with a pause between
 * pages (`pause()` resolves after it). `get(url)` returns
 * `{status, json}`. Tries `hashes` in turn while Spotify doesn't know one.
 */
export async function readPlaylist({
  get,
  playlistId,
  hashes,
  pageSize = 100,
  pause = async () => {},
}) {
  const tries = [...new Set((hashes || []).filter(Boolean))]
  let lastError = new ReadError('query', 'No query to ask Spotify with')
  for (const hash of tries) {
    try {
      return await readWith(get, playlistId, hash, pageSize, pause)
    } catch (err) {
      if (!(err instanceof ReadError) || err.code !== 'query') throw err
      lastError = err
    }
  }
  throw lastError
}

async function readWith(get, playlistId, hash, pageSize, pause) {
  const items = []
  let name = ''
  let offset = 0
  for (let page = 0; page < 100; page += 1) {
    if (page > 0) await pause()
    const { status, json } = await get(
      playlistPageUrl(playlistId, offset, pageSize, hash)
    )
    if (status !== 200) throw statusError(status)
    const errors = json?.errors
    if (Array.isArray(errors) && errors.length) {
      const text = errors.map((e) => e?.message || '').join('; ')
      if (/PersistedQueryNotFound/i.test(text))
        throw new ReadError('query', text)
      throw new ReadError('failed', text.slice(0, 200))
    }
    const playlist = json?.data?.playlistV2
    if (!playlist || playlist.__typename === 'NotFound')
      throw new ReadError('not_found', 'Spotify has no such playlist')
    name = name || playlist.name || ''
    const content = playlist.content || {}
    const pageItems = Array.isArray(content.items) ? content.items : []
    items.push(...pageItems)
    offset += pageItems.length
    const total = Number(content.totalCount) || 0
    if (!pageItems.length || offset >= total) break
  }
  return { name, items }
}

// The web player's own "who is signed in" query (its answer is
// data.me.profile: uri, username, name; null when signed out). Spotify's
// public Web API (api.spotify.com/v1/me) answers the player's token with
// 429, so it isn't used.
export const PROFILE_HASH =
  '08ffb4730af3746e04a8301396f20875dbbce10c75243803091a9274eacc8ac0'

/** The address of the web player's account query. */
export function profileUrl(hash) {
  const params = new URLSearchParams({
    operationName: 'profileAttributes',
    variables: '{}',
    extensions: JSON.stringify({
      persistedQuery: { version: 1, sha256Hash: hash },
    }),
  })
  return `${PATHFINDER}?${params}`
}

/**
 * Who the web player is signed in as: `{status: 'ready', account}`,
 * `{status: 'signed_out'}` or `{status: 'error', message}`. `get(url)`
 * returns `{status, json}`; `hashes` are tried in turn while Spotify
 * doesn't know one.
 */
export async function whoAmI(get, hashes = [PROFILE_HASH]) {
  const tries = [...new Set((hashes || []).filter(Boolean))]
  let last = { status: 'error', message: 'No account query to ask with' }
  for (const hash of tries) {
    const { status, json } = await get(profileUrl(hash))
    if (status === 401) return { status: 'signed_out' }
    if (status === 429)
      return { status: 'error', message: 'Spotify asked to slow down' }
    if (status !== 200)
      return {
        status: 'error',
        message: `Account check answered HTTP ${status}`,
      }
    const errors = json?.errors
    if (Array.isArray(errors) && errors.length) {
      const text = errors.map((e) => e?.message || '').join('; ')
      last = { status: 'error', message: text.slice(0, 200) }
      if (/PersistedQueryNotFound/i.test(text)) continue
      return last
    }
    const profile = json?.data?.me?.profile
    if (!profile) return { status: 'signed_out' }
    const id =
      profile.username ||
      String(profile.uri || '')
        .split(':')
        .pop()
    if (!id) return { status: 'signed_out' }
    return { status: 'ready', account: { id, name: profile.name || id } }
  }
  return last
}

/** A whole number of milliseconds between `low` and `high` seconds. */
export function jitterMs(low, high, random = Math.random) {
  return Math.round((low + (high - low) * random()) * 1000)
}

/** The origin permission pattern for a Downtify address, or ''. */
export function originPattern(address) {
  try {
    const url = new URL(address)
    if (url.protocol !== 'http:' && url.protocol !== 'https:') return ''
    return `${url.protocol}//${url.host}/*`
  } catch {
    return ''
  }
}

/** A Downtify address without a trailing slash, or '' if it isn't one. */
export function cleanAddress(address) {
  const text = String(address || '').trim()
  return originPattern(text) ? text.replace(/\/+$/, '') : ''
}
