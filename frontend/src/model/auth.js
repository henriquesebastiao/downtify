// Who is signed in to this browser. Until someone is, the app shows the
// sign-in page instead of itself (see AppShell); any request refused
// with a 401 gets it there too.
import { computed, ref } from 'vue'

import API from '/src/model/api'
import { ROLE_ADMIN, needsSignIn } from '/src/lib/auth'

const status = ref(null)
const mustSignIn = ref(false)
const loaded = ref(false)

const user = computed(() => status.value?.user || null)
const isAdmin = computed(() => user.value?.role === ROLE_ADMIN)
// DOWNTIFY_DISABLE_AUTH: nobody signs in, so there is nothing to sign out
// of and no accounts to manage.
const authDisabled = computed(() => Boolean(status.value?.auth_disabled))

async function load() {
  try {
    const res = await API.getAuthStatus()
    status.value = res.data
    mustSignIn.value = needsSignIn(res.data)
  } catch {
    // An unreachable server is shown elsewhere; don't block the app on it.
  } finally {
    loaded.value = true
  }
  return status.value
}

API.onUnauthorized(() => {
  mustSignIn.value = true
})

/** Sign in; resolves `true`, or the error's message. */
async function signIn(username, password) {
  try {
    await API.login(username, password)
  } catch (err) {
    if (err?.response?.status === 429) return 'tooMany'
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

/** Replace what's known about the signed-in user (after a change). */
function setUser(next) {
  if (status.value && next) status.value = { ...status.value, user: next }
}

export function useAuth() {
  return {
    status,
    loaded,
    mustSignIn,
    user,
    isAdmin,
    authDisabled,
    load,
    signIn,
    signOut,
    setUser,
  }
}

load()
