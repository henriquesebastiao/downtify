<template>
  <aside
    aria-label="Sidebar"
    class="sticky top-0 h-dvh w-[272px] shrink-0 flex-col border-r border-line bg-side"
  >
    <a
      :href="withBase('/')"
      class="flex h-16 shrink-0 items-center gap-2.5 px-6"
      title="Downtify docs home"
    >
      <Logo :size="28" />
      <span class="text-display text-[19px] font-bold">Downtify</span>
      <span
        class="rounded-full border border-line-3 px-2 py-0.5 text-[11px] font-semibold text-muted"
        >Docs</span
      >
    </a>
    <div class="min-h-0 flex-1 overflow-y-auto px-3 pt-3 pb-8">
      <NavList />
    </div>
  </aside>
</template>

<script setup>
import { withBase } from 'vitepress'
import Logo from './Logo.vue'
import NavList from './NavList.vue'
</script>
