<template>
  <div class="flex min-w-0 flex-col gap-8">
    <SettingGroup :title="t('users.title')" :description="t('users.hint')">
      <div class="flex items-center justify-between gap-3 px-5 py-4">
        <p class="text-sm text-muted">
          {{ t('users.count', { count: users.length }) }}
        </p>
        <UiButton variant="primary" icon="plus" @click="openCreate">
          {{ t('users.add') }}
        </UiButton>
      </div>
      <ul class="flex flex-col">
        <li
          v-for="user in users"
          :key="user.id"
          class="flex items-center gap-3 px-5 py-3"
        >
          <span
            class="flex size-10 shrink-0 items-center justify-center rounded-full bg-surface-2 text-sm font-bold text-muted uppercase"
            aria-hidden="true"
          >
            {{ user.username.slice(0, 1) }}
          </span>
          <span class="flex min-w-0 flex-1 flex-col">
            <span class="flex items-center gap-2">
              <span class="truncate text-sm font-semibold">{{
                user.username
              }}</span>
              <UiBadge
                v-if="user.role === 'admin'"
                tone="accent"
                icon="shield"
                >{{ t('account.roleAdmin') }}</UiBadge
              >
              <UiBadge v-if="user.id === me?.id">{{ t('users.you') }}</UiBadge>
            </span>
            <span class="truncate text-[12px] text-muted">
              {{ details(user) }}
            </span>
          </span>
          <UiIconButton
            icon="pencil"
            :label="t('users.edit', { name: user.username })"
            @click="openEdit(user)"
          />
          <UiIconButton
            v-if="user.id !== me?.id"
            icon="trash"
            :label="t('users.delete', { name: user.username })"
            @click="remove(user)"
          />
        </li>
      </ul>
    </SettingGroup>

    <SettingGroup :title="t('users.everyoneGroup')">
      <SettingRow
        :label="t('users.signOutAll')"
        :description="t('users.signOutAllHint')"
      >
        <UiButton variant="danger" icon="lock" @click="signOutAll">
          {{ t('users.signOutAll') }}
        </UiButton>
      </SettingRow>
    </SettingGroup>

    <!-- Add or edit a user -->
    <UiModal
      :open="editing !== null"
      :title="
        editing?.id
          ? t('users.editTitle', { name: editing.original })
          : t('users.addTitle')
      "
      @close="editing = null"
    >
      <form
        v-if="editing"
        id="user-form"
        class="flex flex-col gap-4"
        @submit.prevent="submit"
      >
        <UiInput
          v-model="editing.username"
          :label="t('account.username')"
          icon="user"
          autocomplete="off"
        />
        <UiInput
          v-model="editing.password"
          type="password"
          :label="editing.id ? t('users.newPassword') : t('account.password')"
          :hint="
            editing.id
              ? t('users.newPasswordHint')
              : t('account.passwordHint', { count: minLength })
          "
          autocomplete="new-password"
        />
        <div class="flex flex-col gap-1.5">
          <span class="text-[13px] font-semibold text-fg-3">{{
            t('users.role')
          }}</span>
          <UiSegmented
            v-model="editing.role"
            show-labels
            :options="[
              { value: 'user', icon: 'user', label: t('account.roleUser') },
              { value: 'admin', icon: 'shield', label: t('account.roleAdmin') },
            ]"
          />
          <span class="text-xs text-muted">{{
            editing.role === 'admin'
              ? t('users.roleAdminHint')
              : t('users.roleUserHint')
          }}</span>
        </div>
        <p v-if="formError" class="text-xs text-danger" role="alert">
          {{ formError }}
        </p>
      </form>
      <template #footer>
        <UiButton variant="ghost" @click="editing = null">
          {{ t('common.cancel') }}
        </UiButton>
        <UiButton
          type="submit"
          form="user-form"
          variant="primary"
          :loading="saving"
          :disabled="
            !editing?.username.trim() || (!editing?.id && !editing?.password)
          "
        >
          {{ editing?.id ? t('apps.save') : t('users.add') }}
        </UiButton>
      </template>
    </UiModal>
  </div>
</template>

<script setup>
// Settings > Users (admins): add, change and delete accounts, and sign
// everyone out. See downtify/users.py.
import { computed, onMounted, ref } from 'vue'
import UiBadge from '../ui/UiBadge.vue'
import UiButton from '../ui/UiButton.vue'
import UiIconButton from '../ui/UiIconButton.vue'
import UiInput from '../ui/UiInput.vue'
import UiModal from '../ui/UiModal.vue'
import UiSegmented from '../ui/UiSegmented.vue'
import SettingGroup from './SettingGroup.vue'
import SettingRow from './SettingRow.vue'
import API from '/src/model/api'
import { useAuth } from '/src/model/auth'
import { useUi } from '/src/model/ui'
import { timeAgo } from '/src/lib/format'
import { useI18n } from '/src/i18n'

const { t, locale } = useI18n()
const ui = useUi()
const auth = useAuth()
const me = auth.user
const minLength = computed(() => auth.status.value?.min_password_length || 8)

const users = ref([])
const editing = ref(null)
const saving = ref(false)
const formError = ref('')

function errorOf(err) {
  return err?.response?.data?.detail || t('toast.actionFailed')
}

async function load() {
  try {
    users.value = (await API.listUsers()).data || []
  } catch (err) {
    ui.toast(errorOf(err), { kind: 'error' })
  }
}

function details(user) {
  const parts = [
    user.last_login_at
      ? t('users.lastSignIn', {
          when: timeAgo(user.last_login_at, locale.value),
        })
      : t('users.neverSignedIn'),
  ]
  if (user.devices) parts.push(t('apps.deviceCount', { count: user.devices }))
  if (user.default_password) parts.push(t('users.defaultPassword'))
  return parts.join(' · ')
}

function openCreate() {
  formError.value = ''
  editing.value = { id: 0, username: '', password: '', role: 'user' }
}

function openEdit(user) {
  formError.value = ''
  editing.value = {
    id: user.id,
    original: user.username,
    username: user.username,
    password: '',
    role: user.role,
  }
}

async function submit() {
  const form = editing.value
  if (!form) return
  saving.value = true
  formError.value = ''
  try {
    if (form.id) {
      const changes = { username: form.username.trim(), role: form.role }
      if (form.password) changes.password = form.password
      const res = await API.updateUser(form.id, changes)
      if (form.id === me.value?.id) {
        // Your own role may have changed what this page may show.
        if (res.data.role !== me.value.role) window.location.reload()
        auth.setUser({ ...me.value, ...res.data })
      }
    } else {
      await API.createUser({
        username: form.username.trim(),
        password: form.password,
        role: form.role,
      })
    }
    editing.value = null
    ui.toast(t('account.saved'), { kind: 'success' })
    load()
  } catch (err) {
    formError.value = errorOf(err)
  } finally {
    saving.value = false
  }
}

async function remove(user) {
  const ok = await ui.confirm({
    title: t('users.deleteTitle', { name: user.username }),
    body: t('users.deleteBody'),
    confirmLabel: t('users.deleteConfirm'),
    danger: true,
  })
  if (!ok) return
  try {
    await API.deleteUser(user.id)
    users.value = users.value.filter((u) => u.id !== user.id)
  } catch (err) {
    ui.toast(errorOf(err), { kind: 'error' })
  }
}

async function signOutAll() {
  const ok = await ui.confirm({
    title: t('users.signOutAllTitle'),
    body: t('users.signOutAllBody'),
    confirmLabel: t('users.signOutAll'),
    danger: true,
  })
  if (!ok) return
  try {
    await API.revokeAll()
    window.location.reload()
  } catch (err) {
    ui.toast(errorOf(err), { kind: 'error' })
  }
}

onMounted(load)
</script>
