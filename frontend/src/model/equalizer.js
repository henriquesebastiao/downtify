// The player's equalizer: a Web Audio filter bank between the shared
// <audio> element and the speakers, plus its saved settings.
//
// The audio graph is only built once the equalizer is on and the user
// switches it on or presses play (a gesture, so the browser lets the
// AudioContext run). Until then
// playback is a plain <audio> element, exactly as before. Once built it
// stays for the life of the page — an element can only be routed into
// Web Audio once — and switching off just flattens every filter.
import { computed, ref, watch } from 'vue'
import {
  BAND_Q,
  BANDS,
  CUSTOM,
  GAIN_LIMIT,
  PREAMP_LIMIT,
  dbToGain,
  defaultSettings,
  headroomDb,
  matchPreset,
  parseSettings,
  presetGains,
  snapGain,
} from '/src/lib/equalizer'

const STORAGE_KEY = 'downtify-equalizer'
// Time constant for gain changes: fast enough to feel instant, slow
// enough not to click.
const RAMP = 0.03

function storage() {
  try {
    return typeof localStorage !== 'undefined' ? localStorage : null
  } catch {
    return null
  }
}

function load() {
  return parseSettings(storage()?.getItem(STORAGE_KEY))
}

const initial = load()
const enabled = ref(initial.enabled)
const preset = ref(initial.preset)
const gains = ref(initial.gains)
const preamp = ref(initial.preamp)
const supported =
  typeof window !== 'undefined' &&
  typeof (window.AudioContext || window.webkitAudioContext) === 'function'

// Headroom depends on the filters' sample rate; 48 kHz is close enough
// before the context exists.
const sampleRate = ref(48000)
const headroom = computed(() => headroomDb(gains.value, sampleRate.value))

let element = null
let context = null
let filters = []
let output = null
let failed = false
const graphState = ref('none') // 'none' | 'suspended' | 'running' | 'error'

function save() {
  try {
    storage()?.setItem(
      STORAGE_KEY,
      JSON.stringify({
        enabled: enabled.value,
        preset: preset.value,
        gains: gains.value,
        preamp: preamp.value,
      })
    )
  } catch {
    // Not persisted; still applied for this visit.
  }
}

function set(param, value) {
  param.setTargetAtTime(value, context.currentTime, RAMP)
}

function apply() {
  if (!context) return
  const on = enabled.value
  filters.forEach((filter, i) => set(filter.gain, on ? gains.value[i] : 0))
  set(output.gain, on ? dbToGain(preamp.value + headroom.value) : 1)
}

function build() {
  if (context || failed || !element || !supported) return
  try {
    const Context = window.AudioContext || window.webkitAudioContext
    context = new Context()
    sampleRate.value = context.sampleRate
    const source = context.createMediaElementSource(element)
    filters = BANDS.map((band) => {
      const filter = context.createBiquadFilter()
      filter.type = band.type
      filter.frequency.value = band.frequency
      filter.Q.value = BAND_Q
      filter.gain.value = 0
      return filter
    })
    output = context.createGain()
    let node = source
    for (const filter of filters) {
      node.connect(filter)
      node = filter
    }
    node.connect(output)
    output.connect(context.destination)
    context.addEventListener('statechange', () => {
      graphState.value = context.state
    })
    graphState.value = context.state
    apply()
  } catch (error) {
    console.error('Equalizer unavailable', error)
    graphState.value = 'error'
    failed = true
    context = null
  }
}

/** Called by the player once it has created its <audio> element. */
export function attachEqualizer(audio) {
  element = audio
}

/**
 * Called from the player's play actions. That's where a saved "on"
 * equalizer gets built (a play is a user gesture, so the AudioContext may
 * start), and where a suspended context is woken — without it the routed
 * element would play in silence.
 */
export function resumeEqualizer() {
  if (enabled.value && !context) build()
  if (context && context.state !== 'running') {
    context.resume().catch(() => {})
  }
}

function setEnabled(value) {
  enabled.value = !!value
  if (enabled.value) {
    build()
    resumeEqualizer()
  }
  apply()
  save()
}

function setGain(index, value) {
  const next = gains.value.slice()
  next[index] = snapGain(value, GAIN_LIMIT)
  gains.value = next
  preset.value = matchPreset(next)
  if (!enabled.value) setEnabled(true)
  else {
    apply()
    save()
  }
}

function setPreamp(value) {
  preamp.value = snapGain(value, PREAMP_LIMIT)
  apply()
  save()
}

function selectPreset(id) {
  gains.value = [...presetGains(id)]
  preset.value = matchPreset(gains.value)
  if (!enabled.value && id !== 'flat') setEnabled(true)
  else {
    apply()
    save()
  }
}

function reset() {
  const defaults = defaultSettings()
  gains.value = defaults.gains
  preset.value = defaults.preset
  preamp.value = defaults.preamp
  setEnabled(false)
}

// Another tab changed the settings.
if (
  typeof window !== 'undefined' &&
  typeof window.addEventListener === 'function'
) {
  window.addEventListener('storage', (event) => {
    if (event.key !== STORAGE_KEY) return
    const next = load()
    enabled.value = next.enabled
    preset.value = next.preset
    gains.value = next.gains
    preamp.value = next.preamp
    // Built on the next play in this tab (no user gesture here).
    apply()
  })
}

watch(headroom, apply)

export function useEqualizer() {
  return {
    supported,
    enabled,
    preset,
    gains,
    preamp,
    headroom,
    graphState,
    isCustom: computed(() => preset.value === CUSTOM),
    setEnabled,
    setGain,
    setPreamp,
    selectPreset,
    reset,
  }
}
