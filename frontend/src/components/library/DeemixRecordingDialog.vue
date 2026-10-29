<template>
  <UiModal
    :open="Boolean(job)"
    :title="t('upgrade.chooseRecording')"
    :description="t('upgrade.chooseRecordingHint')"
    @close="$emit('close')"
  >
    <form class="flex flex-col gap-4" @submit.prevent="previewLink">
      <p class="text-sm font-semibold">{{ job?.title }} · {{ job?.artist }}</p>
      <UiInput
        v-model="url"
        :label="t('upgrade.recordingLink')"
        placeholder="https://www.deezer.com/track/…"
        :error="error"
      />
      <UiButton type="submit" :loading="loading" :disabled="!recordingId">{{
        t('upgrade.previewRecording')
      }}</UiButton>
    </form>
    <div v-if="preview" class="mt-4 rounded-control border border-line-2 p-4">
      <p class="font-semibold">{{ preview.name }}</p>
      <p class="text-sm text-muted">{{ preview.subtitle }}</p>
      <p class="text-sm">
        {{ preview.tracks[0].album_name }} ·
        {{ formatDuration(preview.tracks[0].duration) }}
      </p>
      <p class="mt-3 text-sm text-muted">
        {{ t('upgrade.recordingReviewHint') }}
      </p>
    </div>
    <template #footer>
      <UiButton variant="secondary" @click="$emit('close')">{{
        t('common.cancel')
      }}</UiButton>
      <UiButton
        :disabled="!preview || loading"
        @click="$emit('choose', { file: job.file, id: recordingId })"
        >{{ t('upgrade.analyzeRecording') }}</UiButton
      >
    </template>
  </UiModal>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import UiModal from '/src/components/ui/UiModal.vue'
import UiButton from '/src/components/ui/UiButton.vue'
import UiInput from '/src/components/ui/UiInput.vue'
import API from '/src/model/api'
import { formatDuration } from '/src/lib/format'
import { deezerRecordingId } from '/src/lib/upgrade'
import { useI18n } from '/src/i18n'

const props = defineProps({ job: { type: Object, default: null } })
defineEmits(['close', 'choose'])
const { t } = useI18n()
const url = ref(''),
  preview = ref(null),
  error = ref(''),
  loading = ref(false)
const recordingId = computed(() => deezerRecordingId(url.value))
let generation = 0
watch(
  () => props.job,
  () => {
    url.value = ''
    preview.value = null
    error.value = ''
    loading.value = false
    generation++
  }
)
watch(url, () => {
  preview.value = null
  error.value = ''
  loading.value = false
  generation++
})
async function previewLink() {
  if (!recordingId.value) return
  const request = ++generation
  loading.value = true
  error.value = ''
  try {
    const { data } = await API.resolveUrl(
      `https://www.deezer.com/track/${recordingId.value}`
    )
    if (request !== generation) return
    if (data.kind !== 'track' || data.tracks?.length !== 1)
      throw new Error('not-track')
    preview.value = data
  } catch {
    if (request === generation)
      error.value = t('upgrade.recordingPreviewFailed')
  } finally {
    if (request === generation) loading.value = false
  }
}
</script>
