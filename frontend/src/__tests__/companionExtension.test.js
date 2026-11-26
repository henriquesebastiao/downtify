import { describe, expect, it } from 'vitest'
import {
  captureFromRequest,
  cleanAddress,
  jitterMs,
  originPattern,
  playlistPageUrl,
  queryFromRequest,
  readPlaylist,
  ReadError,
  spotifyHeaders,
  whoAmI,
} from '../../../downtify/companion_extension/lib.js'

const HASH = 'a'.repeat(64)
const OTHER = 'b'.repeat(64)

function page(items, total, name = 'Sad Mix') {
  return {
    status: 200,
    json: {
      data: {
        playlistV2: {
          __typename: 'Playlist',
          name,
          content: { items, totalCount: total },
        },
      },
    },
  }
}

describe('companion: what the web player sends', () => {
  it('takes the token from the player tab only', () => {
    const headers = [
      { name: 'Authorization', value: 'Bearer abc' },
      { name: 'client-token', value: 'ct' },
      { name: 'spotify-app-version', value: '1.2.3' },
    ]
    expect(captureFromRequest({ tabId: 4, requestHeaders: headers })).toEqual({
      token: 'abc',
      clientToken: 'ct',
      appVersion: '1.2.3',
    })
    // The extension's own requests come from no tab.
    expect(captureFromRequest({ tabId: -1, requestHeaders: headers })).toBe(
      null
    )
    expect(captureFromRequest({ tabId: 4, requestHeaders: [] })).toBe(null)
  })

  it('reads the playlist query from a GET or a POST', () => {
    const get = new URL('https://api-partner.spotify.com/pathfinder/v1/query')
    get.searchParams.set('operationName', 'fetchPlaylist')
    get.searchParams.set(
      'extensions',
      JSON.stringify({ persistedQuery: { sha256Hash: HASH } })
    )
    expect(queryFromRequest({ tabId: 1, url: String(get) })).toEqual({
      operation: 'fetchPlaylist',
      hash: HASH,
    })
    const body = JSON.stringify({
      operationName: 'fetchPlaylist',
      extensions: { persistedQuery: { sha256Hash: OTHER } },
    })
    expect(
      queryFromRequest({
        tabId: 1,
        url: 'https://api-partner.spotify.com/pathfinder/v2/query',
        requestBody: { raw: [{ bytes: new TextEncoder().encode(body) }] },
      })
    ).toEqual({ operation: 'fetchPlaylist', hash: OTHER })
    expect(queryFromRequest({ tabId: 1, url: 'not a url' })).toBe(null)
  })
})

describe('companion: reading a playlist', () => {
  it('asks page by page with a pause between pages', async () => {
    const asked = []
    let pauses = 0
    const result = await readPlaylist({
      get: async (url) => {
        const vars = JSON.parse(new URL(url).searchParams.get('variables'))
        asked.push(vars.offset)
        return vars.offset === 0 ? page([1, 2], 3) : page([3], 3)
      },
      playlistId: 'x',
      hashes: [HASH],
      pageSize: 2,
      pause: async () => {
        pauses += 1
      },
    })
    expect(result).toEqual({ name: 'Sad Mix', items: [1, 2, 3] })
    expect(asked).toEqual([0, 2])
    expect(pauses).toBe(1)
  })

  it('tries the player’s own query when Spotify forgot ours', async () => {
    const used = []
    const result = await readPlaylist({
      get: async (url) => {
        const ext = JSON.parse(new URL(url).searchParams.get('extensions'))
        used.push(ext.persistedQuery.sha256Hash)
        if (ext.persistedQuery.sha256Hash === HASH) {
          return {
            status: 200,
            json: { errors: [{ message: 'PersistedQueryNotFound' }] },
          }
        }
        return page([1], 1)
      },
      playlistId: 'x',
      hashes: [HASH, OTHER, ''],
    })
    expect(result.items).toEqual([1])
    expect(used).toEqual([HASH, OTHER])
  })

  it('says why it failed', async () => {
    const fail = (status) =>
      readPlaylist({
        get: async () => ({ status, json: null }),
        playlistId: 'x',
        hashes: [HASH],
      }).catch((err) => err)
    expect((await fail(401)).code).toBe('signed_out')
    expect((await fail(429)).code).toBe('rate_limited')
    expect((await fail(500)).code).toBe('failed')
    const missing = await readPlaylist({
      get: async () => ({
        status: 200,
        json: { data: { playlistV2: { __typename: 'NotFound' } } },
      }),
      playlistId: 'x',
      hashes: [HASH],
    }).catch((err) => err)
    expect(missing).toBeInstanceOf(ReadError)
    expect(missing.code).toBe('not_found')
  })

  it('sends the player’s headers', () => {
    expect(
      spotifyHeaders({ token: 't', clientToken: 'c', appVersion: '' })
    ).toEqual({
      Accept: 'application/json',
      Authorization: 'Bearer t',
      'app-platform': 'WebPlayer',
      'client-token': 'c',
    })
    const url = new URL(playlistPageUrl('abc', 100, 50, HASH))
    expect(JSON.parse(url.searchParams.get('variables'))).toMatchObject({
      uri: 'spotify:playlist:abc',
      offset: 100,
      limit: 50,
    })
  })
})

describe('companion: who is signed in', () => {
  const profile = (me) => async () => ({ status: 200, json: { data: { me } } })

  it('asks the web player’s own account query', async () => {
    const asked = []
    const result = await whoAmI(async (url) => {
      asked.push(new URL(url).searchParams.get('operationName'))
      return {
        status: 200,
        json: {
          data: {
            me: {
              profile: {
                uri: 'spotify:user:me1',
                username: 'me1',
                name: 'Shiv',
              },
            },
          },
        },
      }
    })
    expect(result).toEqual({
      status: 'ready',
      account: { id: 'me1', name: 'Shiv' },
    })
    expect(asked).toEqual(['profileAttributes'])
  })

  it('knows signed out and trouble apart', async () => {
    expect(await whoAmI(profile({ profile: null }))).toEqual({
      status: 'signed_out',
    })
    expect(await whoAmI(profile(null))).toEqual({ status: 'signed_out' })
    expect(await whoAmI(async () => ({ status: 401 }))).toEqual({
      status: 'signed_out',
    })
    expect((await whoAmI(async () => ({ status: 429 }))).status).toBe('error')
  })

  it('tries the next query when Spotify forgot one', async () => {
    const used = []
    const result = await whoAmI(
      async (url) => {
        const ext = JSON.parse(new URL(url).searchParams.get('extensions'))
        used.push(ext.persistedQuery.sha256Hash)
        return used.length === 1
          ? {
              status: 200,
              json: { errors: [{ message: 'PersistedQueryNotFound' }] },
            }
          : {
              status: 200,
              json: { data: { me: { profile: { username: 'u', name: 'U' } } } },
            }
      },
      [HASH, OTHER]
    )
    expect(result.status).toBe('ready')
    expect(used).toEqual([HASH, OTHER])
  })
})

describe('companion: small helpers', () => {
  it('cleans addresses and makes permission patterns', () => {
    expect(cleanAddress(' http://192.168.1.5:8000/ ')).toBe(
      'http://192.168.1.5:8000'
    )
    expect(cleanAddress('ftp://x')).toBe('')
    expect(originPattern('https://music.example/sub')).toBe(
      'https://music.example/*'
    )
  })

  it('jitters within the range', () => {
    expect(jitterMs(1.5, 4, () => 0)).toBe(1500)
    expect(jitterMs(1.5, 4, () => 1)).toBe(4000)
  })
})
