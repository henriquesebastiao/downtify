import { computed, ref } from 'vue'
import { musicAI } from './musicAI'
import { usePlayer } from './player'
import { normalizeTrack } from '/src/lib/library'
import { useUi } from './ui'

const loading = ref(false)
let serial = 0
export const mixAvailable = computed(() => musicAI.capabilities.value?.features?.similarity === true)

// Local by default. Exact native file handles distinguish alternate versions.
export async function startSongMix(seed) {
  if (!seed?.file || seed.stream || seed.isPodcast) return
  const mine = ++serial
  const owner = musicAI.account.value
  const player = usePlayer()
  const current = player.currentTrack.value
  loading.value = true
  try {
    await musicAI.refresh(true)
    if (!mixAvailable.value) throw new Error('La similarité locale est désactivée.')
    const response = await musicAI.similar('', '', { library_file: seed.file })
    if (mine !== serial || owner !== musicAI.account.value) return
    if (!mixAvailable.value) throw new Error('La similarité locale est désactivée.')
    const seen = new Set([seed.file])
    const tracks = (response.data?.tracks || []).filter((row) => {
      if (!row.file || seen.has(row.file)) return false
      seen.add(row.file)
      return true
    }).map((row) => normalizeTrack({ ...row, title: row.name, album: row.album_name }))
    if (!tracks.length) throw new Error('Aucun titre proche disponible pour le moment.')
    // Do not replace music the listener changed while the request was running.
    if (player.currentTrack.value !== current) return
    player.startMix(seed, tracks)
    useUi().toast(`Mix lancé · ${tracks.length + 1} titres`, { kind: 'success' })
  } catch (failure) {
    if (mine === serial && owner === musicAI.account.value)
      useUi().toast(failure?.response?.data?.detail || failure.message, { kind: 'error' })
  } finally {
    if (mine === serial) loading.value = false
  }
}

export const songMixLoading = loading
