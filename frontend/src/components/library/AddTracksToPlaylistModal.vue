<template>
  <UiModal
    :open="open"
    :title="t('playlists.addSongsTitle', { name: playlist?.title || '' })"
    :description="t('playlists.addSongsHint')"
    width="sm:max-w-lg"
    @close="close"
  >
    <div class="flex flex-col gap-3">
      <label
        class="flex h-10 items-center gap-2.5 rounded-control border border-line-2 bg-surface px-3"
      >
        <AppIcon name="filter" :size="16" class="text-faint" />
        <input
          v-model="query"
          type="search"
          :placeholder="t('library.filterPlaceholder')"
          class="h-full min-w-0 flex-1 bg-transparent text-sm outline-none placeholder:text-faint"
        />
      </label>
      <ul class="max-h-80 overflow-y-auto">
        <li
          v-for="track in visible"
          :key="track.file"
          class="flex h-12 items-center gap-3 rounded-[10px] px-1 hover:bg-surface-2"
        >
          <input
            :id="`add-${track.file}`"
            v-model="picked"
            type="checkbox"
            :value="track.file"
            class="size-4 accent-accent"
          />
          <label
            :for="`add-${track.file}`"
            class="min-w-0 flex-1 cursor-pointer"
          >
            <p class="truncate text-sm font-semibold">{{ track.title }}</p>
            <p class="truncate text-[13px] text-muted">{{ track.artist }}</p>
          </label>
        </li>
      </ul>
    </div>
    <template #footer>
      <UiButton variant="ghost" @click="close">{{
        t('common.cancel')
      }}</UiButton>
      <UiButton
        variant="primary"
        icon="plus"
        :disabled="!picked.length || saving"
        :loading="saving"
        @click="submit"
      >
        {{ t('playlists.addSongs') }}
      </UiButton>
    </template>
  </UiModal>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { watchDebounced } from '@vueuse/core'
import AppIcon from '../ui/AppIcon.vue'
import UiButton from '../ui/UiButton.vue'
import UiModal from '../ui/UiModal.vue'
import { useLibrary } from '/src/model/library'
import { usePlaylistActions } from '/src/model/playlistActions'
import { useI18n } from '/src/i18n'

const { t } = useI18n()
const library = useLibrary()
const actions = usePlaylistActions()
const query = ref('')
const hits = ref([])
const picked = ref([])
const saving = ref(false)

const open = computed({
  get: () => actions.addOpen.value,
  set: (value) => {
    actions.addOpen.value = value
  },
})
const playlist = computed(() => actions.addPlaylist.value)

const visible = computed(() => {
  const have = new Set((playlist.value?.tracks || []).map((item) => item.file))
  return hits.value.filter((track) => !have.has(track.file))
})

async function searchLibrary(text) {
  hits.value = await library.searchTracks(text, { limit: 80 })
}

watch(open, (value) => {
  if (value) {
    query.value = ''
    picked.value = []
    searchLibrary('')
  }
})

watchDebounced(
  query,
  (text) => {
    if (open.value) searchLibrary(text)
  },
  { debounce: 200 }
)

function close() {
  open.value = false
}

async function submit() {
  if (!playlist.value || !picked.value.length || saving.value) return
  saving.value = true
  try {
    await actions.addFiles(playlist.value, picked.value)
    close()
  } finally {
    saving.value = false
  }
}
</script>
