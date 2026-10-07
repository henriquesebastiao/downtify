<template>
  <div class="flex flex-col gap-3">
    <div class="flex flex-wrap items-center gap-3">
      <UiButton
        variant="secondary"
        icon="radar"
        :loading="testing"
        :disabled="!ready"
        @click="run"
      >
        {{ testing ? t('settings.test.testing') : t('settings.test.button') }}
      </UiButton>
      <p v-if="!ready" class="text-[13px] text-muted">
        {{ t('settings.test.needFields') }}
      </p>
    </div>

    <!-- Announced as it arrives, since the result replaces nothing the
         person is looking at. -->
    <ul class="flex flex-col gap-2" role="status" aria-live="polite">
      <li
        v-for="(line, index) in lines"
        :key="`${line.key}-${index}`"
        class="flex items-start gap-2.5 text-[13px] text-pretty"
        :class="TONES[line.status]"
      >
        <AppIcon
          :name="ICONS[line.status]"
          :size="16"
          stroke-width="2.2"
          class="mt-0.5 shrink-0"
        />
        <span class="text-fg-3">{{
          t(`settings.test.${line.key}`, line.params)
        }}</span>
      </li>
      <li
        v-if="failed"
        class="flex items-start gap-2.5 text-[13px] text-danger"
      >
        <AppIcon
          name="x"
          :size="16"
          stroke-width="2.2"
          class="mt-0.5 shrink-0"
        />
        <span class="text-fg-3">{{ t('settings.test.requestFailed') }}</span>
      </li>
    </ul>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import AppIcon from '../ui/AppIcon.vue'
import UiButton from '../ui/UiButton.vue'
import { canTest, describeTest, REQUIRED_FIELDS } from '/src/lib/connectionTest'
import API from '/src/model/api'
import { useI18n } from '/src/i18n'

const props = defineProps({
  // 'slskd' | 'navidrome': which integration, and so which endpoint.
  kind: { type: String, required: true },
  // The settings object as it is in the form (saved or not).
  config: { type: Object, required: true },
  // The address that was typed, for the messages that name it.
  url: { type: String, default: '' },
})

const { t } = useI18n()

const TONES = { ok: 'text-accent', warn: 'text-warn', fail: 'text-danger' }
const ICONS = { ok: 'check', warn: 'alert', fail: 'x' }

const testing = ref(false)
const result = ref(null)
const failed = ref(false)
// Bumped whenever the answer to a running test stops being relevant.
let serial = 0

const ready = computed(() =>
  canTest(props.config, REQUIRED_FIELDS[props.kind] || [])
)
const lines = computed(() => describeTest(result.value, { url: props.url }))

// What was typed changed, so what a test said about it no longer holds —
// nor should a slow answer to the old values land on the new ones.
watch(
  () => props.config,
  () => {
    serial += 1
    result.value = null
    failed.value = false
    testing.value = false
  },
  { deep: true }
)

async function run() {
  const mine = (serial += 1)
  testing.value = true
  failed.value = false
  result.value = null
  try {
    const call = props.kind === 'slskd' ? API.testSlskd : API.testNavidrome
    const res = await call(props.config)
    if (mine === serial) result.value = res.data
  } catch {
    if (mine === serial) failed.value = true
  } finally {
    if (mine === serial) testing.value = false
  }
}
</script>
