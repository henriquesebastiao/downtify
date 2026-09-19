// Library upgrade: run state and progress maths. Pure, so it's
// unit-testable and the view only has to render what these return.

/** Categories the backend scans for, in the order they're shown. */
export const CATEGORIES = ['artwork', 'lyrics', 'metadata']

/** Where artwork may come from; `highest` compares every source. */
export const ARTWORK_SOURCES = ['highest', 'spotify', 'itunes', 'youtube-music']

/** Target sizes offered for "upgrade artwork below". */
export const ARTWORK_SIZES = [300, 500, 600, 1000, 1200]

const EMPTY_COUNTS = {
  total: 0,
  queued: 0,
  running: 0,
  completed: 0,
  skipped: 0,
  failed: 0,
  finished: 0,
  processed_bytes: 0,
}

/** A `GET /api/library/upgrade` payload with every field present. */
export function normalizeStatus(payload) {
  const data = payload || {}
  const run = data.run || null
  return {
    state: String(data.state || 'idle'),
    run,
    counts: { ...EMPTY_COUNTS, ...(data.counts || {}) },
    scan: {
      scanned: Number(data.scan?.scanned) || 0,
      total: Number(data.scan?.total) || 0,
    },
    summary: {
      categories: data.summary?.categories || {},
      categoryBytes: data.summary?.category_bytes || {},
      tracks: Number(data.summary?.tracks) || 0,
      // Tracks the scan didn't read because every category had been
      // looked at recently enough.
      recentlyChecked: Number(data.summary?.recently_checked) || 0,
      libraryTracks: Number(data.summary?.library_tracks) || 0,
      libraryBytes: Number(data.summary?.library_bytes) || 0,
    },
    options: run?.options || {},
  }
}

export function isScanning(state) {
  return state === 'scanning'
}

export function isRunning(state) {
  return state === 'running'
}

/** True while a scan or a run is working: the UI shows progress. */
export function isBusy(state) {
  return isScanning(state) || isRunning(state)
}

/** A finished scan with something to do is waiting for confirmation. */
export function isWaitingToStart(status) {
  return status.state === 'ready' && status.counts.total > 0
}

export function canScan(state) {
  return !isBusy(state)
}

export function canPause(state) {
  return isRunning(state)
}

export function canResume(state) {
  return state === 'paused'
}

/**
 * Only a run that has actually started can be stopped. A scan waiting
 * for confirmation is dropped by scanning again, not by "Stop", which
 * next to the start button would read as "don't upgrade anything".
 */
export function canCancel(state) {
  return isRunning(state) || state === 'paused'
}

function pct(done, total) {
  if (!total) return 0
  return Math.max(0, Math.min(100, Math.round((done / total) * 100)))
}

/** `{ done, total, pct }` over the tracks queued for this run. */
export function trackProgress(counts) {
  return {
    done: counts.finished,
    total: counts.total,
    pct: pct(counts.finished, counts.total),
  }
}

/**
 * `{ done, total, pct }` in bytes. Sizes come from the queued files, so
 * this is an estimate — it's here because "8 of 51 GB" reads better than
 * a track count on a library that takes hours.
 */
export function byteProgress(counts, queuedBytes) {
  return {
    done: counts.processed_bytes,
    total: queuedBytes,
    pct: pct(counts.processed_bytes, queuedBytes),
  }
}

export function scanProgress(scan) {
  return { ...scan, pct: pct(scan.scanned, scan.total) }
}

/** Total bytes of the tracks a scan queued, for the byte estimate. */
export function queuedBytes(summary) {
  return CATEGORIES.reduce(
    (max, name) => Math.max(max, Number(summary.categoryBytes[name]) || 0),
    0
  )
}

/** Categories a scan actually found something for. */
export function foundCategories(summary) {
  return CATEGORIES.filter((name) => (summary.categories[name] || 0) > 0)
}

/**
 * The categories to pre-tick: everything the scan found. The user
 * unticks what they don't want before starting.
 */
export function defaultSelection(summary) {
  return foundCategories(summary)
}

export function toggleCategory(selected, name, on) {
  const next = new Set(selected)
  if (on) next.add(name)
  else next.delete(name)
  return CATEGORIES.filter((item) => next.has(item))
}

/** Tracks that would run, given a selection (a track may need several). */
export function selectedTrackCount(summary, selected) {
  return selected.reduce(
    (max, name) => Math.max(max, Number(summary.categories[name]) || 0),
    0
  )
}

const STATUS_ORDER = ['running', 'failed', 'queued', 'done', 'skipped']

/** Group job rows by status, in the order the UI lists them. */
export function groupJobs(jobs) {
  const groups = new Map(STATUS_ORDER.map((status) => [status, []]))
  for (const job of jobs || []) {
    const bucket = groups.get(job.status)
    if (bucket) bucket.push(job)
  }
  return STATUS_ORDER.map((status) => ({
    status,
    jobs: groups.get(status),
  })).filter((group) => group.jobs.length > 0)
}

/** `artwork 1200px (itunes)` -> `1200px`, for a compact row badge. */
export function artworkSizeFromDetail(detail) {
  const match = /(\d+)px/.exec(String(detail || ''))
  return match ? `${match[1]}px` : ''
}
