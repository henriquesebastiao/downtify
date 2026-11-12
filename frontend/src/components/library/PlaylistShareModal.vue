<template>
  <UiModal
    :open="open"
    :title="t('sharing.title', { name: playlist?.title || '' })"
    :description="t('sharing.hint')"
    @close="close"
  >
    <div class="flex flex-col gap-4">
      <div class="flex flex-col gap-2" role="radiogroup">
        <button
          v-for="option in options"
          :key="option.value"
          type="button"
          role="radio"
          :aria-checked="visibility === option.value"
          class="flex items-start gap-3 rounded-control border px-3.5 py-3 text-left transition-colors"
          :class="
            visibility === option.value
              ? 'border-accent bg-accent/10'
              : 'border-line-2 hover:bg-surface-2'
          "
          @click="visibility = option.value"
        >
          <AppIcon :name="option.icon" :size="18" class="mt-0.5 shrink-0" />
          <span class="min-w-0">
            <span class="block text-sm font-semibold">{{ option.label }}</span>
            <span class="block text-[13px] text-muted">{{ option.hint }}</span>
          </span>
        </button>
      </div>

      <div v-if="visibility === 'shared'" class="flex flex-col gap-2">
        <p v-if="loading" class="text-[13px] text-muted">
          {{ t('sharing.loadingUsers') }}
        </p>
        <p v-else-if="!usernames.length" class="text-[13px] text-muted">
          {{ t('sharing.noOtherUsers') }}
        </p>
        <template v-else>
          <UiInput
            v-if="usernames.length > 8"
            v-model="filter"
            :label="t('sharing.findUser')"
            icon="search"
          />
          <ul
            class="flex max-h-56 flex-col overflow-y-auto rounded-control border border-line-2"
          >
            <li v-for="name in shownUsernames" :key="name">
              <label
                class="flex cursor-pointer items-center gap-3 px-3.5 py-2.5 text-sm hover:bg-surface-2"
              >
                <input
                  v-model="picked"
                  type="checkbox"
                  :value="name"
                  class="size-4 accent-[var(--color-accent)]"
                />
                <span class="truncate">{{ name }}</span>
              </label>
              <label
                v-if="playlist?.manual && picked.includes(name)"
                class="flex cursor-pointer items-center gap-3 py-2 pr-3.5 pl-10 text-[13px] text-muted hover:bg-surface-2"
              >
                <input
                  v-model="editors"
                  type="checkbox"
                  :value="name"
                  class="size-4 accent-[var(--color-accent)]"
                />
                {{ t('collaboration.canEdit') }}
              </label>
            </li>
          </ul>
          <!-- An imported playlist follows its source: editors work on a
               copy, which stays the user's own. -->
          <div
            v-if="!playlist?.manual"
            class="flex flex-col items-start gap-2 text-[13px] text-muted"
          >
            <p>{{ t('collaboration.copyHint') }}</p>
            <UiButton
              variant="secondary"
              size="sm"
              icon="copy"
              :loading="copying"
              @click="makeCollaborativeCopy"
            >
              {{ t('collaboration.copy') }}
            </UiButton>
          </div>
        </template>
      </div>

      <p v-if="error" class="text-[13px] text-danger" role="alert">
        {{ error }}
      </p>
    </div>
    <template #footer>
      <UiButton variant="ghost" @click="close">{{
        t('common.cancel')
      }}</UiButton>
      <UiButton
        variant="primary"
        icon="check"
        :disabled="!canSave"
        :loading="saving"
        @click="save"
      >
        {{ t('apps.save') }}
      </UiButton>
    </template>
  </UiModal>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import AppIcon from '../ui/AppIcon.vue'
import UiButton from '../ui/UiButton.vue'
import UiInput from '../ui/UiInput.vue'
import UiModal from '../ui/UiModal.vue'
import API from '/src/model/api'
import { useLibrary } from '/src/model/library'
import { usePlaylistActions } from '/src/model/playlistActions'
import { useUi } from '/src/model/ui'
import { useI18n } from '/src/i18n'

const { t } = useI18n()
const actions = usePlaylistActions()
const library = useLibrary()
const ui = useUi()

const open = actions.shareOpen
const playlist = computed(() => actions.sharePlaylist.value)
const visibility = ref('private')
const picked = ref([])
const editors = ref([])
const usernames = ref([])
const filter = ref('')
const loading = ref(false)
const saving = ref(false)
const copying = ref(false)
const error = ref('')
// The people picked for an imported playlist, carried over to its
// collaborative copy as its editors.
let carried = null

const options = computed(() => [
  {
    value: 'private',
    icon: 'lock',
    label: t('sharing.private'),
    hint: t('sharing.privateHint'),
  },
  {
    value: 'shared',
    icon: 'users',
    label: t('sharing.shared'),
    hint: t('sharing.sharedHint'),
  },
  {
    value: 'public',
    icon: 'globe',
    label: t('sharing.public'),
    hint: t('sharing.publicHint'),
  },
])

const shownUsernames = computed(() => {
  const needle = filter.value.trim().toLowerCase()
  return needle
    ? usernames.value.filter((name) => name.toLowerCase().includes(needle))
    : usernames.value
})

const canSave = computed(
  () =>
    !saving.value &&
    !(visibility.value === 'shared' && picked.value.length === 0)
)

watch(open, async (value) => {
  if (!value) return
  const current = playlist.value
  const seed = carried
  carried = null
  visibility.value = seed ? 'shared' : current?.visibility || 'private'
  picked.value = [...(seed || current?.sharedWith || [])]
  editors.value = [...(seed || current?.editors || [])]
  filter.value = ''
  error.value = ''
  loading.value = true
  try {
    usernames.value = (await API.listShareableUsernames()).data?.usernames || []
  } catch {
    usernames.value = []
  } finally {
    loading.value = false
  }
})

function close() {
  open.value = false
}

async function makeCollaborativeCopy() {
  const people = [...picked.value]
  copying.value = true
  const created = await actions.copy(playlist.value)
  copying.value = false
  if (!created) return
  close()
  await nextTick()
  const copied = library.findPlaylist(created)
  if (!copied) return
  carried = people.length ? people : null
  actions.openShare(copied)
}

async function save() {
  const current = playlist.value
  if (!current || !canSave.value) return
  saving.value = true
  error.value = ''
  try {
    const shared = visibility.value === 'shared'
    await API.setPlaylistVisibility(
      current.name,
      visibility.value,
      shared ? picked.value : [],
      current.manual
        ? editors.value.filter((name) => shared && picked.value.includes(name))
        : undefined
    )
    await library.refreshPlaylists()
    ui.toast(t(`sharing.saved.${visibility.value}`, { name: current.title }), {
      kind: 'success',
    })
    close()
  } catch (err) {
    error.value = err?.response?.data?.detail || t('toast.actionFailed')
  } finally {
    saving.value = false
  }
}
</script>
