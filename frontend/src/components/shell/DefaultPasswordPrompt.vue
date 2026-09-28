<template>
  <UiModal
    :open="open"
    :title="t('account.defaultPasswordTitle')"
    @close="dismiss"
  >
    <p class="text-sm text-pretty text-fg-2">
      {{
        t('account.defaultPasswordBody', { name: auth.user.value?.username })
      }}
    </p>
    <template #footer>
      <UiButton variant="ghost" @click="dismiss">
        {{ t('account.later') }}
      </UiButton>
      <UiButton variant="primary" icon="key" @click="change">
        {{ t('account.changePassword') }}
      </UiButton>
    </template>
  </UiModal>
</template>

<script setup>
// Signed in with the default password (admin / downtify): suggest
// changing it, once per browser session, until it's changed.
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import UiButton from '../ui/UiButton.vue'
import UiModal from '../ui/UiModal.vue'
import { useAuth } from '/src/model/auth'
import { useI18n } from '/src/i18n'

const KEY = 'downtify-default-password-seen'

const { t } = useI18n()
const auth = useAuth()
const router = useRouter()

function seen() {
  try {
    return sessionStorage.getItem(KEY) === '1'
  } catch {
    return false
  }
}

const dismissed = ref(seen())
const open = computed(
  () =>
    Boolean(auth.user.value?.default_password) &&
    !auth.authDisabled.value &&
    !dismissed.value
)

function dismiss() {
  dismissed.value = true
  try {
    sessionStorage.setItem(KEY, '1')
  } catch {
    // Shown again next time; harmless.
  }
}

function change() {
  dismiss()
  router.push({ name: 'Settings', params: { section: 'general' } })
}
</script>
