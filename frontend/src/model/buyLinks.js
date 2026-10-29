// What the "Support the artist" dialog is open for (one at a time, for the
// whole app - see BuyLinksDialog in AppShell), and the store links for it.
import { ref } from 'vue'

import API from '/src/model/api'
import { storeCountry } from '/src/lib/buyLinks'

// { artist, title, album } - a song has a title, an album no title, an
// artist only the artist.
const target = ref(null)
// Answers by request, for the page's lifetime: reopening the dialog for
// the same song shouldn't ask the store again.
const answers = new Map()

function open(next) {
  if (!next?.artist) return
  target.value = next
}

function close() {
  target.value = null
}

function load(item) {
  const params = {
    artist: item.artist,
    title: item.title || '',
    album: item.album || '',
    country: storeCountry(globalThis.navigator?.languages),
  }
  const key = JSON.stringify(params)
  if (!answers.has(key)) {
    answers.set(
      key,
      API.getBuyLinks(params)
        .then((res) => res.data)
        .catch((err) => {
          answers.delete(key)
          throw err
        })
    )
  }
  return answers.get(key)
}

export function useBuyLinks() {
  return { target, open, close, load }
}
