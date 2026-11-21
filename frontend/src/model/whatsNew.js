// The "What's new" dialog: open on the first visit after an update (see
// lib/whatsNew.js), and again from Settings → About.
import { computed, ref } from 'vue'

import API from '/src/model/api'
import { currentLocale } from '/src/i18n'
import notes from '/src/lib/releaseHighlights'
import {
  highlightsFor,
  markWhatsNewSeen,
  releaseUrl,
  shouldShowWhatsNew,
} from '/src/lib/whatsNew'

const open = ref(false)
const version = ref('')
let checked = false

function storage() {
  try {
    return localStorage
  } catch {
    return null
  }
}

const highlights = computed(() =>
  highlightsFor(notes, version.value, currentLocale.value)
)
const url = computed(() => (version.value ? releaseUrl(version.value) : ''))

/** Open the dialog if this browser hasn't seen this version's notes. */
async function check() {
  if (checked) return
  checked = true
  const current = await API.versionReady
  version.value = current
  if (shouldShowWhatsNew(storage(), current)) open.value = true
}

/** Open it by hand (Settings → About). */
async function show() {
  version.value = await API.versionReady
  open.value = true
}

function close() {
  open.value = false
  markWhatsNewSeen(storage(), version.value)
}

export function useWhatsNew() {
  return { open, version, highlights, url, check, show, close }
}
