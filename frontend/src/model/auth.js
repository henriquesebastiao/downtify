// Sign-in state for this browser. When the server requires sign-in and
// this browser isn't signed in, the app shows the sign-in page instead of
// itself (see AppShell); any request refused with a 401 gets it there too.
import { ref } from 'vue'

import API from '/src/model/api'
import { needsSignIn } from '/src/lib/auth'

const status = ref(null)
const mustSignIn = ref(false)

async function load() {
  try {
    const res = await API.getAuthStatus()
    status.value = res.data
    mustSignIn.value = needsSignIn(res.data)
  } catch {
    // An unreachable server is shown elsewhere; don't block the app on it.
  }
  return status.value
}

API.onUnauthorized(() => {
  mustSignIn.value = true
})

/** Sign in; resolves `true`, or the error's message. */
async function signIn(password) {
  try {
    await API.login(password)
  } catch (err) {
    return err?.response?.data?.detail || err?.message || 'failed'
  }
  // Every model and the WebSocket start over, now signed in.
  window.location.reload()
  return true
}

async function signOut() {
  try {
    await API.logout()
  } finally {
    window.location.reload()
  }
}

export function useAuth() {
  return { status, mustSignIn, load, signIn, signOut }
}

load()
