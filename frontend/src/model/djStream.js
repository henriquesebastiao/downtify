// Keep idle DJ pages from opening a live stream; fence asynchronous setup.
export function createDjStream({
  media,
  url,
  current,
  onFatal,
  onDiagnostic = () => {},
  loadHls = () => import('hls.js'),
}) {
  let hls,
    loading,
    connected = false,
    generation = 0
  const number = (value) =>
    Number.isFinite(value) ? Math.round(value * 1000) / 1000 : 0
  function diagnostic(epoch, kind, data) {
    if (epoch !== generation || !current()) return
    let buffered = 0
    for (let i = 0; i < (media.buffered?.length || 0); i++)
      if (
        media.buffered.start(i) <= media.currentTime &&
        media.currentTime <= media.buffered.end(i)
      )
        buffered = media.buffered.end(i) - media.currentTime
    const timing = (data.frag?.stats || data.stats)?.loading
    onDiagnostic({
      kind,
      buffered_seconds: number(buffered),
      latency_seconds: number(hls?.latency),
      first_byte_ms: timing ? number(timing.first - timing.start) : 0,
      load_ms: timing ? number(timing.end - timing.start) : 0,
      ...(kind === 'error'
        ? {
            error: {
              type: String(data.type || '').slice(0, 40),
              detail: String(data.details || '').slice(0, 80),
              fatal: data.fatal === true,
              http_status: number(
                data.response?.code || data.networkDetails?.status
              ),
              position: number(media.currentTime),
            },
          }
        : {}),
    })
  }
  async function connect() {
    if (!current()) return false
    if (connected) return true
    if (loading) return loading
    const epoch = generation
    const task = (async () => {
      const { default: Hls } = await loadHls()
      if (epoch !== generation || !current()) return false
      if (Hls.isSupported()) {
        hls = new Hls({
          liveSyncDuration: 24,
          liveMaxLatencyDuration: 48,
          maxBufferLength: 30,
          maxMaxBufferLength: 36,
          maxLiveSyncPlaybackRate: 1,
          lowLatencyMode: false,
        })
        hls.on(Hls.Events.ERROR, (_, data) => {
          diagnostic(epoch, 'error', data)
          if (data.fatal && epoch === generation && current()) {
            unload()
            onFatal()
          }
        })
        hls.on(Hls.Events.FRAG_LOADED, (_, data) =>
          diagnostic(epoch, 'segment', data)
        )
        hls.on(Hls.Events.LEVEL_LOADED, (_, data) =>
          diagnostic(epoch, 'playlist', data)
        )
        hls.attachMedia(media)
        hls.loadSource(url)
      } else if (media.canPlayType('application/vnd.apple.mpegurl'))
        media.src = url
      else throw new Error('unsupported-hls')
      connected = true
      return true
    })()
    loading = task
    try {
      return await task
    } catch (error) {
      if (epoch === generation) {
        hls?.destroy()
        hls = null
        connected = false
      }
      throw error
    } finally {
      if (loading === task) loading = null
    }
  }
  function unload() {
    generation++
    hls?.destroy()
    hls = null
    connected = false
    loading = null
  }
  function position(origin) {
    if (Number.isFinite(origin) && origin > 0) {
      const date = hls?.playingDate
      if (date instanceof Date && Number.isFinite(date.getTime()))
        return Math.max(0, date.getTime() / 1000 - origin)
      const start = media.getStartDate?.()
      if (start instanceof Date && Number.isFinite(start.getTime()))
        return Math.max(0, start.getTime() / 1000 + media.currentTime - origin)
    }
    return media.currentTime || 0
  }
  return { connect, unload, position }
}
