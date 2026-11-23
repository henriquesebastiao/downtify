<template>
  <SettingGroup :title="t('aurral.title')" :description="t('aurral.hint')">
    <SettingRow
      :label="t('aurral.enable')"
      :description="t('aurral.enableHint')"
    >
      <UiSwitch
        v-model="settings.aurral_enabled"
        :aria-label="t('aurral.enable')"
      />
    </SettingRow>
    <SettingRow
      :label="t('aurral.key')"
      :description="t('aurral.keyHint')"
      stacked
    >
      <div class="flex w-full flex-col gap-3">
        <div class="flex flex-wrap gap-2">
          <UiButton icon="plus" :loading="making" @click="makeKey">
            {{ t('aurral.makeKey') }}
          </UiButton>
          <UiButton :href="PLUGIN_URL" icon="link" icon-right="arrow-up-right">
            {{ t('aurral.plugin') }}
          </UiButton>
        </div>
        <template v-if="token">
          <p class="text-[13px] text-pretty text-warn" role="status">
            {{ t('aurral.keyOnce') }}
          </p>
          <div class="flex w-full flex-col gap-2 sm:flex-row sm:items-end">
            <UiInput
              :model-value="token"
              class="min-w-0 flex-1"
              :label="t('aurral.key')"
              icon="lock"
              readonly
            />
            <UiButton icon="copy" @click="copy">
              {{ copied ? t('aurral.copied') : t('aurral.copy') }}
            </UiButton>
          </div>
        </template>
      </div>
    </SettingRow>
  </SettingGroup>
</template>

<script setup>
// Settings > Apps > Aurral: let Aurral's Downtify plugin use this server
// as a download source (downtify/aurral.py), and make the key it signs
// in with - a paired-app token, listed and revoked under Paired apps.
// The switch is saved with the rest of the settings (the save bar).
import { ref } from 'vue'
import UiButton from '../ui/UiButton.vue'
import UiInput from '../ui/UiInput.vue'
import UiSwitch from '../ui/UiSwitch.vue'
import SettingGroup from './SettingGroup.vue'
import SettingRow from './SettingRow.vue'
import API from '/src/model/api'
import { useSettingsManager } from '/src/model/settings'
import { useUi } from '/src/model/ui'
import { useI18n } from '/src/i18n'

const emit = defineEmits(['key-made'])
const { t } = useI18n()
const ui = useUi()
const { settings } = useSettingsManager()
const PLUGIN_URL =
  'https://github.com/lklynet/aurral-plugins/tree/main/downtify'

const token = ref('')
const making = ref(false)
const copied = ref(false)

async function makeKey() {
  making.value = true
  copied.value = false
  try {
    const res = await API.aurralKey()
    token.value = res.data.token
    emit('key-made')
  } catch (err) {
    ui.toast(err?.response?.data?.detail || t('toast.actionFailed'), {
      kind: 'error',
    })
  } finally {
    making.value = false
  }
}

async function copy() {
  try {
    await navigator.clipboard.writeText(token.value)
    copied.value = true
  } catch {
    // The key stays selectable in the box.
  }
}
</script>
