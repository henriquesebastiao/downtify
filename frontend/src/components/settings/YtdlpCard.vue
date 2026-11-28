<template>
  <div class="flex flex-col gap-3 px-5 py-4">
    <div class="min-w-0">
      <p class="flex flex-wrap items-center gap-2 text-sm font-semibold">
        {{ t('settings.ytdlpTitle') }}
        <UiBadge v-if="status.running" tone="neutral">{{
          t('settings.ytdlpRunning', { version: status.running })
        }}</UiBadge>
        <UiBadge
          v-if="status.running"
          :tone="status.running_source === 'saved' ? 'accent' : 'neutral'"
          >{{
            status.running_source === 'saved'
              ? t('settings.ytdlpFromUpdate')
              : t('settings.ytdlpFromImage')
          }}</UiBadge
        >
      </p>
      <p class="mt-0.5 text-[13px] text-pretty text-muted">
        {{ t('settings.ytdlpHint') }}
      </p>
    </div>

    <p
      v-if="status.youtube?.failing"
      class="flex items-start gap-2 text-[13px] text-danger"
    >
      <AppIcon name="alert" :size="15" class="mt-0.5" />{{
        t('settings.ytdlpFailing', {
          count: status.youtube.streak,
          error: status.youtube.last_error || '?',
        })
      }}
    </p>
    <p
      v-if="status.boot_error"
      class="flex items-start gap-2 text-[13px] text-warn"
    >
      <AppIcon name="alert" :size="15" class="mt-0.5" />{{
        t('settings.ytdlpBootError', { error: status.boot_error })
      }}
    </p>

    <UiSwitch
      :model-value="status.enabled"
      :label="t('settings.ytdlpAuto')"
      :description="t('settings.ytdlpAutoHint')"
      :disabled="saving"
      @update:model-value="(v) => save({ enabled: v })"
    />
    <UiSwitch
      v-if="status.enabled"
      :model-value="status.auto_restart"
      :label="t('settings.ytdlpAutoRestart')"
      :description="t('settings.ytdlpAutoRestartHint')"
      :disabled="saving"
      @update:model-value="(v) => save({ auto_restart: v })"
    />

    <div class="flex flex-wrap items-center gap-2 text-[13px]">
      <UiButton
        variant="secondary"
        size="sm"
        icon="refresh"
        :loading="checking || status.busy"
        @click="check"
      >
        {{ checking || status.busy ? phaseLabel : t('settings.ytdlpCheck') }}
      </UiButton>
      <span v-if="status.latest" class="text-muted">{{
        t('settings.ytdlpLatest', { version: status.latest })
      }}</span>
      <span v-if="status.checked_at" class="text-muted">{{
        t('settings.ytdlpChecked', {
          when: timeAgo(status.checked_at, locale),
        })
      }}</span>
    </div>

    <p
      v-if="status.update_available && !status.enabled"
      class="text-[13px] text-pretty"
    >
      {{ t('settings.ytdlpUpdateOut', { version: status.latest }) }}
    </p>
    <p v-if="status.error" class="text-[13px] text-pretty text-warn">
      {{ status.error }}
    </p>

    <div
      v-if="status.restart_pending"
      class="flex flex-wrap items-center gap-2 rounded-[12px] bg-surface-2 p-3 text-[13px]"
    >
      <AppIcon name="info" :size="16" class="text-muted" />
      <span class="min-w-0 flex-1">{{
        status.active && status.enabled
          ? t('settings.ytdlpPending', { version: status.active })
          : t('settings.ytdlpPendingImage')
      }}</span>
      <UiButton
        v-if="status.can_restart"
        size="sm"
        icon="refresh"
        :loading="restarting"
        @click="restart"
      >
        {{ t('settings.ytdlpRestart') }}
      </UiButton>
    </div>

    <div
      v-if="status.previous || status.running_source === 'saved'"
      class="flex flex-wrap items-center gap-2"
    >
      <UiButton
        v-if="status.previous && status.previous !== status.active"
        variant="ghost"
        size="sm"
        :disabled="saving"
        @click="use('previous')"
      >
        {{ t('settings.ytdlpUsePrevious', { version: status.previous }) }}
      </UiButton>
      <UiButton
        v-if="status.running_source === 'saved' || status.active"
        variant="ghost"
        size="sm"
        :disabled="saving"
        @click="useImage"
      >
        {{ t('settings.ytdlpUseImage') }}
      </UiButton>
    </div>

    <p class="text-xs text-pretty text-muted">
      {{ t('settings.ytdlpNotify') }}
    </p>
    <p v-if="error" class="text-[13px] text-danger">{{ error }}</p>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import AppIcon from '../ui/AppIcon.vue'
import UiBadge from '../ui/UiBadge.vue'
import UiButton from '../ui/UiButton.vue'
import UiSwitch from '../ui/UiSwitch.vue'
import API from '/src/model/api'
import { useUi } from '/src/model/ui'
import { timeAgo } from '/src/lib/format'
import { useI18n } from '/src/i18n'

const { t, locale } = useI18n()
const ui = useUi()

// Shape: GET /api/ytdlp (downtify/ytdlp_routes.py).
const status = ref({
  enabled: false,
  auto_restart: true,
  running: null,
  running_source: 'image',
  youtube: { failing: false },
})
const saving = ref(false)
const checking = ref(false)
const restarting = ref(false)
const error = ref('')
let poll = null

const phaseLabel = computed(
  () =>
    ({
      downloading: t('settings.ytdlpDownloading'),
      testing: t('settings.ytdlpTesting'),
    })[status.value.phase] || t('settings.ytdlpChecking')
)

function detailOf(err) {
  return err?.response?.data?.detail || err?.message || String(err)
}

async function refresh() {
  try {
    status.value = (await API.getYtdlp()).data
    error.value = ''
  } catch (err) {
    error.value = detailOf(err)
  }
}

async function save(switches) {
  saving.value = true
  try {
    status.value = (await API.setYtdlp(switches)).data
    error.value = ''
  } catch (err) {
    error.value = detailOf(err)
  } finally {
    saving.value = false
  }
}

async function check() {
  checking.value = true
  // The check can take a few minutes: show its step meanwhile.
  poll = setInterval(refresh, 2000)
  try {
    status.value = (await API.checkYtdlp()).data
    error.value = ''
  } catch (err) {
    error.value = detailOf(err)
  } finally {
    clearInterval(poll)
    poll = null
    checking.value = false
  }
}

async function use(version) {
  saving.value = true
  try {
    status.value = (await API.useYtdlp(version)).data
    error.value = ''
  } catch (err) {
    error.value = detailOf(err)
  } finally {
    saving.value = false
  }
}

async function useImage() {
  const ok = await ui.confirm({
    title: t('settings.ytdlpUseImage'),
    body: t('settings.ytdlpUseImageConfirm'),
  })
  if (ok) await use('image')
}

async function restart() {
  restarting.value = true
  try {
    await API.restartForYtdlp()
    ui.toast(t('settings.ytdlpRestarting'), { kind: 'info' })
  } catch (err) {
    error.value = detailOf(err)
    restarting.value = false
  }
}

onMounted(refresh)
onBeforeUnmount(() => poll && clearInterval(poll))
</script>
