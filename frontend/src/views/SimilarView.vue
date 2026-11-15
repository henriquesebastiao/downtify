<template>
  <div
    class="mx-auto flex max-w-[1680px] flex-col gap-8 px-4 pt-6 sm:px-6 md:pt-8 lg:px-10"
  >
    <PageHeader :title="t('similar.title')" :subtitle="subtitle" />
    <div class="flex flex-wrap items-center gap-3">
      <label v-if="similar.canSearch.value" for="similar-source"
        >Rechercher dans</label
      >
      <select
        v-if="similar.canSearch.value"
        id="similar-source"
        :value="similar.source.value"
        class="rounded border border-line-2 bg-surface p-2"
        @change="changeSource"
      >
        <option v-if="similar.localEnabled.value" value="local">
          Ma bibliothèque — analyse locale
        </option>
        <option
          v-if="similar.capabilities.value?.features.external_beta"
          value="external"
        >
          YouTube Music — bêta
        </option>
      </select>
      <RouterLink to="/settings/ai" class="text-accent"
        >Préférences musicales</RouterLink
      >
    </div>

    <UiEmpty
      v-if="similar.capabilities.value && !similar.canSearch.value"
      icon="search"
      title="Les musiques similaires sont désactivées."
      body="Les préférences musicales indiquent les sources autorisées sur votre compte et sur ce serveur."
    />
    <p v-else-if="!similar.capabilities.value" role="status" class="text-muted">
      Vérification des sources disponibles…
    </p>
    <template v-if="similar.canSearch.value">
      <form
        class="flex flex-col gap-2 sm:flex-row sm:items-end"
        @submit.prevent="submit"
      >
        <UiInput
          v-model.trim="artistInput"
          class="sm:flex-1"
          :label="t('similar.artist')"
          :placeholder="t('similar.artistPlaceholder')"
          autocomplete="off"
        />
        <UiInput
          v-model.trim="trackInput"
          class="sm:flex-1"
          :label="t('similar.track')"
          :placeholder="t('similar.trackPlaceholder')"
          autocomplete="off"
        />
        <UiButton
          type="submit"
          icon="search"
          :disabled="similar.loading.value || (!artistInput && !trackInput)"
          >Rechercher</UiButton
        >
      </form>

      <div v-if="similar.loading.value" class="flex flex-col gap-2">
        <div v-for="n in 6" :key="n" class="flex h-16 items-center gap-3 px-3">
          <UiSkeleton class="size-11 !rounded-[8px]" />
          <div class="flex flex-1 flex-col gap-2">
            <UiSkeleton class="h-3.5 w-1/3" />
            <UiSkeleton class="h-3 w-1/5" />
          </div>
        </div>
      </div>

      <UiEmpty
        v-else-if="similar.error.value"
        icon="alert"
        :title="t('similar.failed')"
        :body="similar.error.value"
      >
        <UiButton icon="refresh" @click="retry">{{
          t('common.retry')
        }}</UiButton>
      </UiEmpty>

      <UiEmpty
        v-else-if="similar.searched.value && !similar.songs.value.length"
        icon="search"
        :title="t('similar.noResults')"
        :body="t('similar.noResultsHint')"
      />

      <template v-else-if="similar.searched.value">
        <section class="flex flex-col gap-3">
          <h2 class="text-display text-xl font-semibold">
            {{ resultsTitle }}
          </h2>
          <div class="-mx-3 flex flex-col">
            <TrackDownPlayHeader />
            <SimilarTrackRow
              v-for="(song, i) in similar.songs.value"
              :key="`${song.artist}|${song.name}`"
              :song="song"
              :index="i"
              :songs="similar.songs.value"
            />
          </div>
          <!-- The endless list: reaching the end loads the next page. -->
          <div ref="sentinel" class="flex flex-col gap-2">
            <div
              v-if="similar.loadingMore.value"
              class="flex h-16 items-center gap-3 px-3"
            >
              <UiSkeleton class="size-11 !rounded-[8px]" />
              <div class="flex flex-1 flex-col gap-2">
                <UiSkeleton class="h-3.5 w-1/3" />
                <UiSkeleton class="h-3 w-1/5" />
              </div>
            </div>
          </div>
        </section>
      </template>

      <div v-else class="grid gap-4 md:grid-cols-2">
        <div
          v-for="tip in tips"
          :key="tip.title"
          class="flex flex-col gap-2 rounded-panel border border-line-2 bg-surface p-5"
        >
          <span
            class="flex size-10 items-center justify-center rounded-[10px]"
            :class="tip.tone"
          >
            <AppIcon :name="tip.icon" :size="20" />
          </span>
          <p class="mt-1 text-[15px] font-semibold">{{ tip.title }}</p>
          <p class="text-[13px] text-pretty text-muted">{{ tip.body }}</p>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppIcon from '/src/components/ui/AppIcon.vue'
import UiButton from '/src/components/ui/UiButton.vue'
import UiEmpty from '/src/components/ui/UiEmpty.vue'
import UiInput from '/src/components/ui/UiInput.vue'
import UiSkeleton from '/src/components/ui/UiSkeleton.vue'
import PageHeader from '/src/components/library/PageHeader.vue'
import TrackDownPlayHeader from '/src/components/library/TrackDownPlayHeader.vue'
import SimilarTrackRow from '/src/components/similar/SimilarTrackRow.vue'
import { useSimilar } from '/src/model/similar'
import { useLibrary } from '/src/model/library'
import { usePlayer } from '/src/model/player'
import { songToPlayerTrack } from '/src/model/songPlay'
import { useI18n } from '/src/i18n'
import { musicAI } from '/src/model/musicAI'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const similar = useSimilar()
const library = useLibrary()
const player = usePlayer()

const artistInput = ref(similar.artist.value)
const trackInput = ref(similar.track.value)
onMounted(() => musicAI.refresh())
function changeSource(event) {
  const artist = artistInput.value
  const track = trackInput.value
  similar.setSource(event.target.value)
  if (artist || track) similar.searchFor(artist, track)
}

watch(
  () => similar.songs.value,
  (songs) => similar.lookupSongs(songs)
)

// A track row's Similar button lands here with ?artist=&track=: fill the
// form and search at once. Guarded by what's already searched, so typing
// in the form (which rewrites the same query below) never re-triggers.
function applyQuery() {
  const artist = String(route.query.artist || '').trim()
  const track = String(route.query.track || '').trim()
  if (!artist && !track) return
  if (
    artist === similar.artist.value &&
    track === similar.track.value &&
    !route.query.file
  ) {
    return
  }
  artistInput.value = artist
  trackInput.value = track
  similar.searchFor(
    artist,
    track,
    route.query.file ? { library_file: String(route.query.file) } : {}
  )
}

watch(
  () => [route.query.artist, route.query.track, route.query.file],
  applyQuery,
  {
    immediate: true,
  }
)

const resultsTitle = computed(() => {
  const a = similar.artist.value
  const seedTrack = similar.track.value
  if (a && seedTrack)
    return t('similar.resultsFor', { track: seedTrack, artist: a })
  if (a) return t('similar.resultsForArtist', { artist: a })
  return t('similar.resultsForTrack', { track: seedTrack })
})

function submit() {
  const artist = artistInput.value.trim()
  const track = trackInput.value.trim()
  if (!artist && !track) return
  // Keep the URL shareable; the watcher above ignores it when it matches
  // what's already searched.
  router.replace({ name: 'Similar', query: { artist, track } })
  similar.searchFor(artist, track)
}

function retry() {
  similar.searchFor(similar.artist.value, similar.track.value)
}

// Scrolling to the list end loads the next page, endlessly.
const sentinel = ref(null)
let observer = null
watch(
  sentinel,
  (el) => {
    observer?.disconnect()
    observer = null
    if (!el || typeof IntersectionObserver === 'undefined') return
    observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) similar.loadMore()
      },
      { rootMargin: '600px' }
    )
    observer.observe(el)
  },
  { immediate: true }
)
onBeforeUnmount(() => observer?.disconnect())

function isSongCurrent(song, current) {
  if (!current) return false
  const vid = String(song.song_id || '').trim()
  if (vid && String(current.video_id || '').trim() === vid) return true
  const a = String((song.artists || [])[0] || song.artist || '')
    .trim()
    .toLowerCase()
  const n = String(song.name || '')
    .trim()
    .toLowerCase()
  if (!a || !n) return false
  const ca = String(current.artist || (current.artists || [])[0] || '')
    .trim()
    .toLowerCase()
  const cn = String(current.title || current.name || '')
    .trim()
    .toLowerCase()
  return a === ca && n === cn
}

// Playback reached the list tail: grow the list from it and queue what was
// added, so listening never stops at twenty songs.
let extending = false
watch(
  () => player.currentTrack.value,
  async (current) => {
    if (extending || !current || !similar.hasMore.value) return
    const songs = similar.songs.value
    if (!songs.length) return
    if (!isSongCurrent(songs[songs.length - 1], current)) return
    extending = true
    try {
      const added = await similar.loadMore()
      if (added.length) {
        player.enqueue(
          added.map((song) => songToPlayerTrack(song, library.findTrack))
        )
      }
    } finally {
      extending = false
    }
  }
)

const subtitle = computed(() =>
  !similar.canSearch.value
    ? 'Consultez vos préférences pour activer une source musicale.'
    : similar.source.value === 'local'
      ? 'Des morceaux proches de votre titre, à partir de l’analyse sonore de votre bibliothèque.'
      : t('similar.subtitle')
)
const tips = computed(() =>
  similar.source.value === 'local'
    ? [
        {
          icon: 'wand',
          tone: 'bg-accent/12 text-accent',
          title: 'Partez d’un titre local',
          body: 'Indiquez son artiste ou son titre, puis lancez la recherche dans votre bibliothèque analysée.',
        },
        {
          icon: 'play',
          tone: 'bg-accent/12 text-accent',
          title: 'Écoutez vos découvertes',
          body: 'Les résultats utilisent vos fichiers locaux, sans téléchargement ni recherche chez un fournisseur externe.',
        },
      ]
    : [
        {
          icon: 'wand',
          tone: 'bg-accent/12 text-accent',
          title: t('similar.tipSimilarTitle'),
          body: t('similar.tipSimilarBody'),
        },
        {
          icon: 'download',
          tone: 'bg-src-ytm/12 text-src-ytm',
          title: t('similar.tipDownloadTitle'),
          body: t('similar.tipDownloadBody'),
        },
      ]
)
</script>
