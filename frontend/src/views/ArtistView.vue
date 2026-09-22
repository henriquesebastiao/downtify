<template>
  <div>
    <DetailState
      :loaded="library.loaded.value"
      :found="!!artist"
      icon="user"
      :missing="t('artist.notFound')"
    >
      <CollectionHero
        :title="artist.name"
        :kicker="t('artist.kicker')"
        :cover="artPhotoUrl || artist.cover"
        :banner="artBannerUrl"
        photo-editable
        banner-editable
        :name="artist.name"
        icon="user"
        round
        @edit-photo="openArtModal('photo')"
        @edit-banner="openArtModal('banner')"
      >
        <template #subtitle>
          {{ facts }}
        </template>
        <template #actions>
          <PlayButton
            :label="t('actions.playItem', { name: artist.name })"
            :playing="isThisPlaying"
            @click="togglePlay"
          />
          <UiIconButton
            icon="shuffle"
            :label="t('actions.shuffle')"
            size="lg"
            round
            :photo="!!artBannerUrl"
            @click="actions.play(allTracks, 0, context, { shuffled: true })"
          />
          <UiButton
            :variant="artBannerUrl ? 'photo' : 'ghost'"
            icon="queue"
            @click="actions.enqueue(allTracks)"
          >
            {{ t('actions.addToQueue') }}
          </UiButton>
          <UiButton
            :variant="artBannerUrl ? 'photo' : 'ghost'"
            icon="search"
            :to="{ name: 'Search', params: { query: artist.name } }"
          >
            {{ t('artist.findMore') }}
          </UiButton>
        </template>
      </CollectionHero>

      <div
        class="mx-auto flex max-w-[1680px] flex-col gap-12 px-4 sm:px-6 lg:px-10"
      >
        <section v-if="artist.albums.length" class="flex flex-col gap-4">
          <h2 class="text-display text-xl font-semibold">
            {{ t('library.albums') }}
          </h2>
          <div
            class="grid grid-cols-2 gap-x-5 gap-y-7 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 2xl:grid-cols-6"
          >
            <MediaTile
              v-for="album in artist.albums"
              :key="album.key"
              :to="{
                name: 'Album',
                query: { artist: album.artist, title: album.title },
              }"
              :title="album.title"
              :subtitle="
                [album.year, t('common.tracks', { count: album.tracks.length })]
                  .filter(Boolean)
                  .join(' · ')
              "
              :cover="album.cover"
              :name="album.title"
              @play="playAlbum(album)"
            />
          </div>
        </section>

        <section class="flex flex-col gap-4">
          <div class="flex items-baseline justify-between gap-4">
            <h2 class="text-display text-xl font-semibold">
              {{ t('library.tracks') }}
            </h2>
            <span class="tabular text-[13px] text-muted">{{
              t('common.tracks', { count: allTracks.length })
            }}</span>
          </div>
          <TrackList
            :tracks="allTracks"
            :context="context"
            :show-added="false"
            :hide-menu="['artist']"
          />
        </section>
      </div>
    </DetailState>

    <ArtistArtModal
      v-if="artist"
      :open="artModalOpen"
      :artist-name="artist.name"
      :kind="artModalKind"
      :track-files="trackFiles"
      :has-current="artModalKind === 'banner' ? !!artBannerUrl : !!artPhotoUrl"
      @close="artModalOpen = false"
      @saved="refreshArt"
    />
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import UiButton from '/src/components/ui/UiButton.vue'
import UiIconButton from '/src/components/ui/UiIconButton.vue'
import ArtistArtModal from '/src/components/library/ArtistArtModal.vue'
import CollectionHero from '/src/components/library/CollectionHero.vue'
import DetailState from '/src/components/library/DetailState.vue'
import MediaTile from '/src/components/library/MediaTile.vue'
import PlayButton from '/src/components/library/PlayButton.vue'
import TrackList from '/src/components/library/TrackList.vue'
import API from '/src/model/api'
import { useLibrary } from '/src/model/library'
import { usePlayer } from '/src/model/player'
import { useTrackActions } from '/src/model/trackActions'
import { sortItems } from '/src/lib/library'
import { splitLength } from '/src/lib/format'
import { useI18n } from '/src/i18n'

const { t } = useI18n()
const route = useRoute()
const library = useLibrary()
const player = usePlayer()
const actions = useTrackActions()

const artist = computed(() =>
  library.findArtist(String(route.query.name || ''))
)

// Album by album (newest first), then loose tracks.
const allTracks = computed(() => {
  const a = artist.value
  if (!a) return []
  const inAlbums = a.albums.flatMap((album) => album.tracks)
  const seen = new Set(inAlbums.map((track) => track.file))
  const loose = sortItems(
    a.tracks.filter((track) => !seen.has(track.file)),
    'title'
  )
  return [...inAlbums, ...loose]
})

const context = computed(() => ({
  type: 'artist',
  title: artist.value?.name,
  cover: artist.value?.cover,
  route: { name: 'Artist', query: { name: artist.value?.name } },
}))

const facts = computed(() => {
  const a = artist.value
  const { hours, minutes } = splitLength(a.duration)
  return [
    a.albums.length ? t('common.albums', { count: a.albums.length }) : '',
    t('common.tracks', { count: a.tracks.length }),
    hours
      ? t('common.lengthHours', { hours, minutes })
      : t('common.lengthMinutes', { minutes }),
  ]
    .filter(Boolean)
    .join(' · ')
})

const isThisPlaying = computed(
  () =>
    player.isPlaying.value &&
    player.context.value?.type === 'artist' &&
    player.context.value?.title === artist.value?.name
)

function togglePlay() {
  if (isThisPlaying.value) player.pause()
  else actions.play(allTracks.value, 0, context.value)
}

function playAlbum(album) {
  actions.play(album.tracks, 0, {
    type: 'album',
    title: album.title,
    subtitle: album.artist,
    cover: album.cover,
    route: {
      name: 'Album',
      query: { artist: album.artist, title: album.title },
    },
  })
}

// ── Artist photo / banner (manual picker, always available here - the
// download_cover_art_artist(_banner) settings are reserved for a future
// automatic fetch during the download pipeline, not this page) ────────
const trackFiles = computed(() =>
  allTracks.value.map((track) => track.file).filter(Boolean)
)
const artPhotoUrl = ref('')
const artBannerUrl = ref('')

async function refreshArt() {
  if (!artist.value?.name) {
    artPhotoUrl.value = ''
    artBannerUrl.value = ''
    return
  }
  try {
    const res = await API.getArtistArt(artist.value.name)
    // The saved file keeps the same URL across re-saves (named after the
    // artist, see downtify/artist_profile.py), so a re-upload never changes
    // the <img> src on its own - a cache-busting suffix forces a reload.
    const bust = Date.now()
    artPhotoUrl.value = res.data?.photo_url
      ? `${res.data.photo_url}?v=${bust}`
      : ''
    artBannerUrl.value = res.data?.banner_url
      ? `${res.data.banner_url}?v=${bust}`
      : ''
  } catch {
    artPhotoUrl.value = ''
    artBannerUrl.value = ''
  }
}

watch(() => artist.value?.name, refreshArt, { immediate: true })

const artModalOpen = ref(false)
const artModalKind = ref('photo')

function openArtModal(kind) {
  artModalKind.value = kind
  artModalOpen.value = true
}
</script>
