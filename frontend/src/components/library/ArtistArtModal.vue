<template>
  <UiModal
    :open="open"
    :title="
      kind === 'banner'
        ? t('artistArt.titleBanner', { name: artistName })
        : t('artistArt.titlePhoto', { name: artistName })
    "
    :description="t('artistArt.description')"
    width="sm:max-w-xl"
    @close="$emit('close')"
  >
    <div class="flex flex-col gap-4">
      <form class="flex gap-2" @submit.prevent="search">
        <label
          class="flex h-11 min-w-0 flex-1 items-center gap-2.5 rounded-control border border-line-3 bg-bg px-3.5 focus-within:border-accent"
        >
          <AppIcon
            :name="isUrlQuery ? 'link' : 'search'"
            :size="16"
            class="text-faint"
          />
          <span class="sr-only">{{ t('artistArt.searchPlaceholder') }}</span>
          <input
            v-model="query"
            type="text"
            autocomplete="off"
            :placeholder="t('artistArt.searchPlaceholder')"
            class="h-full min-w-0 flex-1 bg-transparent text-sm outline-none placeholder:text-faint"
          />
        </label>
        <UiButton
          type="submit"
          variant="primary"
          icon="search"
          :loading="loading"
        >
          {{ t('search.searchButton') }}
        </UiButton>
      </form>

      <div class="flex flex-wrap items-center gap-x-5 gap-y-2">
        <button
          type="button"
          class="flex w-fit items-center gap-1.5 text-[13px] text-muted hover:text-fg"
          @click="filePicker?.click()"
        >
          <AppIcon name="upload" :size="14" />{{ t('artistArt.upload') }}
        </button>
        <button
          v-if="hasCurrent"
          type="button"
          class="flex w-fit items-center gap-1.5 text-[13px] text-danger hover:text-danger/80"
          @click="removeArt"
        >
          <AppIcon name="trash" :size="14" />{{ removeLabel }}
        </button>
      </div>
      <input
        ref="filePicker"
        type="file"
        accept="image/*"
        class="hidden"
        @change="onUploadChange"
      />

      <p v-if="errorText" class="text-[13px] text-danger">{{ errorText }}</p>

      <div
        v-if="cards.length"
        class="grid grid-cols-3 gap-3"
        :class="kind === 'banner' ? 'sm:grid-cols-2' : 'sm:grid-cols-4'"
      >
        <button
          v-for="(candidate, i) in cards"
          :key="`${candidate.source}-${i}`"
          type="button"
          class="group flex flex-col gap-1.5 text-left disabled:opacity-50"
          :disabled="saving"
          @click="choose(candidate)"
        >
          <CoverArt
            :src="candidate.image_url"
            :name="candidate.name"
            :round="kind === 'photo'"
            shadow
            :class="
              kind === 'banner' ? 'aspect-video w-full' : 'aspect-square w-full'
            "
            class="ring-1 ring-line-2 transition-transform group-hover:scale-[1.02]"
          >
            <span
              class="absolute bottom-1.5 left-1/2 flex size-6 -translate-x-1/2 items-center justify-center rounded-full shadow-[0_1px_4px_rgba(0,0,0,0.45)] ring-2 ring-black/25"
              :style="{ background: sourceBadgeColor(candidate.source) }"
            >
              <AppIcon
                :name="sourceIcon(candidate.source)"
                :size="12"
                class="text-white"
              />
              <span class="sr-only">{{
                sourceLabel(candidate.source, t('artistArt.sourceLink'))
              }}</span>
            </span>
          </CoverArt>
          <span class="truncate text-[13px] text-muted">{{
            candidate.name
          }}</span>
        </button>
      </div>
      <p v-else-if="!loading" class="text-[13px] text-muted">
        {{ t('artistArt.noResults') }}
      </p>
    </div>
  </UiModal>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import AppIcon from '../ui/AppIcon.vue'
import CoverArt from '../ui/CoverArt.vue'
import UiButton from '../ui/UiButton.vue'
import UiModal from '../ui/UiModal.vue'
import API from '/src/model/api'
import {
  artCandidates,
  isImageUrlQuery,
  sourceBadgeColor,
  sourceIcon,
  sourceLabel,
} from '/src/lib/artistArt'
import { useUi } from '/src/model/ui'
import { useI18n } from '/src/i18n'

const props = defineProps({
  open: { type: Boolean, default: false },
  artistName: { type: String, required: true },
  kind: { type: String, required: true }, // 'photo' | 'banner'
  trackFiles: { type: Array, default: () => [] },
  // Whether the artist already has a saved photo/banner for this kind -
  // only then is "Remove" offered.
  hasCurrent: { type: Boolean, default: false },
})
const emit = defineEmits(['close', 'saved'])

const { t } = useI18n()
const ui = useUi()

const query = ref('')
const results = ref([])
const spotifyCandidate = ref(null)
const loading = ref(false)
const saving = ref(false)
const errorText = ref('')
const filePicker = ref(null)

const isUrlQuery = computed(() => isImageUrlQuery(query.value))
const cards = computed(() =>
  artCandidates(spotifyCandidate.value, results.value)
)
const removeLabel = computed(() =>
  props.kind === 'banner'
    ? t('artistArt.removeBanner')
    : t('artistArt.removePhoto')
)

async function findSpotifyCandidate() {
  // Tries a handful of the artist's own tracks - the first one that came
  // from Spotify (see downtify.track_index) resolves the artist's photo
  // or banner directly, no name search needed. Photo and banner are
  // genuinely different Spotify images (see downtify.spotify), so the
  // kind has to be passed through - many artists have no banner set at
  // all, in which case no Spotify candidate is offered for one.
  for (const file of props.trackFiles.slice(0, 5)) {
    try {
      const res = await API.getSpotifyArtistArtCandidate(file, props.kind)
      if (res.data?.image_url) {
        spotifyCandidate.value = res.data
        return
      }
    } catch {
      // try the next track
    }
  }
}

async function search() {
  // An empty field searches by the artist's own name - only text the
  // user actually typed can be a pasted image link.
  const typed = query.value.trim()
  const text = typed || props.artistName
  if (!text) return
  errorText.value = ''
  if (isUrlQuery.value) {
    results.value = [{ source: 'link', name: typed, image_url: typed }]
    return
  }
  loading.value = true
  try {
    const res = await API.searchArtistArt(text)
    results.value = res.data || []
  } catch (err) {
    errorText.value = err?.response?.data?.detail || t('artistArt.searchFailed')
  } finally {
    loading.value = false
  }
}

async function choose(candidate) {
  saving.value = true
  errorText.value = ''
  try {
    const res = await API.setArtistArtFromUrl(
      props.artistName,
      props.kind,
      candidate.image_url,
      candidate.source
    )
    ui.toast(t('artistArt.saved'), { kind: 'success' })
    emit('saved', res.data.url)
    emit('close')
  } catch (err) {
    errorText.value = err?.response?.data?.detail || t('artistArt.saveFailed')
  } finally {
    saving.value = false
  }
}

async function onUploadChange(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) return
  saving.value = true
  errorText.value = ''
  try {
    const res = await API.uploadArtistArt(
      props.artistName,
      props.kind,
      file,
      'upload'
    )
    ui.toast(t('artistArt.saved'), { kind: 'success' })
    emit('saved', res.data.url)
    emit('close')
  } catch (err) {
    errorText.value = err?.response?.data?.detail || t('artistArt.saveFailed')
  } finally {
    saving.value = false
  }
}

async function removeArt() {
  const ok = await ui.confirm({
    title:
      props.kind === 'banner'
        ? t('confirm.removeArtistBannerTitle', { name: props.artistName })
        : t('confirm.removeArtistPhotoTitle', { name: props.artistName }),
    body: t('confirm.removeArtistArtBody'),
    confirmLabel: removeLabel.value,
    danger: true,
  })
  if (!ok) return
  saving.value = true
  errorText.value = ''
  try {
    await API.deleteArtistArt(props.artistName, props.kind)
    ui.toast(t('artistArt.removed'), { kind: 'success' })
    emit('saved')
    emit('close')
  } catch (err) {
    errorText.value = err?.response?.data?.detail || t('artistArt.removeFailed')
  } finally {
    saving.value = false
  }
}

watch(
  () => props.open,
  (isOpen) => {
    if (!isOpen) return
    query.value = ''
    results.value = []
    spotifyCandidate.value = null
    errorText.value = ''
    // Field starts empty, but the results grid still fills in right
    // away by searching the artist's own name (see search() above).
    search()
    findSpotifyCandidate()
  },
  { immediate: true }
)
</script>
