<template>
  <ul class="not-doc my-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
    <li v-for="item in items" :key="item.link">
      <a
        :href="withBase(item.link)"
        class="group flex h-full flex-col gap-3 rounded-panel border border-line-2 bg-surface p-5 transition-[transform,border-color] duration-200 ease-out-soft hover:-translate-y-0.5 hover:border-accent/50"
      >
        <span
          class="flex size-10 items-center justify-center rounded-control bg-surface-2 text-fg-3 transition-colors group-hover:bg-accent/12 group-hover:text-accent"
        >
          <Icon :name="item.icon" :size="20" />
        </span>
        <span class="text-display text-[15px] font-semibold text-fg">{{
          item.title
        }}</span>
        <span class="text-[13px] leading-relaxed text-muted">{{
          item.text
        }}</span>
      </a>
    </li>
  </ul>
</template>

<script setup>
import { withBase } from 'vitepress'
import Icon from './Icon.vue'

defineProps({ items: { type: Array, required: true } })
</script>
