<template>
  <Transition name="now-playing">
    <div
      v-if="count"
      class="sticky top-[76px] z-20 flex flex-wrap items-center gap-2 rounded-[14px] border border-line-3 bg-surface-2/95 p-2 pl-4 shadow-float backdrop-blur-xl md:top-[84px]"
    >
      <span class="tabular text-sm font-semibold">{{
        t('library.selectedCount', { count })
      }}</span>
      <button
        v-if="count < total"
        type="button"
        class="rounded-control px-2 py-1 text-[13px] font-semibold text-accent hover:bg-accent/10"
        @click="$emit('select-all')"
      >
        {{ t('library.selectAllCount', { count: total }) }}
      </button>
      <div class="ml-auto flex flex-wrap items-center gap-1.5">
        <UiButton
          size="sm"
          variant="secondary"
          icon="play"
          @click="$emit('play')"
        >
          <span class="max-sm:sr-only">{{ t('actions.play') }}</span>
        </UiButton>
        <UiButton
          size="sm"
          variant="secondary"
          icon="queue"
          @click="$emit('enqueue')"
        >
          <span class="max-sm:sr-only">{{ t('actions.addToQueue') }}</span>
        </UiButton>
        <UiButton
          size="sm"
          variant="secondary"
          icon="playlist"
          @click="$emit('add-to-playlist')"
        >
          <span class="max-sm:sr-only">{{ t('actions.addToPlaylist') }}</span>
        </UiButton>
        <UiButton
          size="sm"
          variant="secondary"
          icon="zip"
          :loading="zipping"
          @click="$emit('zip')"
        >
          <span class="max-sm:sr-only">{{ t('library.downloadZip') }}</span>
        </UiButton>
        <UiButton
          v-if="canHide"
          size="sm"
          variant="secondary"
          icon="eye-off"
          @click="$emit('hide-from-users')"
        >
          <span class="max-sm:sr-only">{{ t('visibility.hide') }}</span>
        </UiButton>
        <UiButton
          v-if="canShow"
          size="sm"
          variant="secondary"
          icon="eye"
          @click="$emit('show-to-users')"
        >
          <span class="max-sm:sr-only">{{ t('visibility.show') }}</span>
        </UiButton>
        <UiButton
          v-if="!trash.enabled.value || auth.isAdmin.value"
          size="sm"
          variant="danger"
          icon="trash"
          @click="$emit('delete')"
        >
          <span class="max-sm:sr-only">{{
            trash.enabled.value ? t('trash.move') : t('actions.delete')
          }}</span>
        </UiButton>
        <UiIconButton
          icon="x"
          :label="t('library.clearSelection')"
          size="sm"
          @click="$emit('clear')"
        />
      </div>
    </div>
  </Transition>
</template>

<script setup>
import UiButton from '../ui/UiButton.vue'
import UiIconButton from '../ui/UiIconButton.vue'
import { useAuth } from '/src/model/auth'
import { useTrashCapability } from '/src/lib/trash'
import { useI18n } from '/src/i18n'

defineProps({
  count: { type: Number, default: 0 },
  total: { type: Number, default: 0 },
  zipping: { type: Boolean, default: false },
  // Admins: whether the selection has songs to hide from users / show.
  canHide: { type: Boolean, default: false },
  canShow: { type: Boolean, default: false },
})
defineEmits([
  'select-all',
  'play',
  'enqueue',
  'zip',
  'delete',
  'clear',
  'add-to-playlist',
  'hide-from-users',
  'show-to-users',
])
const { t } = useI18n()
const auth = useAuth()
// With the music trash on, only admins remove songs, and to the trash.
const trash = useTrashCapability()
</script>
