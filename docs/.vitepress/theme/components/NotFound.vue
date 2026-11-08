<template>
  <div
    class="mx-auto flex max-w-[640px] flex-col items-center gap-5 px-4 py-24 text-center sm:py-32"
  >
    <p class="text-display text-[88px] leading-none font-bold text-accent">
      404
    </p>
    <h1 class="text-display text-2xl font-semibold">
      {{ ui.notFoundTitle }}
    </h1>
    <p class="text-muted">{{ ui.notFoundText }}</p>
    <div class="mt-2 flex flex-wrap justify-center gap-2.5">
      <button
        type="button"
        class="inline-flex h-11 items-center gap-2 rounded-control bg-accent px-5 text-sm font-semibold text-on-accent hover:bg-accent-hi"
        @click="search.show()"
      >
        <Icon name="search" :size="17" /> {{ ui.searchDocs }}
      </button>
      <ButtonLink :link="home" :text="ui.docsHomeButton" />
    </div>
  </div>
</template>

<script setup>
import ButtonLink from './ButtonLink.vue'
import Icon from './Icon.vue'
import { useSearch } from '../composables/search'
import { useUi } from '../composables/ui'

const search = useSearch()
const { ui, home } = useUi()
</script>
