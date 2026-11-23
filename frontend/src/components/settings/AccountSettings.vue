<template>
  <SettingGroup :title="t('account.title')" :description="t('account.hint')">
    <div class="flex items-center gap-3 px-5 py-4">
      <span
        class="flex size-11 shrink-0 items-center justify-center rounded-full bg-accent/15 text-base font-bold text-accent uppercase"
        aria-hidden="true"
      >
        {{ (user?.username || '?').slice(0, 1) }}
      </span>
      <span class="flex min-w-0 flex-1 flex-col">
        <span class="truncate text-sm font-semibold">{{ user?.username }}</span>
        <span class="text-[12px] text-muted">
          {{
            user?.role === 'admin'
              ? t('account.roleAdmin')
              : t('account.roleUser')
          }}
        </span>
      </span>
      <UiButton variant="ghost" icon="log-out" @click="auth.signOut">
        {{ t('account.signOut') }}
      </UiButton>
    </div>

    <!-- Storage quota (issue #677): what your downloads take, and the
         limit an admin set. -->
    <div v-if="storageState !== 'failed'" class="flex flex-col gap-2 px-5 py-4">
      <div
        class="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1"
      >
        <p class="text-sm font-semibold text-fg">{{ t('quota.title') }}</p>
        <Transition name="reveal" mode="out-in">
          <UiSkeleton
            v-if="storageState === 'loading'"
            key="skeleton"
            class="h-3.5 w-36"
          />
          <p
            v-else
            key="line"
            class="text-[13px] text-muted tabular-nums"
            aria-live="polite"
          >
            {{ storageLine }}
          </p>
        </Transition>
      </div>
      <UiProgress
        v-if="storage && !storage.unlimited"
        :value="quotaPercent(storage)"
        :color="toneClass"
        :aria-label="t('quota.title')"
      />
      <p v-if="storage?.exceeded" class="text-[13px] text-pretty text-danger">
        {{ t('quota.full') }}
      </p>
    </div>

    <div
      v-if="user?.default_password"
      class="flex items-start gap-3 bg-warn/10 px-5 py-3 text-[13px] text-pretty text-warn"
      role="status"
    >
      <AppIcon name="alert" :size="17" class="mt-0.5 shrink-0" />
      <span>{{ t('account.defaultPasswordWarning') }}</span>
    </div>

    <SettingRow
      :label="t('account.username')"
      :description="t('account.usernameHint')"
      stacked
    >
      <form
        class="flex w-full flex-col gap-2 sm:flex-row sm:items-end"
        @submit.prevent="saveUsername"
      >
        <UiInput
          v-model="username"
          class="min-w-0 flex-1"
          :label="t('account.username')"
          icon="user"
          autocomplete="username"
          :error="usernameError"
        />
        <UiButton
          type="submit"
          :loading="savingUsername"
          :disabled="!username.trim() || username.trim() === user?.username"
        >
          {{ t('apps.save') }}
        </UiButton>
      </form>
    </SettingRow>

    <SettingRow
      :label="t('account.password')"
      :description="t('account.passwordHint', { count: minLength })"
      stacked
    >
      <form
        class="grid w-full gap-2 sm:grid-cols-[1fr_1fr_1fr_auto] sm:items-end"
        @submit.prevent="savePassword"
      >
        <UiInput
          v-model="currentPassword"
          type="password"
          :label="t('account.currentPassword')"
          autocomplete="current-password"
        />
        <UiInput
          v-model="newPassword"
          type="password"
          :label="t('account.newPassword')"
          autocomplete="new-password"
        />
        <UiInput
          v-model="confirmPassword"
          type="password"
          :label="t('account.confirmPassword')"
          autocomplete="new-password"
        />
        <UiButton
          type="submit"
          :loading="savingPassword"
          :disabled="!currentPassword || !newPassword || !confirmPassword"
        >
          {{ t('apps.save') }}
        </UiButton>
        <p
          v-if="passwordError"
          class="text-xs text-danger sm:col-span-4"
          role="alert"
        >
          {{ passwordError }}
        </p>
      </form>
    </SettingRow>
  </SettingGroup>
</template>

<script setup>
// Settings > General > Account: who is signed in, their username and
// password, and signing out. Everyone manages their own here; admins
// manage the others in Settings > Users.
import { computed, onMounted, ref, watch } from 'vue'
import AppIcon from '../ui/AppIcon.vue'
import UiButton from '../ui/UiButton.vue'
import UiInput from '../ui/UiInput.vue'
import UiProgress from '../ui/UiProgress.vue'
import UiSkeleton from '../ui/UiSkeleton.vue'
import SettingGroup from './SettingGroup.vue'
import SettingRow from './SettingRow.vue'
import API from '/src/model/api'
import { useAuth } from '/src/model/auth'
import { useUi } from '/src/model/ui'
import { useI18n } from '/src/i18n'
import { formatBytes } from '/src/lib/format'
import { quotaPercent, quotaTone } from '/src/lib/storageQuota'

const { t } = useI18n()
const ui = useUi()
const auth = useAuth()
const user = auth.user
const minLength = computed(() => auth.status.value?.min_password_length || 8)

function errorOf(err) {
  return err?.response?.data?.detail || t('toast.actionFailed')
}

// 'loading' | 'ready' | 'failed' - kept apart from the answer itself, so
// the skeleton shows until it is known (and nothing when it can't be).
const storage = ref(null)
const storageState = ref('loading')

async function loadStorage() {
  try {
    storage.value = (await API.getMyStorage()).data
    storageState.value = 'ready'
  } catch {
    storageState.value = 'failed'
  }
}

const storageLine = computed(() => {
  const value = storage.value
  if (!value) return ''
  const used = formatBytes(value.used)
  if (value.unlimited) return t('quota.usedUnlimited', { used })
  return `${t('quota.used', { used, limit: formatBytes(value.limit) })} · ${t(
    'quota.left',
    { left: formatBytes(value.remaining) }
  )}`
})

const toneClass = computed(
  () =>
    ({ danger: 'bg-danger', warn: 'bg-warn' })[quotaTone(storage.value)] || ''
)

onMounted(loadStorage)

const username = ref(user.value?.username || '')
const usernameError = ref('')
const savingUsername = ref(false)
watch(user, (value) => {
  if (value) username.value = value.username
})

async function saveUsername() {
  savingUsername.value = true
  usernameError.value = ''
  try {
    const res = await API.renameMe(username.value.trim())
    auth.setUser(res.data.user)
    ui.toast(t('account.saved'), { kind: 'success' })
  } catch (err) {
    usernameError.value = errorOf(err)
  } finally {
    savingUsername.value = false
  }
}

const currentPassword = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const passwordError = ref('')
const savingPassword = ref(false)

async function savePassword() {
  passwordError.value = ''
  if (newPassword.value !== confirmPassword.value) {
    passwordError.value = t('account.passwordsDiffer')
    return
  }
  savingPassword.value = true
  try {
    const res = await API.changeMyPassword(
      currentPassword.value,
      newPassword.value
    )
    auth.setUser(res.data.user)
    currentPassword.value = ''
    newPassword.value = ''
    confirmPassword.value = ''
    ui.toast(t('account.passwordSaved'), { kind: 'success' })
  } catch (err) {
    passwordError.value =
      err?.response?.status === 403
        ? t('account.wrongCurrentPassword')
        : errorOf(err)
  } finally {
    savingPassword.value = false
  }
}
</script>
