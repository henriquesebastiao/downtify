import { afterEach, expect, it, vi } from 'vitest'
import { nextTick } from 'vue'

vi.mock('/src/model/musicAI', async () => {
  const { ref } = await import('vue')
  return { musicAI: { account: ref(1), capabilities: ref({ features: { personalization: true }, profile_revision: 0 }), refresh: vi.fn(), listen: vi.fn().mockResolvedValue({}) } }
})
import { musicAI } from '../model/musicAI'
import { attachMusicAiListening } from '../model/musicAiListening'

afterEach(() => vi.restoreAllMocks())

it('counts repeated audible DJ occurrences separately without inventing manual skips', () => {
  let now = 0, occurrence = 0
  vi.spyOn(performance, 'now').mockImplementation(() => now)
  const audio = new EventTarget()
  Object.assign(audio, {currentTime:0,paused:false,seeking:false})
  musicAI.listen.mockClear(); musicAI.account.value = 1
  musicAI.capabilities.value = { features:{personalization:true},profile_revision:0 }
  const dispose = attachMusicAiListening(audio, () => ({file:'synthetic.flac',djSession:'local',djOccurrence:occurrence}))
  audio.dispatchEvent(new Event('playing'))
  now = 1000; audio.currentTime = 1; audio.dispatchEvent(new Event('timeupdate'))
  occurrence = 1
  now = 2000; audio.currentTime = 2; audio.dispatchEvent(new Event('timeupdate'))
  now = 3000; audio.currentTime = 3; audio.dispatchEvent(new Event('pause'))
  const calls = musicAI.listen.mock.calls.map(([event]) => event)
  expect(calls.map(event => event.outcome)).toEqual(['pause','pause'])
  expect(calls[0].event_id).not.toBe(calls[1].event_id)
  expect(calls.map(event => event.seconds)).toEqual([1,1])
  dispose()
})

it('reports actual time, distinguishes errors, and removes all hooks on disposal', async () => {
  let now = 0
  vi.spyOn(performance, 'now').mockImplementation(() => now)
  const audio = new EventTarget()
  audio.currentTime = 0
  audio.paused = false
  audio.seeking = false
  musicAI.listen.mockClear()
  musicAI.account.value = 1
  musicAI.capabilities.value = { features: { personalization: true }, profile_revision: 0 }
  const dispose = attachMusicAiListening(audio, () => ({ file: 'synthetic.flac' }))
  audio.dispatchEvent(new Event('playing'))
  for (let i = 1; i <= 21; i++) {
    now = i * 1000
    audio.currentTime = i
    audio.dispatchEvent(new Event('timeupdate'))
  }
  audio.dispatchEvent(new Event('error'))
  audio.dispatchEvent(new Event('pause'))
  expect(musicAI.listen.mock.calls.map(([event]) => event.outcome)).toEqual(['pause', 'error'])
  expect(musicAI.listen.mock.calls[0][0].seconds).toBe(20)
  expect(musicAI.listen.mock.calls[1][0].sequence).toBe(2)
  dispose()
  audio.dispatchEvent(new Event('loadstart'))
  audio.dispatchEvent(new Event('playing'))
  audio.dispatchEvent(new Event('pause'))
  musicAI.account.value = 2
  await nextTick()
  expect(musicAI.listen).toHaveBeenCalledTimes(2)
})

it('keeps the completed outcome through a late pause and allows replay', () => {
  let now = 0
  vi.spyOn(performance, 'now').mockImplementation(() => now)
  const audio = new EventTarget()
  Object.assign(audio, { currentTime: 0, paused: false, seeking: false })
  musicAI.listen.mockClear()
  musicAI.account.value = 1
  musicAI.capabilities.value = { features: { personalization: true }, profile_revision: 0 }
  const dispose = attachMusicAiListening(audio, () => ({ file: 'synthetic.flac' }))
  audio.dispatchEvent(new Event('playing'))
  now = 1000
  audio.currentTime = 1
  audio.dispatchEvent(new Event('ended'))
  audio.paused = true
  audio.dispatchEvent(new Event('pause'))
  expect(musicAI.listen.mock.calls.map(([event]) => event.outcome)).toEqual(['complete'])
  const completed = musicAI.listen.mock.calls[0][0].event_id
  audio.currentTime = 0
  audio.paused = false
  audio.dispatchEvent(new Event('playing'))
  now = 2000
  audio.currentTime = 1
  audio.dispatchEvent(new Event('timeupdate'))
  audio.paused = true
  audio.dispatchEvent(new Event('pause'))
  expect(musicAI.listen.mock.calls[1][0].event_id).not.toBe(completed)
  expect(musicAI.listen.mock.calls[1][0].seconds).toBe(1)
  dispose()
})
