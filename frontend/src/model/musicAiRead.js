const wait = ms => new Promise(resolve => setTimeout(resolve, ms))

// Retry only temporary read failures. A disabled module, changed account or
// disposed view cancels further requests; authentication failures never retry.
export async function readMixIndex(fetch, current, sleep = wait) {
  for (let attempt = 0; attempt < 3 && current(); attempt++) {
    try {
      const value = await fetch()
      return current() ? value : undefined
    } catch (error) {
      if (!current()) return undefined
      const status = error?.response?.status
      const temporary = !status || [408, 502, 503, 504].includes(status)
      if (!temporary || attempt === 2) throw error
      await sleep(1500 * (attempt + 1))
    }
  }
}
