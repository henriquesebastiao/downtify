<template>
  <ul
    class="not-doc my-6 grid gap-3 sm:grid-cols-2"
    :class="items.length % 3 === 0 ? 'xl:grid-cols-3' : ''"
  >
    <li v-for="item in items" :key="item.link">
      <a
        :href="external(item.link) ? item.link : withBase(item.link)"
        :target="external(item.link) ? '_blank' : undefined"
        :rel="external(item.link) ? 'noopener' : undefined"
        class="group flex h-full flex-col gap-3 rounded-panel border border-line-2 bg-surface p-5 transition-[transform,border-color] duration-200 ease-out-soft hover:-translate-y-0.5 hover:border-accent/50"
      >
        <span class="flex items-center justify-between">
          <span
            class="flex size-10 items-center justify-center rounded-[12px] bg-accent text-on-accent"
          >
            <Icon :name="item.icon" :size="20" :stroke-width="2" />
          </span>
          <Icon
            :name="external(item.link) ? 'arrow-up-right' : 'arrow-right'"
            :size="16"
            class="text-faint transition-colors group-hover:text-accent"
          />
        </span>
        <span class="text-display text-[16px] font-semibold text-fg">{{
          item.title
        }}</span>
        <span class="text-[14px] leading-relaxed text-muted">{{
          item.text
        }}</span>
      </a>
    </li>
  </ul>
</template>

<script setup>
import { withBase } from 'vitepress'
import Icon from './Icon.vue'

// items: [{ icon, title, text, link }]
defineProps({ items: { type: Array, required: true } })

const external = (link) => /^https?:/.test(link)
</script>
