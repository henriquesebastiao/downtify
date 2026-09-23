<template>
  <UiModal
    :open="open"
    :title="modalTitle"
    :description="modalDescription"
    width="sm:max-w-3xl"
    @close="$emit('close')"
  >
    <div class="flex flex-col gap-4 sm:flex-row sm:items-start sm:gap-6">
      <div class="flex flex-col gap-3 sm:w-44 sm:shrink-0">
        <button
          type="button"
          class="mx-auto flex flex-col items-center gap-1.5 sm:mx-0"
          @click="activeTab = 'photo'"
        >
          <CoverArt
            :src="photoUrl"
            :name="artistName"
            round
            shadow
            :letter-size="52"
            :icon-size="40"
            class="size-32 ring-1 ring-line-2"
          />
          <UiBadge :icon="currentCover ? sourceIcon(currentCover) : ''">
            {{
              currentCover
                ? sourceLabel(currentCover, t('artistArt.sourceLink'))
                : t('artistArt.currentPhoto')
            }}
          </UiBadge>
        </button>

        <nav
          class="-mx-1 flex gap-1 overflow-x-auto px-1 pb-1 [scrollbar-width:none] sm:mx-0 sm:flex-col sm:overflow-visible sm:px-0 sm:pb-0"
        >
          <button
            v-for="tab in tabOptions"
            :key="tab.value"
            type="button"
            class="flex h-10 shrink-0 items-center gap-2.5 rounded-control px-3 text-sm whitespace-nowrap transition-colors sm:w-full"
            :class="
              activeTab === tab.value
                ? 'bg-surface-2 font-semibold text-fg'
                : 'font-medium text-muted hover:bg-surface-2/60 hover:text-fg'
            "
            @click="activeTab = tab.value"
          >
            <AppIcon
              :name="tab.icon"
              :size="17"
              :class="activeTab === tab.value ? 'text-accent' : ''"
            />
            {{ tab.label }}
          </button>
        </nav>
      </div>

      <div class="flex min-w-0 flex-1 flex-col gap-4">
        <template v-if="activeTab === 'photo' || activeTab === 'banner'">
          <form class="flex gap-2" @submit.prevent="search">
            <label
              class="flex h-11 min-w-0 flex-1 items-center gap-2.5 rounded-control border border-line-3 bg-bg px-3.5 focus-within:border-accent"
            >
              <AppIcon
                :name="isUrlQuery ? 'link' : 'search'"
                :size="16"
                class="text-faint"
              />
              <span class="sr-only">{{
                t('artistArt.searchPlaceholder')
              }}</span>
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

          <p v-if="errorText" class="text-[13px] text-danger">
            {{ errorText }}
          </p>

          <div
            v-if="cards.length"
            class="grid grid-cols-3 gap-3"
            :class="
              activeTab === 'banner' ? 'sm:grid-cols-2' : 'sm:grid-cols-3'
            "
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
                :round="activeTab === 'photo'"
                shadow
                :class="
                  activeTab === 'banner'
                    ? 'aspect-video w-full'
                    : 'aspect-square w-full'
                "
                class="ring-1 ring-line-2 transition-transform group-hover:scale-[1.02]"
              >
                <UiBadge
                  class="absolute bottom-1.5 left-1/2 -translate-x-1/2 shadow-[0_1px_4px_rgba(0,0,0,0.45)]"
                >
                  {{ sourceLabel(candidate.source, t('artistArt.sourceLink')) }}
                </UiBadge>
              </CoverArt>
              <span class="truncate text-[13px] text-muted">{{
                candidate.name
              }}</span>
            </button>
          </div>
          <p v-else-if="!loading" class="text-[13px] text-muted">
            {{ t('artistArt.noResults') }}
          </p>
        </template>

        <template v-else-if="activeTab === 'bio'">
          <button
            type="button"
            class="flex w-fit items-center gap-1.5 text-[13px] text-muted hover:text-fg disabled:opacity-50"
            :disabled="bioFetching"
            @click="fetchBioFromStreams"
          >
            <AppIcon
              name="zap"
              :size="14"
              :class="bioFetching ? 'animate-pulse' : ''"
            />{{ t('artistBio.fetchButton') }}
          </button>
          <textarea
            v-model="bioDraft"
            rows="10"
            :placeholder="t('artistArt.bioPlaceholder')"
            class="min-h-40 w-full resize-y rounded-control border border-line-3 bg-bg px-3.5 py-3 text-sm outline-none placeholder:text-faint focus:border-accent"
          />
          <p v-if="errorText" class="text-[13px] text-danger">
            {{ errorText }}
          </p>
          <UiButton
            variant="primary"
            class="self-end"
            :loading="savingBio"
            @click="saveBio"
          >
            {{ t('artistArt.save') }}
          </UiButton>
        </template>

        <template v-else-if="activeTab === 'social'">
          <div class="flex flex-col gap-3">
            <UiInput
              v-model="socialDraft.twitter"
              :label="t('artistArt.socialTwitter')"
              placeholder="https://twitter.com/…"
            />
            <UiInput
              v-model="socialDraft.instagram"
              :label="t('artistArt.socialInstagram')"
              placeholder="https://instagram.com/…"
            />
            <UiInput
              v-model="socialDraft.facebook"
              :label="t('artistArt.socialFacebook')"
              placeholder="https://facebook.com/…"
            />
            <UiInput
              v-model="socialDraft.youtube"
              :label="t('artistArt.socialYoutube')"
              placeholder="https://youtube.com/…"
            />
            <UiInput
              v-model="socialDraft.website"
              :label="t('artistArt.socialWebsite')"
              placeholder="https://…"
            />
          </div>
          <p v-if="errorText" class="text-[13px] text-danger">
            {{ errorText }}
          </p>
          <UiButton
            variant="primary"
            class="self-end"
            :loading="savingSocial"
            @click="saveSocial"
          >
            {{ t('artistArt.save') }}
          </UiButton>
        </template>
      </div>
    </div>
  </UiModal>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import AppIcon from '../ui/AppIcon.vue'
import CoverArt from '../ui/CoverArt.vue'
import UiBadge from '../ui/UiBadge.vue'
import UiButton from '../ui/UiButton.vue'
import UiInput from '../ui/UiInput.vue'
import UiModal from '../ui/UiModal.vue'
import API from '/src/model/api'
import {
  artCandidates,
  isImageUrlQuery,
  sourceIcon,
  sourceLabel,
} from '/src/lib/artistArt'
import { useUi } from '/src/model/ui'
import { useI18n } from '/src/i18n'

const props = defineProps({
  open: { type: Boolean, default: false },
  artistName: { type: String, required: true },
  trackFiles: { type: Array, default: () => [] },
  // Shown above the tabs as a reminder of the current photo - the artist
  // page itself hides it once a banner is set (see CollectionHero).
  photoUrl: { type: String, default: '' },
  // Which source the current photo came from (spotify/youtube/deezer/
  // link/upload, matches artist_profile.py's current_cover) - badges the
  // preview above the tabs the same way a search result card is badged.
  // Empty when no photo is saved yet, or it predates this tracking.
  currentCover: { type: String, default: '' },
  // Whether the artist already has a saved photo/banner - only then is
  // "Remove" offered for that tab.
  hasPhoto: { type: Boolean, default: false },
  hasBanner: { type: Boolean, default: false },
  // Current bio/social text, so the Bio/Social tabs open pre-filled
  // with what's already saved instead of blank fields.
  bio: { type: String, default: '' },
  social: {
    type: Object,
    default: () => ({
      twitter: '',
      facebook: '',
      website: '',
      instagram: '',
      youtube: '',
    }),
  },
  // Which tab to open on - 'banner' by default (the photo itself may be
  // hidden from the artist page's header when a banner is set, see
  // CollectionHero), but the caller passes 'photo' when the user opened
  // this from the photo's own edit affordance specifically.
  initialTab: { type: String, default: 'banner' },
})
const emit = defineEmits(['close', 'saved'])

const { t, locale } = useI18n()
const ui = useUi()

// Photo, banner, bio and social are all edited from the same modal - a
// vertical menu picks which one.
const activeTab = ref(props.initialTab)
const tabOptions = computed(() => [
  { value: 'photo', label: t('artistArt.tabProfile'), icon: 'user' },
  { value: 'banner', label: t('artistArt.tabBanner'), icon: 'image' },
  { value: 'bio', label: t('artistArt.tabBio'), icon: 'pencil' },
  { value: 'social', label: t('artistArt.tabSocial'), icon: 'link' },
])

const modalTitle = computed(() => {
  const name = props.artistName
  if (activeTab.value === 'banner') return t('artistArt.titleBanner', { name })
  if (activeTab.value === 'bio') return t('artistArt.titleBio', { name })
  if (activeTab.value === 'social') return t('artistArt.titleSocial', { name })
  return t('artistArt.titlePhoto', { name })
})
const modalDescription = computed(() => {
  if (activeTab.value === 'bio') return t('artistArt.bioDescription')
  if (activeTab.value === 'social') return t('artistArt.socialDescription')
  return t('artistArt.description')
})

const query = ref('')
const results = ref([])
const spotifyCandidate = ref(null)
const loading = ref(false)
const saving = ref(false)
const errorText = ref('')
const filePicker = ref(null)

const bioDraft = ref('')
const socialDraft = ref({
  twitter: '',
  facebook: '',
  website: '',
  instagram: '',
  youtube: '',
})
const savingBio = ref(false)
const savingSocial = ref(false)
const bioFetching = ref(false)

const isUrlQuery = computed(() => isImageUrlQuery(query.value))
const cards = computed(() =>
  artCandidates(spotifyCandidate.value, results.value)
)
const hasCurrent = computed(() =>
  activeTab.value === 'banner' ? props.hasBanner : props.hasPhoto
)
const removeLabel = computed(() =>
  activeTab.value === 'banner'
    ? t('artistArt.removeBanner')
    : t('artistArt.removePhoto')
)

async function findSpotifyCandidate() {
  // Tries a handful of the artist's own tracks - the first one that came
  // from Spotify (see downtify.track_index) resolves the artist's photo
  // or banner directly, no name search needed. Photo and banner are
  // genuinely different Spotify images (see downtify.spotify), so the
  // active tab has to be passed through - many artists have no banner
  // set at all, in which case no Spotify candidate is offered for one.
  for (const file of props.trackFiles.slice(0, 5)) {
    try {
      const res = await API.getSpotifyArtistArtCandidate(file, activeTab.value)
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
      activeTab.value,
      candidate.image_url,
      candidate.source
    )
    ui.toast(t('artistArt.saved'), { kind: 'success' })
    emit('saved', res.data.url)
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
      activeTab.value,
      file,
      'upload'
    )
    ui.toast(t('artistArt.saved'), { kind: 'success' })
    emit('saved', res.data.url)
  } catch (err) {
    errorText.value = err?.response?.data?.detail || t('artistArt.saveFailed')
  } finally {
    saving.value = false
  }
}

async function removeArt() {
  const ok = await ui.confirm({
    title:
      activeTab.value === 'banner'
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
    await API.deleteArtistArt(props.artistName, activeTab.value)
    ui.toast(t('artistArt.removed'), { kind: 'success' })
    emit('saved')
  } catch (err) {
    errorText.value = err?.response?.data?.detail || t('artistArt.removeFailed')
  } finally {
    saving.value = false
  }
}

async function fetchBioFromStreams() {
  if (bioFetching.value) return
  bioFetching.value = true
  errorText.value = ''
  try {
    const res = await API.fetchArtistBio(props.artistName, locale.value)
    bioDraft.value = res.data.bio
    socialDraft.value = { ...res.data.social }
    ui.toast(t('artistBio.fetched'), { kind: 'success' })
    emit('saved')
  } catch (err) {
    errorText.value = err?.response?.data?.detail || t('artistBio.fetchFailed')
  } finally {
    bioFetching.value = false
  }
}

async function saveBio() {
  savingBio.value = true
  errorText.value = ''
  try {
    await API.saveArtistBio(props.artistName, bioDraft.value)
    ui.toast(t('artistArt.bioSaved'), { kind: 'success' })
    emit('saved')
  } catch (err) {
    errorText.value =
      err?.response?.data?.detail || t('artistArt.bioSaveFailed')
  } finally {
    savingBio.value = false
  }
}

async function saveSocial() {
  savingSocial.value = true
  errorText.value = ''
  try {
    await API.saveArtistSocial(props.artistName, socialDraft.value)
    ui.toast(t('artistArt.socialSaved'), { kind: 'success' })
    emit('saved')
  } catch (err) {
    errorText.value =
      err?.response?.data?.detail || t('artistArt.socialSaveFailed')
  } finally {
    savingSocial.value = false
  }
}

function resetArtState() {
  query.value = ''
  results.value = []
  spotifyCandidate.value = null
  errorText.value = ''
  // Field starts empty, but the results grid still fills in right
  // away by searching the artist's own name (see search() above).
  search()
  findSpotifyCandidate()
}

watch(
  () => props.open,
  (isOpen) => {
    if (!isOpen) return
    activeTab.value = props.initialTab
    bioDraft.value = props.bio
    socialDraft.value = { ...props.social }
    errorText.value = ''
    resetArtState()
  },
  { immediate: true }
)

watch(activeTab, (tab) => {
  if (!props.open) return
  errorText.value = ''
  if (tab === 'photo' || tab === 'banner') resetArtState()
})
</script>
