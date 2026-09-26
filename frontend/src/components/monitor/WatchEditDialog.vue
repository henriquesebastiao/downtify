<template>
  <UiModal
    :open="!!watch"
    :title="t('monitor.editTitle')"
    width="sm:max-w-xl"
    @close="$emit('close')"
  >
    <form
      v-if="watch"
      :id="formId"
      class="flex flex-col gap-5"
      @submit.prevent="save"
    >
      <div class="flex items-center gap-3">
        <CoverArt
          :src="cover"
          :name="watch.name"
          :round="kind === 'artist'"
          :icon="kind === 'artist' ? 'user' : 'playlist'"
          rounded="rounded-[10px]"
          :letter-size="18"
          class="size-12"
        />
        <div class="min-w-0 flex-1">
          <p class="truncate font-semibold text-fg">{{ watch.name }}</p>
          <p class="text-xs text-muted">
            {{
              kind === 'artist'
                ? t('monitor.kindArtist')
                : t('monitor.kindPlaylist')
            }}
          </p>
        </div>
        <WatchSourceBadge :source="watch.source" />
      </div>

      <div class="flex flex-col gap-1.5">
        <UiInput
          v-model="url"
          :label="t('monitor.link')"
          type="url"
          icon="link"
          mono
          :error="urlError"
          :hint="
            kind === 'artist'
              ? t('monitor.editLinkHintArtist')
              : t('monitor.editLinkHintPlaylist')
          "
        />
        <div class="flex flex-wrap gap-1">
          <UiButton
            size="sm"
            variant="ghost"
            icon="copy"
            type="button"
            @click="copy"
          >
            {{ t('monitor.copyLink') }}
          </UiButton>
          <UiButton
            size="sm"
            variant="ghost"
            icon="arrow-up-right"
            :href="watch.url"
          >
            {{ t('monitor.openSource') }}
          </UiButton>
          <UiButton
            v-if="urlChanged"
            size="sm"
            variant="ghost"
            icon="retry"
            type="button"
            @click="url = watch.url"
          >
            {{ t('monitor.undoLink') }}
          </UiButton>
        </div>
      </div>

      <div class="grid gap-4 sm:grid-cols-2">
        <label class="flex flex-col gap-1.5">
          <span class="text-[13px] font-semibold text-fg-3">{{
            t('monitor.interval')
          }}</span>
          <UiSelect
            v-model="interval"
            :options="intervalOptions(t, watch.interval_minutes)"
            :label="t('monitor.interval')"
            icon="clock"
            block
          />
        </label>
        <div class="flex flex-col gap-1.5">
          <span class="text-[13px] font-semibold text-fg-3">{{
            t('monitor.colActive')
          }}</span>
          <div class="flex h-10 items-center">
            <UiSwitch v-model="enabled" :aria-label="t('monitor.colActive')" />
            <span class="ml-3 text-sm text-muted">{{
              enabled ? t('monitor.activeOn') : t('monitor.activeOff')
            }}</span>
          </div>
        </div>
      </div>

      <ReleaseFilters
        v-if="kind === 'artist'"
        v-model:types="releaseTypes"
        v-model:new-only="newOnly"
        existing
        :was-new-only="!!watch.new_only"
        class="rounded-[12px] border border-line-2 px-4 py-3"
      />

      <dl
        class="grid grid-cols-[auto_1fr] gap-x-6 gap-y-2 rounded-[12px] bg-surface-2 px-4 py-3 text-[13px]"
      >
        <dt class="text-muted">{{ t('monitor.added') }}</dt>
        <dd class="text-fg-2">{{ formatDate(watch.created_at) }}</dd>
        <dt class="text-muted">{{ t('monitor.colLastChecked') }}</dt>
        <dd class="text-fg-2">
          {{
            watch.last_checked
              ? formatDate(watch.last_checked)
              : t('monitor.never')
          }}
        </dd>
        <dt class="text-muted">{{ t('monitor.colSize') }}</dt>
        <dd class="text-fg-2">
          {{
            kind === 'artist'
              ? t('monitor.releases', { count: watch.last_track_count })
              : t('common.tracks', { count: watch.last_track_count })
          }}
        </dd>
      </dl>

      <p
        v-if="error"
        class="flex items-start gap-2 text-sm text-danger"
        role="alert"
      >
        <AppIcon name="alert" :size="16" class="mt-0.5 shrink-0" />{{ error }}
      </p>
    </form>

    <template #footer>
      <UiButton variant="ghost" type="button" @click="$emit('close')">
        {{ t('common.cancel') }}
      </UiButton>
      <UiButton
        variant="primary"
        type="submit"
        :form="formId"
        :loading="saving"
        :disabled="!dirty || !!urlError"
      >
        {{ t('monitor.save') }}
      </UiButton>
    </template>
  </UiModal>
</template>

<script setup>
import { computed, ref, useId, watch as watchValue } from 'vue'
import AppIcon from '../ui/AppIcon.vue'
import CoverArt from '../ui/CoverArt.vue'
import UiButton from '../ui/UiButton.vue'
import UiInput from '../ui/UiInput.vue'
import UiModal from '../ui/UiModal.vue'
import UiSelect from '../ui/UiSelect.vue'
import UiSwitch from '../ui/UiSwitch.vue'
import ReleaseFilters from './ReleaseFilters.vue'
import WatchSourceBadge from './WatchSourceBadge.vue'
import { intervalOptions } from './intervals'
import monitorAPI from '/src/model/monitor'
import { useUi } from '/src/model/ui'
import { watchKind, watchKindOfUrl, watchReleaseTypes } from '/src/lib/watches'
import { useI18n } from '/src/i18n'

const props = defineProps({
  // The watch being edited, or null when closed.
  watch: { type: Object, default: null },
  // Its picture (an artist's photo), when it has one.
  cover: { type: String, default: '' },
})
const emit = defineEmits(['close', 'saved'])

const { t, locale } = useI18n()
const ui = useUi()
const formId = `watch-edit-${useId()}`

const url = ref('')
const interval = ref(360)
const enabled = ref(true)
const releaseTypes = ref([])
const newOnly = ref(false)
const saving = ref(false)
const error = ref('')

watchValue(
  () => props.watch,
  (value) => {
    if (!value) return
    url.value = value.url
    interval.value = value.interval_minutes
    enabled.value = value.enabled
    releaseTypes.value = watchReleaseTypes(value)
    newOnly.value = Boolean(value.new_only)
    error.value = ''
  },
  { immediate: true }
)

const kind = computed(() => watchKind(props.watch))
const trimmedUrl = computed(() => url.value.trim())
const urlChanged = computed(
  () => !!props.watch && trimmedUrl.value !== props.watch.url
)

const urlError = computed(() => {
  if (!urlChanged.value) return ''
  if (!trimmedUrl.value) return t('monitor.linkRequired')
  const detected = watchKindOfUrl(trimmedUrl.value)
  if (detected && detected !== kind.value) {
    return kind.value === 'artist'
      ? t('monitor.needArtistLink')
      : t('monitor.needPlaylistLink')
  }
  return ''
})

const changes = computed(() => {
  const w = props.watch
  if (!w) return {}
  const out = {}
  if (urlChanged.value) out.url = trimmedUrl.value
  if (interval.value !== w.interval_minutes)
    out.interval_minutes = interval.value
  if (enabled.value !== w.enabled) out.enabled = enabled.value
  if (kind.value === 'artist') {
    if (releaseTypes.value.join() !== watchReleaseTypes(w).join())
      out.release_types = releaseTypes.value
    if (newOnly.value !== Boolean(w.new_only)) out.new_only = newOnly.value
  }
  return out
})
const dirty = computed(() => Object.keys(changes.value).length > 0)

function formatDate(value) {
  try {
    return new Intl.DateTimeFormat(locale.value, {
      dateStyle: 'medium',
      timeStyle: 'short',
    }).format(new Date(value))
  } catch {
    return value
  }
}

async function copy() {
  try {
    await navigator.clipboard.writeText(props.watch.url)
    ui.toast(t('monitor.linkCopied'), { kind: 'success' })
  } catch {
    ui.toast(t('toast.actionFailed'), { kind: 'error' })
  }
}

async function save() {
  if (!dirty.value || urlError.value || saving.value) return
  saving.value = true
  error.value = ''
  const before = props.watch
  try {
    const res = await monitorAPI.updateMonitoredPlaylist(
      before.id,
      changes.value
    )
    const updated = res.data
    const retargeted = updated.spotify_id !== before.spotify_id
    ui.toast(
      retargeted
        ? t('monitor.retargeted', { name: updated.name })
        : t('monitor.saved'),
      { kind: 'success' }
    )
    emit('saved', updated)
    emit('close')
  } catch (err) {
    error.value = err?.response?.data?.detail || t('toast.actionFailed')
  } finally {
    saving.value = false
  }
}
</script>
