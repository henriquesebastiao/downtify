<template>
  <div class="flex items-center gap-1">
    <a
      v-for="link in theme.social"
      :key="link.link"
      :href="link.link"
      target="_blank"
      rel="noopener"
      :title="link.label"
      class="flex size-10 items-center justify-center rounded-control text-muted transition-colors hover:bg-surface-2 hover:text-fg"
    >
      <Icon :name="link.icon" :size="18" />
      <span class="sr-only">{{ link.label }}</span>
    </a>
  </div>
</template>

<script setup>
import { useData } from 'vitepress'
import Icon from './Icon.vue'

const { theme } = useData()
</script>
