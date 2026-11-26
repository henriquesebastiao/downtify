// The companion's settings page: Downtify's address and key, and how it
// is doing. Saving asks the browser for permission to reach that address.
import { cleanAddress, originPattern } from './lib.js'

const $ = (id) => document.getElementById(id)

const REASONS = {
  off: 'The companion is turned off in Downtify',
  never_connected: 'Waiting for the first check-in',
  signed_out: 'On hold: this browser is signed out of Spotify',
  no_player: 'On hold: no Spotify tab to read with',
  other_account: 'On hold: signed in to a different Spotify account',
  away: 'On hold',
  error: 'On hold: something went wrong',
  busy: 'Reading a mix',
  gap: 'Waiting a little before the next read',
  between_slots: 'Waiting for the next time slot',
  slot_opening: 'A time slot is opening',
  nothing_due: 'No mix is due',
  no_slots: 'No time slots are set in Downtify',
  reading: 'Reading a mix',
}

function when(ms) {
  return ms ? new Date(ms).toLocaleString() : 'Never'
}

async function load() {
  const { settings } = await chrome.storage.local.get('settings')
  let values = settings
  if (!values?.downtify_url) {
    try {
      const bundled = await (
        await fetch(chrome.runtime.getURL('config.json'))
      ).json()
      values = { ...bundled, ...(settings || {}) }
    } catch {
      values = settings || {}
    }
  }
  $('url').value = values.downtify_url || ''
  $('key').value = values.key || ''
  $('tab').checked = values.keep_tab !== false
}

async function show() {
  const { status } = await chrome.storage.local.get('status')
  const s = status || {}
  $('at').textContent = when(s.at)
  const spotify = s.spotify || {}
  const spotifyEl = $('spotify')
  if (spotify.status === 'ready') {
    spotifyEl.textContent = `Signed in as ${spotify.account?.name || '?'}`
    spotifyEl.className = ''
  } else if (spotify.status) {
    spotifyEl.textContent =
      spotify.message || REASONS[spotify.status] || spotify.status
    spotifyEl.className = 'warn'
  }
  let text = REASONS[s.downtify] || s.downtify || 'Unknown'
  if (s.wait_seconds && s.downtify !== 'reading') {
    text += ` (asks again in ${Math.round(s.wait_seconds / 60)} min or less)`
  }
  $('downtify').textContent = text
  const last = s.last_read
  $('read').textContent = last
    ? `${last.name}: ${last.error ? `failed (${last.error})` : `${last.songs} songs`}, ${when(last.at)}`
    : 'None yet'
  $('problem').textContent = s.problem || ''
}

$('save').addEventListener('click', async () => {
  const address = cleanAddress($('url').value)
  if (!address) {
    $('saved').textContent = 'That address is not a web address'
    return
  }
  // Must run straight from the click: the browser asks you once.
  const granted = await chrome.permissions.request({
    origins: [originPattern(address)],
  })
  if (!granted) {
    $('saved').textContent = 'Without that permission it cannot reach Downtify'
    return
  }
  await chrome.storage.local.set({
    settings: {
      downtify_url: address,
      key: $('key').value.trim(),
      keep_tab: $('tab').checked,
    },
  })
  $('saved').textContent = 'Saved'
  chrome.runtime.sendMessage({ type: 'tick' })
})

$('now').addEventListener('click', async () => {
  $('saved').textContent = 'Checking in…'
  await chrome.runtime.sendMessage({ type: 'tick' })
  $('saved').textContent = ''
})

chrome.storage.onChanged.addListener(show)
load()
show()
