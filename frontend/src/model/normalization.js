// Playback volume normalization: the server's loudness measurement of a
// library track (downtify/loudness.py) becomes one constant gain, applied
// by the equalizer's output node. Audio files are never changed.
import { ref, watch } from 'vue'
import API from '/src/model/api'
import { usePlayerPrefs } from '/src/model/playerPrefs'

export const normalizationEnabled = usePlayerPrefs().normalizeVolume
export const normalizationLevel = usePlayerPrefs().normalizationLevel
export const normalizationGain = ref(0)
export const normalizationState = ref('unanalysed')
let appliedProfile = null

watch(normalizationLevel, (level) => {
  normalizationGain.value = safeNormalizationGain(appliedProfile, level)
})

// Profiles already fetched, by library path, so resuming, repeating or
// reaching a prefetched track applies its gain without waiting. Kept a
// while only: an analysis run or a replaced file changes them.
const PROFILE_TTL_MS = 10 * 60 * 1000
const MAX_PROFILES = 200
const profiles = new Map()
const pending = new Map()

function remember(file, profile) {
  profiles.delete(file)
  profiles.set(file, { profile, at: Date.now() })
  if (profiles.size > MAX_PROFILES) {
    profiles.delete(profiles.keys().next().value)
  }
}

export function safeNormalizationGain(profile, level = 'normal') {
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
  const offset = level === 'louder' ? 6 : level === 'maximum' ? 12 : 0
  return Math.min(12, -18 + offset - integrated, -1 - peak, gain + offset)
}

/**
 * The profile to apply to `track` right away: null when there is nothing
 * to look up (normalization off, a streamed track), undefined while it
 * still has to be fetched.
 */
export function knownTrackNormalization(track) {
  if (!normalizationEnabled.value || !track?.file) return null
  const hit = profiles.get(track.file)
  if (hit && Date.now() - hit.at < PROFILE_TTL_MS) return hit.profile
  return undefined
}

export function getTrackNormalization(track) {
  const known = knownTrackNormalization(track)
  if (known !== undefined) return Promise.resolve(known)
  const file = track.file
  if (!pending.has(file)) {
    pending.set(
      file,
      API.getTrackLoudness(file)
        .then(({ data }) => {
          remember(file, data)
          return data
        })
        // Not remembered: the next play asks again.
        .catch(() => ({ state: 'unavailable', gain_db: 0 }))
        .finally(() => pending.delete(file))
    )
  }
  return pending.get(file)
}

/** Look up the next track's profile while this one plays. */
export function prefetchTrackNormalization(track) {
  if (knownTrackNormalization(track) === undefined) {
    void getTrackNormalization(track)
  }
}

export function applyTrackNormalization(profile) {
  appliedProfile = profile
  normalizationGain.value = safeNormalizationGain(
    profile,
    normalizationLevel.value
  )
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
