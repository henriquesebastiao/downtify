import { describe, expect, it } from 'vitest'

import { songDownloadState } from '../lib/downloadState'

const item = (state) => ({ state })

describe('songDownloadState', () => {
  it('shows a queued, active or failed job whatever the library holds', () => {
    for (const state of ['queued', 'active', 'failed']) {
      expect(songDownloadState(item(state), false)).toBe(state)
      expect(songDownloadState(item(state), true)).toBe(state)
    }
  })

  it('shows a downloaded job as downloaded only while the file is there', () => {
    expect(songDownloadState(item('done'), true)).toBe('done')
    // A finished row outlives its file: deleting the track from the
    // library must leave it downloadable again.
    expect(songDownloadState(item('done'), false)).toBe('new')
  })

  it('falls back to the library when there is no queue row', () => {
    expect(songDownloadState(null, true)).toBe('library')
    expect(songDownloadState(null, false)).toBe('new')
  })
})
