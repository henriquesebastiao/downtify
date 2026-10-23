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
      v-if="normalizeVolume"
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
          :disabled="busy || status?.active || status?.pending > 0"
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
import { useI18n } from '/src/i18n'

const { t } = useI18n()
const { normalizeVolume } = usePlayerPrefs()
const { supported } = useEqualizer()
const auth = useAuth()
const status = ref(null)
const error = ref('')
const busy = ref(false)
let timer

async function refresh() {
  if (!auth.isAdmin.value) return
  try {
    status.value = (await API.getLoudnessStatus()).data
  } catch {
    error.value = t('normalization.states.unavailable')
  }
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
}
onMounted(() => {
  void refresh()
  timer = setInterval(refresh, 3000)
})
onUnmounted(() => clearInterval(timer))
</script>
