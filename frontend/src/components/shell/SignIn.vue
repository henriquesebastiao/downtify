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
      <div class="flex flex-col gap-4">
        <UiInput
          v-model="username"
          :label="t('auth.username')"
          icon="user"
          autocomplete="username"
        />
        <UiInput
          v-model="password"
          type="password"
          :label="t('auth.password')"
          icon="lock"
          autocomplete="current-password"
          :error="error"
        />
      </div>
      <UiButton
        type="submit"
        variant="primary"
        size="lg"
        :loading="busy"
        :disabled="!username.trim() || !password"
      >
        {{ t('auth.signIn') }}
      </UiButton>
      <p class="text-center text-[12px] text-faint">
        {{ t('auth.forgotHint') }}
      </p>
    </form>

    <!-- A server upgraded from a version without accounts says so once. -->
    <UiModal
      :open="noticeOpen"
      :title="t('auth.noticeTitle')"
      @close="noticeOpen = false"
    >
      <div class="flex flex-col gap-4 text-sm text-pretty text-fg-2">
        <p>{{ t('auth.noticeBody') }}</p>
        <dl
          v-if="notice"
          class="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 rounded-control border border-line-2 bg-surface-2 px-4 py-3"
        >
          <dt class="text-muted">{{ t('auth.username') }}</dt>
          <dd class="font-mono font-semibold select-all">
            {{ notice.username }}
          </dd>
          <dt class="text-muted">{{ t('auth.password') }}</dt>
          <dd
            class="font-semibold"
            :class="notice.password ? 'font-mono select-all' : ''"
          >
            {{ notice.password || t('auth.noticeKeptPassword') }}
          </dd>
        </dl>
        <p class="text-muted">{{ t('auth.noticeChange') }}</p>
      </div>
      <template #footer>
        <UiButton variant="primary" @click="useNotice">
          {{ t('auth.noticeOk') }}
        </UiButton>
      </template>
    </UiModal>
  </main>
</template>

<script setup>
// Shown instead of the app while this browser isn't signed in (see
// model/auth.js).
import { computed, ref, watch } from 'vue'
import AppLogo from '../ui/AppLogo.vue'
import UiButton from '../ui/UiButton.vue'
import UiInput from '../ui/UiInput.vue'
import UiModal from '../ui/UiModal.vue'
import { useAuth } from '/src/model/auth'
import { useI18n } from '/src/i18n'

const { t } = useI18n()
const auth = useAuth()
const username = ref('')
const password = ref('')
const busy = ref(false)
const error = ref('')

const notice = computed(() => auth.status.value?.notice || null)
const noticeOpen = ref(false)
watch(
  notice,
  (value) => {
    if (value) noticeOpen.value = true
  },
  { immediate: true }
)

function useNotice() {
  username.value = notice.value?.username || username.value
  if (notice.value?.password) password.value = notice.value.password
  noticeOpen.value = false
}

async function submit() {
  if (!username.value.trim() || !password.value || busy.value) return
  busy.value = true
  error.value = ''
  const result = await auth.signIn(username.value.trim(), password.value)
  if (result !== true) {
    if (result === 'Wrong username or password')
      error.value = t('auth.wrongPassword')
    else if (result === 'tooMany') error.value = t('auth.tooMany')
    else error.value = String(result)
    busy.value = false
  }
}
</script>
