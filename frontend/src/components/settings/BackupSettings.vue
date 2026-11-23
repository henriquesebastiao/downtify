<template>
  <SettingGroup :title="t('backup.title')" :description="t('backup.hint')">
    <SettingRow
      :label="t('backup.schedule')"
      :description="t('backup.scheduleHint', { keep: status?.keep ?? 2 })"
      stacked
    >
      <UiSegmented
        :options="intervalOptions"
        :model-value="status?.interval_hours ?? 0"
        show-labels
        @update:model-value="setInterval"
      />
    </SettingRow>
    <SettingRow
      :label="t('backup.saved')"
      :description="t('backup.savedHint')"
      stacked
    >
      <div class="flex w-full flex-col gap-2">
        <UiButton
          class="self-start"
          icon="hard-drive"
          :loading="busy === 'backup' || status?.running"
          :disabled="!!busy"
          @click="backUpNow"
        >
          {{ t('backup.now') }}
        </UiButton>
        <p
          v-if="status?.last_error"
          class="text-[13px] text-pretty text-danger"
          role="alert"
        >
          {{ t('backup.failed', { error: status.last_error.error }) }}
        </p>
        <UiSkeletonRows
          v-if="!loaded"
          :count="2"
          cover=""
          action
          row-class="h-11"
          gap="gap-0"
        />
        <p v-else-if="!status?.backups?.length" class="text-[13px] text-faint">
          {{ t('backup.none') }}
        </p>
        <ul v-else class="flex animate-reveal flex-col divide-y divide-line">
          <li
            v-for="item in status.backups"
            :key="item.name"
            class="flex flex-wrap items-center gap-x-3 gap-y-1 py-2"
          >
            <div class="min-w-0 flex-1">
              <p class="text-[14px] text-fg">
                {{ formatDate(item.created_at) }}
              </p>
              <p class="text-[12px] text-faint">
                {{
                  t('backup.counts', {
                    watches: item.watches,
                    songs: item.songs,
                    size: formatBytes(item.size),
                  })
                }}
              </p>
            </div>
            <UiButton
              variant="ghost"
              icon="download"
              :href="downloadURL(item.name)"
            >
              {{ t('backup.download') }}
            </UiButton>
            <UiButton
              variant="ghost"
              icon="refresh"
              :disabled="!!busy"
              @click="restoreSaved(item)"
            >
              {{ t('backup.restore') }}
            </UiButton>
          </li>
        </ul>
      </div>
    </SettingRow>
    <SettingRow
      :label="t('backup.fromFile')"
      :description="t('backup.fromFileHint')"
      stacked
    >
      <div class="flex w-full flex-col gap-3">
        <div class="flex flex-col gap-2">
          <label
            v-for="part in PARTS"
            :key="part"
            class="flex items-center gap-2 text-[14px] text-fg-2"
          >
            <UiSwitch v-model="parts[part]" :aria-label="partLabel(part)" />
            {{ partLabel(part) }}
          </label>
        </div>
        <input
          ref="fileInput"
          type="file"
          accept=".gz,.json,application/gzip,application/json"
          class="hidden"
          @change="restoreFile"
        />
        <UiButton
          class="self-start"
          icon="upload"
          :loading="busy === 'restore'"
          :disabled="!!busy || !anyPart"
          @click="fileInput?.click()"
        >
          {{ t('backup.chooseFile') }}
        </UiButton>
        <p
          v-if="result"
          class="text-[13px] text-pretty text-fg-2"
          aria-live="polite"
        >
          {{ resultLine }}
        </p>
      </div>
    </SettingRow>
  </SettingGroup>
</template>

<script setup>
// Settings > Server > Backups (admins): automatic and manual backups of
// settings, watches and the library's song list, and restoring one into
// this install. See downtify/backup.py.
import { computed, onMounted, reactive, ref } from 'vue'
import UiButton from '../ui/UiButton.vue'
import UiSegmented from '../ui/UiSegmented.vue'
import UiSwitch from '../ui/UiSwitch.vue'
import UiSkeletonRows from '../ui/UiSkeletonRows.vue'
import SettingGroup from './SettingGroup.vue'
import SettingRow from './SettingRow.vue'
import API from '/src/model/api'
import { useUi } from '/src/model/ui'
import { formatBytes } from '/src/lib/format'
import { restoreSummary } from '/src/lib/backups'
import { useI18n } from '/src/i18n'

const PARTS = ['settings', 'watches', 'songs']

const { t, locale } = useI18n()
const ui = useUi()

const status = ref(null)
const loaded = ref(false)
const busy = ref('')
const result = ref(null)
const fileInput = ref(null)
const parts = reactive({ settings: true, watches: true, songs: true })

const anyPart = computed(() => PARTS.some((part) => parts[part]))
const intervalOptions = computed(() =>
  (status.value?.intervals || [0, 24, 72, 168]).map((hours) => ({
    value: hours,
    label: t(`backup.every${hours}`),
  }))
)
const resultLine = computed(() => restoreSummary(result.value, t))

function partLabel(part) {
  return t(`backup.part_${part}`)
}

function formatDate(when) {
  const date = new Date(when)
  return Number.isNaN(date.getTime())
    ? String(when || '')
    : date.toLocaleString(locale.value)
}

function downloadURL(name) {
  return API.backupDownloadURL(name)
}

function errorOf(err) {
  return err?.response?.data?.detail || t('toast.actionFailed')
}

async function load() {
  try {
    status.value = (await API.getBackups()).data
  } catch {
    status.value = null
  } finally {
    loaded.value = true
  }
}

async function setInterval(hours) {
  try {
    status.value = (await API.setBackupSchedule(hours)).data
  } catch (err) {
    ui.toast(errorOf(err), { kind: 'error' })
  }
}

async function backUpNow() {
  busy.value = 'backup'
  try {
    await API.createBackup()
    ui.toast(t('backup.done'), { kind: 'success' })
  } catch (err) {
    ui.toast(errorOf(err), { kind: 'error' })
  } finally {
    busy.value = ''
    await load()
  }
}

async function confirmRestore() {
  return ui.confirm({
    title: t('backup.confirmTitle'),
    body: t('backup.confirmBody', {
      parts: PARTS.filter((part) => parts[part])
        .map(partLabel)
        .join(', '),
    }),
    confirmLabel: t('backup.restore'),
  })
}

async function restore(send) {
  if (!anyPart.value || !(await confirmRestore())) return
  busy.value = 'restore'
  result.value = null
  try {
    result.value = (await send({ ...parts })).data
    ui.toast(t('backup.restored'), { kind: 'success' })
  } catch (err) {
    ui.toast(errorOf(err), { kind: 'error' })
  } finally {
    busy.value = ''
  }
}

function restoreSaved(item) {
  return restore((options) => API.restoreBackup(item.name, options))
}

async function restoreFile(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) return
  await restore((options) => API.restoreBackupFile(file, options))
}

onMounted(load)
</script>
