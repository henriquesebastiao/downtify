<template>
  <div class="flex flex-col gap-2">
    <input
      ref="picker"
      type="file"
      accept=".csv,text/csv"
      class="hidden"
      @change="onPick"
    />
    <UiButton
      variant="secondary"
      icon="file-music"
      :loading="busy"
      @click="picker?.click()"
    >
      {{ t('queue.importButton') }}
    </UiButton>
    <p v-if="error" class="text-xs text-danger">{{ error }}</p>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import UiButton from '../ui/UiButton.vue'
import { useDownloadManager } from '/src/model/download'
import { useUi } from '/src/model/ui'
import { useI18n } from '/src/i18n'

const { t } = useI18n()
const dm = useDownloadManager()
const ui = useUi()
const router = useRouter()
const picker = ref(null)
const busy = ref(false)
const error = ref('')

async function onPick(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) return
  busy.value = true
  error.value = ''
  try {
    const result = await dm.fromCsvFile(file, file.name.replace(/\.csv$/i, ''))
    ui.toast(t('toast.csvQueued', { count: result?.count ?? 0 }), {
      kind: 'success',
    })
    router.push({ name: 'Queue', params: { tab: 'queued' } })
  } catch (err) {
    error.value = err?.response?.data?.detail || t('queue.importFailed')
  } finally {
    busy.value = false
  }
}
</script>
