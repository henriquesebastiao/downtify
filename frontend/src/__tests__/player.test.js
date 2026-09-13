import { beforeAll, describe, expect, it } from 'vitest'

// player.js reads localStorage at module load time (to restore the
// saved volume), which doesn't exist in Vitest's default (non-browser)
// environment — stub it before dynamically importing the module,
// rather than adding a jsdom/happy-dom dependency just for this test.
let trackInfoFromFile

beforeAll(async () => {
  globalThis.localStorage = {
    getItem: () => null,
    setItem: () => {},
  }
  ;({ trackInfoFromFile } = await import('../model/player.js'))
})

describe('trackInfoFromFile', () => {
  it('parses "Artist - Title" for a file at the library root', () => {
    const track = trackInfoFromFile('The Night Owls - Do I Still Recall.mp3')
    expect(track.artist).toBe('The Night Owls')
    expect(track.title).toBe('Do I Still Recall')
  })

  it('does not leak the playlist folder into the artist', () => {
    // The bug: parsing the whole path found the first " - " in
    // "My Playlist/Artist - Title.mp3" *before* the real one, so the
    // artist came out as "My Playlist/Artist" instead of "Artist".
    const track = trackInfoFromFile(
      'My Playlist/The Night Owls - Do I Still Recall.mp3'
    )
    expect(track.artist).toBe('The Night Owls')
    expect(track.title).toBe('Do I Still Recall')
  })

  it('strips a nested Artist/Album organize-by-* folder too', () => {
    const track = trackInfoFromFile(
      'The Night Owls/Some Album/The Night Owls - Do I Still Recall.mp3'
    )
    expect(track.artist).toBe('The Night Owls')
    expect(track.title).toBe('Do I Still Recall')
  })

  it('is unaffected by a folder name that itself contains " - "', () => {
    const track = trackInfoFromFile('My Playlist - 2026/Artist - Title.mp3')
    expect(track.artist).toBe('Artist')
    expect(track.title).toBe('Title')
  })

  it('only splits on the first " - ", keeping the rest in the title', () => {
    const track = trackInfoFromFile('Artist - Title - Remix.mp3')
    expect(track.artist).toBe('Artist')
    expect(track.title).toBe('Title - Remix')
  })

  it('falls back to the whole basename as the title when there is no " - "', () => {
    const track = trackInfoFromFile('My Playlist/Standalone Track.mp3')
    expect(track.artist).toBe('')
    expect(track.title).toBe('Standalone Track')
  })

  it('keeps the full relative path (with folder) in the file field', () => {
    const track = trackInfoFromFile('My Playlist/Artist - Title.mp3')
    expect(track.file).toBe('My Playlist/Artist - Title.mp3')
  })
})
