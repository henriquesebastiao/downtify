<template>
  <footer class="border-t border-line">
    <div
      class="flex flex-col gap-3 px-4 py-6 text-[13px] text-faint sm:flex-row sm:items-center sm:justify-between sm:px-6 lg:px-10"
    >
      <p>{{ theme.copyright }}</p>
      <p class="flex flex-wrap gap-x-5 gap-y-1">
        <a
          :href="`${theme.repo}/releases`"
          target="_blank"
          rel="noopener"
          class="hover:text-fg"
          >Releases</a
        >
        <a
          :href="`${theme.repo}/issues`"
          target="_blank"
          rel="noopener"
          class="hover:text-fg"
          >Issues</a
        >
        <a
          :href="`${theme.repo}/blob/main/LICENSE`"
          target="_blank"
          rel="noopener"
          class="hover:text-fg"
          >License</a
        >
      </p>
    </div>
  </footer>
</template>

<script setup>
import { useData } from 'vitepress'

const { theme } = useData()
</script>
