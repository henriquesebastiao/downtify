// The "change the default password" prompt (DefaultPasswordPrompt.vue):
// suggested once per browser session until the password is changed.
// Shared so other first-visit dialogs (What's new) can wait their turn.
import { computed, ref } from 'vue'

import { useAuth } from '/src/model/auth'

const KEY = 'downtify-default-password-seen'

function seen() {
  try {
    return sessionStorage.getItem(KEY) === '1'
  } catch {
    return false
  }
}

const dismissed = ref(seen())

function dismiss() {
  dismissed.value = true
  try {
    sessionStorage.setItem(KEY, '1')
  } catch {
    // Shown again next time; harmless.
  }
}

export function useDefaultPasswordPrompt() {
  const auth = useAuth()
  const open = computed(
    () =>
      Boolean(auth.user.value?.default_password) &&
      !auth.authDisabled.value &&
      !dismissed.value
  )
  return { open, dismiss }
}
