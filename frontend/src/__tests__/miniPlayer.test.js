import { describe, expect, it } from 'vitest'
import { miniPlayerVisibility } from '../model/miniPlayerVisibility.js'

const base = {
  enabled: true,
  hasCurrentTrack: true,
  isPlayerRoute: false,
  collapsed: false,
}

describe('miniPlayerVisibility', () => {
  it('shows the bar when a track is loaded, enabled, and not on Player', () => {
    expect(miniPlayerVisibility(base)).toEqual({
      showBar: true,
      showRestoreButton: false,
    })
  })

  it('shows the restore button instead of the bar once collapsed', () => {
    expect(miniPlayerVisibility({ ...base, collapsed: true })).toEqual({
      showBar: false,
      showRestoreButton: true,
    })
  })

  it('shows neither on the Player page itself, even if collapsed', () => {
    expect(miniPlayerVisibility({ ...base, isPlayerRoute: true })).toEqual({
      showBar: false,
      showRestoreButton: false,
    })
    expect(
      miniPlayerVisibility({
        ...base,
        isPlayerRoute: true,
        collapsed: true,
      })
    ).toEqual({ showBar: false, showRestoreButton: false })
  })

  it('shows neither when nothing is loaded', () => {
    expect(miniPlayerVisibility({ ...base, hasCurrentTrack: false })).toEqual({
      showBar: false,
      showRestoreButton: false,
    })
  })

  it('shows neither when disabled in Settings, regardless of collapsed', () => {
    expect(miniPlayerVisibility({ ...base, enabled: false })).toEqual({
      showBar: false,
      showRestoreButton: false,
    })
    expect(
      miniPlayerVisibility({ ...base, enabled: false, collapsed: true })
    ).toEqual({ showBar: false, showRestoreButton: false })
  })
})
