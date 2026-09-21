<template>
  <aside
    class="sticky top-0 h-dvh shrink-0 flex-col gap-7 overflow-y-auto border-r border-line bg-side px-3 py-6 transition-[width] duration-300 ease-out-soft"
    :class="collapsed ? 'w-[72px]' : 'w-[72px] xl:w-[248px] xl:px-4'"
  >
    <div class="flex items-center gap-2.5 px-2.5">
      <RouterLink
        :to="{ name: 'Home' }"
        class="flex items-center gap-2.5"
        :title="t('nav.home')"
      >
        <AppLogo :size="28" />
        <span class="text-display text-[19px] font-bold" :class="labelClass"
          >Downtify</span
        >
      </RouterLink>
    </div>

    <nav class="flex flex-col gap-0.5" :aria-label="t('nav.main')">
      <RouterLink
        v-for="item in items"
        :key="item.name"
        :to="{ name: item.name }"
        class="group relative flex h-10 items-center gap-3 rounded-control px-3 text-sm transition-colors"
        :class="
          isActive(item)
            ? 'bg-surface-2 font-semibold text-fg'
            : 'font-medium text-muted hover:bg-surface-2/60 hover:text-fg'
        "
        :title="t(item.label)"
      >
        <AppIcon
          :name="item.icon"
          :size="18"
          :class="isActive(item) ? 'text-accent' : ''"
        />
        <span :class="labelClass">{{ t(item.label) }}</span>
        <span
          v-if="item.name === 'Queue' && pending"
          class="tabular flex h-5 min-w-5 items-center justify-center rounded-full bg-accent px-1.5 text-[11px] font-bold text-on-accent"
          :class="
            collapsed
              ? 'absolute top-0.5 right-0.5 h-4 min-w-4 px-1 text-[10px]'
              : 'absolute top-0.5 right-0.5 h-4 min-w-4 px-1 text-[10px] xl:static xl:ml-auto xl:h-5 xl:min-w-5 xl:px-1.5 xl:text-[11px]'
          "
          >{{ pending }}</span
        >
      </RouterLink>
    </nav>

    <div
      v-if="recentPlaylists.length"
      class="flex flex-col gap-1"
      :class="labelClass"
    >
      <div class="flex items-center justify-between px-3 pb-1.5">
        <span class="eyebrow">{{ t('nav.playlists') }}</span>
        <RouterLink
          :to="{ name: 'Library', params: { tab: 'playlists' } }"
          class="text-xs font-semibold text-faint hover:text-fg"
          >{{ t('common.seeAll') }}</RouterLink
        >
      </div>
      <RouterLink
        v-for="playlist in recentPlaylists"
        :key="playlist.key"
        :to="{ name: 'Playlist', query: { name: playlist.name } }"
        class="flex h-11 items-center gap-2.5 rounded-control px-3 transition-colors hover:bg-surface-2/60"
      >
        <CoverArt
          :src="playlist.cover || playlist.covers[0] || ''"
          :covers="playlist.covers"
          :name="playlist.title"
          rounded="rounded-[7px]"
          :letter-size="13"
          :icon-size="14"
          :icon="playlist.liked ? 'heart' : 'playlist'"
          :symbol="playlist.liked"
          class="size-[30px]"
        />
        <span class="flex min-w-0 flex-col">
          <span class="truncate text-[13px] font-medium text-fg-2">{{
            playlist.title
          }}</span>
          <span class="tabular text-[11px] text-faint">{{
            t('common.tracks', { count: playlist.tracks.length })
          }}</span>
        </span>
      </RouterLink>
    </div>

    <div class="mt-auto flex flex-col gap-0.5">
      <a
        v-if="update?.update_available"
        :href="update.release_url"
        target="_blank"
        rel="noopener"
        class="mb-2 flex items-center gap-2.5 rounded-control bg-accent/12 px-3 py-2 text-[13px] font-semibold text-accent"
        :title="t('nav.updateAvailable', { version: update.latest_version })"
      >
        <AppIcon name="sparkle" :size="17" />
        <span :class="labelClass">{{
          t('nav.updateAvailable', { version: update.latest_version })
        }}</span>
      </a>
      <RouterLink
        :to="{ name: 'Settings' }"
        class="flex h-10 items-center gap-3 rounded-control px-3 text-sm transition-colors"
        :class="
          route.name === 'Settings'
            ? 'bg-surface-2 font-semibold text-fg'
            : 'font-medium text-muted hover:bg-surface-2/60 hover:text-fg'
        "
        :title="t('nav.settings')"
      >
        <AppIcon
          name="settings"
          :size="18"
          :class="route.name === 'Settings' ? 'text-accent' : ''"
        />
        <span :class="labelClass">{{ t('nav.settings') }}</span>
      </RouterLink>
      <button
        type="button"
        class="hidden h-10 items-center gap-3 rounded-control px-3 text-left text-sm font-medium text-faint transition-colors hover:bg-surface-2/60 hover:text-fg xl:flex"
        :title="collapsed ? t('nav.expand') : t('nav.collapse')"
        @click="collapsed = !collapsed"
      >
        <AppIcon name="panel-left" :size="18" />
        <span :class="labelClass">{{ t('nav.collapse') }}</span>
      </button>
      <p
        v-if="version"
        class="tabular px-3 pt-2 text-[11px] text-faint"
        :class="labelClass"
      >
        Downtify {{ version }}
      </p>
    </div>
  </aside>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useLocalStorage } from '@vueuse/core'
import AppIcon from '../ui/AppIcon.vue'
import AppLogo from '../ui/AppLogo.vue'
import CoverArt from '../ui/CoverArt.vue'
import { useI18n } from '/src/i18n'
import { useLibrary } from '/src/model/library'
import { useUpdateCheck } from '/src/model/updateCheck'
import { usePendingCount } from './navState'

const { t } = useI18n()
const route = useRoute()
const library = useLibrary()
const pending = usePendingCount()
const update = useUpdateCheck().status
const collapsed = useLocalStorage('downtify-sidebar-collapsed', false)
const version = computed(() => {
  const v = localStorage.getItem('version')
  return v && v !== '0.0.0' ? v : ''
})

const items = [
  { name: 'Home', icon: 'home', label: 'nav.home' },
  {
    name: 'Search',
    icon: 'search',
    label: 'nav.search',
    match: ['Link', 'TopSongs'],
  },
  {
    name: 'Library',
    icon: 'library',
    label: 'nav.library',
    match: ['Album', 'Artist', 'Playlist'],
  },
  { name: 'Queue', icon: 'download', label: 'nav.queue' },
  { name: 'Monitor', icon: 'radar', label: 'nav.monitor' },
  {
    name: 'Podcasts',
    icon: 'mic',
    label: 'nav.podcasts',
    match: ['PodcastShow'],
  },
]

function isActive(item) {
  return route.name === item.name || (item.match || []).includes(route.name)
}

const labelClass = computed(() =>
  collapsed.value ? 'hidden' : 'hidden xl:inline xl:flex-1 xl:truncate'
)

const recentPlaylists = computed(() =>
  [...library.playlists.value]
    .filter((playlist) => playlist.tracks.length)
    // The liked songs stay at the top; the rest are the newest.
    .sort((a, b) => Number(b.liked) - Number(a.liked) || b.added - a.added)
    .slice(0, 6)
)
</script>
