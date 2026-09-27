<template>
  <main class="flex min-h-dvh items-center justify-center bg-bg px-4 text-fg">
    <form
      class="flex w-full max-w-sm flex-col gap-6 rounded-panel border border-line-2 bg-surface p-6 sm:p-8"
      @submit.prevent="submit"
    >
      <div class="flex flex-col items-center gap-3 text-center">
        <AppLogo :size="48" />
        <h1 class="text-display text-2xl font-semibold">
          {{ t('auth.signInTitle') }}
        </h1>
        <p class="text-sm text-muted">{{ t('auth.signInBody') }}</p>
      </div>
      <UiInput
        v-model="password"
        type="password"
        :label="t('auth.password')"
        icon="lock"
        autocomplete="current-password"
        :error="error"
      />
      <UiButton
        type="submit"
        variant="primary"
        size="lg"
        :loading="busy"
        :disabled="!password"
      >
        {{ t('auth.signIn') }}
      </UiButton>
      <p class="text-center text-[12px] text-faint">
        {{ t('auth.forgotHint') }}
      </p>
    </form>
  </main>
</template>

<script setup>
// Shown instead of the app while the server requires sign-in and this
// browser isn't signed in (see model/auth.js).
import { ref } from 'vue'
import AppLogo from '../ui/AppLogo.vue'
import UiButton from '../ui/UiButton.vue'
import UiInput from '../ui/UiInput.vue'
import { useAuth } from '/src/model/auth'
import { useI18n } from '/src/i18n'

const { t } = useI18n()
const auth = useAuth()
const password = ref('')
const busy = ref(false)
const error = ref('')

async function submit() {
  if (!password.value || busy.value) return
  busy.value = true
  error.value = ''
  const result = await auth.signIn(password.value)
  if (result !== true) {
    error.value =
      result === 'Wrong password' ? t('auth.wrongPassword') : String(result)
    busy.value = false
  }
}
</script>
