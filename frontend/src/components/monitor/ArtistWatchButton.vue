<template>
  <!-- Watch artist on a Library artist page; see model/artistWatch.js. -->
  <UiButton
    v-if="state.followed.value"
    :variant="variant"
    icon="radar"
    :to="{ name: 'Monitor', params: { tab: 'artists' } }"
  >
    {{ t('nav.monitor') }}
  </UiButton>
  <UiButton
    v-else
    :variant="variant"
    icon="radar"
    :loading="state.busy.value && !state.open.value"
    :disabled="state.busy.value"
    @click="follow"
  >
    {{ t('monitor.watchArtist') }}
  </UiButton>
  <UiModal
    :open="state.open.value"
    :title="t('artistSuggestions.choose', { name })"
    width="sm:max-w-2xl"
    @close="close"
  >
    <div class="flex flex-col gap-4">
      <p
        class="text-sm"
        :class="state.lookupFailed.value ? 'text-danger' : 'text-muted'"
      >
        {{ message }}
      </p>
      <p v-if="state.error.value" class="text-sm text-danger" role="alert">
        {{ state.error.value }}
      </p>
      <ReleaseFilters
        v-model:types="state.releaseTypes.value"
        v-model:new-only="state.newOnly.value"
      />
      <ArtistCandidateList
        v-if="state.candidates.value.length"
        :candidates="state.candidates.value"
        :busy="state.busy.value"
        :chosen="state.chosen.value"
        @choose="choose"
      />
      <form :id="formId" @submit.prevent="submit">
        <UiInput
          v-model="state.url.value"
          :label="t('monitor.urlLabelArtist')"
          :placeholder="t('monitor.urlPlaceholderArtist')"
          type="url"
        />
      </form>
    </div>
    <template #footer>
      <UiButton variant="ghost" :disabled="state.busy.value" @click="close">{{
        t('common.cancel')
      }}</UiButton>
      <UiButton
        type="submit"
        :form="formId"
        variant="primary"
        :loading="state.busy.value && state.chosen.value === linkUrl"
        :disabled="!valid || state.busy.value"
        >{{ t('monitor.watchArtist') }}</UiButton
      >
    </template>
  </UiModal>
</template>

<script setup>
import { computed, useId, watch } from 'vue'
import { useRouter } from 'vue-router'
import UiButton from '../ui/UiButton.vue'
import UiInput from '../ui/UiInput.vue'
import UiModal from '../ui/UiModal.vue'
import ArtistCandidateList from './ArtistCandidateList.vue'
import ReleaseFilters from './ReleaseFilters.vue'
import { isArtistLink, useArtistWatch } from '/src/model/artistWatch'
import { classifyInput } from '/src/lib/input'
import { useUi } from '/src/model/ui'
import { useI18n } from '/src/i18n'

const props = defineProps({
  name: { type: String, required: true },
  variant: { type: String, default: 'ghost' },
})
const { t } = useI18n()
const router = useRouter()
const ui = useUi()
const state = useArtistWatch()
const formId = `artist-watch-${useId()}`
const valid = computed(() => isArtistLink(state.url.value))
const linkUrl = computed(() =>
  valid.value ? classifyInput(state.url.value).url : ''
)
const message = computed(() => {
  if (state.lookupFailed.value) return t('artistSuggestions.lookupFailed')
  if (!state.candidates.value.length)
    return t('artistSuggestions.notFound', { name: props.name })
  return t('artistSuggestions.chooseHelp', { name: props.name })
})

watch(
  () => props.name,
  () => state.reset()
)

function close() {
  if (!state.busy.value) state.open.value = false
}

function announce(added) {
  if (!added) return
  ui.toast(t('toast.watching', { name: props.name }), {
    kind: 'success',
    action: {
      label: t('nav.monitor'),
      run: () => router.push({ name: 'Monitor', params: { tab: 'artists' } }),
    },
  })
}

async function follow() {
  announce(await state.follow(props.name))
}

async function choose(candidate) {
  announce(await state.choose(candidate))
}

async function submit() {
  announce(await state.submit())
}
</script>
