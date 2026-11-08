import { ref, watch } from 'vue'
import API from '/src/model/api'

export const libraryOnly = ref(false)
export const policyLoaded = ref(false)
export const musicPolicyRevision = ref(0)
watch(
  libraryOnly,
  () => {
    musicPolicyRevision.value += 1
  },
  { flush: 'sync' }
)

export async function refreshMusicPolicy() {
  try {
    const response = await API.getServerInfo()
    libraryOnly.value = response.data?.library_only === true
  } catch {
    // Keep the last known policy when the server cannot be reached.
  } finally {
    policyLoaded.value = true
  }
}

export function startMusicPolicy() {
  void refreshMusicPolicy()
  const timer = setInterval(refreshMusicPolicy, 15000)
  const unsubscribe = API.onMessage((data) => {
    if (data?.type === 'music_policy_changed') {
      libraryOnly.value = data.library_only === true
    }
  })
  return () => {
    clearInterval(timer)
    unsubscribe()
  }
}
