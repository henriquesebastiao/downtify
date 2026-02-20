<template>
  <div
    class="navbar m-2 shadow-lg bg-neutral text-neutral-content rounded-box"
    style="width: auto !important"
  >
    <button
      class="px-2 mx-2 navbar-start"
      @click="router.push({ name: 'Home' })"
    >
      <div class="bg-cover bg-no-repeat bg-center">
        <img src="../assets/downtify.svg" class="py-2 pr-2 w-10 center" />
      </div>
      <span class="text-lg font-bold">Downtify</span>
    </button>
    <div class="hidden sm:flex px-2 mx-2 navbar-center w-96 space-x-4">
      <SearchInput class="w-full" />
    </div>
    <div class="navbar-end">
      <a
        class="btn btn-circle mx-2"
        :class="route.name === 'List' ? 'btn-primary' : ''"
        @click="router.push({ name: 'List' })"
        title="List"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
          stroke-width="1.5"
          stroke="currentColor"
          class="size-6"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            d="M8.25 6.75h12M8.25 12h12m-12 5.25h12M3.75 6.75h.007v.008H3.75V6.75Zm.375 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0ZM3.75 12h.007v.008H3.75V12Zm.375 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm-.375 5.25h.007v.008H3.75v-.008Zm.375 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Z"
          />
        </svg>
      </a>
      <label class="btn btn-circle swap swap-rotate mx-2">
        <input
          type="checkbox"
          @change="
            themeMgr.setTheme(
              ($event.target as HTMLInputElement)?.checked ? 'light' : 'dark'
            )
          "
          :checked="themeMgr.currentTheme.value === 'dark' ? false : true"
        />
        <svg
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
          stroke-width="1.5"
          stroke="currentColor"
          class="swap-on size-6 h-8 w-8 m-4"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            d="M12 3v2.25m6.364.386-1.591 1.591M21 12h-2.25m-.386 6.364-1.591-1.591M12 18.75V21m-4.773-4.227-1.591 1.591M5.25 12H3m4.227-4.773L5.636 5.636M15.75 12a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0Z"
          />
        </svg>

        <svg
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
          stroke-width="1.5"
          stroke="currentColor"
          class="swap-off size-6 h-8 w-8 m-4"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            d="M21.752 15.002A9.72 9.72 0 0 1 18 15.75c-5.385 0-9.75-4.365-9.75-9.75 0-1.33.266-2.597.748-3.752A9.753 9.753 0 0 0 3 11.25C3 16.635 7.365 21 12.75 21a9.753 9.753 0 0 0 9.002-5.998Z"
          />
        </svg>
      </label>
      <label for="my-modal" class="btn btn-circle modal-button mx-2">
        <svg
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
          stroke-width="1.5"
          stroke="currentColor"
          class="size-6"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.325.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 0 1 1.37.49l1.296 2.247a1.125 1.125 0 0 1-.26 1.431l-1.003.827c-.293.241-.438.613-.43.992a7.723 7.723 0 0 1 0 .255c-.008.378.137.75.43.991l1.004.827c.424.35.534.955.26 1.43l-1.298 2.247a1.125 1.125 0 0 1-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.47 6.47 0 0 1-.22.128c-.331.183-.581.495-.644.869l-.213 1.281c-.09.543-.56.94-1.11.94h-2.594c-.55 0-1.019-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 0 1-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 0 1-1.369-.49l-1.297-2.247a1.125 1.125 0 0 1 .26-1.431l1.004-.827c.292-.24.437-.613.43-.991a6.932 6.932 0 0 1 0-.255c.007-.38-.138-.751-.43-.992l-1.004-.827a1.125 1.125 0 0 1-.26-1.43l1.297-2.247a1.125 1.125 0 0 1 1.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.086.22-.128.332-.183.582-.495.644-.869l.214-1.28Z"
          />
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z"
          />
        </svg>
      </label>
      <div class="indicator mx-2">
        <div
          v-if="pt.downloadQueue.value.length > 0"
          class="indicator-item indicator-top indicator-end badge badge-secondary"
          style="top: -5px; right: -5px"
        >
          {{ pt.downloadQueue.value.length }}
        </div>
        <label for="my-modal" class="btn btn-circle modal-button">
          <a
            class="btn btn-circle"
            :class="
              pt.downloadQueue.value.length > 0 || route.name === 'Download'
                ? 'btn-primary'
                : 'btn-ghost'
            "
            @click="
              route.name === 'Download'
                ? router.push({
                    name: 'Search',
                    params: { query: sm.searchTerm.value },
                  })
                : router.push({ name: 'Download' })
            "
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              stroke-width="1.5"
              stroke="currentColor"
              class="size-6"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5M16.5 12 12 16.5m0 0L7.5 12m4.5 4.5V3"
              />
            </svg>
          </a>
        </label>
      </div>
    </div>
  </div>
  <div class="sm:hidden px-2 mx-2">
    <SearchInput class="w-full" />
  </div>
</template>

<script setup lang="ts">
import router from '../router'
import { useRoute } from 'vue-router'

import { useBinaryThemeManager } from '../model/theme'
import { useProgressTracker, useDownloadManager } from '../model/download'
import { useSearchManager } from '../model/search'

import { Icon } from '@iconify/vue'
import SearchInput from '../components/SearchInput.vue'

const pt = useProgressTracker()
const dm = useDownloadManager()
const sm = useSearchManager()
const route = useRoute()

const themeMgr = useBinaryThemeManager({
  newLightAlias: 'downtify-light',
  newDarkAlias: 'downtify-dark',
})
</script>

<style scoped>
.center {
  text-align: center;

  margin-left: auto;
  margin-right: auto;
}
</style>
