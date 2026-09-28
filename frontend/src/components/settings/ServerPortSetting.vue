<template>
  <SettingRow
    v-if="status"
    :label="t('port.label')"
    :description="
      status.locked_by
        ? t('port.locked', { source: status.locked_by })
        : t('port.hint')
    "
    stacked
  >
    <form
      class="flex w-full flex-col gap-2 sm:flex-row sm:items-end"
      @submit.prevent="save(false)"
    >
      <UiInput
        v-model="port"
        class="min-w-0 sm:w-40"
        :label="t('port.label')"
        type="number"
        inputmode="numeric"
        :min="status.min"
        :max="status.max"
        :error="error"
        :readonly="!portField(status).editable"
        :icon="portField(status).editable ? '' : 'lock'"
        mono
      />
      <template v-if="!status.locked_by">
        <UiButton type="submit" :loading="saving" :disabled="!changed">
          {{ t('port.save') }}
        </UiButton>
        <UiButton
          v-if="status.can_restart"
          variant="primary"
          icon="refresh"
          :loading="saving"
          :disabled="Number(port) === status.port"
          @click="save(true)"
        >
          {{ t('port.saveRestart') }}
        </UiButton>
      </template>
    </form>
    <p class="text-[12px] text-faint">
      {{ t('port.listening', { port: String(status.port) }) }}
      <template v-if="status.next !== status.port">
        · {{ t('port.nextStart', { port: String(status.next) }) }}
      </template>
    </p>
    <div
      v-if="!status.locked_by && (status.in_docker || !direct)"
      class="flex items-start gap-2.5 rounded-control bg-warn/10 px-3 py-2.5 text-[13px] text-pretty text-warn"
      role="note"
    >
      <AppIcon name="alert" :size="16" class="mt-0.5 shrink-0" />
      <span>{{
        status.in_docker ? t('port.dockerWarning') : t('port.proxyWarning')
      }}</span>
    </div>
  </SettingRow>

  <!-- Restarting on the new port -->
  <UiModal
    :open="restarting !== null"
    :title="t('port.restartingTitle', { port: String(restarting?.port ?? '') })"
    @close="restarting = null"
  >
    <div class="flex flex-col gap-3 text-sm text-pretty text-fg-2">
      <p v-if="restarting?.state === 'waiting'" aria-live="polite">
        {{ t('port.restartingBody') }}
      </p>
      <p v-else-if="restarting?.state === 'unreachable'">
        {{ t('port.unreachable') }}
      </p>
      <p v-else>{{ t('port.openNew') }}</p>
      <a
        v-if="restarting && restarting.state !== 'waiting'"
        :href="restarting.url"
        class="font-mono text-accent underline"
        >{{ restarting.url }}</a
      >
    </div>
  </UiModal>
</template>

<script setup>
// Settings > Server > Port (admins): the port the server listens on. A new
// one applies on the next start, or right away with "Save and restart";
// the page then follows the server to it when it can. See
// downtify/server_port.py.
import { computed, onMounted, ref } from 'vue'
import AppIcon from '../ui/AppIcon.vue'
import UiButton from '../ui/UiButton.vue'
import UiInput from '../ui/UiInput.vue'
import UiModal from '../ui/UiModal.vue'
import SettingRow from './SettingRow.vue'
import API from '/src/model/api'
import { useUi } from '/src/model/ui'
import {
  portField,
  reachesDirectly,
  urlOnPort,
  validPort,
} from '/src/lib/serverPort'
import { useI18n } from '/src/i18n'

const { t } = useI18n()
const ui = useUi()

const status = ref(null)
const port = ref('')
const error = ref('')
const saving = ref(false)
const restarting = ref(null)

const direct = computed(() =>
  status.value ? reachesDirectly(window.location, status.value.port) : true
)
const changed = computed(
  () => String(port.value).trim() !== String(status.value?.next ?? '')
)

async function load() {
  try {
    const res = await API.getServerPort()
    status.value = res.data
    port.value = portField(res.data).value
  } catch {
    status.value = null
  }
}

function errorOf(err) {
  return err?.response?.data?.detail || t('toast.actionFailed')
}

async function save(restart) {
  // Set by DOWNTIFY_PORT (or --port): shown, not editable.
  if (!portField(status.value).editable) return
  error.value = ''
  if (!validPort(port.value, status.value.min, status.value.max)) {
    error.value = t('port.invalid', {
      min: status.value.min,
      max: status.value.max,
    })
    return
  }
  if (restart) {
    const ok = await ui.confirm({
      title: t('port.confirmTitle', { port: String(port.value) }),
      body: [
        t('port.confirmBody'),
        status.value.in_docker ? t('port.dockerWarning') : '',
      ]
        .filter(Boolean)
        .join(' '),
      confirmLabel: t('port.saveRestart'),
      danger: true,
    })
    if (!ok) return
  }
  saving.value = true
  try {
    const res = await API.setServerPort(port.value, restart)
    status.value = res.data
    port.value = String(res.data.next)
    if (res.data.restarting) follow(res.data.next)
    else
      ui.toast(t('port.saved', { port: String(res.data.next) }), {
        kind: 'success',
      })
  } catch (err) {
    error.value = errorOf(err)
  } finally {
    saving.value = false
  }
}

// Wait for the server on its new port, then go there - only when this
// page reaches the server directly (otherwise a proxy or a Docker port
// mapping stands in between, and it's for the admin to update).
async function follow(newPort) {
  const url = urlOnPort(window.location, newPort)
  restarting.value = {
    port: newPort,
    url,
    state: direct.value ? 'waiting' : 'open',
  }
  if (!direct.value) return
  const health = new URL('/api/health', url).toString()
  const deadline = Date.now() + 60000
  while (Date.now() < deadline && restarting.value) {
    await new Promise((resolve) => setTimeout(resolve, 1500))
    try {
      const res = await fetch(health, { cache: 'no-store' })
      if (res.ok) {
        window.location.href = url
        return
      }
    } catch {
      // Not up yet.
    }
  }
  if (restarting.value) restarting.value.state = 'unreachable'
}

onMounted(load)
</script>
