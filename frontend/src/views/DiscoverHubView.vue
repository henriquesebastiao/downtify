<template>
  <div>
    <div class="mx-auto max-w-[1680px] px-4 pt-6 sm:px-6 md:pt-8 lg:px-10">
      <UiTabs :items="tabs" :model-value="active" />
    </div>
    <RouterView v-slot="{ Component }">
      <Transition name="page" mode="out-in">
        <component :is="Component" :key="route.name" />
      </Transition>
    </RouterView>
  </div>
</template>

<script setup>
// Discover and the Finder under one menu entry, one tab each. A thin shell:
// each tab is its own page (its own route, header and state), rendered here
// through a nested <RouterView> and unaware of the other - this only draws
// the tabs above whichever one the route picked.
//
// Both routes share a `viewKey` (see router/index.js), so switching tabs
// swaps the page below without remounting this, the tabs included.
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import UiTabs from '/src/components/ui/UiTabs.vue'
import { useI18n } from '/src/i18n'

const { t } = useI18n()
const route = useRoute()

const active = computed(() => (route.name === 'Finder' ? 'finder' : 'discover'))

// Coming back to the Finder tab reopens the last search there, the way
// leaving and returning to any page with a query in its URL would.
const lastSearch = ref('')
watch(
  () => [route.name, route.query.q],
  ([name, q]) => {
    if (name === 'Finder') lastSearch.value = String(q || '')
  },
  { immediate: true }
)

const tabs = computed(() => [
  {
    id: 'discover',
    label: t('nav.discover'),
    to: { name: 'Discover' },
  },
  {
    id: 'finder',
    label: t('nav.finder'),
    to: lastSearch.value
      ? { name: 'Finder', query: { q: lastSearch.value } }
      : { name: 'Finder' },
  },
])
</script>
