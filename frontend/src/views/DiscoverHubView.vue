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
      <FinderResults v-if="query" key="results" :query="query" />
      <DiscoverView v-else key="discover" />
    </Transition>
  </div>
</template>

<script setup>
// Discover and the Finder on one page: the Finder's search box on top, with
// the recent searches beside it; below, Discover's suggestions - replaced by
// what the Finder found while a search (`?q=`) is on. Clearing the box, or
// going back, brings the suggestions back.
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
const text = ref(query.value)

// The box mirrors the search on screen (a recent search clicked, going
// back), and every search on screen is remembered.
watch(
  query,
  (value) => {
    text.value = value
    remember(value)
  },
  { immediate: true }
)

function search(term) {
  router.push({ name: 'Discover', query: { q: term } })
}

function clearSearch() {
  if (query.value) router.push({ name: 'Discover' })
}
</script>
