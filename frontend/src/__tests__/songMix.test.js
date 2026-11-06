import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ref } from 'vue'

const mocks = vi.hoisted(() => ({ refresh: vi.fn(), similar: vi.fn(), startMix: vi.fn(), toast: vi.fn() }))
vi.mock('../model/musicAI', () => ({ musicAI: {
  account: ref('synthetic-owner'), capabilities: ref({ features: { similarity: true } }),
  refresh: mocks.refresh, similar: mocks.similar,
} }))
vi.mock('../model/player', () => ({ usePlayer: () => ({ currentTrack: current, startMix: mocks.startMix }) }))
vi.mock('../model/ui', () => ({ useUi: () => ({ toast: mocks.toast }) }))
vi.mock('/src/lib/library', () => ({ normalizeTrack: row => row }))
const current = ref(null)
const { musicAI } = await import('../model/musicAI')
const { startSongMix } = await import('../model/songMix')
const seed = { file: 'synthetic/version-b.flac', artist: 'Synthetic', title: 'Title' }

beforeEach(() => {
  vi.clearAllMocks()
  current.value = null
  musicAI.account.value = 'synthetic-owner'
  musicAI.capabilities.value = { features: { similarity: true } }
  mocks.refresh.mockResolvedValue()
  mocks.similar.mockResolvedValue({ data: { tracks: [
    { file: seed.file }, { file: 'synthetic/next.flac', name: 'Next' },
    { file: 'synthetic/next.flac', name: 'Duplicate' }, { url: 'https://fixture.test' },
  ] } })
})

describe('seeded local mix', () => {
  it('pins the exact version and plays only unique local results', async () => {
    await startSongMix(seed)
    expect(mocks.similar).toHaveBeenCalledWith('', '', { library_file: seed.file })
    expect(mocks.startMix).toHaveBeenCalledWith(seed, [expect.objectContaining({ file: 'synthetic/next.flac' })])
  })
  it('does not request suggestions when the module is disabled', async () => {
    musicAI.capabilities.value.features.similarity = false
    await startSongMix(seed)
    expect(mocks.similar).not.toHaveBeenCalled()
    expect(mocks.startMix).not.toHaveBeenCalled()
  })
  it.each(['account', 'track', 'disabled'])('rejects an obsolete response after %s changes', async (change) => {
    mocks.similar.mockImplementation(async () => {
      if (change === 'account') musicAI.account.value = 'other-owner'
      if (change === 'track') current.value = { file: 'another.flac' }
      if (change === 'disabled') musicAI.capabilities.value.features.similarity = false
      return { data: { tracks: [{ file: 'synthetic/next.flac' }] } }
    })
    await startSongMix(seed)
    expect(mocks.startMix).not.toHaveBeenCalled()
  })
})
