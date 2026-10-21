import { describe, expect, it } from 'vitest'

import { buildPlaylists, splitPlaylists } from '../lib/library.js'
import en from '../i18n/locales/en.js'

const row = (name, extra = {}) => ({
  name,
  files: [],
  count: 0,
  added: 1,
  cover: '',
  liked: false,
  manual: false,
  ...extra,
})
const build = (rows) => buildPlaylists(rows, new Map())

describe('buildPlaylists sharing fields', () => {
  it('treats a row without them as the user’s own, private playlist', () => {
    const [playlist] = build([row('Mine')])
    expect(playlist).toMatchObject({
      mine: true,
      owner: '',
      visibility: 'private',
      sharedWith: [],
      followed: false,
      sharedWithMe: false,
      isNew: false,
    })
  })

  it('carries what the server says about someone else’s playlist', () => {
    const [playlist] = build([
      row('Road', {
        mine: false,
        owner: 'ana',
        visibility: 'shared',
        shared_with_me: true,
        new: true,
      }),
    ])
    expect(playlist).toMatchObject({
      mine: false,
      owner: 'ana',
      visibility: 'shared',
      sharedWithMe: true,
      isNew: true,
    })
  })

  it('lists who the user shared their own playlist with', () => {
    const [playlist] = build([
      row('Mix', { visibility: 'shared', shared_with: ['bob', 'cyd'] }),
    ])
    expect(playlist.sharedWith).toEqual(['bob', 'cyd'])
  })
})

describe('splitPlaylists', () => {
  const lists = build([
    row('Zed', { mine: false, owner: 'bob', visibility: 'public' }),
    row('Mine'),
    row('Beta', { mine: false, owner: 'ana', visibility: 'public' }),
    row('Alpha', { mine: false, owner: 'ana', visibility: 'public' }),
    row('Old', {
      mine: false,
      owner: 'ana',
      visibility: 'shared',
      shared_with_me: true,
    }),
    row('Fresh', {
      mine: false,
      owner: 'zoe',
      visibility: 'shared',
      shared_with_me: true,
      new: true,
    }),
    row('Followed', {
      mine: false,
      owner: 'cyd',
      visibility: 'public',
      followed: true,
    }),
  ])
  const names = (list) => list.map((playlist) => playlist.name)

  it('never mixes other people’s playlists into the user’s own', () => {
    const { own, shared, public: publicOnes } = splitPlaylists(lists)
    expect(names(own)).toEqual(['Mine'])
    expect(names(shared)).toEqual(['Fresh', 'Old'])
    expect(names(publicOnes)).toHaveLength(4)
  })

  it('puts new shares first, then sorts public ones by owner and name', () => {
    const { shared, public: publicOnes } = splitPlaylists(lists)
    expect(shared[0].isNew).toBe(true)
    expect(names(publicOnes)).toEqual(['Alpha', 'Beta', 'Zed', 'Followed'])
  })
})

describe('sharing labels', () => {
  it('has the text the sharing UI asks for', () => {
    for (const key of [
      'title',
      'private',
      'shared',
      'public',
      'follow',
      'unfollow',
      'saveCopy',
      'detach',
      'detachBody',
      'sharedWithMe',
      'publicPlaylists',
    ]) {
      expect(en.sharing[key], key).toBeTruthy()
    }
    for (const visibility of ['private', 'shared', 'public']) {
      expect(en.sharing.saved[visibility], visibility).toBeTruthy()
    }
  })
})
