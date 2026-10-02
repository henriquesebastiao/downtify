<template>
  <div>
    <DetailState
      :loaded="ready"
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
          <!-- "Various Artists" has no page: its tracks are on their own
               artists' pages. -->
          <RouterLink
            v-if="album.artist && !isCompilation"
            :to="{ name: 'Artist', query: { name: album.artist } }"
            class="font-semibold text-fg hover:underline"
            >{{ album.artist }}</RouterLink
          >
          <span v-else-if="album.artist" class="font-semibold text-fg">{{
            album.artist
          }}</span>
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
            v-if="auth.isAdmin.value"
            variant="ghost"
            :icon="isCompilation ? 'user' : 'users'"
            :loading="changingCompilation"
            @click="toggleCompilation"
          >
            {{
              isCompilation
                ? t('album.unmarkCompilation')
                : t('album.markCompilation')
            }}
          </UiButton>
          <!-- Download as ZIP lives in the ⋯ menu below. -->
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
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import UiButton from '/src/components/ui/UiButton.vue'
import UiIconButton from '/src/components/ui/UiIconButton.vue'
import UiMenu from '/src/components/ui/UiMenu.vue'
import CollectionHero from '/src/components/library/CollectionHero.vue'
import DetailState from '/src/components/library/DetailState.vue'
import MediaTile from '/src/components/library/MediaTile.vue'
import PlayButton from '/src/components/library/PlayButton.vue'
import TrackList from '/src/components/library/TrackList.vue'
import API from '/src/model/api'
import { useAuth } from '/src/model/auth'
import { useLibrary } from '/src/model/library'
import { usePlayer } from '/src/model/player'
import { usePlaylistActions } from '/src/model/playlistActions'
import { useTrackActions } from '/src/model/trackActions'
import { useUi } from '/src/model/ui'
import { albumKey, isVariousArtists } from '/src/lib/library'
import { formatBytes, splitLength } from '/src/lib/format'
import { useI18n } from '/src/i18n'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const library = useLibrary()
const player = usePlayer()
const actions = useTrackActions()
const playlistActions = usePlaylistActions()

const ready = ref(false)

async function loadAlbum() {
  ready.value = false
  await library.loadArtistTracks(String(route.query.artist || ''))
  ready.value = true
}

onMounted(loadAlbum)
watch(
  () => [route.query.artist, route.query.title],
  () => loadAlbum()
)
const auth = useAuth()
const ui = useUi()

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

// Admins can put the whole album in one of their playlists (or a new one).
const addToPlaylist = computed(() =>
  playlistActions.addMenuItems(album.value?.tracks || [])
)

const isCompilation = computed(() => isVariousArtists(album.value?.artist))
const changingCompilation = ref(false)

// Marks (or unmarks) the album as a Various Artists compilation (admins
// only, like Replace audio): the server rewrites every track's
// album-artist tag and compilation flag, so the album moves to the artist
// it now belongs to - follow it there. Tracks whose files already were in
// that state (a stale listing) come back unchanged but re-read: the album
// they really are in is followed the same way.
async function toggleCompilation() {
  if (changingCompilation.value) return
  const current = album.value
  const compilation = !isCompilation.value
  changingCompilation.value = true
  try {
    const { data } = await API.setAlbumCompilation(
      current.tracks.map((track) => track.file),
      compilation
    )
    await library.load({ force: true })
    if (data.failed?.length) {
      ui.toast(t('album.compilationPartial'), { kind: 'error' })
    } else {
      ui.toast(
        t(
          compilation ? 'album.markedCompilation' : 'album.unmarkedCompilation'
        ),
        { kind: 'success' }
      )
    }
    if (data.album_artist && data.album_artist !== current.artist) {
      router.replace({
        name: 'Album',
        query: { artist: data.album_artist, title: current.title },
      })
    }
  } catch (err) {
    ui.toast(err?.response?.data?.detail || t('album.compilationFailed'), {
      kind: 'error',
    })
  } finally {
    changingCompilation.value = false
  }
}

const menu = computed(() => [
  {
    label: t('actions.playNext'),
    icon: 'play-next',
    action: () => actions.playNext(album.value.tracks),
  },
  ...(addToPlaylist.value.length
    ? [{ divider: true }, ...addToPlaylist.value, { divider: true }]
    : []),
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
