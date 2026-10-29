<template>
  <SettingGroup
    :title="t('normalization.title')"
    :description="t('normalization.hint')"
  >
    <SettingRow
      :label="t('normalization.enable')"
      :description="t('normalization.enableHint')"
    >
      <UiSwitch
        v-model="normalizeVolume"
        :aria-label="t('normalization.enable')"
      />
    </SettingRow>
    <p
      v-if="normalizeVolume && player.currentTrack.value"
      class="px-5 pb-4 text-sm text-muted"
      role="status"
    >
      {{
        t(
          `normalization.states.${supported ? normalizationState : 'unavailable'}`
        )
      }}
    </p>
    <div
      v-if="auth.isAdmin.value"
      class="flex flex-col gap-3 border-t border-line px-5 py-4"
    >
      <p class="text-sm text-muted">{{ t('normalization.analysisHint') }}</p>
      <p v-if="status" class="text-sm" role="status">
        {{
          t('normalization.progress', {
            done: status.done,
            total: status.total,
            failed: status.failed,
          })
        }}
      </p>
      <div class="flex flex-wrap gap-2">
        <UiButton
          :disabled="busy || status?.active"
          @click="control('start')"
          >{{ t('normalization.analyze') }}</UiButton
        >
        <UiButton
          v-if="status?.active"
          variant="ghost"
          :disabled="busy || status.pause_requested"
          @click="control('pause')"
          >{{ t('normalization.pause') }}</UiButton
        >
        <UiButton
          v-if="!status?.active && status?.pending"
          variant="ghost"
          :disabled="busy"
          @click="control('resume')"
          >{{ t('normalization.resume') }}</UiButton
        >
      </div>
      <p
        v-if="status?.pause_requested && status?.active"
        class="text-sm text-muted"
      >
        {{ t('normalization.pausing') }}
      </p>
      <p v-if="error" class="text-sm text-danger" role="alert">{{ error }}</p>
    </div>
  </SettingGroup>
</template>

<script setup>
import { onMounted, onUnmounted, ref } from 'vue'
import SettingGroup from './SettingGroup.vue'
import SettingRow from './SettingRow.vue'
import UiButton from '../ui/UiButton.vue'
import UiSwitch from '../ui/UiSwitch.vue'
import API from '/src/model/api'
import { usePlayerPrefs } from '/src/model/playerPrefs'
import { normalizationState } from '/src/model/normalization'
import { useEqualizer } from '/src/model/equalizer'
import { useAuth } from '/src/model/auth'
import { usePlayer } from '/src/model/player'
import { useI18n } from '/src/i18n'

const { t } = useI18n()
const { normalizeVolume } = usePlayerPrefs()
const { supported } = useEqualizer()
const auth = useAuth()
const player = usePlayer()
const status = ref(null)
const error = ref('')
const busy = ref(false)
let timer
let unmounted = false

// Polled only while an analysis runs.
function schedule() {
  clearTimeout(timer)
  if (!unmounted && status.value?.active) timer = setTimeout(refresh, 3000)
}
async function refresh() {
  if (!auth.isAdmin.value) return
  try {
    status.value = (await API.getLoudnessStatus()).data
  } catch {
    error.value = t('normalization.states.unavailable')
  }
  schedule()
}
async function control(action) {
  busy.value = true
  error.value = ''
  try {
    status.value = (await API.controlLoudness(action)).data
  } catch (err) {
    error.value = err?.response?.data?.detail || t('toast.actionFailed')
  } finally {
    busy.value = false
  }
  schedule()
}
onMounted(refresh)
onUnmounted(() => {
  unmounted = true
  clearTimeout(timer)
})
</script>
