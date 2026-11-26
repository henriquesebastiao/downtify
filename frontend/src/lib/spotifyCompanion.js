// The Spotify companion (downtify/spotify_companion.py): helpers for its
// settings card and the Monitor page's badges.
import { ref } from 'vue'
import API from '/src/model/api'

export const KINDS = ['daily', 'weekly', 'mixes']
export const DAYS = [0, 1, 2, 3, 4, 5, 6] // Monday first, like Python

/** Badge tone for a health status. */
export function statusTone(status) {
  if (status === 'ready') return 'accent'
  if (status === 'off' || status === 'never_connected') return 'neutral'
  return 'warn'
}

/** Short weekday names (Monday first) in *locale*. */
export function dayNames(locale) {
  // 2024-01-01 was a Monday.
  const format = new Intl.DateTimeFormat(locale || undefined, {
    weekday: 'short',
    timeZone: 'UTC',
  })
  return DAYS.map((d) => format.format(new Date(Date.UTC(2024, 0, 1 + d))))
}

/** A new slot that doesn't clash with *slots*' ids. */
export function newSlot(slots) {
  const ids = new Set((slots || []).map((s) => s.id))
  let n = (slots || []).length + 1
  while (ids.has(`slot${n}`)) n += 1
  return {
    id: `slot${n}`,
    name: '',
    days: [...DAYS],
    start: '12:00',
    end: '14:00',
    seats: 20,
    kinds: [...KINDS],
  }
}

/** Toggle *value* in a list, keeping the order of *all*. */
export function toggled(list, value, all) {
  const has = list.includes(value)
  return all.filter((v) => (v === value ? !has : list.includes(v)))
}

/** What is wrong with a slot (an i18n key), or ''. */
export function slotProblem(slot) {
  if (!slot.days.length) return 'companion.problemDays'
  if (!slot.kinds.length) return 'companion.problemKinds'
  if (!slot.start || !slot.end || slot.start === slot.end)
    return 'companion.problemTimes'
  return ''
}

// ── The Monitor page's badges ─────────────────────────────────────

const watches = ref({ enabled: false, status: 'off', watches: {} })
let loadedAt = 0
let loading = null

/**
 * The companion's view of the watches, shared by every badge on the page.
 * Each call fetches it again unless it was fetched in the last 15
 * seconds, so a page that opens shows how things stand now.
 */
export function useCompanionWatches() {
  if (!loading && Date.now() - loadedAt > 15000) {
    loadedAt = Date.now()
    loading = API.get('/api/companion/watches')
      .then((res) => {
        watches.value = res.data
      })
      .catch(() => {})
      .finally(() => {
        loading = null
      })
  }
  return watches
}

/** The toast after "Check now", by what the server said. */
export function checkToastKey(response) {
  return response?.data?.status === 'companion_queued'
    ? 'monitor.companionQueued'
    : 'monitor.checking'
}
