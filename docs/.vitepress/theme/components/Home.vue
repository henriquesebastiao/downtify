<template>
  <div class="page-in">
    <section class="relative overflow-hidden border-b border-line">
      <div
        aria-hidden="true"
        class="pointer-events-none absolute inset-0 bg-[radial-gradient(55%_60%_at_50%_0%,color-mix(in_srgb,var(--c-accent)_18%,transparent),transparent_72%)]"
      />
      <div
        class="relative mx-auto flex max-w-[1100px] flex-col items-center gap-5 px-4 pt-10 pb-14 text-center sm:px-6 md:pt-14 md:pb-20 lg:px-10"
      >
        <!-- The product, its category and the promise: what the page is
             about, in one heading, for readers and search engines alike. -->
        <h1 class="flex flex-col items-center gap-5">
          <span
            class="eyebrow rounded-full border border-line-3 bg-surface/60 px-3.5 py-1.5"
            >Downtify · {{ hero.eyebrow }}</span
          >
          <span
            class="text-display max-w-[900px] text-[42px] leading-[1.02] font-bold tracking-[-0.03em] sm:text-[58px] md:text-[68px]"
          >
            <template v-for="(line, i) in hero.headline" :key="i">
              <br v-if="i" />
              <span :class="i ? 'text-accent' : ''">{{ line }}</span>
            </template>
          </span>
        </h1>
        <p
          class="max-w-[680px] text-[17px] leading-relaxed text-fg-3 sm:text-lg"
        >
          {{ hero.lead }}
        </p>
        <p class="text-[15px] font-semibold text-fg">{{ hero.note }}</p>
        <HomeActions :actions="hero.actions" class="justify-center" />
        <p class="flex flex-wrap justify-center gap-2">
          <a
            v-for="shield in hero.shields"
            :key="shield.src"
            :href="shield.link"
            target="_blank"
            rel="noopener"
          >
            <img :src="shield.src" :alt="shield.alt" height="20" class="h-5" />
          </a>
        </p>
        <HomeVideo
          v-if="frontmatter.video"
          :video="frontmatter.video"
          class="mt-5 md:mt-8"
        />
      </div>
    </section>
    <div class="mx-auto max-w-[1100px] px-4 pt-4 pb-20 sm:px-6 lg:px-10">
      <Content class="doc doc-home" />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useData } from 'vitepress'
import HomeActions from './HomeActions.vue'
import HomeVideo from './HomeVideo.vue'

const { frontmatter } = useData()
const hero = computed(() => frontmatter.value.hero)
</script>
