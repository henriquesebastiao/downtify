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
        :cover="artist.cover"
        :name="artist.name"
        icon="user"
        round
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
            @click="actions.play(allTracks, 0, context, { shuffled: true })"
          />
          <UiButton
            variant="ghost"
            icon="queue"
            @click="actions.enqueue(allTracks)"
          >
            {{ t('actions.addToQueue') }}
          </UiButton>
          <UiButton
            variant="ghost"
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
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import UiButton from '/src/components/ui/UiButton.vue'
import UiIconButton from '/src/components/ui/UiIconButton.vue'
import CollectionHero from '/src/components/library/CollectionHero.vue'
import DetailState from '/src/components/library/DetailState.vue'
import MediaTile from '/src/components/library/MediaTile.vue'
import PlayButton from '/src/components/library/PlayButton.vue'
import TrackList from '/src/components/library/TrackList.vue'
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
</script>
