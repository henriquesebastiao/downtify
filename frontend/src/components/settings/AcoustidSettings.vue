<template>
  <div class="flex flex-col gap-3 px-5 py-4">
    <p class="text-[13px] text-pretty text-muted">
      {{ t('settings.acoustidKeyHint') }}
      <a
        href="https://acoustid.org/new-application"
        target="_blank"
        rel="noopener"
        class="text-accent underline"
        >acoustid.org/new-application</a
      >
    </p>
    <div class="flex flex-wrap items-end gap-2">
      <UiInput
        v-model.trim="draft"
        class="min-w-[220px] flex-1"
        type="password"
        mono
        :label="t('settings.acoustidKey')"
        :placeholder="
          status.keySet ? status.keyHint : t('settings.acoustidKeyPlaceholder')
        "
        :error="draft && !looksLikeKey(draft) ? t('settings.acoustidBad') : ''"
      />
      <UiButton
        variant="primary"
        icon="check"
        :loading="saving"
        :disabled="!draft || !looksLikeKey(draft)"
        @click="save(draft)"
      >
        {{ t('settings.acoustidSaveKey') }}
      </UiButton>
      <UiButton
        icon="radar"
        :loading="testing"
        :disabled="!status.keySet"
        @click="test"
      >
        {{ t('settings.acoustidTest') }}
      </UiButton>
      <UiButton
        v-if="status.keySet"
        variant="ghost"
        icon="x"
        :disabled="saving"
        @click="save('')"
      >
        {{ t('settings.acoustidRemoveKey') }}
      </UiButton>
    </div>
    <p
      v-if="result"
      role="status"
      class="text-[13px]"
      :class="result.ok ? 'text-accent' : 'text-danger'"
    >
      {{ result.ok ? t('settings.acoustidKeyWorks') : result.detail }}
    </p>
    <p
      class="text-[13px]"
      :class="status.fingerprinter ? 'text-muted' : 'text-danger'"
    >
      {{ t(`settings.${fingerprinterKey(status)}`) }}
    </p>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import UiButton from '../ui/UiButton.vue'
import UiInput from '../ui/UiInput.vue'
import {
  fingerprinterKey,
  looksLikeKey,
  normalizeAcoustid,
} from '/src/lib/acoustid'
import API from '/src/model/api'
import { useI18n } from '/src/i18n'

const { t } = useI18n()
const status = ref(normalizeAcoustid(null))
const draft = ref('')
const saving = ref(false)
const testing = ref(false)
const result = ref(null)

async function load() {
  try {
    status.value = normalizeAcoustid((await API.getAcoustid()).data)
  } catch {
    // Left as "not set up"; the settings page shows its own errors.
  }
}

async function save(key) {
  saving.value = true
  result.value = null
  try {
    status.value = normalizeAcoustid((await API.setAcoustidKey(key)).data)
    draft.value = ''
  } catch (error) {
    result.value = {
      ok: false,
      detail: error?.response?.data?.detail || t('settings.acoustidSaveFailed'),
    }
  } finally {
    saving.value = false
  }
}

async function test() {
  testing.value = true
  result.value = null
  try {
    result.value = (await API.testAcoustid()).data
  } catch {
    result.value = { ok: false, detail: t('settings.acoustidSaveFailed') }
  } finally {
    testing.value = false
  }
}

onMounted(load)
</script>
