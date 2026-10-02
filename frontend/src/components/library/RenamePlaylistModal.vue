<template>
  <UiModal
    :open="open"
    :title="t('playlists.renameTitle')"
    :description="t('playlists.renameHint')"
    @close="close"
  >
    <form class="flex flex-col gap-4" @submit.prevent="submit">
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
        icon="pencil"
        :disabled="!canSave"
        :loading="saving"
        @click="submit"
      >
        {{ t('playlists.rename') }}
      </UiButton>
    </template>
  </UiModal>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import UiButton from '../ui/UiButton.vue'
import UiInput from '../ui/UiInput.vue'
import UiModal from '../ui/UiModal.vue'
import { usePlaylistActions } from '/src/model/playlistActions'
import { useI18n } from '/src/i18n'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const actions = usePlaylistActions()
const name = ref('')
const saving = ref(false)

const open = actions.renameOpen
const playlist = computed(() => actions.renamePlaylist.value)
const canSave = computed(() => {
  const next = name.value.trim()
  const current = playlist.value?.name || ''
  return Boolean(next) && next !== current && !saving.value
})

watch(open, (value) => {
  if (value) name.value = playlist.value?.name || ''
})

function close() {
  open.value = false
}

async function submit() {
  const title = name.value.trim()
  const current = playlist.value
  if (!title || !current || saving.value) return
  saving.value = true
  try {
    const renamed = await actions.renameNamed(current, title)
    close()
    if (
      renamed &&
      route.name === 'Playlist' &&
      String(route.query.name || '') === current.name
    ) {
      router.replace({ name: 'Playlist', query: { name: renamed } })
    }
  } catch {
    /* toast in renameNamed */
  } finally {
    saving.value = false
  }
}
</script>
