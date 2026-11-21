<template>
  <div
    class="not-doc my-6 columns-1 gap-3 sm:columns-2 lg:columns-3 xl:columns-4"
  >
    <section
      v-for="group in groups"
      :key="group.title"
      class="mb-3 break-inside-avoid rounded-panel border border-line-2 bg-surface p-4"
    >
      <h3
        class="text-display mt-0 mb-2 flex items-center gap-2.5 px-1 text-[15px] font-semibold text-fg"
      >
        <span
          class="flex size-8 shrink-0 items-center justify-center rounded-[10px] bg-accent/12 text-accent"
        >
          <Icon :name="group.icon" :size="17" />
        </span>
        {{ group.title }}
      </h3>
      <ul class="not-doc flex flex-col">
        <li v-for="item in group.items" :key="item.link">
          <a
            :href="withBase(item.link)"
            class="group flex items-center gap-2.5 rounded-[9px] px-1.5 py-1.5 text-[13.5px] leading-snug text-muted transition-colors hover:bg-surface-2 hover:text-fg"
          >
            <Icon
              :name="item.icon"
              :size="15"
              class="text-faint transition-colors group-hover:text-accent"
            />
            <span>{{ item.title }}</span>
          </a>
        </li>
      </ul>
    </section>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { withBase } from 'vitepress'
import Icon from './Icon.vue'
import { useNav } from '../composables/nav'

// Every feature, grouped as in the sidebar and in the page's language: the
// sidebar's feature areas are the groups that carry an icon (nav.mjs).
const { sidebar } = useNav()
const groups = computed(() =>
  sidebar.value.filter((entry) => entry.items && entry.icon)
)
</script>
