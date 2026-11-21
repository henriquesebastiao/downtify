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
import { useRouter } from 'vue-router'
import UiButton from '../ui/UiButton.vue'
import UiModal from '../ui/UiModal.vue'
import { useAuth } from '/src/model/auth'
import { useDefaultPasswordPrompt } from '/src/model/defaultPassword'
import { useI18n } from '/src/i18n'

const { t } = useI18n()
const auth = useAuth()
const router = useRouter()
const { open, dismiss } = useDefaultPasswordPrompt()

function change() {
  dismiss()
  router.push({ name: 'Settings', params: { section: 'general' } })
}
</script>
