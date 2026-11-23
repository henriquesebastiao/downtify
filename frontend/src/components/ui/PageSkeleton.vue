<template>
  <!-- A page that isn't there yet: the shape every page shares (a title, a
       line under it, a row of controls, then content). Shown while the app
       learns what it may show, and while a page's own code is on its way. -->
  <div
    class="mx-auto flex max-w-[1680px] flex-col gap-6 px-4 pt-6 sm:px-6 md:pt-8 lg:px-10"
    aria-busy="true"
  >
    <div class="flex flex-col gap-2.5">
      <UiSkeleton class="h-9 w-56 sm:h-10" />
      <UiSkeleton class="h-4 w-80 max-w-full" />
    </div>
    <div class="flex gap-6 border-b border-line pb-3">
      <UiSkeleton v-for="n in 4" :key="n" class="h-3 w-16" />
    </div>
    <div
      class="grid grid-cols-2 gap-x-5 gap-y-7 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 2xl:grid-cols-6"
    >
      <div v-for="n in tiles" :key="n" class="flex flex-col gap-2.5">
        <UiSkeleton class="aspect-square w-full !rounded-cover" />
        <UiSkeleton class="h-4 w-3/4" />
        <UiSkeleton class="h-3 w-1/2" />
      </div>
    </div>
  </div>
</template>

<script setup>
import UiSkeleton from './UiSkeleton.vue'

defineProps({
  tiles: { type: Number, default: 10 },
})
</script>
