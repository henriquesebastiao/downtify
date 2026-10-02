import { afterEach, describe, expect, it } from 'vitest'

const KEY = 'downtify-recent-contexts'
const store = {}
globalThis.localStorage = {
  getItem: (key) => (key in store ? store[key] : null),
  setItem: (key, value) => {
    store[key] = String(value)
  },
  removeItem: (key) => {
    delete store[key]
  },
}

const { useHistory } = await import('../model/history')

describe('history', () => {
  afterEach(() => {
    localStorage.removeItem(KEY)
    useHistory().recent.value = []
  })

  it('rewrites a renamed playlist in Jump back in', () => {
    const history = useHistory()
    history.remember({
      type: 'playlist',
      title: 'tesdte',
      route: { name: 'Playlist', query: { name: 'tesdte' } },
      cover: '/cover?file=a.mp3',
    })
    history.retitlePlaylist('tesdte', 'Late night')
    expect(history.recent.value).toHaveLength(1)
    expect(history.recent.value[0]).toMatchObject({
      title: 'Late night',
      route: { name: 'Playlist', query: { name: 'Late night' } },
    })
    const stored = JSON.parse(localStorage.getItem(KEY))
    expect(stored[0].title).toBe('Late night')
  })
})
