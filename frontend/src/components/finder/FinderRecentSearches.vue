<template>
  <section class="flex min-w-0 flex-col gap-2">
    <div class="flex items-center justify-between gap-3">
      <h2 class="eyebrow">{{ t('search.recent') }}</h2>
      <button
        type="button"
        class="text-[13px] font-semibold text-muted hover:text-fg"
        @click="emit('clear')"
      >
        {{ t('common.clear') }}
      </button>
    </div>
    <div class="flex flex-wrap gap-2">
      <RouterLink
        v-for="term in terms"
        :key="term"
        :to="{ name: 'Discover', query: { q: term } }"
        class="flex h-8 max-w-full items-center gap-2 rounded-full bg-surface-2 px-3 text-[13px] text-fg-3 hover:bg-raised"
        :class="term === active ? 'ring-1 ring-accent' : ''"
        :aria-current="term === active ? 'true' : undefined"
      >
        <AppIcon name="clock" :size="13" class="shrink-0 text-faint" />
        <span class="truncate">{{ term }}</span>
      </RouterLink>
    </div>
  </section>
</template>

<script setup>
// The Finder's recent searches, as chips that run the search again. The
// list itself is the page's (see model/finder.js useRecentSearches).
import AppIcon from '../ui/AppIcon.vue'
import { useI18n } from '/src/i18n'

defineProps({
  terms: { type: Array, required: true },
  // The search on screen, marked among them.
  active: { type: String, default: '' },
})
const emit = defineEmits(['clear'])

const { t } = useI18n()
</script>
