<template>
  <div>
    <div class="mx-auto max-w-[1680px] px-4 pt-6 sm:px-6 md:pt-8 lg:px-10">
      <div
        class="grid gap-4 lg:grid-cols-[minmax(0,42rem)_minmax(0,1fr)] lg:items-start lg:gap-10"
      >
        <FinderSearchBar v-model="text" @submit="search" @clear="clearSearch" />
        <FinderRecentSearches
          v-if="recent.length"
          :terms="recent"
          :active="query"
          @clear="clearRecent"
        />
      </div>
    </div>
    <Transition name="page" mode="out-in">
      <FinderResults
        v-if="query || artist"
        key="results"
        :query="query"
        :artist="artist"
        :search-links="false"
      />
      <DiscoverView v-else key="discover" />
    </Transition>
  </div>
</template>

<script setup>
// Discover and the Finder on one page: the Finder's search box on top, with
// the recent searches beside it; below, Discover's suggestions - replaced by
// what the Finder found while a search (`?q=`) is on, or by an artist's songs
// (`?artist=<Deezer id>&name=`, Discover's "Find songs"). Clearing the box,
// or going back, brings the suggestions back.
//
// A thin shell: DiscoverView and FinderResults are each whole on their own
// and don't know about each other.
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import FinderRecentSearches from '/src/components/finder/FinderRecentSearches.vue'
import FinderResults from '/src/components/finder/FinderResults.vue'
import FinderSearchBar from '/src/components/finder/FinderSearchBar.vue'
import DiscoverView from '/src/views/DiscoverView.vue'
import { useRecentSearches } from '/src/model/finder'

const route = useRoute()
const router = useRouter()
const { recent, remember, clear: clearRecent } = useRecentSearches()

const query = computed(() => String(route.query.q || '').trim())
const artist = computed(() => {
  const id = String(route.query.artist || '').trim()
  return id ? { id, name: String(route.query.name || '').trim() } : null
})
const text = ref('')

// The box mirrors what's on screen (a recent search clicked, going back,
// an artist's songs), and every typed search is remembered.
watch(
  [query, artist],
  ([value, shown]) => {
    text.value = value || shown?.name || ''
    remember(value)
  },
  { immediate: true }
)

function search(term) {
  router.push({ name: 'Discover', query: { q: term } })
}

function clearSearch() {
  if (query.value || artist.value) router.push({ name: 'Discover' })
}
</script>
