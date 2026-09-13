import { ref } from 'vue'

import API from '/src/model/api'

// Shape mirrors UpdateChecker.status() in downtify/update_check.py.
const status = ref(null)

// The backend already checks GitHub Releases on its own hourly loop
// (downtify/update_check.py) — this just re-reads its cached result
// often enough that a page left open notices without a full reload.
const POLL_INTERVAL_MS = 60 * 60 * 1000

let started = false

async function refresh() {
  try {
    const res = await API.check_for_update()
    status.value = res.data || null
  } catch {
    // Silent — a footer notice failing to load isn't worth surfacing
    // as an error, and the next hourly poll will just try again.
  }
}

function start() {
  if (started) return
  started = true
  refresh()
  setInterval(refresh, POLL_INTERVAL_MS)
}

export function useUpdateCheck() {
  start()
  return { status }
}
