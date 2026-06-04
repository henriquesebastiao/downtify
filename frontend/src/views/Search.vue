<template>
  <div class="min-h-screen">
    <Navbar />
    <Settings />
    <SearchList
      :data="sm.results.value"
      :error="sm.error.value"
      @download="(song) => dm.queue(song)"
    />
  </div>
</template>

<script setup>
import { onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'

import { useSearchManager } from '../model/search'
import { useDownloadManager } from '../model/download'

import Navbar from '/src/components/Navbar.vue'
import Settings from '/src/components/Settings.vue'
import SearchList from '/src/components/SearchList.vue'

onMounted(() => window.scroll(0, 0))

const route = useRoute()
const sm = useSearchManager()
const dm = useDownloadManager()

watch(
  () => route.params.query,
  (query) => {
    if (query) sm.searchFor(query)
  }
)

sm.searchFor(route.params.query)
</script>
