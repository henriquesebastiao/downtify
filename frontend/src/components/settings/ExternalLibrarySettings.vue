<template>
  <SettingGroup
    :title="t('settings.externalLibraryTitle')"
    :description="t('settings.externalLibraryHint')"
  >
    <div class="flex flex-col gap-3 px-5 py-4">
      <div
        v-for="(folder, index) in folders"
        :key="index"
        class="flex flex-col gap-1.5"
      >
        <label v-if="index === 0" class="text-[13px] font-semibold text-fg-3">{{
          t('settings.externalLibraryFolder')
        }}</label>
        <div class="flex items-center gap-2">
          <PathSuggestInput
            :model-value="folder"
            :placeholder="t('settings.externalLibraryPlaceholder')"
            @update:model-value="setFolder(index, $event)"
          />
          <UiButton
            variant="ghost"
            icon="trash"
            :aria-label="t('settings.externalLibraryRemove')"
            @click="removeFolder(index)"
          />
        </div>
        <p v-if="index === folders.length - 1" class="text-xs text-muted">
          {{ folderHint }}
        </p>
      </div>
      <div class="flex flex-wrap items-center gap-2">
        <UiButton variant="secondary" icon="plus" @click="addFolder">
          {{ t('settings.externalLibraryAdd') }}
        </UiButton>
        <UiButton
          variant="primary"
          icon="refresh"
          :loading="syncing"
          :disabled="!hasFolder || syncing"
          @click="sync"
        >
          {{ t('settings.externalLibrarySync') }}
        </UiButton>
      </div>
      <p
        v-if="statusLine"
        class="text-[13px]"
        :class="syncFailed ? 'text-danger' : 'text-accent'"
      >
        {{ statusLine }}
      </p>
      <p v-if="syncing && progress.total" class="text-[13px] text-muted">
        {{
          t('settings.externalLibrarySyncProgress', {
            done: progress.done,
            total: progress.total,
          })
        }}
      </p>
      <div
        v-if="!syncing && syncLog.length"
        class="max-h-64 overflow-y-auto rounded-lg border border-line-3 bg-surface-2"
        role="status"
        aria-live="polite"
      >
        <p
          class="sticky top-0 border-b border-line-3 bg-surface-2 px-3 py-2 text-[11px] font-medium uppercase tracking-wide text-muted"
        >
          {{ t('settings.externalLibraryLogTitle') }}
        </p>
        <ul class="flex flex-col gap-0 px-3 py-2">
          <li
            v-for="(item, index) in syncLog"
            :key="`${item.status}-${item.file}-${index}`"
            class="flex items-start gap-2 py-1 text-[13px]"
            :class="logTone(item.status)"
          >
            <AppIcon
              :name="logIcon(item.status)"
              :size="15"
              stroke-width="2.2"
              class="mt-0.5 shrink-0"
            />
            <span class="min-w-0 text-pretty text-fg-3">
              {{ logLine(item) }}
            </span>
          </li>
        </ul>
      </div>
    </div>
  </SettingGroup>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import PathSuggestInput from '/src/components/settings/PathSuggestInput.vue'
import SettingGroup from '/src/components/settings/SettingGroup.vue'
import AppIcon from '/src/components/ui/AppIcon.vue'
import UiButton from '/src/components/ui/UiButton.vue'
import API from '/src/model/api'
import { useLibrary } from '/src/model/library'
import { useSettingsManager } from '/src/model/settings'
import { useI18n } from '/src/i18n'

const { t } = useI18n()
const sm = useSettingsManager()
const library = useLibrary()

const folders = computed(() => {
  const list = sm.settings.value.external_library?.folders
  return Array.isArray(list) ? list : []
})

const hasFolder = computed(() =>
  folders.value.some((item) => String(item || '').trim())
)

const folderHint = computed(() => t('settings.externalLibraryFolderHint'))

const syncing = ref(false)
const syncFailed = ref(false)
const statusLine = ref('')
const syncLog = ref([])
const progress = ref({ done: 0, total: 0, current: '' })
let wasRunning = false
let pollTimer = null
let stopWs = null

const LOG_ICONS = {
  imported: 'check',
  duplicate: 'copy',
  duplicate_folder: 'copy',
  error: 'x',
  missing_folder: 'alert',
}

function logIcon(status) {
  return LOG_ICONS[status] || 'alert'
}

function logTone(status) {
  if (status === 'imported') return 'text-accent'
  if (status === 'error' || status === 'missing_folder') return 'text-danger'
  return 'text-muted'
}

function logLine(item) {
  const artist =
    String(item.artist || '').trim() ||
    t('settings.externalLibraryLogUnknownArtist')
  const title = String(item.title || '').trim() || String(item.file || '')
  const params = { artist, title, file: String(item.file || '') }
  let line
  if (item.status === 'imported') {
    line = t('settings.externalLibraryLogImported', params)
  } else if (item.status === 'duplicate') {
    line = t('settings.externalLibraryLogDuplicate', params)
  } else if (item.status === 'duplicate_folder') {
    line = t('settings.externalLibraryLogDuplicateFolder', params)
  } else if (item.status === 'missing_folder') {
    line = t('settings.externalLibraryLogMissingFolder', params)
  } else {
    line = t('settings.externalLibraryLogError', params)
  }
  const notes = []
  if (item.lyrics) notes.push(t('settings.externalLibraryLogNoteLyrics'))
  if (item.cover) notes.push(t('settings.externalLibraryLogNoteCover'))
  if (item.genre) notes.push(t('settings.externalLibraryLogNoteGenre'))
  if (item.lyrics_missing) {
    notes.push(t('settings.externalLibraryLogNoteNoLyrics'))
  }
  if (notes.length) {
    return `${line} · ${notes.join(' · ')}`
  }
  return line
}

function summaryFromResult(data) {
  if (!data || typeof data !== 'object') return ''
  const added = Number(data.added) || 0
  const skipped = Number(data.skipped_duplicates) || 0
  const missing = Array.isArray(data.missing) ? data.missing.length : 0
  const parts = [t('settings.externalLibrarySynced', { count: added })]
  if (skipped) {
    parts.push(t('settings.externalLibrarySkipped', { count: skipped }))
  }
  if (missing) {
    parts.push(t('settings.externalLibraryMissing', { count: missing }))
  }
  const lyrics = Number(data.lyrics_embedded) || 0
  if (lyrics) {
    parts.push(t('settings.externalLibraryLyrics', { count: lyrics }))
  }
  const covers = Number(data.covers_fetched) || 0
  if (covers) {
    parts.push(t('settings.externalLibraryCovers', { count: covers }))
  }
  const errors = Number(data.errors) || 0
  if (errors) {
    parts.push(t('settings.externalLibraryErrors', { count: errors }))
  }
  return parts.join(' ')
}

function applyStatus(payload) {
  if (!payload || typeof payload !== 'object') return
  const running = payload.state === 'running'
  const justFinished = wasRunning && !running
  wasRunning = running
  syncing.value = running
  progress.value = {
    done: Number(payload.progress?.done) || 0,
    total: Number(payload.progress?.total) || 0,
    current: String(payload.progress?.current || ''),
  }
  if (running) {
    syncFailed.value = false
    statusLine.value = t('settings.externalLibrarySyncing')
    syncLog.value = []
    return
  }
  if (payload.state === 'error' && payload.error) {
    syncFailed.value = true
    statusLine.value = t('settings.externalLibrarySyncError')
  } else {
    syncFailed.value = false
    statusLine.value = summaryFromResult(payload.result)
  }
  syncLog.value = Array.isArray(payload.result?.log) ? payload.result.log : []
  if (justFinished) {
    library.load({ force: true })
  }
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

function startPolling() {
  stopPolling()
  pollTimer = setInterval(async () => {
    try {
      const { data } = await API.getExternalSync()
      applyStatus(data)
      if (data?.state !== 'running') stopPolling()
    } catch {
      stopPolling()
    }
  }, 2000)
}

async function loadStatus() {
  try {
    const { data } = await API.getExternalSync()
    applyStatus(data)
    if (data?.state === 'running') startPolling()
  } catch {
    /* settings still usable without the last log */
  }
}

function ensureBlock() {
  if (!sm.settings.value.external_library) {
    sm.settings.value.external_library = { folders: [] }
  }
  if (!Array.isArray(sm.settings.value.external_library.folders)) {
    sm.settings.value.external_library.folders = []
  }
}

function addFolder() {
  ensureBlock()
  sm.settings.value.external_library.folders.push('')
}

function setFolder(index, value) {
  ensureBlock()
  sm.settings.value.external_library.folders[index] = value
}

async function removeFolder(index) {
  ensureBlock()
  const path = String(
    sm.settings.value.external_library.folders[index] || ''
  ).trim()
  if (!path) {
    sm.settings.value.external_library.folders.splice(index, 1)
    return
  }
  try {
    const { data } = await API.unmapExternalFolder(path)
    sm.rememberExternalFolders(Array.isArray(data.folders) ? data.folders : [])
    for (const id of data.folder_ids || []) {
      if (id) library.forgetByPrefix(`ext/${id}/`)
    }
    await library.load({ force: true })
  } catch {
    statusLine.value = t('settings.externalLibraryUnmapError')
    syncFailed.value = true
  }
}

async function sync() {
  ensureBlock()
  if (sm.dirty.value) {
    const saved = await sm.saveSettings()
    if (!saved) {
      syncing.value = false
      syncFailed.value = true
      statusLine.value = t('settings.externalLibrarySyncError')
      return
    }
  }
  const paths = folders.value.map((item) => String(item || '').trim())
  syncFailed.value = false
  statusLine.value = t('settings.externalLibrarySyncing')
  syncing.value = true
  syncLog.value = []
  try {
    const { data } = await API.syncExternalLibrary(paths)
    applyStatus(data)
    if (data?.state === 'running') startPolling()
  } catch (error) {
    if (error?.response?.status === 409) {
      await loadStatus()
      return
    }
    syncing.value = false
    syncFailed.value = true
    statusLine.value = t('settings.externalLibrarySyncError')
  }
}

onMounted(() => {
  loadStatus()
  stopWs = API.onMessage((data) => {
    if (data?.type !== 'external_sync') return
    applyStatus(data.sync)
    if (data.sync?.state !== 'running') stopPolling()
  })
})

onUnmounted(() => {
  stopPolling()
  if (typeof stopWs === 'function') stopWs()
})
</script>
