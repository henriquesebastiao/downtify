<template>
  <header class="sticky top-0 z-30 glass-nav">
    <div
      class="mx-auto flex h-16 w-full max-w-6xl items-center gap-3 px-4 sm:px-6"
    >
      <button
        class="flex items-center gap-2 shrink-0"
        @click="router.push({ name: 'Home' })"
        :title="'Home'"
      >
        <img
          src="../assets/downtify.svg"
          class="h-8 w-8 drop-shadow-[0_0_8px_rgba(26,208,92,0.55)]"
        />
        <span class="hidden sm:inline text-lg font-bold tracking-tight">
          Downtify
        </span>
      </button>

      <div class="hidden md:flex flex-1 justify-center">
        <SearchInput class="w-full max-w-md" :compact="true" />
      </div>

      <div class="ml-auto flex items-center gap-1 sm:gap-2">
        <button
          class="icon-btn"
          :class="{ 'icon-btn-active': route.name === 'List' }"
          @click="router.push({ name: 'List' })"
          title="Library"
        >
          <Icon icon="clarity:library-line" class="h-5 w-5" />
        </button>

        <button
          class="icon-btn"
          :class="{ 'icon-btn-active': route.name === 'Monitor' }"
          @click="router.push({ name: 'Monitor' })"
          title="Playlist Monitor"
        >
          <Icon icon="clarity:eye-line" class="h-5 w-5" />
        </button>

        <button
          class="icon-btn relative"
          :class="{ 'icon-btn-active': route.name === 'Download' }"
          @click="
            route.name === 'Download'
              ? router.push({
                  name: 'Search',
                  params: { query: sm.searchTerm.value || ' ' },
                })
              : router.push({ name: 'Download' })
          "
          title="Queue"
        >
          <Icon icon="clarity:download-line" class="h-5 w-5" />
          <span
            v-if="pt.downloadQueue.value.length > 0"
            class="absolute -top-1 -right-1 inline-flex h-5 min-w-[1.25rem] items-center justify-center rounded-full bg-primary text-[10px] font-bold text-primary-content shadow-glow-sm"
          >
            {{ pt.downloadQueue.value.length }}
          </span>
        </button>

        <button
          class="icon-btn"
          @click="
            themeMgr.setTheme(
              themeMgr.currentTheme.value === 'dark' ? 'light' : 'dark'
            )
          "
          :title="
            themeMgr.currentTheme.value === 'dark'
              ? 'Switch to light'
              : 'Switch to dark'
          "
        >
          <Icon
            v-if="themeMgr.currentTheme.value === 'dark'"
            icon="clarity:sun-line"
            class="h-5 w-5"
          />
          <Icon v-else icon="clarity:moon-line" class="h-5 w-5" />
        </button>

        <label
          for="settings-modal"
          class="icon-btn cursor-pointer"
          title="Settings"
        >
          <Icon icon="clarity:cog-line" class="h-5 w-5" />
        </label>
      </div>
    </div>

    <div class="md:hidden px-4 pb-3">
      <SearchInput :compact="true" />
    </div>
  </header>
</template>

<script setup>
import { Icon } from '@iconify/vue'
import { useRoute } from 'vue-router'

import router from '../router'
import { useBinaryThemeManager } from '../model/theme'
import { useProgressTracker } from '../model/download'
import { useSearchManager } from '../model/search'

import SearchInput from './SearchInput.vue'

const route = useRoute()
const themeMgr = useBinaryThemeManager({
  newLightAlias: 'downtify-light',
  newDarkAlias: 'downtify-dark',
})
const pt = useProgressTracker()
const sm = useSearchManager()
</script>
