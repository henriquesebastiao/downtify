<template>
  <div class="page-in">
    <section class="relative overflow-hidden border-b border-line">
      <div
        aria-hidden="true"
        class="pointer-events-none absolute inset-0 bg-[radial-gradient(60%_80%_at_85%_0%,color-mix(in_srgb,var(--c-accent)_16%,transparent),transparent_70%)]"
      />
      <div
        class="relative mx-auto flex max-w-[1100px] flex-col items-start gap-6 px-4 pt-12 pb-14 sm:px-6 md:pt-20 md:pb-20 lg:px-10"
      >
        <Logo :size="64" />
        <div class="flex flex-col gap-4">
          <p class="eyebrow">{{ hero.eyebrow }}</p>
          <h1
            class="text-display text-[44px] leading-[1.02] font-bold sm:text-[64px] md:text-[76px]"
          >
            {{ frontmatter.title }}
          </h1>
          <p
            class="max-w-[640px] text-[17px] leading-relaxed text-fg-3 sm:text-lg"
          >
            <template v-for="(line, i) in hero.lead" :key="i">
              <br v-if="i" class="max-sm:hidden" />{{ line }}{{ ' ' }}
            </template>
          </p>
        </div>
        <HomeActions :actions="hero.actions" />
        <p class="flex flex-wrap gap-2">
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
import Logo from './Logo.vue'

const { frontmatter } = useData()
const hero = computed(() => frontmatter.value.hero)
</script>
