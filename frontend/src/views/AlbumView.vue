<template>
  <div>
    <DetailState
      :loaded="library.loaded.value"
      :found="!!album"
      icon="disc"
      :missing="t('album.notFound')"
    >
      <CollectionHero
        :title="album.title"
        :kicker="[t('album.kicker'), album.year].filter(Boolean).join(' · ')"
        :cover="album.cover"
        :name="album.title"
      >
        <template #subtitle>
          <RouterLink
            v-if="album.artist"
            :to="{ name: 'Artist', query: { name: album.artist } }"
            class="font-semibold text-fg hover:underline"
            >{{ album.artist }}</RouterLink
          >
          <span v-for="part in facts" :key="part"> · {{ part }}</span>
        </template>
        <template #actions>
          <PlayButton
            :label="t('actions.playItem', { name: album.title })"
            :playing="isThisPlaying"
            @click="togglePlay"
          />
          <UiIconButton
            icon="shuffle"
            :label="t('actions.shuffle')"
            size="lg"
            round
            @click="actions.play(album.tracks, 0, context, { shuffled: true })"
          />
          <UiButton
            variant="ghost"
            icon="queue"
            @click="actions.enqueue(album.tracks)"
          >
            {{ t('actions.addToQueue') }}
          </UiButton>
          <UiButton
            variant="ghost"
            icon="zip"
            class="max-sm:hidden"
            @click="actions.downloadZip(album.tracks)"
          >
            {{ t('library.downloadZip') }}
          </UiButton>
          <UiMenu :items="menu" :label="t('common.more')" size="lg" />
        </template>
      </CollectionHero>

      <section class="mx-auto max-w-[1680px] px-4 sm:px-6 lg:px-10">
        <TrackList
          :tracks="album.tracks"
          :context="context"
          :show-album="false"
          :show-added="false"
          :show-cover="false"
          :link-artist="false"
          numbering="track"
          :hide-menu="['album']"
        />
      </section>

      <section
        v-if="moreByArtist.length"
        class="mx-auto mt-12 flex max-w-[1680px] flex-col gap-4 px-4 sm:px-6 lg:px-10"
      >
        <div class="flex items-baseline justify-between">
          <h2 class="text-display text-xl font-semibold">
            {{ t('album.moreBy', { artist: album.artist }) }}
          </h2>
          <RouterLink
            :to="{ name: 'Artist', query: { name: album.artist } }"
            class="text-[13px] font-semibold text-muted hover:text-fg"
            >{{ t('common.seeAll') }}</RouterLink
          >
        </div>
        <div
          class="grid grid-cols-2 gap-x-5 gap-y-7 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 2xl:grid-cols-6"
        >
          <MediaTile
            v-for="other in moreByArtist"
            :key="other.key"
            :to="{
              name: 'Album',
              query: { artist: other.artist, title: other.title },
            }"
            :title="other.title"
            :subtitle="other.year"
            :cover="other.cover"
            :name="other.title"
            @play="actions.play(other.tracks, 0, albumContext(other))"
          />
        </div>
      </section>
    </DetailState>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import UiButton from '/src/components/ui/UiButton.vue'
import UiIconButton from '/src/components/ui/UiIconButton.vue'
import UiMenu from '/src/components/ui/UiMenu.vue'
import CollectionHero from '/src/components/library/CollectionHero.vue'
import DetailState from '/src/components/library/DetailState.vue'
import MediaTile from '/src/components/library/MediaTile.vue'
import PlayButton from '/src/components/library/PlayButton.vue'
import TrackList from '/src/components/library/TrackList.vue'
import { useLibrary } from '/src/model/library'
import { usePlayer } from '/src/model/player'
import { useTrackActions } from '/src/model/trackActions'
import { albumKey } from '/src/lib/library'
import { formatBytes, splitLength } from '/src/lib/format'
import { useI18n } from '/src/i18n'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const library = useLibrary()
const player = usePlayer()
const actions = useTrackActions()

const album = computed(() =>
  library.findAlbum(
    String(route.query.artist || ''),
    String(route.query.title || '')
  )
)

function albumContext(item) {
  return {
    type: 'album',
    title: item.title,
    subtitle: item.artist,
    cover: item.cover,
    route: { name: 'Album', query: { artist: item.artist, title: item.title } },
  }
}

const context = computed(() => (album.value ? albumContext(album.value) : null))

const facts = computed(() => {
  const a = album.value
  const { hours, minutes } = splitLength(a.duration)
  const formats = [...new Set(a.tracks.map((track) => track.format))].join(', ')
  return [
    t('common.tracks', { count: a.tracks.length }),
    hours
      ? t('common.lengthHours', { hours, minutes })
      : t('common.lengthMinutes', { minutes }),
    formats,
    formatBytes(a.size),
  ].filter(Boolean)
})

const isThisPlaying = computed(() => {
  const current = player.currentTrack.value
  return (
    player.isPlaying.value &&
    !!current &&
    albumKey(current.albumArtist, current.album) === album.value?.key
  )
})

function togglePlay() {
  if (isThisPlaying.value) player.pause()
  else actions.play(album.value.tracks, 0, context.value)
}

const moreByArtist = computed(() => {
  const artist = library.findArtist(album.value?.artist)
  if (!artist) return []
  return artist.albums
    .filter((other) => other.key !== album.value.key)
    .slice(0, 6)
})

const menu = computed(() => [
  {
    label: t('actions.playNext'),
    icon: 'play-next',
    action: () => actions.playNext(album.value.tracks),
  },
  {
    label: t('library.downloadZip'),
    icon: 'zip',
    action: () => actions.downloadZip(album.value.tracks),
  },
  {
    label: t('album.searchMore'),
    icon: 'search',
    action: () =>
      router.push({
        name: 'Search',
        params: { query: `${album.value.artist} ${album.value.title}` },
      }),
  },
  { divider: true },
  {
    label: t('album.delete'),
    icon: 'trash',
    danger: true,
    action: async () => {
      const deleted = await actions.remove(album.value.tracks)
      if (deleted.length)
        router.push({ name: 'Library', params: { tab: 'albums' } })
    },
  },
])
</script>
