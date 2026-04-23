<template>
  <header class="absolute top-0 inset-x-0 z-30">
    <div
      class="mx-auto flex h-16 w-full max-w-6xl items-center gap-3 px-4 sm:px-6"
    >
      <div class="flex items-center gap-2">
        <img
          src="../assets/downtify.svg"
          class="h-8 w-8 drop-shadow-[0_0_8px_rgba(26,208,92,0.55)]"
        />
        <span class="text-lg font-bold tracking-tight">Downtify</span>
      </div>
      <div class="ml-auto flex items-center gap-1 sm:gap-2">
        <button
          class="icon-btn"
          @click="router.push({ name: 'List' })"
          title="Library"
        >
          <Icon icon="clarity:library-line" class="h-5 w-5" />
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
  </header>
</template>

<script setup>
import { Icon } from '@iconify/vue'
import router from '../router'
import { useBinaryThemeManager } from '../model/theme'

const themeMgr = useBinaryThemeManager({
  newLightAlias: 'downtify-light',
  newDarkAlias: 'downtify-dark',
})
</script>
