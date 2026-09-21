import { describe, expect, it } from 'vitest'
import {
  episodeToTrack,
  hasResumePosition,
  isKeepAll,
  isNearlyDone,
  sortEpisodesByDate,
} from '../lib/podcasts.js'

const show = { id: 7, name: 'Radiolab' }

describe('episodeToTrack', () => {
  it('builds a player-ready track from an episode and its show', () => {
    const track = episodeToTrack(
      {
        id: 42,
        show_id: 7,
        filename: 'Podcasts/Radiolab/2026-09-18 - The Sweetest Thing.mp3',
        title: 'The Sweetest Thing',
        episode_number: 712,
        published_at: '2026-09-18T14:00:00+00:00',
        duration_seconds: 1862,
      },
      show
    )
    expect(track.title).toBe('The Sweetest Thing')
    expect(track.artist).toBe('Radiolab')
    expect(track.album).toBe('Radiolab')
    expect(track.trackNumber).toBe(712)
    expect(track.year).toBe('2026')
    expect(track.duration).toBe(1862)
    expect(track.format).toBe('MP3')
    expect(track.isPodcast).toBe(true)
    expect(track.podcastEpisodeId).toBe(42)
    expect(track.podcastShowId).toBe(7)
    expect(track.url).toBe(
      '/downloads/Podcasts/Radiolab/2026-09-18%20-%20The%20Sweetest%20Thing.mp3'
    )
  })

  it('falls back to empty strings when the show or fields are missing', () => {
    const track = episodeToTrack({ title: '', filename: '' }, null)
    expect(track.title).toBe('Untitled episode')
    expect(track.artist).toBe('')
    expect(track.duration).toBe(0)
  })
})

describe('isKeepAll', () => {
  it('is true only for a retention of zero', () => {
    expect(isKeepAll(0)).toBe(true)
    expect(isKeepAll(undefined)).toBe(true)
    expect(isKeepAll(5)).toBe(false)
  })
})

describe('hasResumePosition', () => {
  it('is false right at the start', () => {
    expect(
      hasResumePosition({ position_seconds: 2, duration_seconds: 600 })
    ).toBe(false)
  })

  it('is true partway through', () => {
    expect(
      hasResumePosition({ position_seconds: 120, duration_seconds: 600 })
    ).toBe(true)
  })

  it('is false once basically finished', () => {
    expect(
      hasResumePosition({ position_seconds: 598, duration_seconds: 600 })
    ).toBe(false)
  })

  it('survives a missing episode', () => {
    expect(hasResumePosition(null)).toBe(false)
  })
})

describe('isNearlyDone', () => {
  it('is false with no known duration', () => {
    expect(isNearlyDone(100, 0)).toBe(false)
  })

  it('is false with plenty of time left', () => {
    expect(isNearlyDone(100, 600)).toBe(false)
  })

  it('is true within the last few seconds', () => {
    expect(isNearlyDone(598, 600)).toBe(true)
  })
})

describe('sortEpisodesByDate', () => {
  it('orders newest published first', () => {
    const episodes = [
      { title: 'Old', published_at: '2026-01-01T00:00:00Z' },
      { title: 'New', published_at: '2026-09-01T00:00:00Z' },
      { title: 'Middle', published_at: '2026-05-01T00:00:00Z' },
    ]
    expect(sortEpisodesByDate(episodes).map((e) => e.title)).toEqual([
      'New',
      'Middle',
      'Old',
    ])
  })

  it('does not mutate the input array', () => {
    const episodes = [
      { title: 'A', published_at: '2026-01-01T00:00:00Z' },
      { title: 'B', published_at: '2026-02-01T00:00:00Z' },
    ]
    const copy = [...episodes]
    sortEpisodesByDate(episodes)
    expect(episodes).toEqual(copy)
  })

  it('survives a missing list', () => {
    expect(sortEpisodesByDate(undefined)).toEqual([])
  })
})
