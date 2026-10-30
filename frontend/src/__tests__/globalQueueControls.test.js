import { test } from 'vitest'
import assert from 'node:assert/strict'
import { createQueueControl } from '../model/globalQueueControls.js'

const status = (paused = false, active = 0) => ({
  paused,
  active,
  can_control: true,
  global_pause_supported: true,
})
const response = (data, code = 200) => ({
  ok: code < 400,
  status: code,
  json: async () => data,
})
const base = 'https://example.test/api/queue/'

test('reads actual state after a successful pause', async () => {
  const calls = []
  const replies = [
    response(status()),
    response({ paused: true }),
    response(status(true, 1)),
  ]
  const client = createQueueControl(async (url, options) => {
    calls.push([url.pathname, options.method])
    return replies.shift()
  }, base)
  await client.refresh()
  await client.change(true)
  assert.deepEqual(calls, [
    ['/api/queue/state', 'GET'],
    ['/api/queue/pause', 'POST'],
    ['/api/queue/state', 'GET'],
  ])
  assert.equal(client.state.status.paused, true)
  assert.equal(client.state.status.active, 1)
  assert.equal(client.state.busy, false)
})

test('403 never pretends to have paused', async () => {
  const replies = [response(status()), response({}, 403)]
  const client = createQueueControl(async () => replies.shift(), base)
  await client.refresh()
  await client.change(true)
  assert.equal(client.state.status.paused, false)
  assert.equal(client.state.error, 403)
  assert.equal(client.state.busy, false)
})

test('a lost confirmation is recovered by reading, without another POST', async () => {
  let posts = 0
  const replies = [
    response(status()),
    response({}),
    response({}, 503),
    response(status(true)),
  ]
  const client = createQueueControl(async (url, options) => {
    if (options.method === 'POST') posts++
    return replies.shift()
  }, base)
  await client.refresh()
  await client.change(true)
  assert.equal(client.state.status.paused, false)
  assert.equal(client.state.error, 503)
  await client.refresh()
  assert.equal(client.state.status.paused, true)
  assert.equal(client.state.error, null)
  assert.equal(posts, 1)
})

test('unsupported servers and non-admins cannot be controlled', async () => {
  let posts = 0
  const client = createQueueControl(async (url, options) => {
    if (options.method === 'POST') posts++
    return response({ ...status(), can_control: false })
  }, base)
  await client.refresh()
  await client.change(true)
  assert.equal(posts, 0)
  client.state.status = { ...status(), global_pause_supported: false }
  await client.change(true)
  assert.equal(posts, 0)
})

test('a stale GET cannot overwrite a confirmed change', async () => {
  let resolveOld
  let call = 0
  const client = createQueueControl(async () => {
    call++
    if (call === 2)
      return new Promise((resolve) => {
        resolveOld = resolve
      })
    return response(call === 1 ? status() : status(true))
  }, base)
  await client.refresh()
  const old = client.refresh()
  await client.change(true)
  resolveOld(response(status()))
  await old
  assert.equal(client.state.status.paused, true)
})

test('network failure and malformed state preserve the last known state', async () => {
  let call = 0
  const client = createQueueControl(async () => {
    if (++call === 1) return response(status())
    if (call === 2) throw new Error('offline')
    return response({ paused: 'false' })
  }, base)
  await client.refresh()
  await client.refresh()
  assert.equal(client.state.status.paused, false)
  assert.equal(client.state.error, 'network')
  await client.refresh()
  assert.equal(client.state.status.paused, false)
  assert.equal(client.state.error, 'network')
})
