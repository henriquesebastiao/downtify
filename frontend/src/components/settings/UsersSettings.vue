<template>
  <div class="flex min-w-0 flex-col gap-8">
    <SettingGroup :title="t('users.title')" :description="t('users.hint')">
      <div class="flex items-center justify-between gap-3 px-5 py-4">
        <UiSkeleton v-if="!loaded" class="h-4 w-24" />
        <p v-else class="text-sm text-muted">
          {{ t('users.count', { count: users.length }) }}
        </p>
        <UiButton variant="primary" icon="plus" @click="openCreate">
          {{ t('users.add') }}
        </UiButton>
      </div>
      <p v-if="totalsLine()" class="px-5 pb-4 text-[12px] text-muted">
        {{ t('users.usageTotal') }}: {{ totalsLine() }}
      </p>
      <UiSkeletonRows
        v-if="!loaded"
        :count="3"
        cover="size-10"
        round
        action
        row-class="h-16 px-5"
        gap="gap-0"
      />
      <ul v-else class="flex animate-reveal flex-col">
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
              <UiBadge
                v-if="storageOf(user)?.exceeded"
                tone="danger"
                icon="alert"
                >{{ t('quota.fullBadge') }}</UiBadge
              >
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

    <!-- Storage quotas (issue #677, downtify/storage_quota.py) -->
    <SettingGroup
      :title="t('quota.groupTitle')"
      :description="t('quota.groupHint')"
    >
      <SettingRow
        :label="t('quota.defaultLabel')"
        :description="t('quota.defaultHint')"
        stacked
      >
        <Transition name="reveal" mode="out-in">
          <UiSkeleton
            v-if="!storageLoaded"
            key="skeleton"
            class="h-10 w-full sm:w-80"
          />
          <form
            v-else
            key="form"
            class="flex w-full flex-col gap-2 sm:flex-row sm:items-end"
            @submit.prevent="saveDefault"
          >
            <UiInput
              v-model="defaultGb"
              class="min-w-0 sm:w-56"
              type="number"
              inputmode="decimal"
              min="0"
              suffix="GB"
              :aria-label="t('quota.defaultLabel')"
              :placeholder="t('quota.unlimited')"
              :error="defaultError"
            />
            <UiButton type="submit" :loading="savingDefault">
              {{ t('apps.save') }}
            </UiButton>
          </form>
        </Transition>
      </SettingRow>
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
        <div class="flex flex-col gap-1.5">
          <span class="text-[13px] font-semibold text-fg-3">{{
            t('quota.quotaLabel')
          }}</span>
          <template v-if="editing.role === 'admin'">
            <span class="text-xs text-muted">{{ t('quota.adminHint') }}</span>
          </template>
          <template v-else>
            <UiSegmented
              v-model="editing.quotaMode"
              show-labels
              :options="[
                { value: MODE_DEFAULT, label: t('quota.modeDefault') },
                { value: MODE_UNLIMITED, label: t('quota.modeUnlimited') },
                { value: MODE_CUSTOM, label: t('quota.modeCustom') },
              ]"
            />
            <UiInput
              v-if="editing.quotaMode === MODE_CUSTOM"
              v-model="editing.quotaGb"
              type="number"
              inputmode="decimal"
              min="0"
              suffix="GB"
              :aria-label="t('quota.quotaLabel')"
            />
            <span class="text-xs text-muted">{{ quotaHint(editing) }}</span>
          </template>
          <div
            v-if="editing.id && storageOf(editing)"
            class="mt-1 flex flex-wrap items-center justify-between gap-2"
          >
            <span class="text-xs text-muted tabular-nums">{{
              usageLine(storageOf(editing))
            }}</span>
            <UiButton
              v-if="storageOf(editing).used > 0"
              variant="ghost"
              icon="retry"
              :loading="resetting"
              @click="resetUsage(editing)"
            >
              {{ t('quota.resetUsage') }}
            </UiButton>
          </div>
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
import UiSkeleton from '../ui/UiSkeleton.vue'
import UiSkeletonRows from '../ui/UiSkeletonRows.vue'
import SettingGroup from './SettingGroup.vue'
import SettingRow from './SettingRow.vue'
import API from '/src/model/api'
import { useAuth } from '/src/model/auth'
import { useUi } from '/src/model/ui'
import { formatBytes, timeAgo } from '/src/lib/format'
import {
  MODE_CUSTOM,
  MODE_DEFAULT,
  MODE_UNLIMITED,
  bytesToGb,
  gbToBytes,
  quotaMode,
  quotaPayload,
} from '/src/lib/storageQuota'
import { useI18n } from '/src/i18n'

const { t, locale } = useI18n()
const ui = useUi()
const auth = useAuth()
const me = auth.user
const minLength = computed(() => auth.status.value?.min_password_length || 8)

const users = ref([])
const loaded = ref(false)
const stats = ref(null)
const editing = ref(null)
const saving = ref(false)
const formError = ref('')
// GET /api/users/storage: {default, users: [{id, used, limit, own, …}]}.
const storage = ref(null)
const storageLoaded = ref(false)
const defaultGb = ref('')
const defaultError = ref('')
const savingDefault = ref(false)
const resetting = ref(false)

function errorOf(err) {
  return err?.response?.data?.detail || t('toast.actionFailed')
}

async function load() {
  try {
    users.value = (await API.listUsers()).data || []
  } catch (err) {
    ui.toast(errorOf(err), { kind: 'error' })
  } finally {
    loaded.value = true
  }
  try {
    stats.value = (await API.getUserStats()).data || null
  } catch {
    stats.value = null
  }
}

async function loadStorage() {
  try {
    storage.value = (await API.getUsersStorage()).data || null
    defaultGb.value = bytesToGb(storage.value?.default)
  } catch {
    storage.value = null
  } finally {
    storageLoaded.value = true
  }
}

function storageOf(user) {
  return storage.value?.users?.find((row) => row.id === user.id) || null
}

function usageLine(row) {
  const used = formatBytes(row.used)
  if (row.unlimited) return t('quota.usedUnlimited', { used })
  return t('quota.used', { used, limit: formatBytes(row.limit) })
}

function quotaHint(form) {
  if (form.quotaMode === MODE_UNLIMITED) return t('quota.modeUnlimitedHint')
  if (form.quotaMode === MODE_CUSTOM) return t('quota.modeCustomHint')
  const fallback = storage.value?.default
  return fallback
    ? t('quota.modeDefaultHint', { limit: formatBytes(fallback) })
    : t('quota.modeDefaultNone')
}

async function saveDefault() {
  defaultError.value = ''
  const text = String(defaultGb.value ?? '').trim()
  const bytes = gbToBytes(text)
  if (text && bytes === null) {
    defaultError.value = t('quota.invalid')
    return
  }
  savingDefault.value = true
  try {
    storage.value = (await API.setDefaultStorageQuota(bytes)).data
    defaultGb.value = bytesToGb(storage.value?.default)
    ui.toast(t('account.saved'), { kind: 'success' })
  } catch (err) {
    defaultError.value = errorOf(err)
  } finally {
    savingDefault.value = false
  }
}

async function resetUsage(form) {
  const ok = await ui.confirm({
    title: t('quota.resetTitle', { name: form.original }),
    body: t('quota.resetBody'),
    confirmLabel: t('quota.resetUsage'),
    danger: true,
  })
  if (!ok) return
  resetting.value = true
  try {
    await API.resetUserStorage(form.id)
    ui.toast(t('quota.resetDone'), { kind: 'success' })
    await Promise.all([loadStorage(), load()])
  } catch (err) {
    ui.toast(errorOf(err), { kind: 'error' })
  } finally {
    resetting.value = false
  }
}

function usageParts(row) {
  return [
    t('users.tracksStat', { count: row.tracks }),
    formatBytes(row.bytes),
    t('users.likesStat', { count: row.likes }),
    t('users.playlistsStat', { count: row.playlists }),
    t('users.trafficStat', {
      down: formatBytes(row.traffic_in),
      up: formatBytes(row.traffic_out),
    }),
  ].join(' · ')
}

function usageOf(user) {
  const row = stats.value?.users?.find((entry) => entry.id === user.id)
  if (!row) return ''
  return usageParts(row)
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
  const usage = usageOf(user)
  if (usage) parts.push(usage)
  const quota = storageOf(user)
  if (quota && !quota.unlimited) {
    parts.push(
      t('quota.usageOf', {
        used: formatBytes(quota.used),
        limit: formatBytes(quota.limit),
      })
    )
  }
  return parts.join(' · ')
}

function totalsLine() {
  const totals = stats.value?.totals
  if (!totals) return ''
  return usageParts(totals)
}

function openCreate() {
  formError.value = ''
  editing.value = {
    id: 0,
    username: '',
    password: '',
    role: 'user',
    quotaMode: MODE_DEFAULT,
    quotaGb: '',
    savedQuota: null,
  }
}

function openEdit(user) {
  formError.value = ''
  const own = storageOf(user)?.own ?? null
  editing.value = {
    id: user.id,
    original: user.username,
    username: user.username,
    password: '',
    role: user.role,
    quotaMode: quotaMode(own),
    quotaGb: own > 0 ? bytesToGb(own) : '',
    savedQuota: own,
  }
}

async function submit() {
  const form = editing.value
  if (!form) return
  formError.value = ''
  // Admins are never limited: their own setting is left as it is.
  const quota =
    form.role === 'admin'
      ? form.savedQuota
      : quotaPayload(form.quotaMode, form.quotaGb)
  if (quota === undefined) {
    formError.value = t('quota.invalid')
    return
  }
  saving.value = true
  try {
    let id = form.id
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
      const res = await API.createUser({
        username: form.username.trim(),
        password: form.password,
        role: form.role,
      })
      id = res.data.id
    }
    if (id && quota !== form.savedQuota) {
      await API.setUserStorageQuota(id, quota)
    }
    editing.value = null
    ui.toast(t('account.saved'), { kind: 'success' })
    load()
    loadStorage()
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

onMounted(() => {
  load()
  loadStorage()
})
</script>
