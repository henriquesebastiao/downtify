<template>
  <div class="flex flex-col gap-3 px-5 py-4">
    <div class="flex items-start justify-between gap-4">
      <div class="min-w-0">
        <p class="flex items-center gap-2 text-sm font-semibold">
          {{ t('settings.cookies') }}
          <UiBadge v-if="status.configured" tone="accent" icon="check">{{
            t('settings.cookiesOn')
          }}</UiBadge>
        </p>
        <p class="mt-0.5 text-[13px] text-pretty text-muted">
          {{ t('settings.cookiesHint') }}
        </p>
      </div>
    </div>

    <div
      v-if="status.locked"
      class="flex items-start gap-2.5 rounded-[12px] bg-surface-2 p-3 text-[13px]"
    >
      <AppIcon name="lock" :size="16" class="mt-0.5 text-muted" />
      <div class="min-w-0">
        <p>{{ t('settings.cookiesLocked') }}</p>
        <p class="mt-0.5 truncate font-mono text-xs text-muted">
          {{ status.path }}
        </p>
        <p v-if="!status.configured" class="mt-1 text-xs text-danger">
          {{ t('settings.cookiesEnvMissing') }}
        </p>
      </div>
    </div>

    <div v-else class="flex flex-wrap items-center gap-2">
      <input
        ref="picker"
        type="file"
        accept=".txt,text/plain"
        class="hidden"
        @change="onPick"
      />
      <UiButton
        variant="secondary"
        icon="upload"
        :loading="busy"
        @click="picker?.click()"
      >
        {{
          status.configured
            ? t('settings.cookiesReplace')
            : t('settings.cookiesUpload')
        }}
      </UiButton>
      <UiButton
        v-if="status.configured"
        variant="danger"
        icon="trash"
        :disabled="busy"
        @click="remove"
      >
        {{ t('common.delete') }}
      </UiButton>
      <span
        v-if="status.configured && status.updated_at"
        class="text-xs text-muted"
      >
        {{
          t('settings.cookiesUpdated', {
            when: timeAgo(status.updated_at, locale),
          })
        }}
      </span>
    </div>

    <p v-if="error" class="text-[13px] text-danger">{{ error }}</p>
    <p
      v-for="warning in warnings"
      :key="warning"
      class="flex items-start gap-2 text-[13px] text-warn"
    >
      <AppIcon name="alert" :size="15" class="mt-0.5" />{{ warning }}
    </p>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import AppIcon from '../ui/AppIcon.vue'
import UiBadge from '../ui/UiBadge.vue'
import UiButton from '../ui/UiButton.vue'
import { useCookiesManager } from '/src/model/cookies'
import { useUi } from '/src/model/ui'
import { timeAgo } from '/src/lib/format'
import { useI18n } from '/src/i18n'

const { t, locale } = useI18n()
const cookies = useCookiesManager()
const ui = useUi()
const picker = ref(null)
const { status, busy, error, warnings } = cookies

onMounted(cookies.refresh)

async function onPick(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (file && (await cookies.upload(file))) {
    ui.toast(t('settings.cookiesSaved'), { kind: 'success' })
  }
}

async function remove() {
  const ok = await ui.confirm({
    title: t('settings.cookiesDeleteTitle'),
    confirmLabel: t('common.delete'),
    danger: true,
  })
  if (ok) await cookies.remove()
}
</script>
