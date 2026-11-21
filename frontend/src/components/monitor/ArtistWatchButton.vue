<template>
  <!-- Watch artist on a Library artist page; see model/artistWatch.js.
       Once watched it says so, with the watch's page and Stop watching. -->
  <UiMenu v-if="state.followed.value" :items="watchedMenu">
    <template #trigger>
      <UiButton :variant="variant" icon="check" :loading="state.stopping.value">
        {{ t('monitor.watched') }}
      </UiButton>
    </template>
  </UiMenu>
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
import UiMenu from '../ui/UiMenu.vue'
import UiModal from '../ui/UiModal.vue'
import ArtistCandidateList from './ArtistCandidateList.vue'
import ReleaseFilters from './ReleaseFilters.vue'
import { isArtistLink, useArtistWatch } from '/src/model/artistWatch'
import { classifyInput } from '/src/lib/input'
import { watchRouteFor } from '/src/lib/watchStats'
import { useAuth } from '/src/model/auth'
import { useUi } from '/src/model/ui'
import { useI18n } from '/src/i18n'

const props = defineProps({
  name: { type: String, required: true },
  variant: { type: String, default: 'ghost' },
})
const { t } = useI18n()
const router = useRouter()
const ui = useUi()
const auth = useAuth()
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
  (name) => {
    state.reset()
    state.check(name, auth.user.value?.id ?? null)
  },
  { immediate: true }
)

const monitorRoute = { name: 'Monitor', params: { tab: 'artists' } }
const watchedMenu = computed(() => [
  {
    label: t('watchStats.details'),
    icon: 'activity',
    action: () => router.push(watchRouteFor(state.watch.value) || monitorRoute),
  },
  {
    label: t('nav.monitor'),
    icon: 'radar',
    action: () => router.push(monitorRoute),
  },
  { divider: true },
  {
    label: t('monitor.stop'),
    icon: 'trash',
    danger: true,
    disabled: !state.watch.value?.id,
    action: stopWatching,
  },
])

async function stopWatching() {
  const ok = await ui.confirm({
    title: t('confirm.stopWatchingTitle', {
      name: state.watch.value?.name || props.name,
    }),
    body: t('confirm.stopWatchingBody'),
    confirmLabel: t('monitor.stop'),
    danger: true,
  })
  if (!ok) return
  if (!(await state.stop())) {
    ui.toast(t('toast.actionFailed'), { kind: 'error' })
  }
}

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
