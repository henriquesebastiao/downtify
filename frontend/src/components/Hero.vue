<template>
  <div class="hero min-h-screen">
    <div v-if="true" class="flex justify-end absolute top-0 right-0">
      <label class="btn btn-circle swap swap-rotate m-2">
        <input
          type="checkbox"
          @change="
            themeMgr.setTheme(
              ($event.target as HTMLInputElement)?.checked ? 'light' : 'dark'
            )
          "
          :checked="themeMgr.currentTheme.value === 'dark' ? false : true"
        />
        <Icon
          icon="clarity:sun-line"
          class="swap-on fill-current h-8 w-8 m-4"
        />
        <Icon
          icon="clarity:moon-line"
          class="swap-off fill-current h-8 w-8 m-4"
        />
      </label>
      <label for="my-modal" class="btn btn-square modal-button m-2">
        <Icon icon="clarity:settings-line" class="h-6 w-6" />
      </label>
    </div>
    <div class="block text-center justify-center hero-content">
      <div class="bg-cover bg-no-repeat bg-center">
        <img src="../assets/downtify.svg" class="mb-5 w-32 center" />
      </div>
      <div>
        <h1 class="mb-1 text-5xl font-bold text-base-content">Downtify</h1>
        <span
          class="mb-5 inline-flex items-center rounded-md bg-green-400/10 px-2 py-1 text-xs font-medium text-green-400 inset-ring inset-ring-green-500/20"
          >v0.3.2</span
        >
        <p class="mb-5 text-base-content">
          Your music along with album art, lyrics and metadata.
        </p>
      </div>

      <SearchInput />
    </div>
  </div>
</template>

<script setup lang="ts">
import { Icon } from '@iconify/vue'
import SearchInput from '../components/SearchInput.vue'

import { useBinaryThemeManager } from '../model/theme'

const themeMgr = useBinaryThemeManager({
  newLightAlias: 'downtify-light',
  newDarkAlias: 'downtify-dark',
})

const version = localStorage.getItem('version') || '0.0.0'
</script>

<style scoped>
.center {
  text-align: center;
  margin-left: auto;
  margin-right: auto;
}
</style>
