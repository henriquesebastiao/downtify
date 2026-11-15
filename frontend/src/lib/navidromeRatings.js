import { computed, ref } from 'vue'

import API from '/src/model/api'
import { currentLocale, t } from '/src/i18n'

const FAST_MS = 1500
const SLOW_MS = 15000

function formatDate(iso) {
  try {
    return new Date(iso).toLocaleString(currentLocale.value)
  } catch {
    return iso
  }
}

function failureText(failed) {
  const code = failed?.error?.code
  const message = failed?.error?.message || ''
  if (code === 'deezer_unreachable') return t('settings.ratingsFailedDeezer')
  if (code === 'navidrome_failed') {
    return t('settings.ratingsFailedNavidrome', { message })
  }
  return t('settings.ratingsFailed', { message })
}

// What the settings page shows for a ratings status: the job in
// progress, the last finished run, the next scheduled run and, after a
// preview, the songs it would change.
export function describeRatings({ job, last, nextRunAt }, now = Date.now()) {
  const running = job?.state === 'running'
  const progress = job?.progress || { done: 0, total: 0, step: '' }
  const view = {
    running,
    percent: progress.total ? (progress.done / progress.total) * 100 : 0,
    indeterminate: progress.step === 'library' || !progress.total,
    progressText: '',
    lastError: '',
    lastText: t('settings.ratingsNever'),
    nextText: '',
    changes: [],
    unmatched: [],
    unmatchedCount: 0,
  }
  if (running) {
    view.progressText =
      progress.step === 'library'
        ? t('settings.ratingsReading')
        : t('settings.ratingsProgress', {
            done: progress.done.toLocaleString(),
            total: progress.total.toLocaleString(),
          })
  }
  if (last?.state === 'failed') {
    view.lastError = failureText(last)
  } else if (last) {
    const result = last.result || {}
    const text = t(
      last.preview ? 'settings.ratingsLastPreview' : 'settings.ratingsLast',
      {
        when: formatDate(last.finished_at),
        rated: (result.rated ?? 0).toLocaleString(),
        skipped: (result.skipped ?? 0).toLocaleString(),
        notFound: (result.not_found ?? 0).toLocaleString(),
      }
    )
    view.lastText =
      last.state === 'stopped'
        ? `${text} · ${t('settings.ratingsStopped')}`
        : text
  }
  // Only a finished preview has changes worth listing.
  if (last?.preview && last.result) {
    view.changes = last.result.changes || []
    view.unmatched = last.result.unmatched || []
    view.unmatchedCount = last.result.not_found ?? view.unmatched.length
  }
  const when = nextRunAt ? new Date(nextRunAt).getTime() : NaN
  if (!Number.isNaN(when)) {
    // The server sends the Unix epoch when nothing has run yet, and a
    // past time while it waits for its hourly check.
    view.nextText =
      when <= now
        ? t('settings.ratingsNextSoon')
        : t('settings.ratingsNext', { when: formatDate(nextRunAt) })
  }
  return view
}

function runErrorText(err) {
  const detail = err?.response?.data?.detail
  if (detail?.code === 'navidrome_not_configured') {
    return t('settings.ratingsNotConfigured')
  }
  if (detail?.code === 'ratings_busy') return t('settings.ratingsBusy')
  if (typeof detail === 'string' && detail) return detail
  return t('settings.ratingsFailed', { message: err?.message || '' })
}

// Polls the ratings job (fast while one runs) and starts or stops it.
// `getOptions` is read when a run starts, never changed.
export function useNavidromeRatings(getOptions) {
  const job = ref(null)
  const last = ref(null)
  const nextRunAt = ref(null)
  const runError = ref('')
  let timer = null
  let gone = false

  const view = computed(() =>
    describeRatings({
      job: job.value,
      last: last.value,
      nextRunAt: nextRunAt.value,
    })
  )

  async function refresh() {
    clearTimeout(timer)
    try {
      const { data } = await API.navidromeRatingsStatus()
      job.value = data.job || null
      last.value = data.last || null
      nextRunAt.value = data.next_run_at || null
    } catch {
      // The next poll tries again.
    }
    if (!gone) {
      timer = setTimeout(
        refresh,
        job.value?.state === 'running' ? FAST_MS : SLOW_MS
      )
    }
  }

  async function start(preview) {
    runError.value = ''
    try {
      await API.navidromeRatingsRun({ preview, ...getOptions() })
    } catch (err) {
      runError.value = runErrorText(err)
    }
    await refresh()
  }

  async function stop() {
    try {
      await API.navidromeRatingsCancel()
    } catch {
      // Looking again shows what really happened.
    }
    await refresh()
  }

  function dispose() {
    gone = true
    clearTimeout(timer)
  }

  return { view, runError, refresh, start, stop, dispose }
}
