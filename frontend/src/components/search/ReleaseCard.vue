<template>
  <article class="tile group relative flex min-w-0 flex-col gap-2.5">
    <RouterLink :to="linkTo" class="block" :aria-label="release.name">
      <CoverArt
        :src="release.cover_url"
        :name="release.name"
        :round="round"
        :icon="round ? 'user' : 'disc'"
        shadow
        :letter-size="round ? 40 : 52"
        class="aspect-square w-full"
      >
        <span
          v-if="typeLabel"
          class="absolute top-2.5 left-2.5 rounded-full bg-black/55 px-2 py-0.5 text-[11px] font-semibold text-white backdrop-blur"
          >{{ typeLabel }}</span
        >
      </CoverArt>
    </RouterLink>
    <button
      v-if="!round"
      type="button"
      class="tile-play absolute right-3 bottom-[4.25rem] flex size-11 items-center justify-center rounded-full shadow-float transition-transform hover:scale-105"
      :class="queued ? 'bg-surface text-accent' : 'bg-accent text-on-accent'"
      :aria-label="t('actions.downloadItem', { name: release.name })"
      :disabled="queued"
      @click="download"
    >
      <AppIcon
        :name="queued ? 'check' : 'download'"
        :size="18"
        stroke-width="2.2"
      />
    </button>
    <RouterLink
      :to="linkTo"
      class="flex min-w-0 flex-col gap-0.5"
      :class="round ? 'items-center text-center' : ''"
    >
      <span class="w-full truncate text-sm font-semibold">{{
        release.name
      }}</span>
      <span class="w-full truncate text-[13px] text-muted">{{ subtitle }}</span>
    </RouterLink>
  </article>
</template>

<script setup>
import { computed, ref } from 'vue'
import AppIcon from '../ui/AppIcon.vue'
import CoverArt from '../ui/CoverArt.vue'
import { useDownloadManager } from '/src/model/download'
import { useUi } from '/src/model/ui'
import { useI18n } from '/src/i18n'

const props = defineProps({
  release: { type: Object, required: true },
  round: { type: Boolean, default: false },
})
const { t } = useI18n()
const dm = useDownloadManager()
const ui = useUi()
const queued = ref(false)

const linkTo = computed(() => ({
  name: 'Link',
  query: { url: props.release.url },
}))

const typeLabel = computed(() => {
  const type = String(props.release.release_type || '').toLowerCase()
  if (!type || props.round) return ''
  const known = {
    album: t('search.typeAlbum'),
    single: t('search.typeSingle'),
    ep: t('search.typeEp'),
  }
  return known[type] || props.release.release_type
})

const subtitle = computed(() => {
  if (props.round) return t('search.artist')
  return [props.release.artist, props.release.year].filter(Boolean).join(' · ')
})

async function download() {
  queued.value = true
  try {
    const count = await dm.fromURL(props.release.url)
    ui.toast(t('toast.queuedTracks', { count, name: props.release.name }), {
      kind: 'success',
    })
  } catch (err) {
    queued.value = false
    ui.toast(err?.response?.data?.detail || t('toast.actionFailed'), {
      kind: 'error',
    })
  }
}
</script>
