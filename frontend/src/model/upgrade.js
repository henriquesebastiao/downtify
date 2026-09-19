// Reactive state for the library upgrade: the scan, the queue and the
// progress the backend pushes over the WebSocket.
import { computed, ref, shallowRef } from 'vue'

import {
  byteProgress,
  canCancel,
  canPause,
  canResume,
  canScan,
  defaultSelection,
  foundCategories,
  isBusy,
  isRunning,
  isScanning,
  isWaitingToStart,
  normalizeStatus,
  queuedBytes,
  scanProgress,
  selectedTrackCount,
  toggleCategory,
  trackProgress,
} from '/src/lib/upgrade'
import API from '/src/model/api'
import { useLibrary } from '/src/model/library'

const status = ref(normalizeStatus(null))
const jobs = shallowRef([])
const loading = ref(false)
const loaded = ref(false)
const error = ref('')
const selected = ref([])
// Set once per scan result, so re-ticking a box isn't undone by the
// next progress message.
let selectionFor = null

const state = computed(() => status.value.state)
const counts = computed(() => status.value.counts)
const summary = computed(() => status.value.summary)
const tracks = computed(() => trackProgress(counts.value))
const bytes = computed(() =>
  byteProgress(counts.value, queuedBytes(summary.value))
)
const scan = computed(() => scanProgress(status.value.scan))
const found = computed(() => foundCategories(summary.value))
const busy = computed(() => isBusy(state.value))
const willRun = computed(() =>
  selectedTrackCount(summary.value, selected.value)
)

function apply(payload) {
  status.value = normalizeStatus(payload)
  const key = `${status.value.run?.id || 0}:${status.value.state}`
  if (status.value.state === 'ready' && selectionFor !== key) {
    selectionFor = key
    selected.value = defaultSelection(status.value.summary)
  }
}

async function load({ force = false } = {}) {
  if (loaded.value && !force) return
  loading.value = true
  error.value = ''
  try {
    const res = await API.getLibraryUpgrade()
    apply(res.data)
    loaded.value = true
    await refreshJobs()
  } catch (err) {
    error.value = err?.response?.data?.detail || err?.message || 'failed'
  } finally {
    loading.value = false
  }
}

async function refreshJobs() {
  try {
    const res = await API.getLibraryUpgradeJobs({ limit: 60 })
    jobs.value = res.data || []
  } catch {
    jobs.value = []
  }
}

async function run(call) {
  error.value = ''
  try {
    const res = await call()
    apply(res.data)
    await refreshJobs()
  } catch (err) {
    error.value = err?.response?.data?.detail || err?.message || 'failed'
  }
}

const startScan = (options) => run(() => API.scanLibraryUpgrade(options || {}))
const start = () => run(() => API.startLibraryUpgrade(selected.value))
const pause = () => run(() => API.pauseLibraryUpgrade())
const resume = () => run(() => API.resumeLibraryUpgrade())
const cancel = () => run(() => API.cancelLibraryUpgrade())

function toggle(name, on) {
  selected.value = toggleCategory(selected.value, name, on)
}

let jobTimer = null
let wasBusy = false

API.onMessage((data) => {
  if (data?.type !== 'library_upgrade') return
  apply(data.upgrade)
  const nowBusy = isBusy(status.value.state)
  if (wasBusy && !nowBusy) {
    // The run just stopped: fetch the rows now, so the list doesn't sit
    // there claiming tracks are still being worked on, and reload the
    // library, whose covers and tags just changed on disk.
    clearTimeout(jobTimer)
    jobTimer = null
    refreshJobs()
    useLibrary().refreshSoon(500)
  } else if (!jobTimer) {
    // Rows change far faster than anyone can read them; while a run is
    // going, poll them at a human pace instead of once per track.
    jobTimer = setTimeout(() => {
      jobTimer = null
      refreshJobs()
    }, 1500)
  }
  wasBusy = nowBusy
})

export function useUpgrade() {
  return {
    status,
    state,
    counts,
    summary,
    jobs,
    tracks,
    bytes,
    scan,
    found,
    busy,
    selected,
    willRun,
    loading,
    loaded,
    error,
    load,
    refreshJobs,
    startScan,
    start,
    pause,
    resume,
    cancel,
    toggle,
    isScanning: computed(() => isScanning(state.value)),
    isRunning: computed(() => isRunning(state.value)),
    waitingToStart: computed(() => isWaitingToStart(status.value)),
    canScan: computed(() => canScan(state.value)),
    canPause: computed(() => canPause(state.value)),
    canResume: computed(() => canResume(state.value)),
    canCancel: computed(() => canCancel(state.value)),
  }
}
