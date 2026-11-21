<template>
  <DoctorSection
    id="ai"
    :title="t('doctor.ai.title')"
    :description="t('doctor.ai.hint')"
    :status="badge.text"
    :status-tone="badge.tone"
  >
    <SettingRow :label="t('doctor.ai.helper')" :description="runningText">
      <UiButton
        :variant="status.running ? 'secondary' : 'primary'"
        :icon="status.running ? 'x' : 'sparkle'"
        :loading="switching"
        @click="toggle"
      >
        {{ status.running ? t('doctor.ai.stop') : t('doctor.ai.start') }}
      </UiButton>
    </SettingRow>

    <!-- Which assistants can connect, before and after starting. -->
    <div class="flex flex-col gap-2 px-5 py-4 text-[13px]">
      <p class="font-semibold text-fg">{{ t('doctor.ai.whoTitle') }}</p>
      <ul class="flex list-disc flex-col gap-1 pl-5 text-fg-3">
        <li>{{ t('doctor.ai.whoCode') }}</li>
        <li>{{ t('doctor.ai.whoDesktop') }}</li>
        <li>{{ t('doctor.ai.whoWeb') }}</li>
        <li>{{ t('doctor.ai.whoChatgpt') }}</li>
      </ul>
      <p class="text-muted">{{ t('doctor.ai.scope') }}</p>
    </div>

    <template v-if="status.running">
      <div class="flex flex-col gap-3 px-5 py-4 text-[13px]">
        <p class="font-semibold text-fg">{{ t('doctor.ai.connectTitle') }}</p>
        <UiSegmented
          v-model="client"
          :options="clientOptions"
          show-labels
          :aria-label="t('doctor.ai.connectTitle')"
        />
        <p class="text-fg-3">{{ clientHint }}</p>
        <div class="flex flex-col gap-1">
          <pre
            class="max-h-60 overflow-auto rounded-control bg-surface-2 px-3 py-2 font-mono text-[12px] break-all whitespace-pre-wrap text-fg"
            >{{ snippet }}</pre>
          <div>
            <UiButton size="sm" icon="copy" @click="copy(snippet)">
              {{ t('doctor.ai.copy') }}
            </UiButton>
          </div>
        </div>
        <p class="text-muted">{{ t('doctor.ai.keyHint') }}</p>
      </div>

      <div class="flex flex-col gap-2 px-5 py-4 text-[13px]">
        <p class="font-semibold text-fg">{{ t('doctor.ai.firstTitle') }}</p>
        <p class="text-fg-3">{{ t('doctor.ai.firstHint') }}</p>
        <pre
          class="rounded-control bg-surface-2 px-3 py-2 font-sans text-[13px] whitespace-pre-wrap text-fg"
          >{{ t('doctor.ai.firstMessage') }}</pre>
        <div>
          <UiButton
            size="sm"
            icon="copy"
            @click="copy(t('doctor.ai.firstMessage'))"
          >
            {{ t('doctor.ai.copy') }}
          </UiButton>
        </div>
      </div>

      <SettingRow
        :label="t('doctor.ai.canApply')"
        :description="t('doctor.ai.canApplyHint')"
      >
        <UiSwitch
          :model-value="status.can_apply"
          :aria-label="t('doctor.ai.canApply')"
          @update:model-value="setCanApply"
        />
      </SettingRow>
    </template>

    <!-- The assistant's suggestions, as the Doctor's usual cards. -->
    <div class="flex flex-col gap-1 px-5 py-4 text-[13px]">
      <p class="font-semibold text-fg">
        {{ t('doctor.ai.suggestionsTitle') }}
      </p>
      <p v-if="!suggestions.length" class="text-muted">
        {{ t('doctor.ai.none') }}
      </p>
    </div>
    <div
      v-for="item in suggestions"
      :key="item.id"
      class="flex flex-col"
      :data-suggestion="item.id"
    >
      <div class="flex flex-wrap items-center gap-2 px-5 pt-4 text-[13px]">
        <UiBadge :tone="item.decision === 'merge' ? 'accent' : 'neutral'">
          {{
            item.decision === 'merge'
              ? t('doctor.ai.decisionMerge')
              : t('doctor.ai.decisionApart')
          }}
        </UiBadge>
        <UiBadge :tone="stateTone(item.state)">
          {{ t(`doctor.ai.state.${item.state}`) }}
        </UiBadge>
      </div>
      <PlaylistGroupCard
        :group="item.group"
        :cover-version="item.created_at"
        readonly
        :apart="item.decision === 'apart'"
      />
      <div class="flex flex-col gap-2 px-5 pb-4 text-[13px]">
        <p class="rounded-control bg-accent/6 px-3 py-2 text-fg">
          <span class="font-semibold">{{ t('doctor.ai.why') }}</span>
          {{ item.reason }}
        </p>
        <p v-if="item.error" class="text-danger">{{ item.error }}</p>
        <div v-if="item.state === 'waiting'" class="flex flex-wrap gap-2">
          <UiButton
            size="sm"
            variant="primary"
            icon="check"
            :disabled="busy || applying"
            @click="apply([item.id])"
          >
            {{ t('doctor.ai.apply') }}
          </UiButton>
          <UiButton
            size="sm"
            variant="ghost"
            icon="x"
            :disabled="applying"
            @click="dismiss([item.id])"
          >
            {{ t('doctor.ai.dismiss') }}
          </UiButton>
        </div>
      </div>
    </div>
    <div
      v-if="waiting.length > 1 || finished.length"
      class="sticky bottom-0 z-10 flex flex-wrap items-center justify-between gap-3 border-t border-line-2 bg-surface/95 px-5 py-3 backdrop-blur"
    >
      <UiButton
        v-if="finished.length"
        size="sm"
        variant="ghost"
        @click="clearFinished"
      >
        {{ t('doctor.ai.clear') }}
      </UiButton>
      <UiButton
        v-if="waiting.length > 1"
        variant="primary"
        icon="check"
        :disabled="busy || applying"
        @click="apply(waiting.map((s) => s.id))"
      >
        {{ t('doctor.ai.applyAll', { count: waiting.length }) }}
      </UiButton>
    </div>
  </DoctorSection>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

import API from '/src/model/api'
import { useI18n } from '/src/i18n'
import { useUi } from '/src/model/ui'
import { connectionSnippet, helperUrl } from '/src/lib/doctorAi'
import UiBadge from '/src/components/ui/UiBadge.vue'
import UiButton from '/src/components/ui/UiButton.vue'
import UiSegmented from '/src/components/ui/UiSegmented.vue'
import UiSwitch from '/src/components/ui/UiSwitch.vue'
import SettingRow from '/src/components/settings/SettingRow.vue'
import DoctorSection from './DoctorSection.vue'
import PlaylistGroupCard from './PlaylistGroupCard.vue'

defineProps({
  /** A Doctor job is running: applying waits for it. */
  busy: { type: Boolean, default: false },
})
const emit = defineEmits(['applied'])

const { t } = useI18n()
const ui = useUi()

const status = ref({ running: false, key: '', suggestions: [] })
const switching = ref(false)
const applying = ref(false)
const client = ref('code')
let timer = 0

const suggestions = computed(() => status.value.suggestions || [])
const waiting = computed(() =>
  suggestions.value.filter((s) => s.state === 'waiting')
)
const finished = computed(() =>
  suggestions.value.filter((s) => ['applied', 'failed'].includes(s.state))
)

const badge = computed(() => {
  if (waiting.value.length)
    return {
      text: t('doctor.ai.waitingBadge', { count: waiting.value.length }),
      tone: 'accent',
    }
  if (status.value.running) return { text: t('doctor.ai.on'), tone: 'accent' }
  return { text: '', tone: 'neutral' }
})

const runningText = computed(() => {
  const s = status.value
  if (!s.running) return t('doctor.ai.offHint')
  const minutes = Math.max(1, Math.round((s.stops_in || 0) / 60))
  return s.client
    ? t('doctor.ai.connected', { client: s.client, minutes })
    : t('doctor.ai.waitingForAi', { minutes })
})

/** The address assistants use: this page's server plus the MCP path. */
const url = computed(() =>
  helperUrl(window.location.origin, status.value.mcp_path)
)

const clientOptions = computed(() => [
  { value: 'code', label: t('doctor.ai.clientCode') },
  { value: 'desktop', label: t('doctor.ai.clientDesktop') },
  { value: 'other', label: t('doctor.ai.clientOther') },
])

const clientHint = computed(() =>
  t(
    {
      code: 'doctor.ai.codeHint',
      desktop: 'doctor.ai.desktopHint',
      other: 'doctor.ai.otherHint',
    }[client.value]
  )
)

const snippet = computed(() =>
  connectionSnippet(client.value, url.value, status.value.key)
)

function stateTone(state) {
  if (state === 'applied') return 'accent'
  if (state === 'failed') return 'danger'
  return 'neutral'
}

function errorOf(err) {
  const detail = err?.response?.data?.detail
  if (detail?.message) return detail.message
  if (detail?.code) return t(`doctor.error.${detail.code}`)
  return t('toast.actionFailed')
}

async function copy(text) {
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text)
    } else {
      // A plain-http server address: no clipboard API, so copy the old way.
      const area = document.createElement('textarea')
      area.value = text
      area.setAttribute('readonly', '')
      area.style.position = 'fixed'
      area.style.opacity = '0'
      document.body.appendChild(area)
      area.select()
      const ok = document.execCommand('copy')
      area.remove()
      if (!ok) throw new Error('copy')
    }
    ui.toast(t('doctor.ai.copied'), { kind: 'success' })
  } catch {
    ui.toast(t('doctor.ai.copyFailed'), { kind: 'error' })
  }
}

async function refresh() {
  try {
    const { data } = await API.doctorAiStatus()
    const before = status.value.suggestions || []
    status.value = data
    const done = data.suggestions.some(
      (s) =>
        s.state === 'applied' &&
        before.find((b) => b.id === s.id && b.state !== 'applied')
    )
    if (done) emit('applied')
  } catch {
    // The next poll tries again.
  }
}

function schedule() {
  clearTimeout(timer)
  // Quick while the helper runs (suggestions arrive from the chat).
  timer = setTimeout(
    async () => {
      await refresh()
      schedule()
    },
    status.value.running ? 3000 : 30000
  )
}

async function toggle() {
  switching.value = true
  try {
    const { data } = status.value.running
      ? await API.doctorAiStop()
      : await API.doctorAiStart()
    status.value = data
    schedule()
  } catch (err) {
    ui.toast(errorOf(err), { kind: 'error' })
  } finally {
    switching.value = false
  }
}

async function setCanApply(value) {
  try {
    const { data } = await API.doctorAiSettings({ can_apply: value })
    status.value = data
  } catch (err) {
    ui.toast(errorOf(err), { kind: 'error' })
  }
}

async function apply(ids) {
  applying.value = true
  try {
    const { data } = await API.doctorAiApply(ids)
    status.value = data
    emit('applied')
  } catch (err) {
    ui.toast(errorOf(err), { kind: 'error' })
    await refresh()
  } finally {
    applying.value = false
  }
}

async function dismiss(ids) {
  try {
    const { data } = await API.doctorAiDismiss(ids)
    status.value = data
  } catch (err) {
    ui.toast(errorOf(err), { kind: 'error' })
  }
}

async function clearFinished() {
  try {
    const { data } = await API.doctorAiClear()
    status.value = data
  } catch (err) {
    ui.toast(errorOf(err), { kind: 'error' })
  }
}

onMounted(async () => {
  await refresh()
  schedule()
})
onBeforeUnmount(() => clearTimeout(timer))
</script>
