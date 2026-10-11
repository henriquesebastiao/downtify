import { beforeEach, describe, expect, it, vi } from 'vitest'

const { deleteDownloadsBatch } = vi.hoisted(() => ({
  deleteDownloadsBatch: vi.fn(),
}))

vi.mock('/src/model/api', () => ({
  default: {
    onMessage: () => () => {},
    deleteDownloadsBatch,
  },
}))

vi.mock('/src/model/player', () => ({
  usePlayer: () => ({ forgetFiles: () => {} }),
}))

import { useLibrary } from '../model/library.js'

describe('deleteFiles', () => {
  beforeEach(() => {
    deleteDownloadsBatch.mockReset()
  })

  it('counts a released shared file as gone from the library', async () => {
    // The server answers `{ "released": true }` with no `deleted`
    // flag when the file stays on disk for its other owners.
    deleteDownloadsBatch.mockResolvedValue({
      data: { results: { 'Shared.mp3': { released: true } } },
    })

    const { deleted, released, failed } =
      await useLibrary().deleteFiles(['Shared.mp3'])

    expect(deleteDownloadsBatch).toHaveBeenCalledWith(['Shared.mp3'])
    expect(deleted).toEqual(['Shared.mp3'])
    expect(released).toEqual(['Shared.mp3'])
    expect(failed).toBe(0)
  })

  it('counts wiped files as deleted and foreign ones as failed', async () => {
    deleteDownloadsBatch.mockResolvedValue({
      data: {
        results: {
          'Solo.mp3': { deleted: true },
          'Old.mp3': { deleted: false, error: 'Not in your library' },
        },
      },
    })

    const { deleted, released, failed } = await useLibrary().deleteFiles([
      'Solo.mp3',
      'Old.mp3',
    ])

    expect(deleted).toEqual(['Solo.mp3'])
    expect(released).toEqual([])
    expect(failed).toBe(1)
  })
})
