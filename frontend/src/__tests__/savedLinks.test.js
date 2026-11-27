import { beforeEach, describe, expect, it, vi } from 'vitest'

const api = vi.hoisted(() => ({
  getSavedLinks: vi.fn(),
  saveLink: vi.fn(),
  removeSavedLink: vi.fn(),
}))
vi.mock('/src/model/api', () => ({ default: api }))

import { classifyInput } from '../lib/input'
import {
  canSaveLink,
  savedLinkPayload,
  savedLinkSubtitle,
  withSavedLink,
  withoutSavedLink,
} from '../lib/savedLinks'
import { useSavedLinks } from '../model/savedLinks'

const SPOTIFY = 'https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M'
const DEEZER = 'https://www.deezer.com/album/302127'
const t = (key) => ({ 'link.kind.playlist': 'Playlist' })[key] || key

describe('canSaveLink', () => {
  const playlist = { kind: 'playlist', tracks: [] }

  it('offers Save on Spotify, Deezer and YouTube Music playlists and albums', () => {
    expect(canSaveLink(playlist, classifyInput(SPOTIFY))).toBe(true)
    expect(canSaveLink({ kind: 'album' }, classifyInput(DEEZER))).toBe(true)
    expect(
      canSaveLink(
        playlist,
        classifyInput('https://music.youtube.com/playlist?list=PLabcdef')
      )
    ).toBe(true)
  })

  it('leaves out songs, artists, SoundCloud and pages still loading', () => {
    const input = classifyInput(SPOTIFY)
    expect(canSaveLink({ kind: 'track' }, input)).toBe(false)
    expect(canSaveLink({ kind: 'artist' }, input)).toBe(false)
    expect(canSaveLink(null, input)).toBe(false)
    expect(
      canSaveLink(playlist, classifyInput('https://soundcloud.com/a/b'))
    ).toBe(false)
    expect(canSaveLink(playlist, classifyInput('just words'))).toBe(false)
  })
})

describe('savedLinkPayload', () => {
  it('sends the link, its name and its cover', () => {
    const details = { name: 'Hits', cover_url: 'https://i.scdn.co/a' }
    expect(savedLinkPayload(details, SPOTIFY)).toEqual({
      url: SPOTIFY,
      name: 'Hits',
      cover: 'https://i.scdn.co/a',
    })
  })

  it("falls back to the first song's cover, then to none", () => {
    const tracks = [{}, { cover_url: 'https://e.com/2.jpg' }]
    expect(savedLinkPayload({ name: '', tracks }, SPOTIFY)).toEqual({
      url: SPOTIFY,
      name: '',
      cover: 'https://e.com/2.jpg',
    })
    expect(savedLinkPayload({}, SPOTIFY).cover).toBe('')
  })
})

describe('the saved list', () => {
  const a = { url: 'a', name: 'A' }
  const b = { url: 'b', name: 'B' }

  it('puts a new link first and updates one saved in place', () => {
    expect(withSavedLink([a], b)).toEqual([b, a])
    const renamed = { url: 'a', name: 'A2' }
    expect(withSavedLink([b, a], renamed)).toEqual([b, renamed])
  })

  it('removes a link, and never mutates the list', () => {
    const list = [a, b]
    expect(withoutSavedLink(list, 'a')).toEqual([b])
    withSavedLink(list, { url: 'c' })
    expect(list).toEqual([a, b])
  })

  it('survives a missing list or link', () => {
    expect(withSavedLink(undefined, a)).toEqual([a])
    expect(withSavedLink([a], null)).toEqual([a])
    expect(withoutSavedLink(null, 'a')).toEqual([])
  })

  it('names the service and the kind under each link', () => {
    expect(savedLinkSubtitle({ source: 'spotify', kind: 'playlist' }, t)).toBe(
      'Spotify · Playlist'
    )
    expect(savedLinkSubtitle({ source: 'deezer', kind: 'album' }, t)).toBe(
      'Deezer · link.kind.album'
    )
  })
})

describe('useSavedLinks', () => {
  const saved = useSavedLinks()

  beforeEach(() => {
    vi.clearAllMocks()
    saved.links.value = []
  })

  it('loads the list and keeps it when the server is unreachable', async () => {
    api.getSavedLinks.mockResolvedValueOnce({
      data: { links: [{ url: SPOTIFY, name: 'Hits' }] },
    })
    await saved.load()
    expect(saved.links.value.map((link) => link.name)).toEqual(['Hits'])
    expect(saved.loaded.value).toBe(true)
    api.getSavedLinks.mockRejectedValueOnce(new Error('offline'))
    await saved.load()
    expect(saved.links.value).toHaveLength(1)
  })

  it('asks the server whether the open link is saved', async () => {
    api.getSavedLinks.mockResolvedValueOnce({ data: { links: [] } })
    expect(await saved.find(`${SPOTIFY}?si=x`)).toBe(null)
    expect(api.getSavedLinks).toHaveBeenCalledWith(`${SPOTIFY}?si=x`)
  })

  it('shows a saved link in the Library at once, and a removed one goes', async () => {
    const link = { url: SPOTIFY, name: 'Hits', source: 'spotify' }
    api.saveLink.mockResolvedValueOnce({ data: link })
    expect(await saved.save({ url: `${SPOTIFY}?si=x`, name: 'Hits' })).toBe(
      link
    )
    expect(saved.links.value).toEqual([link])

    // The server answers with the URL the link was stored under.
    api.removeSavedLink.mockResolvedValueOnce({
      data: { url: SPOTIFY, removed: true },
    })
    await saved.remove(`${SPOTIFY}?si=x`)
    expect(saved.links.value).toEqual([])
  })
})
