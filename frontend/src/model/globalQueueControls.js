// Global server work control. No device credentials or optimistic pause state.
export function createQueueControl(fetcher, base) {
  const state = { status: null, busy: false, error: null }
  const listeners = new Set()
  let generation = 0
  const emit = () => listeners.forEach((listener) => listener(state))
  async function request(path, method = 'GET') {
    const response = await fetcher(new URL(path, base), {
      method,
      credentials: 'same-origin',
      headers: { Accept: 'application/json' },
      cache: 'no-store',
    })
    if (!response.ok)
      throw Object.assign(new Error('Queue request refused'), {
        status: response.status,
      })
    return response.json()
  }
  function apply(data) {
    if (!data || typeof data.paused !== 'boolean')
      throw new Error('Invalid queue state')
    state.status = { ...data, active: Math.max(0, Number(data.active) || 0) }
    state.error = null
    emit()
  }
  async function refresh() {
    if (state.busy) return
    const revision = generation
    try {
      const data = await request('state')
      if (generation === revision) apply(data)
    } catch (error) {
      if (generation === revision) {
        state.error = error.status || 'network'
        emit()
      }
    }
  }
  async function change(paused) {
    if (
      state.busy ||
      !state.status?.can_control ||
      !state.status?.global_pause_supported
    )
      return
    generation += 1
    state.busy = true
    state.error = null
    emit()
    try {
      await request(paused ? 'pause' : 'resume', 'POST')
      apply(await request('state'))
    } catch (error) {
      state.error = error.status || 'network'
    } finally {
      state.busy = false
      emit()
    }
  }
  return {
    state,
    refresh,
    change,
    subscribe(listener) {
      listeners.add(listener)
      listener(state)
      return () => listeners.delete(listener)
    },
  }
}
