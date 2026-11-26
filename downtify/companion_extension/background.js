// The Downtify Spotify companion's background worker.
//
// Once a minute it tells Downtify how it is (signed in to Spotify, and
// as whom) and asks what to read. Downtify decides what and when (time
// slots, seats, gaps: see downtify/spotify_companion.py); the extension
// only reads the one mix it is given and sends the songs back.
//
// Spotify is asked as little as possible: the account check runs at most
// every half hour and right before a read; a read is one request per 100
// songs, with a pause between pages. Your Spotify password and cookies
// are never read; requests to Spotify carry only the web player's own
// short-lived token, and nothing about Spotify is sent to Downtify but
// song lists and your account's id and name.

import {
  captureFromRequest,
  cleanAddress,
  jitterMs,
  PROFILE_HASH,
  queryFromRequest,
  readPlaylist,
  ReadError,
  spotifyHeaders,
  whoAmI,
} from './lib.js'

const VERSION = chrome.runtime.getManifest().version
const PLAYER_URL = 'https://open.spotify.com/'
// The web player renews its token about hourly; older ones are refreshed
// by reloading its tab before use.
const TOKEN_MAX_AGE = 50 * 60 * 1000
// How long a successful account check is trusted for.
const HEALTH_MAX_AGE = 30 * 60 * 1000
const BUSY_MAX_AGE = 10 * 60 * 1000
const RETRY_AFTER = 2 * 60 * 1000

// ── What the web player sends ──────────────────────────────────────

chrome.webRequest.onBeforeSendHeaders.addListener(
  (details) => {
    const found = captureFromRequest(details)
    if (found) {
      chrome.storage.session.set({ session: { ...found, at: Date.now() } })
    }
  },
  { urls: ['https://*.spotify.com/*'] },
  ['requestHeaders', 'extraHeaders']
)

chrome.webRequest.onBeforeRequest.addListener(
  (details) => {
    const found = queryFromRequest(details)
    if (found?.operation === 'fetchPlaylist') {
      chrome.storage.session.set({ playerHash: found.hash })
    } else if (found?.operation === 'profileAttributes') {
      chrome.storage.session.set({ profileHash: found.hash })
    }
  },
  { urls: ['https://api-partner.spotify.com/pathfinder/*'] },
  ['requestBody']
)

// ── Schedule ───────────────────────────────────────────────────────

function startAlarm() {
  chrome.alarms.create('poll', { delayInMinutes: 0.1, periodInMinutes: 1 })
}

chrome.runtime.onInstalled.addListener((details) => {
  startAlarm()
  if (details.reason === 'install') chrome.runtime.openOptionsPage()
})
chrome.runtime.onStartup.addListener(startAlarm)
chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === 'poll') tick().catch(() => {})
})
chrome.action.onClicked.addListener(() => chrome.runtime.openOptionsPage())
chrome.runtime.onMessage.addListener((message, _sender, reply) => {
  if (message?.type === 'tick') {
    tick({ force: true })
      .catch(() => {})
      .finally(() => reply({ done: true }))
    return true
  }
  return false
})

// ── Helpers ────────────────────────────────────────────────────────

async function config() {
  const { settings } = await chrome.storage.local.get('settings')
  if (settings?.downtify_url && settings?.key) return settings
  // The ZIP from Downtify carries the address and key in config.json.
  try {
    const bundled = await (
      await fetch(chrome.runtime.getURL('config.json'))
    ).json()
    return { keep_tab: true, ...bundled, ...(settings || {}) }
  } catch {
    return { keep_tab: true, ...(settings || {}) }
  }
}

async function note(fields) {
  const { status } = await chrome.storage.local.get('status')
  await chrome.storage.local.set({ status: { ...(status || {}), ...fields } })
}

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

async function getJson(url, headers) {
  const response = await fetch(url, { headers, credentials: 'omit' })
  let json = null
  try {
    json = await response.json()
  } catch {
    json = null
  }
  return { status: response.status, json }
}

async function playerTabs() {
  return chrome.tabs.query({ url: 'https://open.spotify.com/*' })
}

// The companion keeps exactly one Spotify tab of its own: a pinned one.
// It never opens a tab per mix (reads go straight to Spotify's API, not
// through a page), it reuses its tab after a browser restart (pinned tabs
// come back), and it only ever reloads that tab - never one of yours.
let tabJob = null

function ownTab(settings) {
  if (settings.keep_tab === false) return Promise.resolve(null)
  // One at a time, so a check-in and a Save can't both open a tab.
  if (!tabJob) {
    tabJob = findOrOpenTab().finally(() => {
      tabJob = null
    })
  }
  return tabJob
}

async function findOrOpenTab() {
  const { ownTabId } = await chrome.storage.local.get('ownTabId')
  const tabs = await playerTabs()
  const pinned = tabs.filter((t) => t.pinned)
  const mine =
    tabs.find((t) => t.id === ownTabId) || pinned.find((t) => !t.audible)
  if (mine) {
    // Extra pinned Spotify tabs (left over from before) are closed, so
    // tabs never pile up; one that is playing is left alone.
    const extra = pinned.filter((t) => t.id !== mine.id && !t.audible)
    if (extra.length) await chrome.tabs.remove(extra.map((t) => t.id))
    if (mine.id !== ownTabId)
      await chrome.storage.local.set({ ownTabId: mine.id })
    return mine
  }
  const made = await chrome.tabs.create({
    url: PLAYER_URL,
    pinned: true,
    active: false,
  })
  await chrome.storage.local.set({ ownTabId: made.id })
  return made
}

/** The web player's token, refreshed (by reloading its tab) if old. */
async function session(settings, { renew = false } = {}) {
  let { session: found } = await chrome.storage.session.get('session')
  const fresh = found && Date.now() - found.at < TOKEN_MAX_AGE
  if (fresh && !renew) return found
  const tab = await ownTab(settings)
  // Never reload a player that is playing: you'd hear it stop. (While it
  // plays it renews its own token anyway.)
  if (!tab || tab.audible) return fresh ? found : null
  const before = found?.at || 0
  await chrome.tabs.reload(tab.id)
  for (let i = 0; i < 30; i += 1) {
    await sleep(1000)
    ;({ session: found } = await chrome.storage.session.get('session'))
    if (found && found.at > before) return found
  }
  return null
}

/** `{status, account?, message?}` - from a fresh check when `force`. */
async function health(settings, { force = false } = {}) {
  const { health: cached } = await chrome.storage.session.get('health')
  // A good check is trusted for half an hour; anything else is tried
  // again after a couple of minutes.
  const maxAge = cached?.status === 'ready' ? HEALTH_MAX_AGE : RETRY_AFTER
  if (!force && cached && Date.now() - cached.at < maxAge) {
    return cached
  }
  let result
  let current = await session(settings)
  if (!current) {
    result = {
      status: 'no_player',
      message: 'No Spotify web player tab to read with',
    }
  } else {
    const { profileHash } = await chrome.storage.session.get('profileHash')
    const ask = (s) =>
      whoAmI(
        (url) => getJson(url, spotifyHeaders(s)),
        [profileHash, PROFILE_HASH]
      )
    result = await ask(current)
    if (result.status === 'signed_out') {
      // An expired token looks the same: try once with a new one.
      current = await session(settings, { renew: true })
      if (current) result = await ask(current)
    }
  }
  const stamped = { ...result, at: Date.now() }
  await chrome.storage.session.set({ health: stamped })
  return stamped
}

async function downtify(settings, path, body) {
  const response = await fetch(
    `${cleanAddress(settings.downtify_url)}${path}`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${settings.key}`,
      },
      body: JSON.stringify(body),
    }
  )
  if (response.status === 401 || response.status === 403) {
    throw new Error('Downtify refused the key: make a new one in Downtify')
  }
  if (!response.ok && response.status !== 409) {
    throw new Error(`Downtify answered HTTP ${response.status}`)
  }
  return response.json().catch(() => ({}))
}

// ── One tick ───────────────────────────────────────────────────────

let ticking = false

async function tick({ force = false } = {}) {
  // One check-in at a time (an alarm and "Check in now" can meet).
  if (ticking) return
  ticking = true
  try {
    await tickOnce({ force })
  } finally {
    ticking = false
  }
}

async function tickOnce({ force }) {
  const settings = await config()
  if (!cleanAddress(settings.downtify_url) || !settings.key) {
    await note({ problem: 'Set the Downtify address and key', at: Date.now() })
    chrome.action.setBadgeText({ text: '!' })
    return
  }
  const { busy } = await chrome.storage.session.get('busy')
  if (busy && Date.now() - busy < BUSY_MAX_AGE) return
  await chrome.storage.session.set({ busy: Date.now() })
  try {
    await ownTab(settings)
    const state = await health(settings, { force })
    const answer = await downtify(settings, '/api/companion/poll', {
      status: state.status,
      account: state.account || null,
      message: state.message || '',
      version: VERSION,
    })
    await note({
      at: Date.now(),
      problem: '',
      spotify: state,
      downtify: answer.job ? 'reading' : answer.reason || '',
      wait_seconds: answer.wait_seconds || 0,
    })
    chrome.action.setBadgeText({
      text: state.status === 'ready' ? '' : '!',
    })
    if (answer.job) await read(settings, answer.job)
  } catch (err) {
    await note({ at: Date.now(), problem: String(err?.message || err) })
    chrome.action.setBadgeText({ text: '!' })
  } finally {
    await chrome.storage.session.remove('busy')
  }
}

async function read(settings, job) {
  const send = (body) =>
    downtify(settings, '/api/companion/result', { job_id: job.id, ...body })
  // Right before a read, make sure it is still your account.
  const state = await health(settings, { force: true })
  if (state.status !== 'ready') {
    await send({
      error:
        state.status === 'signed_out'
          ? 'signed_out'
          : state.message || state.status,
    })
    return
  }
  const current = await session(settings)
  const { playerHash } = await chrome.storage.session.get('playerHash')
  try {
    const { name, items } = await readPlaylist({
      get: (url) => getJson(url, spotifyHeaders(current)),
      playlistId: job.playlist_id,
      hashes: [job.hash, playerHash],
      pageSize: job.page_size || 100,
      pause: () => sleep(jitterMs(1.5, 4)),
    })
    const done = await send({ name, items })
    await note({
      last_read: {
        name: name || job.name,
        songs: done.songs ?? items.length,
        at: Date.now(),
      },
    })
  } catch (err) {
    const code = err instanceof ReadError ? err.code : 'failed'
    await send({
      error:
        code === 'signed_out' || code === 'rate_limited'
          ? code
          : String(err?.message || err),
    })
    await note({
      last_read: {
        name: job.name,
        error: String(err?.message || err),
        at: Date.now(),
      },
    })
    if (code === 'signed_out') await chrome.storage.session.remove('health')
  }
}
