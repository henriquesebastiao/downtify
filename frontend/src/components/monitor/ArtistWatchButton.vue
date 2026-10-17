<template>
  <UiButton
    :variant="variant"
    icon="radar"
    :loading="state.busy.value"
    :disabled="state.followed.value || !ready"
    @click="follow"
  >
    {{ state.followed.value ? t('nav.monitor') : t('monitor.watchArtist') }}
  </UiButton>
  <UiModal
    :open="state.open.value"
    :title="t('monitor.watchArtist')"
    :description="name"
    @close="close"
  >
    <form :id="formId" class="flex flex-col gap-4" @submit.prevent="submit">
      <p class="text-sm text-muted">{{ t('monitor.artistLinkFallback') }}</p>
      <UiInput
        v-model="state.url.value"
        :label="t('monitor.urlLabelArtist')"
        :placeholder="t('monitor.urlPlaceholderArtist')"
        :hint="t('monitor.needSpotifyArtist')"
        type="url"
        :error="state.error.value"
      />
      <ReleaseFilters
        v-model:types="state.releaseTypes.value"
        v-model:new-only="state.newOnly.value"
      />
    </form>
    <template #footer>
      <UiButton variant="ghost" :disabled="state.busy.value" @click="close">{{
        t('common.cancel')
      }}</UiButton>
      <UiButton
        type="submit"
        :form="formId"
        variant="primary"
        :loading="state.busy.value"
        :disabled="!valid"
        >{{ t('monitor.watchArtist') }}</UiButton
      >
    </template>
  </UiModal>
</template>

<script setup>
import { computed, useId, watch } from 'vue'
import UiButton from '../ui/UiButton.vue'
import UiInput from '../ui/UiInput.vue'
import UiModal from '../ui/UiModal.vue'
import ReleaseFilters from './ReleaseFilters.vue'
import { useArtistWatch } from '/src/model/artistWatch'
import { classifyInput } from '/src/lib/input'
import { useUi } from '/src/model/ui'
import { useI18n } from '/src/i18n'

const props = defineProps({
  name: { type: String, required: true },
  spotifyId: { type: String, default: '' },
  ready: { type: Boolean, default: true },
  variant: { type: String, default: 'ghost' },
})
const { t } = useI18n()
const ui = useUi()
const state = useArtistWatch()
const formId = `artist-watch-${useId()}`
const valid = computed(() => {
  const input = classifyInput(state.url.value)
  return input.kind === 'artist' && input.source === 'spotify'
})
watch(
  () => props.name,
  () => state.reset()
)
function close() {
  if (!state.busy.value) state.open.value = false
}
function announce(success) {
  if (success)
    ui.toast(t('toast.watching', { name: props.name }), { kind: 'success' })
}
async function follow() {
  announce(await state.follow(props.spotifyId))
}
async function submit() {
  announce(await state.submit())
}
</script>
