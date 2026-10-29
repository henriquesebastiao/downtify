import { beforeEach, describe, expect, it, vi } from 'vitest'
import { isArtistLink, useArtistWatch } from '../model/artistWatch'
import monitorAPI from '../model/monitor'

vi.mock('../model/monitor', () => ({
  default: { addMonitoredPlaylist: vi.fn(), resolveArtistSuggestion: vi.fn() },
}))
const CHANNEL = 'https://music.youtube.com/channel/UCabcdefghijklmnopqrstuv'
const OTHER = 'https://music.youtube.com/channel/UCvutsrqponmlkjihgfedcba'
const SPOTIFY = 'https://open.spotify.com/artist/0TnOYISbd1XYRBk9myaseg'
const DAILY_NEW_ONLY = [
  1440,
  { new_only: true, release_types: ['album', 'single', 'ep'] },
]

function resolvesTo(data) {
  monitorAPI.resolveArtistSuggestion.mockResolvedValueOnce({ data })
}

beforeEach(() => vi.resetAllMocks())

describe('watch artist from the library', () => {
  it('follows the one artist with that exact name, new releases daily', async () => {
    resolvesTo({ url: CHANNEL, candidates: [] })
    const state = useArtistWatch()
    expect(await state.follow('Nirvana')).toBe(true)
    expect(monitorAPI.resolveArtistSuggestion).toHaveBeenCalledWith('Nirvana')
    expect(monitorAPI.addMonitoredPlaylist).toHaveBeenCalledWith(
      CHANNEL,
      ...DAILY_NEW_ONLY
    )
    expect(state.followed.value).toBe(true)
    expect(state.open.value).toBe(false)
    expect(await state.follow('Nirvana')).toBe(false)
    expect(monitorAPI.addMonitoredPlaylist).toHaveBeenCalledTimes(1)
  })

  it('lets namesakes be told apart instead of guessing one', async () => {
    const candidates = [
      { name: 'Genesis', artist_id: 'a', url: CHANNEL },
      { name: 'Genesis', artist_id: 'b', url: OTHER },
    ]
    resolvesTo({ url: null, candidates })
    const state = useArtistWatch()
    expect(await state.follow('Genesis')).toBe(false)
    expect(state.open.value).toBe(true)
    expect(state.candidates.value).toEqual(candidates)
    expect(monitorAPI.addMonitoredPlaylist).not.toHaveBeenCalled()
    state.newOnly.value = false
    state.releaseTypes.value = ['album']
    expect(await state.choose(candidates[1])).toBe(true)
    expect(monitorAPI.addMonitoredPlaylist).toHaveBeenCalledWith(OTHER, 1440, {
      new_only: false,
      release_types: ['album'],
    })
    expect(state.open.value).toBe(false)
  })

  it('asks for a link when the lookup fails', async () => {
    monitorAPI.resolveArtistSuggestion.mockRejectedValueOnce(new Error('down'))
    const state = useArtistWatch()
    expect(await state.follow('Someone')).toBe(false)
    expect(state.lookupFailed.value).toBe(true)
    expect(state.open.value).toBe(true)
    state.url.value = SPOTIFY.replace('.com/', '.com/intl-pt/')
    expect(await state.submit()).toBe(true)
    expect(monitorAPI.addMonitoredPlaylist).toHaveBeenCalledWith(
      SPOTIFY,
      ...DAILY_NEW_ONLY
    )
  })

  it('shows why the server refused, and allows another try', async () => {
    resolvesTo({ url: CHANNEL, candidates: [] })
    monitorAPI.addMonitoredPlaylist.mockRejectedValueOnce({
      response: { status: 409, data: { detail: 'Already watched' } },
    })
    const state = useArtistWatch()
    expect(await state.follow('Nirvana')).toBe(false)
    expect(state.followed.value).toBe(false)
    expect(state.open.value).toBe(true)
    expect(state.error.value).toBe('Already watched')
    state.url.value = OTHER
    expect(await state.submit()).toBe(true)
    expect(state.error.value).toBe('')
  })

  it('accepts only Spotify and YouTube Music artist links', async () => {
    expect(isArtistLink(SPOTIFY)).toBe(true)
    expect(isArtistLink(CHANNEL)).toBe(true)
    const state = useArtistWatch()
    for (const url of [
      'https://open.spotify.com/playlist/0TnOYISbd1XYRBk9myaseg',
      'https://www.deezer.com/artist/123',
      'Nirvana',
      '',
    ]) {
      expect(isArtistLink(url)).toBe(false)
      state.url.value = url
      expect(await state.submit()).toBe(false)
    }
    expect(monitorAPI.addMonitoredPlaylist).not.toHaveBeenCalled()
  })

  it('ignores clicks while a watch is being added', async () => {
    let done
    resolvesTo({ url: CHANNEL, candidates: [] })
    monitorAPI.addMonitoredPlaylist.mockReturnValueOnce(
      new Promise((resolve) => {
        done = resolve
      })
    )
    const state = useArtistWatch()
    const pending = state.follow('Nirvana')
    expect(await state.follow('Nirvana')).toBe(false)
    await vi.waitFor(() =>
      expect(monitorAPI.addMonitoredPlaylist).toHaveBeenCalled()
    )
    expect(await state.choose({ url: OTHER })).toBe(false)
    done({ data: {} })
    expect(await pending).toBe(true)
    expect(monitorAPI.addMonitoredPlaylist).toHaveBeenCalledTimes(1)
  })

  it('drops an answer that arrives after moving to another artist', async () => {
    let answer
    monitorAPI.resolveArtistSuggestion.mockReturnValueOnce(
      new Promise((resolve) => {
        answer = resolve
      })
    )
    const state = useArtistWatch()
    const pending = state.follow('First')
    state.reset()
    answer({ data: { url: CHANNEL, candidates: [] } })
    expect(await pending).toBe(false)
    expect(monitorAPI.addMonitoredPlaylist).not.toHaveBeenCalled()
    expect(state.busy.value).toBe(false)
  })
})
