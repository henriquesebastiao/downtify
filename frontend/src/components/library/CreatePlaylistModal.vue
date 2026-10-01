<template>
  <UiModal
    :open="open"
    :title="t('playlists.createTitle')"
    :description="t('playlists.createHint')"
    @close="close"
  >
    <form class="flex flex-col gap-4" @submit.prevent="submit">
      <ul v-if="files.length && manuals.length" class="flex flex-col gap-1">
        <li v-for="playlist in manuals" :key="playlist.name">
          <button
            type="button"
            class="flex h-11 w-full items-center gap-3 rounded-[10px] px-2 text-left text-sm hover:bg-surface-2"
            @click="addTo(playlist)"
          >
            <AppIcon name="playlist" :size="17" />
            <span class="min-w-0 flex-1 truncate">{{ playlist.title }}</span>
          </button>
        </li>
      </ul>
      <UiInput
        v-model="name"
        :label="t('playlists.name')"
        :placeholder="t('playlists.namePlaceholder')"
        icon="playlist"
      />
    </form>
    <template #footer>
      <UiButton variant="ghost" @click="close">{{
        t('common.cancel')
      }}</UiButton>
      <UiButton
        variant="primary"
        icon="plus"
        :disabled="!name.trim() || saving"
        :loading="saving"
        @click="submit"
      >
        {{ t('playlists.create') }}
      </UiButton>
    </template>
  </UiModal>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import AppIcon from '../ui/AppIcon.vue'
import UiButton from '../ui/UiButton.vue'
import UiInput from '../ui/UiInput.vue'
import UiModal from '../ui/UiModal.vue'
import { usePlaylistActions } from '/src/model/playlistActions'
import { useI18n } from '/src/i18n'

const { t } = useI18n()
const actions = usePlaylistActions()
const name = ref('')
const saving = ref(false)
const files = computed(() => actions.createFiles.value)
const manuals = computed(() => actions.manuals())

const open = actions.createOpen

watch(open, (value) => {
  if (value) name.value = ''
})

function close() {
  open.value = false
}

async function addTo(playlist) {
  if (saving.value) return
  saving.value = true
  try {
    await actions.addFiles(playlist, files.value)
    close()
  } finally {
    saving.value = false
  }
}

async function submit() {
  const title = name.value.trim()
  if (!title || saving.value) return
  saving.value = true
  try {
    await actions.createNamed(title, actions.createFiles.value)
    close()
  } catch {
    /* toast in createNamed's caller — wrap createNamed */
  } finally {
    saving.value = false
  }
}
</script>
