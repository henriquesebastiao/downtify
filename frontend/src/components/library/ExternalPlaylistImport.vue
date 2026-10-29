<template>
  <UiButton variant="ghost" icon="folder" @click="show">{{
    t('externalPlaylistImport.open')
  }}</UiButton>
  <UiModal
    :open="open"
    :title="t('externalPlaylistImport.title')"
    @close="open = false"
  >
    <div class="flex flex-col gap-4">
      <p class="text-sm text-muted">{{ t('externalPlaylistImport.hint') }}</p>
      <p v-if="loading" class="text-sm text-muted">
        {{ t('externalPlaylistImport.loading') }}
      </p>
      <p v-else-if="!playlists.length" class="text-sm text-muted">
        {{ t('externalPlaylistImport.empty') }}
      </p>
      <ul class="flex max-h-[55vh] flex-col gap-3 overflow-y-auto">
        <li
          v-for="playlist in playlists"
          :key="playlist.source_id"
          class="rounded-control border border-line-2 p-3"
        >
          <label class="flex items-start gap-3">
            <input
              v-model="selected"
              type="checkbox"
              :value="playlist.source_id"
              :disabled="!playlist.count"
              class="mt-1 size-4 accent-[var(--color-accent)]"
            />
            <span class="min-w-0 flex-1">
              <span class="block break-words text-sm font-semibold">{{
                playlist.name
              }}</span>
              <span class="block text-xs text-muted"
                >{{ playlist.folder }} ·
                {{
                  t('externalPlaylistImport.counts', {
                    count: playlist.count,
                    missing: playlist.missing,
                    duplicates: playlist.duplicates,
                  })
                }}</span
              >
              <span
                v-if="playlist.imported_name"
                class="block text-xs text-accent"
                >{{
                  t('externalPlaylistImport.existing', {
                    name: playlist.imported_name,
                  })
                }}</span
              >
            </span>
          </label>
          <details v-if="playlist.files.length" class="mt-2 text-xs text-muted">
            <summary class="cursor-pointer">
              {{ t('externalPlaylistImport.preview') }}
            </summary>
            <ol class="mt-2 list-decimal pl-5">
              <li
                v-for="file in playlist.files.slice(0, 30)"
                :key="file"
                class="break-words"
              >
                {{ file.split('/').at(-1) }}
              </li>
            </ol>
          </details>
        </li>
      </ul>
      <p v-if="truncated" class="text-sm text-muted">
        {{ t('externalPlaylistImport.truncated') }}
      </p>
      <p v-for="warning in warnings" :key="warning" class="text-xs text-muted">
        {{ warning }}
      </p>
      <p v-if="result" class="text-sm" role="status">{{ result }}</p>
      <p v-if="error" class="text-sm text-danger" role="alert">{{ error }}</p>
    </div>
    <template #footer>
      <UiButton variant="ghost" @click="scan">{{
        t('common.refresh')
      }}</UiButton>
      <UiButton
        variant="primary"
        :loading="saving"
        :disabled="loading || !selected.length || selected.length > 50"
        @click="save"
        >{{
          t('externalPlaylistImport.add', { count: selected.length })
        }}</UiButton
      >
    </template>
  </UiModal>
</template>

<script setup>
import { ref } from 'vue'
import UiButton from '../ui/UiButton.vue'
import UiModal from '../ui/UiModal.vue'
import API from '/src/model/api'
import { useLibrary } from '/src/model/library'
import { useI18n } from '/src/i18n'

const { t } = useI18n()
const library = useLibrary()
const open = ref(false)
const loading = ref(false)
const saving = ref(false)
const playlists = ref([])
const warnings = ref([])
const truncated = ref(false)
const selected = ref([])
const error = ref('')
const result = ref('')

async function show() {
  open.value = true
  result.value = ''
  await scan()
}

async function scan() {
  loading.value = true
  error.value = ''
  selected.value = []
  try {
    const { data } = await API.discoverExternalPlaylists()
    playlists.value = data.playlists || []
    warnings.value = data.warnings || []
    truncated.value = Boolean(data.truncated)
  } catch (err) {
    error.value = err?.response?.data?.detail || t('toast.actionFailed')
  } finally {
    loading.value = false
  }
}

async function save() {
  saving.value = true
  error.value = ''
  try {
    const items = playlists.value
      .filter((item) => selected.value.includes(item.source_id))
      .map(({ source_id, revision }) => ({ source_id, revision }))
    const { data } = await API.importExternalPlaylists(items)
    const rows = data.results || []
    result.value = t('externalPlaylistImport.result', {
      added: rows.filter((row) => row.status === 'added').length,
      existing: rows.filter((row) => row.status === 'already_present').length,
      failed: rows.filter(
        (row) => !['added', 'already_present'].includes(row.status)
      ).length,
    })
    await library.load({ force: true })
    await scan()
  } catch (err) {
    error.value = err?.response?.data?.detail || t('toast.actionFailed')
  } finally {
    saving.value = false
  }
}
</script>
