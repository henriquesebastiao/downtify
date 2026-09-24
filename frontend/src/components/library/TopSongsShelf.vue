<template>
  <div class="flex flex-col gap-3">
    <div class="-mx-3 flex flex-col">
      <TrackDownPlayHeader />
      <TrackDownPlay
        v-for="(song, i) in data.songs"
        :key="song.song_id || song.url"
        :song="song"
        :index="i"
        :queue="queue"
        :context="context"
      />
    </div>
    <!-- Choosing songs, downloading them together or making a playlist is
         what the Top Songs page is for; this list only downloads and plays. -->
    <RouterLink
      v-if="pageUrl"
      :to="{ name: 'TopSongs', query: { url: pageUrl } }"
      class="inline-flex items-center gap-1.5 self-start text-[13px] font-semibold text-muted hover:text-fg"
    >
      <AppIcon name="arrow-up-right" :size="14" />{{ t('artist.topSongsLink') }}
    </RouterLink>
  </div>
</template>

<script setup>
// An artist's top songs on their Library page: a minimal list that
// downloads a song and, once it's in the library, plays it (TrackDownPlay).
import { computed } from 'vue'
import AppIcon from '../ui/AppIcon.vue'
import TrackDownPlay from './TrackDownPlay.vue'
import TrackDownPlayHeader from './TrackDownPlayHeader.vue'
import { useLibrary } from '/src/model/library'
import { playableQueue } from '/src/lib/topSongs'
import { useI18n } from '/src/i18n'

const props = defineProps({
  // `GET /api/artists/top_songs/spotify`: `{ artist_id, name, songs, ... }`.
  data: { type: Object, required: true },
  // The player's "playing from" for the songs played from here.
  context: { type: Object, default: null },
})

const { t } = useI18n()
const library = useLibrary()

// Playing a song queues the list's downloaded songs, in ranking order,
// starting from that one.
const queue = computed(() => playableQueue(props.data.songs, library.findTrack))

// The same artist on the Top Songs page, where they can be picked,
// downloaded together or made into a playlist.
const pageUrl = computed(() =>
  props.data.artist_id
    ? `https://open.spotify.com/artist/${props.data.artist_id}`
    : ''
)
</script>
