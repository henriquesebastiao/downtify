<template>
  <div>
    <Navbar />
    <Settings />
    <SearchList
      :data="sm.results.value"
      :error="sm.error.value"
      :artist="am.artist.value"
      :artist-loading="am.loading.value"
      @download="(song) => dm.queue(song)"
      @download-artist-top-songs="onDownloadArtistTopSongs"
    />
  </div>
</template>

<script setup>
import { onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'

import { useSearchManager } from '../model/search'
import { useDownloadManager } from '../model/download'
import { useArtistManager } from '../model/artist'

import Navbar from '/src/components/Navbar.vue'
import Settings from '/src/components/Settings.vue'
import SearchList from '/src/components/SearchList.vue'

onMounted(() => window.scroll(0, 0))

const route = useRoute()
const sm = useSearchManager()
const dm = useDownloadManager()
const am = useArtistManager()

function resolveQuery(query) {
  if (!query) return
  if (sm.isArtistURL(query)) {
    sm.results.value = []
    sm.albumResults.value = []
    am.fetch(query)
  } else {
    am.reset()
    sm.searchFor(query)
  }
}

function onDownloadArtistTopSongs({ count, createPlaylist }) {
  const artist = am.artist.value
  if (!artist) return
  const needsMore =
    count > artist.songs.length && artist.available > artist.songs.length
  const ready = needsMore
    ? am.fetch(route.params.query, count)
    : Promise.resolve()
  ready.then(() =>
    dm.downloadArtistTopSongs(am.artist.value, count, createPlaylist)
  )
}

watch(
  () => route.params.query,
  () => resolveQuery(route.params.query),
  { deep: true }
)

resolveQuery(route.params.query)
</script>
