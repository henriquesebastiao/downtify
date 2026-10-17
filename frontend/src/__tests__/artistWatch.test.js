import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useArtistWatch } from '../model/artistWatch'
import monitorAPI from '../model/monitor'

vi.mock('../model/monitor', () => ({
  default: { addMonitoredPlaylist: vi.fn() },
}))
const ID = '0TnOYISbd1XYRBk9myaseg'

beforeEach(() => vi.resetAllMocks())

describe('quick artist watch', () => {
  it('asks for a link instead of guessing an artist from a name', async () => {
    const state = useArtistWatch()
    expect(await state.follow('')).toBe(false)
    expect(state.open.value).toBe(true)
    expect(monitorAPI.addMonitoredPlaylist).not.toHaveBeenCalled()
  })
  it('follows a known identity, future releases only, with a daily check', async () => {
    const state = useArtistWatch()
    expect(await state.follow(ID)).toBe(true)
    expect(monitorAPI.addMonitoredPlaylist).toHaveBeenCalledWith(
      `https://open.spotify.com/artist/${ID}`,
      1440,
      { new_only: true, release_types: ['album', 'single', 'ep'] }
    )
    expect(state.followed.value).toBe(true)
    expect(await state.follow(ID)).toBe(false)
    expect(monitorAPI.addMonitoredPlaylist).toHaveBeenCalledTimes(1)
  })
  it('allows manual retry and release filters after resolution failure', async () => {
    monitorAPI.addMonitoredPlaylist.mockRejectedValueOnce({
      response: { data: { detail: 'Artist unavailable' } },
    })
    const state = useArtistWatch()
    expect(await state.follow(ID)).toBe(false)
    expect(state.followed.value).toBe(false)
    expect(state.open.value).toBe(true)
    expect(state.error.value).toBe('Artist unavailable')
    state.newOnly.value = false
    state.releaseTypes.value = ['album']
    expect(await state.submit()).toBe(true)
    expect(monitorAPI.addMonitoredPlaylist).toHaveBeenLastCalledWith(
      state.url.value,
      1440,
      { new_only: false, release_types: ['album'] }
    )
  })
  it('rejects playlist links and Deezer artist links', async () => {
    const state = useArtistWatch()
    for (const url of [
      `https://open.spotify.com/playlist/${ID}`,
      'https://www.deezer.com/artist/123',
      '',
    ]) {
      state.url.value = url
      expect(await state.submit()).toBe(false)
    }
    expect(monitorAPI.addMonitoredPlaylist).not.toHaveBeenCalled()
  })
  it('prevents duplicate submissions while resolving', async () => {
    let resolve
    monitorAPI.addMonitoredPlaylist.mockReturnValueOnce(
      new Promise((done) => {
        resolve = done
      })
    )
    const state = useArtistWatch()
    const pending = state.follow(ID)
    expect(await state.follow(ID)).toBe(false)
    resolve({ data: {} })
    expect(await pending).toBe(true)
    expect(monitorAPI.addMonitoredPlaylist).toHaveBeenCalledTimes(1)
  })
})
