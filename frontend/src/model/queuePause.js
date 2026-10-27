// The download queue's pause switch: `GET /api/queue/state` plus the
// `queue_state` frames the server pushes whenever it changes. A paused
// queue starts nothing new; `pausing` means downloads already running
// are still finishing.
import { computed, reactive, ref } from 'vue'

import API from '/src/model/api'

const status = reactive({ paused: false, state: 'running', active: 0 })
const busy = ref(false)

function apply(data) {
  if (!data || typeof data !== 'object') return
  status.paused = Boolean(data.paused)
  status.state = data.state || (status.paused ? 'paused' : 'running')
  status.active = Number(data.active) || 0
}

export async function refreshQueueState() {
  const res = await API.getQueueState()
  apply(res.data)
}

API.onMessage((data) => {
  if (data?.type === 'queue_state') apply(data)
})

refreshQueueState().catch(() => {})

async function change(request) {
  busy.value = true
  try {
    const res = await request()
    apply(res.data)
  } finally {
    busy.value = false
  }
}

export function useQueuePause() {
  return {
    status,
    busy,
    paused: computed(() => status.paused),
    // Paused, with downloads still running to completion.
    draining: computed(() => status.state === 'pausing'),
    pause: () => change(API.pauseQueue),
    resume: () => change(API.resumeQueue),
    refresh: refreshQueueState,
  }
}
