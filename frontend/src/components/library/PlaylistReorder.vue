<template>
  <div ref="root" class="flex flex-col gap-3">
    <div class="flex flex-wrap items-center gap-2">
      <p class="min-w-0 flex-1 basis-56 text-[13px] text-muted">
        {{ t('playlists.reorderHint') }}
      </p>
      <UiButton variant="ghost" :disabled="saving" @click="emit('close')">
        {{ t('common.cancel') }}
      </UiButton>
      <UiButton
        variant="primary"
        icon="check"
        :loading="saving"
        :disabled="!changed || saving"
        @click="save"
      >
        {{ t('playlists.reorderSave') }}
      </UiButton>
    </div>

    <ol class="flex flex-col">
      <li
        v-for="(track, index) in draft"
        :key="trackRowKey(track)"
        class="group flex h-14 items-center gap-3 rounded-[10px] px-2 transition-colors"
        :class="
          dragOver === index || moved === trackRowKey(track)
            ? 'bg-accent/10'
            : 'hover:bg-surface'
        "
        draggable="true"
        @dragstart="onDragStart($event, index)"
        @dragover.prevent="dragOver = index"
        @dragleave="dragOver = -1"
        @drop.prevent="onDrop(index)"
        @dragend="onDragEnd"
      >
        <AppIcon
          name="grip"
          :size="16"
          class="hidden cursor-grab text-faint sm:block"
        />
        <span class="tabular w-7 shrink-0 text-right text-[13px] text-faint">
          {{ index + 1 }}
        </span>
        <CoverArt
          :thumb="150"
          :src="track.hasCover ? track.cover : ''"
          :name="track.album || track.title"
          rounded="rounded-[6px]"
          :letter-size="12"
          :icon-size="14"
          class="size-10"
        />
        <div class="min-w-0 flex-1">
          <p class="truncate text-sm font-semibold">{{ track.title }}</p>
          <p class="truncate text-[13px] text-muted">{{ track.artist }}</p>
        </div>
        <div class="flex shrink-0 items-center">
          <UiIconButton
            icon="arrow-up-to-line"
            :label="t('playlists.moveTop')"
            size="sm"
            class="max-sm:hidden"
            data-move="top"
            :disabled="index === 0"
            @click="move(index, 0, 'top')"
          />
          <UiIconButton
            icon="chevron-up"
            :label="t('playlists.moveUp')"
            size="sm"
            data-move="up"
            :disabled="index === 0"
            @click="move(index, index - 1, 'up')"
          />
          <UiIconButton
            icon="chevron-down"
            :label="t('playlists.moveDown')"
            size="sm"
            data-move="down"
            :disabled="index === draft.length - 1"
            @click="move(index, index + 1, 'down')"
          />
          <UiIconButton
            icon="arrow-down-to-line"
            :label="t('playlists.moveBottom')"
            size="sm"
            class="max-sm:hidden"
            data-move="bottom"
            :disabled="index === draft.length - 1"
            @click="move(index, draft.length - 1, 'bottom')"
          />
        </div>
      </li>
    </ol>
  </div>
</template>

<script setup>
// Puts a Library playlist's songs in a new order: a draft moved with the
// arrows or by dragging, saved in one go (PUT /api/library/playlists/order).
import { computed, nextTick, ref, watch } from 'vue'
import AppIcon from '../ui/AppIcon.vue'
import CoverArt from '../ui/CoverArt.vue'
import UiButton from '../ui/UiButton.vue'
import UiIconButton from '../ui/UiIconButton.vue'
import { usePlaylistActions } from '/src/model/playlistActions'
import { moveItem, trackRowKey } from '/src/lib/library'
import { useI18n } from '/src/i18n'

const props = defineProps({
  playlist: { type: Object, required: true },
})
const emit = defineEmits(['close', 'saved'])

const { t } = useI18n()
const actions = usePlaylistActions()
const root = ref(null)
const draft = ref([...props.playlist.tracks])
const saving = ref(false)
const dragOver = ref(-1)
const moved = ref('')
let dragFrom = -1

const changed = computed(
  () =>
    draft.value.length !== props.playlist.tracks.length ||
    draft.value.some(
      (track, index) => track.file !== props.playlist.tracks[index]?.file
    )
)

// Another editor changed the songs (or a save found it stale and the
// library reloaded): start again from what the playlist holds now.
watch(
  () => props.playlist.tracks,
  (tracks) => {
    if (!saving.value) draft.value = [...tracks]
  }
)

async function move(from, to, button = '') {
  if (to < 0 || to >= draft.value.length || from === to) return
  draft.value = moveItem(draft.value, from, to)
  moved.value = trackRowKey(draft.value[to])
  if (!button) return
  // The row moved under the pointer: keep the focus on its button so the
  // keyboard can go on moving it.
  await nextTick()
  const row = root.value?.querySelectorAll('li')[to]
  row?.querySelector(`[data-move="${button}"]:not(:disabled)`)?.focus()
}

function onDragStart(event, index) {
  dragFrom = index
  event.dataTransfer.effectAllowed = 'move'
}

function onDrop(index) {
  if (dragFrom >= 0) move(dragFrom, index)
  onDragEnd()
}

function onDragEnd() {
  dragFrom = -1
  dragOver.value = -1
}

async function save() {
  if (!changed.value || saving.value) return
  saving.value = true
  let ok = false
  try {
    ok = await actions.reorder(
      props.playlist,
      draft.value.map((track) => track.file)
    )
  } finally {
    saving.value = false
  }
  if (ok) emit('saved')
  else draft.value = [...props.playlist.tracks]
}
</script>
