<template>
  <div
    class="mx-auto grid w-full max-w-[1200px] gap-10 px-4 pt-8 pb-16 sm:px-6 md:pt-10 lg:px-10 xl:grid-cols-[minmax(0,1fr)_220px]"
  >
    <article class="min-w-0">
      <p class="eyebrow mb-3 flex items-center gap-1.5">
        <span>{{ section }}</span>
        <template v-if="current && current.group">
          <Icon name="chevron-right" :size="12" />
          <span class="text-muted">{{ current.title }}</span>
        </template>
      </p>
      <div :key="route.path" class="page-in">
        <Content class="doc" />
      </div>
      <PageFooter />
    </article>
    <aside class="hidden xl:block" aria-label="On this page">
      <div
        class="sticky top-[96px] max-h-[calc(100dvh-120px)] overflow-y-auto pb-4"
      >
        <Toc />
      </div>
    </aside>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vitepress'
import Icon from './Icon.vue'
import PageFooter from './PageFooter.vue'
import Toc from './Toc.vue'
import { useNav } from '../composables/nav'

const route = useRoute()
const { current } = useNav()
const section = computed(() => current.value?.group || 'Documentation')
</script>
