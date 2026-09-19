<template>
  <header
    class="sticky top-0 z-30 border-b border-line bg-bg/85 backdrop-blur-xl"
  >
    <div class="flex h-16 items-center gap-2 px-4 sm:px-6 lg:px-10">
      <button
        type="button"
        class="-ml-2 flex size-10 items-center justify-center rounded-control text-fg-3 hover:bg-surface-2 lg:hidden"
        aria-label="Open navigation"
        :aria-expanded="navOpen"
        aria-controls="mobile-nav"
        @click="$emit('open-nav')"
      >
        <Icon name="menu" :size="20" />
      </button>
      <a
        :href="withBase('/')"
        class="mr-1 flex items-center gap-2 lg:hidden"
        title="Downtify docs home"
      >
        <Logo :size="26" />
        <span class="text-display hidden text-[17px] font-bold xs:inline"
          >Downtify</span
        >
      </a>

      <button
        type="button"
        class="group ml-auto flex h-10 min-w-0 flex-1 items-center gap-2.5 rounded-control border border-line-2 bg-surface px-3 text-left text-sm text-faint transition-colors hover:border-line-3 sm:max-w-[420px] lg:ml-0 lg:h-11 lg:max-w-[520px]"
        aria-label="Search the docs"
        @click="search.show()"
      >
        <Icon name="search" :size="17" class="text-muted" />
        <span class="truncate">Search the docs</span>
        <kbd
          class="ml-auto hidden rounded-md border border-line-3 px-1.5 py-0.5 font-sans text-[11px] text-muted sm:inline"
          >{{ modKey }} K</kbd
        >
      </button>

      <div class="ml-auto hidden items-center gap-2 sm:flex">
        <ThemeSwitch />
        <SocialLinks />
      </div>
    </div>
  </header>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { withBase } from 'vitepress'
import Icon from './Icon.vue'
import Logo from './Logo.vue'
import SocialLinks from './SocialLinks.vue'
import ThemeSwitch from './ThemeSwitch.vue'
import { useSearch } from '../composables/search'

defineProps({ navOpen: { type: Boolean, default: false } })
defineEmits(['open-nav'])

const search = useSearch()
const modKey = ref('Ctrl')
onMounted(() => {
  if (/Mac|iPhone|iPad/.test(navigator.platform)) modKey.value = '⌘'
})
</script>
