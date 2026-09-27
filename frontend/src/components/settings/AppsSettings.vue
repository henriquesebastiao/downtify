<template>
  <div class="flex min-w-0 flex-col gap-8">
    <!-- This server -->
    <SettingGroup
      :title="t('apps.serverGroup')"
      :description="t('apps.serverGroupHint')"
    >
      <SettingRow
        :label="t('apps.serverName')"
        :description="t('apps.serverNameHint')"
        stacked
      >
        <form
          class="flex w-full flex-col gap-2 sm:flex-row sm:items-end"
          @submit.prevent="saveName"
        >
          <UiInput
            v-model="serverName"
            class="min-w-0 flex-1"
            :label="t('apps.serverName')"
            icon="server"
            :error="nameError"
          />
          <UiButton
            type="submit"
            :loading="savingName"
            :disabled="!serverName.trim() || serverName.trim() === info?.name"
          >
            {{ t('apps.save') }}
          </UiButton>
        </form>
        <p v-if="info" class="text-[12px] text-faint">
          {{ t('apps.serverId', { id: info.server_id }) }} · Downtify
          {{ info.version }}
        </p>
      </SettingRow>
    </SettingGroup>

    <!-- Paired apps -->
    <SettingGroup
      :title="t('apps.devicesGroup')"
      :description="t('apps.devicesGroupHint')"
    >
      <div class="flex items-center justify-between gap-3 px-5 py-4">
        <p class="text-sm text-muted">
          {{ t('apps.deviceCount', { count: devices.length }) }}
        </p>
        <UiButton variant="primary" icon="plus" @click="openPairing">
          {{ t('apps.pair') }}
        </UiButton>
      </div>
      <ul v-if="devices.length" class="flex flex-col">
        <li
          v-for="device in devices"
          :key="device.id"
          class="flex items-center gap-3 px-5 py-3"
        >
          <span
            class="flex size-10 shrink-0 items-center justify-center rounded-full bg-surface-2 text-muted"
          >
            <AppIcon name="monitor" :size="18" />
          </span>
          <span class="flex min-w-0 flex-1 flex-col">
            <span class="truncate text-sm font-semibold">{{
              device.name
            }}</span>
            <span class="truncate text-[12px] text-muted">
              {{ deviceDetails(device) }}
            </span>
          </span>
          <UiButton
            size="sm"
            variant="ghost"
            icon="trash"
            @click="revoke(device)"
          >
            {{ t('apps.revoke') }}
          </UiButton>
        </li>
      </ul>
    </SettingGroup>

    <!-- Sign-in -->
    <SettingGroup
      :title="t('apps.signInGroup')"
      :description="t('apps.signInGroupHint')"
    >
      <SettingRow
        :label="
          status?.has_password
            ? t('apps.changePassword')
            : t('apps.setPassword')
        "
        :description="
          t('apps.passwordHint', { count: status?.min_password_length || 8 })
        "
        stacked
      >
        <form
          class="flex w-full flex-col gap-2 sm:flex-row sm:items-end"
          @submit.prevent="savePassword"
        >
          <UiInput
            v-if="status?.has_password"
            v-model="currentPassword"
            class="min-w-0 flex-1"
            type="password"
            :label="t('apps.currentPassword')"
            autocomplete="current-password"
          />
          <UiInput
            v-model="newPassword"
            class="min-w-0 flex-1"
            type="password"
            :label="t('apps.newPassword')"
            autocomplete="new-password"
            :error="passwordError"
          />
          <UiButton
            type="submit"
            :loading="savingPassword"
            :disabled="!newPassword"
          >
            {{ t('apps.save') }}
          </UiButton>
        </form>
      </SettingRow>
      <SettingRow
        :label="t('apps.requireSignIn')"
        :description="
          status?.forced_by_env
            ? t('apps.requireForced')
            : status?.require_sign_in
              ? t('apps.requireOnHint')
              : t('apps.requireOffHint')
        "
      >
        <UiSwitch
          :model-value="Boolean(status?.require_sign_in)"
          :disabled="Boolean(status?.forced_by_env) || !status?.has_password"
          :aria-label="t('apps.requireSignIn')"
          @update:model-value="toggleRequire"
        />
      </SettingRow>
      <SettingRow
        :label="t('apps.signOutEverywhere')"
        :description="t('apps.signOutEverywhereHint')"
      >
        <UiButton
          v-if="status?.via === 'session'"
          variant="ghost"
          @click="auth.signOut"
        >
          {{ t('apps.signOut') }}
        </UiButton>
        <UiButton variant="danger" icon="lock" @click="revokeEverything">
          {{ t('apps.signOutEverywhereButton') }}
        </UiButton>
      </SettingRow>
    </SettingGroup>

    <!-- Pairing -->
    <UiModal
      :open="pairingOpen"
      :title="t('apps.pairTitle')"
      :description="t('apps.pairBody')"
      @close="closePairing"
    >
      <div class="flex flex-col items-center gap-4 px-5 py-5 sm:px-6">
        <template v-if="pairing && pairingState === 'pending'">
          <svg
            :viewBox="`-2 -2 ${qr.size + 4} ${qr.size + 4}`"
            class="size-56 rounded-[12px] bg-white"
            role="img"
            :aria-label="t('apps.qrLabel')"
            shape-rendering="crispEdges"
          >
            <path :d="qr.d" fill="#000" />
          </svg>
          <p class="text-[13px] text-muted">{{ t('apps.orTypeCode') }}</p>
          <p
            class="font-mono text-3xl font-semibold tracking-[0.2em] text-fg select-all"
          >
            {{ pairing.code }}
          </p>
          <p class="text-[13px] text-muted" aria-live="polite">
            {{ t('apps.expiresIn', { time: formatCountdown(remaining) }) }}
          </p>
        </template>
        <template v-else-if="pairingState === 'paired'">
          <span
            class="flex size-14 items-center justify-center rounded-full bg-accent/15 text-accent"
          >
            <AppIcon name="check" :size="28" />
          </span>
          <p class="text-center text-sm font-semibold">
            {{ t('apps.paired', { name: pairedName }) }}
          </p>
        </template>
        <template v-else>
          <p class="text-center text-sm text-muted">
            {{ t('apps.pairExpired') }}
          </p>
          <UiButton icon="refresh" @click="startPairing">
            {{ t('apps.newCode') }}
          </UiButton>
        </template>
      </div>
    </UiModal>

    <!-- Turning sign-in on asks for the password (it also signs this
         browser in, so the page doesn't lock itself out). -->
    <UiModal
      :open="requireOpen"
      :title="t('apps.requireTitle')"
      :description="t('apps.requireBody')"
      @close="requireOpen = false"
    >
      <form
        class="flex flex-col gap-4 px-5 py-5 sm:px-6"
        @submit.prevent="confirmRequire"
      >
        <UiInput
          v-model="requirePassword"
          type="password"
          :label="t('auth.password')"
          autocomplete="current-password"
          :error="requireError"
        />
        <UiButton
          type="submit"
          variant="primary"
          :loading="savingRequire"
          :disabled="!requirePassword"
        >
          {{ t('apps.requireConfirm') }}
        </UiButton>
      </form>
    </UiModal>
  </div>
</template>

<script setup>
// Settings > Apps: the server's name, paired apps (and pairing a new
// one), the web password and "Require sign-in". See downtify/auth.py.
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import AppIcon from '../ui/AppIcon.vue'
import UiButton from '../ui/UiButton.vue'
import UiInput from '../ui/UiInput.vue'
import UiModal from '../ui/UiModal.vue'
import UiSwitch from '../ui/UiSwitch.vue'
import SettingGroup from './SettingGroup.vue'
import SettingRow from './SettingRow.vue'
import API from '/src/model/api'
import { useAuth } from '/src/model/auth'
import { useUi } from '/src/model/ui'
import { formatCountdown, pairingUri, qrPath } from '/src/lib/auth'
import { timeAgo } from '/src/lib/format'
import { useI18n } from '/src/i18n'

const { t, locale } = useI18n()
const ui = useUi()
const auth = useAuth()
const status = auth.status

const info = ref(null)
const serverName = ref('')
const nameError = ref('')
const savingName = ref(false)
const devices = ref([])

function errorOf(err) {
  return err?.response?.data?.detail || t('toast.actionFailed')
}

async function loadInfo() {
  try {
    const res = await API.getServerInfo()
    info.value = res.data
    serverName.value = res.data.name
  } catch {
    // Shown as missing; the page stays usable.
  }
}

async function loadDevices() {
  try {
    const res = await API.listDevices()
    devices.value = res.data || []
  } catch {
    devices.value = []
  }
}

async function saveName() {
  savingName.value = true
  nameError.value = ''
  try {
    const res = await API.renameServer(serverName.value.trim())
    info.value = res.data
    serverName.value = res.data.name
    ui.toast(t('apps.saved'), { kind: 'success' })
  } catch (err) {
    nameError.value = errorOf(err)
  } finally {
    savingName.value = false
  }
}

function deviceDetails(device) {
  const parts = []
  if (device.platform) parts.push(device.platform)
  if (device.last_seen_at)
    parts.push(
      t('apps.lastSeen', { when: timeAgo(device.last_seen_at, locale.value) })
    )
  if (device.last_ip) parts.push(device.last_ip)
  return parts.join(' · ')
}

async function revoke(device) {
  const ok = await ui.confirm({
    title: t('apps.revokeTitle', { name: device.name }),
    body: t('apps.revokeBody'),
    confirmLabel: t('apps.revoke'),
    danger: true,
  })
  if (!ok) return
  try {
    await API.revokeDevice(device.id)
    devices.value = devices.value.filter((d) => d.id !== device.id)
  } catch (err) {
    ui.toast(errorOf(err), { kind: 'error' })
  }
}

// ── Pairing ─────────────────────────────────────────────────────────
const pairingOpen = ref(false)
const pairing = ref(null)
const pairingState = ref('pending')
const pairedName = ref('')
const remaining = ref(0)
let timer = null
let offMessage = null

const qr = computed(() =>
  qrPath(
    pairingUri({
      origin: window.location.origin,
      serverId: info.value?.server_id,
      code: pairing.value?.code,
    })
  )
)

function stopTimers() {
  clearInterval(timer)
  timer = null
}

async function poll() {
  remaining.value = Math.max(0, remaining.value - 1)
  if (!pairing.value || pairingState.value !== 'pending') return
  if (remaining.value <= 0) {
    pairingState.value = 'expired'
    stopTimers()
    return
  }
  // Every other second is enough; the WebSocket usually tells first.
  if (remaining.value % 2) return
  try {
    const res = await API.getPairing(pairing.value.pairing_id)
    if (res.data.status === 'paired') onPaired(res.data.device)
    else if (res.data.status === 'expired') pairingState.value = 'expired'
  } catch {
    // Try again on the next tick.
  }
}

function onPaired(device) {
  if (pairingState.value === 'paired') return
  pairingState.value = 'paired'
  pairedName.value = device?.name || ''
  stopTimers()
  loadDevices()
}

async function startPairing() {
  stopTimers()
  pairingState.value = 'pending'
  try {
    const res = await API.startPairing()
    pairing.value = res.data
    remaining.value = res.data.expires_in
    timer = setInterval(poll, 1000)
  } catch (err) {
    pairingOpen.value = false
    ui.toast(errorOf(err), { kind: 'error' })
  }
}

function openPairing() {
  pairingOpen.value = true
  startPairing()
}

function closePairing() {
  if (pairing.value && pairingState.value === 'pending')
    API.cancelPairing(pairing.value.pairing_id).catch(() => {})
  pairingOpen.value = false
  pairing.value = null
  stopTimers()
}

// ── Password and "Require sign-in" ─────────────────────────────────
const currentPassword = ref('')
const newPassword = ref('')
const passwordError = ref('')
const savingPassword = ref(false)

async function savePassword() {
  savingPassword.value = true
  passwordError.value = ''
  try {
    await API.setPassword(newPassword.value, currentPassword.value)
    currentPassword.value = ''
    newPassword.value = ''
    await auth.load()
    ui.toast(t('apps.passwordSaved'), { kind: 'success' })
  } catch (err) {
    passwordError.value = errorOf(err)
  } finally {
    savingPassword.value = false
  }
}

const requireOpen = ref(false)
const requirePassword = ref('')
const requireError = ref('')
const savingRequire = ref(false)

async function toggleRequire(enabled) {
  if (enabled) {
    requirePassword.value = ''
    requireError.value = ''
    requireOpen.value = true
    return
  }
  const ok = await ui.confirm({
    title: t('apps.requireOffTitle'),
    body: t('apps.requireOffBody'),
    confirmLabel: t('apps.requireOffConfirm'),
    danger: true,
  })
  if (!ok) return
  try {
    await API.setRequireSignIn(false)
    await auth.load()
  } catch (err) {
    ui.toast(errorOf(err), { kind: 'error' })
  }
}

async function confirmRequire() {
  savingRequire.value = true
  requireError.value = ''
  try {
    await API.setRequireSignIn(true, requirePassword.value)
    requireOpen.value = false
    await auth.load()
    ui.toast(t('apps.requireOnDone'), { kind: 'success' })
  } catch (err) {
    requireError.value = errorOf(err)
  } finally {
    savingRequire.value = false
  }
}

async function revokeEverything() {
  const ok = await ui.confirm({
    title: t('apps.signOutEverywhereTitle'),
    body: t('apps.signOutEverywhereBody'),
    confirmLabel: t('apps.signOutEverywhereButton'),
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
  loadInfo()
  loadDevices()
  auth.load()
  offMessage = API.onMessage((data) => {
    if (
      data?.type === 'device_paired' &&
      data.pairing_id === pairing.value?.pairing_id
    )
      onPaired(data.device)
  })
})

onBeforeUnmount(() => {
  stopTimers()
  offMessage?.()
})
</script>
