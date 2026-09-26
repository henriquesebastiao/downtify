<template>
  <div class="flex min-h-dvh bg-bg text-fg">
    <SideNav class="hidden md:flex" />
    <div class="flex min-w-0 flex-1 flex-col">
      <TopBar />
      <main class="flex-1 pb-8">
        <RouterView v-slot="{ Component, route: viewRoute }">
          <Transition name="page" mode="out-in">
            <component :is="Component" :key="viewKey(viewRoute)" />
          </Transition>
        </RouterView>
      </main>
      <!-- Sticky at the end of the content column, so it floats over the
           page yet lines up with the content next to the sidebar. -->
      <MiniPlayer
        class="sticky bottom-[calc(5.25rem+env(safe-area-inset-bottom))] z-40 mx-2 mb-2 md:bottom-5 md:mx-6 md:mb-5"
      />
      <div class="h-[calc(4.75rem+env(safe-area-inset-bottom))] md:hidden" />
    </div>
    <BottomNav class="md:hidden" />
    <NowPlaying />
    <ShortcutsDialog v-model:open="shortcutsOpen" />
    <UiToasts />
    <UiDialog />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import SideNav from './SideNav.vue'
import TopBar from './TopBar.vue'
import BottomNav from './BottomNav.vue'
import MiniPlayer from './MiniPlayer.vue'
import NowPlaying from './NowPlaying.vue'
import ShortcutsDialog from './ShortcutsDialog.vue'
import UiToasts from '../ui/UiToasts.vue'
import UiDialog from '../ui/UiDialog.vue'
import { usePlayer } from '/src/model/player'
import { usePlayerPrefs } from '/src/model/playerPrefs'
import { useLibrary } from '/src/model/library'
import { useDiscover } from '/src/model/discover'
import { useNowPlaying, useUi } from '/src/model/ui'
import { useShortcuts } from './shortcuts'

const player = usePlayer()
const { showLyrics } = usePlayerPrefs()
const route = useRoute()
const router = useRouter()
const ui = useUi()
const nowPlaying = useNowPlaying()
const shortcutsOpen = ref(false)

// The Now playing overlay lives in the query string (?np=1); it must not
// remount the page underneath it.
function viewKey(viewRoute) {
  return viewRoute.meta.viewKey || viewRoute.path
}

useLibrary().load()
// Count listens for Discover, whichever page the music is playing on.
useDiscover().startListenTracking()

useShortcuts({
  player,
  nowPlaying,
  // "L" opens the lyrics panel, which isn't there when they're hidden.
  lyricsEnabled: () => showLyrics.value,
  focusSearch: ui.focusSearch,
  openHelp: () => (shortcutsOpen.value = true),
  goTo: (name) => router.push({ name }),
  // A modal on top swallows every shortcut; Escape closes it.
  closeModal: () => {
    if (ui.closeTopModal()) return true
    if (ui.dialog.value) {
      ui.closeDialog(false)
      return true
    }
    if (shortcutsOpen.value) {
      shortcutsOpen.value = false
      return true
    }
    return false
  },
  hasModal: () =>
    Boolean(ui.dialog.value) ||
    shortcutsOpen.value ||
    ui.modals.value.length > 0,
})
</script>
