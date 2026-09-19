<template>
  <article
    class="rounded-[14px] border transition-colors"
    :class="[
      item.state === 'failed'
        ? 'border-danger/25 bg-danger/6'
        : item.state === 'active'
          ? 'border-line-2 bg-surface'
          : 'border-transparent hover:bg-surface',
      compact ? 'px-3 py-2' : 'p-3.5',
    ]"
  >
    <div class="flex items-center gap-3.5">
      <CoverArt
        :src="song.cover_url"
        :name="song.album_name || song.name"
        :rounded="compact ? 'rounded-[6px]' : 'rounded-[8px]'"
        :letter-size="compact ? 12 : 18"
        :class="compact ? 'size-10' : 'size-14'"
      />
      <div class="min-w-0 flex-1">
        <div class="flex min-w-0 items-center gap-2">
          <span
            class="truncate text-sm font-semibold"
            :class="compact ? '' : 'text-[15px]'"
            >{{ song.name }}</span
          >
          <SourceBadge
            v-if="item.provider"
            :source="item.provider"
            :compact="compact"
          />
        </div>
        <p class="truncate text-[13px] text-muted">
          {{ artists
          }}<span v-if="song.album_name"> · {{ song.album_name }}</span>
        </p>
        <template v-if="item.state === 'active'">
          <div class="mt-2 flex items-center gap-3">
            <UiProgress
              :value="item.progress"
              :indeterminate="!item.progress"
            />
            <span class="tabular w-9 shrink-0 text-right text-xs text-fg-3">
              {{ item.progress ? `${Math.round(item.progress)}%` : '' }}
            </span>
          </div>
          <p v-if="item.message" class="mt-1 truncate text-xs text-muted">
            {{ item.message }}
          </p>
        </template>
        <p
          v-else-if="item.state === 'failed'"
          class="mt-1 flex items-start gap-1.5 text-xs text-danger"
        >
          <AppIcon name="alert" :size="14" class="mt-px" />
          <span class="line-clamp-2">{{
            item.message || t('queue.failedGeneric')
          }}</span>
        </p>
      </div>

      <div class="flex shrink-0 items-center gap-1">
        <span
          v-if="item.state === 'queued'"
          class="text-xs text-faint max-sm:hidden"
        >
          {{ t('queue.statusQueued') }}
        </span>
        <template v-if="item.state === 'done' && item.filename">
          <UiIconButton
            icon="play"
            :label="t('actions.play')"
            size="sm"
            @click="play"
          />
          <a
            :href="item.web_download_url"
            :download="saveName(item.filename)"
            class="flex size-8 items-center justify-center rounded-control text-muted hover:bg-surface-2 hover:text-fg"
            :title="t('library.saveToDevice')"
            :aria-label="t('library.saveToDevice')"
          >
            <AppIcon name="download" :size="16" />
          </a>
        </template>
        <UiButton
          v-if="item.state === 'failed'"
          size="sm"
          variant="secondary"
          icon="retry"
          @click="dm.retry(song)"
        >
          {{ t('queue.retry') }}
        </UiButton>
        <UiIconButton
          icon="x"
          :label="t('queue.remove')"
          size="sm"
          @click="dm.remove(song)"
        />
      </div>
    </div>

    <form
      v-if="item.state === 'failed'"
      class="mt-3 flex flex-wrap items-center gap-2 pl-[70px] max-sm:pl-0"
      @submit.prevent="useLink"
    >
      <label
        class="flex h-9 min-w-0 flex-1 basis-60 items-center gap-2 rounded-control border border-line-3 bg-bg px-3 focus-within:border-accent"
      >
        <AppIcon name="link" :size="15" class="text-faint" />
        <span class="sr-only">{{ t('queue.overridePlaceholder') }}</span>
        <input
          v-model="override"
          type="url"
          :placeholder="t('queue.overridePlaceholder')"
          class="h-full min-w-0 flex-1 bg-transparent text-[13px] outline-none placeholder:text-faint"
        />
      </label>
      <UiButton size="sm" variant="ghost" type="submit" :disabled="!override">
        {{ t('queue.useLink') }}
      </UiButton>
      <p v-if="overrideError" class="basis-full text-xs text-danger">
        {{ overrideError }}
      </p>
    </form>
  </article>
</template>

<script setup>
import { computed, ref } from 'vue'
import AppIcon from '../ui/AppIcon.vue'
import CoverArt from '../ui/CoverArt.vue'
import SourceBadge from '../ui/SourceBadge.vue'
import UiButton from '../ui/UiButton.vue'
import UiIconButton from '../ui/UiIconButton.vue'
import UiProgress from '../ui/UiProgress.vue'
import { useDownloadManager } from '/src/model/download'
import { useLibrary } from '/src/model/library'
import { useTrackActions } from '/src/model/trackActions'
import { normalizeTrack } from '/src/lib/library'
import { saveName } from '/src/lib/paths'
import { useI18n } from '/src/i18n'

const props = defineProps({
  item: { type: Object, required: true },
  compact: { type: Boolean, default: false },
})

const { t } = useI18n()
const dm = useDownloadManager()
const library = useLibrary()
const actions = useTrackActions()
const override = ref('')
const overrideError = ref('')

const song = computed(() => props.item.song)
const artists = computed(
  () =>
    (song.value.artists || []).join(', ') ||
    song.value.artist ||
    t('common.unknownArtist')
)

function play() {
  const file = props.item.filename
  const track = library.tracksByFile.value.get(file) || normalizeTrack(file)
  actions.play([track], 0, null)
}

function youtubeId(url) {
  const match = String(url || '').match(
    /(?:[?&]v=|youtu\.be\/)([A-Za-z0-9_-]{6,})/
  )
  return match ? match[1] : ''
}

function useLink() {
  const id = youtubeId(override.value)
  if (!id) {
    overrideError.value = t('queue.invalidYoutube')
    return
  }
  overrideError.value = ''
  dm.retryWithAudio(song.value, id)
  override.value = ''
}
</script>
