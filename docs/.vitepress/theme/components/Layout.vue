<template>
  <div class="flex min-h-dvh bg-bg text-fg">
    <a
      href="#main"
      class="sr-only z-[70] rounded-control bg-accent px-4 py-2 font-semibold text-on-accent focus:not-sr-only focus:fixed focus:top-3 focus:left-3"
      >Skip to content</a
    >
    <SideNav class="hidden lg:flex" />
    <div class="flex min-w-0 flex-1 flex-col">
      <TopBar :nav-open="navOpen" @open-nav="navOpen = true" />
      <main id="main" class="flex-1" tabindex="-1">
        <NotFound v-if="page.isNotFound" />
        <Home v-else-if="frontmatter.layout === 'home'" />
        <DocPage v-else />
      </main>
      <SiteFooter />
    </div>
    <MobileNav :open="navOpen" @close="navOpen = false" />
    <SearchDialog />
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useData, useRoute } from 'vitepress'
import DocPage from './DocPage.vue'
import Home from './Home.vue'
import MobileNav from './MobileNav.vue'
import NotFound from './NotFound.vue'
import SearchDialog from './SearchDialog.vue'
import SideNav from './SideNav.vue'
import SiteFooter from './SiteFooter.vue'
import TopBar from './TopBar.vue'
import { useSearch } from '../composables/search'
import { startThemeMode } from '../composables/theme-mode'

const { page, frontmatter } = useData()
const route = useRoute()
const search = useSearch()
const navOpen = ref(false)

watch(
  () => route.path,
  () => (navOpen.value = false)
)

function isTyping(target) {
  return (
    target?.isContentEditable ||
    ['INPUT', 'TEXTAREA', 'SELECT'].includes(target?.tagName)
  )
}

function onKeydown(event) {
  const mod = event.ctrlKey || event.metaKey
  if (mod && event.key.toLowerCase() === 'k') {
    event.preventDefault()
    search.open.value ? search.hide() : search.show()
  } else if (event.key === '/' && !mod && !isTyping(event.target)) {
    event.preventDefault()
    search.show()
  }
}

onMounted(() => {
  startThemeMode()
  window.addEventListener('keydown', onKeydown)
})
onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))
</script>
