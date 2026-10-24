import { ref } from 'vue'
import API from '/src/model/api'
import { usePlayerPrefs } from '/src/model/playerPrefs'

export const normalizationEnabled = usePlayerPrefs().normalizeVolume
export const normalizationGain = ref(0)
export const normalizationState = ref('unanalysed')

export function safeNormalizationGain(profile) {
  if (profile?.state !== 'ready' || profile.algorithm_version !== 1) return 0
  const integrated = profile.integrated_lufs
  const peak = profile.true_peak_dbtp
  const gain = profile.gain_db
  if (![integrated, peak, gain].every(Number.isFinite)) return 0
  if (
    integrated < -120 ||
    integrated > 20 ||
    peak < -160 ||
    peak > 20 ||
    gain < -60
  )
    return 0
  return Math.min(12, -18 - integrated, -1 - peak, gain)
}

export async function getTrackNormalization(track) {
  if (!normalizationEnabled.value || !track?.file) return null
  try {
    return (await API.getTrackLoudness(track.file)).data
  } catch {
    return { state: 'unavailable', gain_db: 0 }
  }
}

export function applyTrackNormalization(profile) {
  normalizationGain.value = safeNormalizationGain(profile)
  const state = profile?.state
  normalizationState.value = [
    'ready',
    'silent',
    'unanalysed',
    'unavailable',
  ].includes(state)
    ? state
    : 'unavailable'
}
