<template>
  <div class="flex flex-col gap-8">
    <section
      v-for="group in groups"
      :key="group.id"
      class="flex flex-col gap-3"
      :aria-label="group.title"
    >
      <h2 class="eyebrow">{{ group.title }}</h2>
      <ul class="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
        <li v-for="link in group.links" :key="link.key">
          <a
            :href="link.url"
            target="_blank"
            rel="noopener noreferrer"
            class="group flex items-center gap-3 rounded-[12px] border border-line-2 bg-surface px-4 py-3 transition-colors hover:bg-surface-2"
          >
            <span
              class="grid size-10 shrink-0 place-items-center rounded-full bg-surface-2 text-fg"
            >
              <AppIcon :name="link.icon" :size="18" />
            </span>
            <span class="min-w-0 flex-1">
              <span class="block truncate text-sm font-semibold">{{
                link.label
              }}</span>
              <span class="block truncate text-[12px] text-muted">{{
                linkHost(link.url)
              }}</span>
            </span>
            <AppIcon
              name="arrow-up-right"
              :size="16"
              class="shrink-0 text-faint transition-colors group-hover:text-fg"
            />
          </a>
        </li>
      </ul>
    </section>
  </div>
</template>

<script setup>
// The artist's Links tab: every profile link, as cards - the streaming
// platforms they were found on, then the social networks they filled in.
// Each card is one external link (see lib/artistLinks.js for what a link is).
import { computed } from 'vue'
import AppIcon from '../ui/AppIcon.vue'
import { linkHost } from '/src/lib/artistLinks'
import { useI18n } from '/src/i18n'

const props = defineProps({
  // `artistPlatformLinks(...)` and `artistSocialLinks(...)`.
  platforms: { type: Array, default: () => [] },
  social: { type: Array, default: () => [] },
})

const { t } = useI18n()

const groups = computed(() =>
  [
    {
      id: 'platforms',
      title: t('artist.linksPlatforms'),
      links: props.platforms,
    },
    { id: 'social', title: t('artist.linksSocial'), links: props.social },
  ].filter((group) => group.links.length)
)
</script>
