// Saved links (issue #731): the playlist and album links this account
// keeps in Library > Playlists to stream. One list for the whole app, so
// a link saved on its page is in the Library at once.
import { ref, shallowRef } from 'vue'

import API from '/src/model/api'
import { withSavedLink, withoutSavedLink } from '/src/lib/savedLinks'

const links = shallowRef([])
const loaded = ref(false)

async function load() {
  try {
    const res = await API.getSavedLinks()
    links.value = Array.isArray(res.data?.links) ? res.data.links : []
    loaded.value = true
  } catch {
    // Keep what is shown; the next visit tries again.
  }
}

/** The saved link that is `url` (opened in any form), or null. */
async function find(url) {
  const res = await API.getSavedLinks(url)
  return res.data?.links?.[0] || null
}

/** Save `{url, name, cover}`; the link as the server stored it. */
async function save(payload) {
  const res = await API.saveLink(payload)
  links.value = withSavedLink(links.value, res.data)
  return res.data
}

/** Forget the link saved under `url`. */
async function remove(url) {
  const res = await API.removeSavedLink(url)
  links.value = withoutSavedLink(links.value, res.data?.url || url)
}

export function useSavedLinks() {
  return { links, loaded, load, find, save, remove }
}
