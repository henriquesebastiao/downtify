import { beforeEach, expect, it, vi } from 'vitest'

const api = vi.hoisted(() => ({
  onMessage: vi.fn(),
  getLibrarySummary: vi.fn(),
  listPlaylists: vi.fn(),
  getPlaylistBatches: vi.fn(),
  deleteLibraryPlaylist: vi.fn(),
}))
vi.mock('../model/api', () => ({ default: api }))
vi.mock('../model/player', () => ({
  usePlayer: () => ({ forgetFiles() {}, refreshTracks() {} }),
}))
vi.mock('../i18n', () => ({ useI18n: () => ({ t: (key) => key }) }))

beforeEach(() => {
  vi.resetModules()
  vi.clearAllMocks()
  api.getLibrarySummary.mockResolvedValue({ data: {} })
  api.getPlaylistBatches.mockResolvedValue({ data: { playlists: [] } })
  api.deleteLibraryPlaylist.mockResolvedValue({ data: { files: [] } })
})

it('fetches after a delete even when a pre-delete listing is in flight', async () => {
  let finishOldListing
  api.listPlaylists.mockImplementationOnce(
    () =>
      new Promise((resolve) => {
        finishOldListing = resolve
      })
  )
  api.listPlaylists.mockResolvedValue({ data: [] })
  const { useLibrary } = await import('../model/library.js')
  const library = useLibrary()
  const oldLoad = library.load()
  const removal = library.deletePlaylist({ name: 'Mix', manual: true })
  await Promise.resolve()
  finishOldListing({
    data: [{ name: 'Mix', files: ['one.mp3'], count: 1, manual: true }],
  })
  await oldLoad
  await removal
  expect(api.listPlaylists).toHaveBeenCalledTimes(2)
  expect(library.playlists.value).toEqual([])
})
