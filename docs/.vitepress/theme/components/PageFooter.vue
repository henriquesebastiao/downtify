<template>
  <footer class="mt-14 flex flex-col gap-6">
    <div
      class="flex flex-wrap items-center justify-between gap-x-6 gap-y-2 text-[13px] text-muted"
    >
      <a
        :href="editUrl"
        target="_blank"
        rel="noopener"
        class="inline-flex items-center gap-1.5 font-medium hover:text-accent"
      >
        <Icon name="pencil" :size="15" />
        Edit this page on GitHub
      </a>
      <p v-if="updated" class="inline-flex items-center gap-1.5">
        <Icon name="clock" :size="15" />
        Last updated
        <time :datetime="isoDate">{{ updated }}</time>
      </p>
    </div>

    <nav
      v-if="nav.prev.value || nav.next.value"
      aria-label="Previous and next pages"
      class="grid gap-3 sm:grid-cols-2"
    >
      <a
        v-if="nav.prev.value"
        :href="withBase(nav.prev.value.link)"
        class="group flex flex-col gap-1 rounded-panel border border-line-2 bg-surface px-5 py-4 transition-colors hover:border-accent/60"
      >
        <span class="eyebrow inline-flex items-center gap-1.5">
          <Icon name="arrow-left" :size="13" /> Previous
        </span>
        <span class="font-semibold text-fg group-hover:text-accent">{{
          nav.prev.value.title
        }}</span>
      </a>
      <a
        v-if="nav.next.value"
        :href="withBase(nav.next.value.link)"
        class="group flex flex-col items-end gap-1 rounded-panel border border-line-2 bg-surface px-5 py-4 text-right transition-colors hover:border-accent/60 sm:col-start-2"
      >
        <span class="eyebrow inline-flex items-center gap-1.5">
          Next <Icon name="arrow-right" :size="13" />
        </span>
        <span class="font-semibold text-fg group-hover:text-accent">{{
          nav.next.value.title
        }}</span>
      </a>
    </nav>
  </footer>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useData, withBase } from 'vitepress'
import Icon from './Icon.vue'
import { useNav } from '../composables/nav'

const { page, theme } = useData()
const nav = useNav()

const editUrl = computed(() => theme.value.editBase + page.value.filePath)
const isoDate = computed(() =>
  page.value.lastUpdated ? new Date(page.value.lastUpdated).toISOString() : ''
)

// Formatted on the client only: the reader's locale and time zone.
const updated = ref('')
function format() {
  updated.value = page.value.lastUpdated
    ? new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(
        new Date(page.value.lastUpdated)
      )
    : ''
}
onMounted(format)
watch(() => page.value.lastUpdated, format)
</script>
