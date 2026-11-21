// LRC (time-synced lyrics) parsing for the Now playing lyrics panel.

const TIME_TAG = /\[(\d{1,3}):(\d{1,2})(?:[.:](\d{1,3}))?\]/g

/**
 * Parse LRC text into `[{ time, text }]` sorted by time (seconds).
 * A line with several time tags (`[00:10][00:40]Chorus`) yields one
 * entry per tag; metadata tags (`[ar:...]`) and blank lines are skipped.
 */
export function parseLrc(source) {
  const lines = []
  for (const raw of String(source || '').split(/\r?\n/)) {
    const tags = [...raw.matchAll(TIME_TAG)]
    if (!tags.length) continue
    const text = raw.replace(TIME_TAG, '').trim()
    for (const [, min, sec, frac = '0'] of tags) {
      const fraction = Number(frac) / 10 ** frac.length
      lines.push({ time: Number(min) * 60 + Number(sec) + fraction, text })
    }
  }
  return lines.sort((a, b) => a.time - b.time)
}

/** Index of the line being sung at `seconds`, or -1 before the first. */
export function activeLineIndex(lines, seconds) {
  let lo = 0
  let hi = lines.length - 1
  let found = -1
  while (lo <= hi) {
    const mid = (lo + hi) >> 1
    if (lines[mid].time <= seconds) {
      found = mid
      lo = mid + 1
    } else {
      hi = mid - 1
    }
  }
  return found
}

// LRC only times the start of a line, so how long it is sung is a guess:
// until the next line, but no longer than a slow singer would need, or a
// line before an untimed solo would crawl across the whole solo.
const SECONDS_PER_CHAR = 0.25
const MIN_SUNG_SECONDS = 3

/** How much of line `index` has been sung at `seconds`, from 0 to 1. */
export function lineProgress(lines, index, seconds) {
  const line = lines[index]
  if (!line) return 0
  const gap = (lines[index + 1]?.time ?? Infinity) - line.time
  const sung = Math.min(
    gap,
    Math.max(MIN_SUNG_SECONDS, line.text.length * SECONDS_PER_CHAR)
  )
  if (sung <= 0) return 1
  return Math.min(1, Math.max(0, (seconds - line.time) / sung))
}

/**
 * Seconds left, whole and capped at `max`, before singing starts again:
 * the dots that count a singer in during an intro or an instrumental gap.
 * 0 while a line is being sung or no words are left.
 */
export function countInBeats(lines, seconds, max = 3) {
  const index = activeLineIndex(lines, seconds)
  if (index >= 0 && lines[index].text) return 0
  const next = lines.slice(index + 1).find((line) => line.text)
  if (!next) return 0
  return Math.min(max, Math.max(0, Math.ceil(next.time - seconds)))
}
