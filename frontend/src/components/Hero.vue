<template>
  <section
    class="relative flex min-h-[calc(100dvh-4rem)] items-center justify-center px-6 pt-24 pb-16 overflow-hidden"
  >
    <div aria-hidden="true" class="pointer-events-none absolute inset-0 -z-10">
      <div
        class="absolute left-1/2 top-1/4 -translate-x-1/2 h-[420px] w-[420px] rounded-full bg-primary/25 blur-[120px]"
      ></div>
      <div
        class="absolute right-10 bottom-12 h-64 w-64 rounded-full bg-primary/10 blur-3xl"
      ></div>
    </div>

    <div class="relative w-full max-w-2xl text-center animate-slide-up">
      <div class="mx-auto mb-6 inline-flex">
        <div
          class="relative inline-flex h-24 w-24 items-center justify-center rounded-3xl surface-strong shadow-glow"
        >
          <img src="../assets/downtify.svg" class="h-14 w-14" />
        </div>
      </div>

      <h1 class="text-balance text-5xl sm:text-6xl font-bold tracking-tight">
        Down<span class="text-primary">tify</span>
      </h1>
      <div class="mt-3 flex items-center justify-center gap-2">
        <span class="badge-soft">v{{ version }}</span>
        <span class="badge-neutral-soft">{{ t('hero.noAccount') }}</span>
      </div>
      <p
        class="mx-auto mt-5 max-w-md text-balance text-base sm:text-lg text-base-content/70"
      >
        {{ t('hero.tagline') }}
      </p>

      <div class="mt-10">
        <SearchInput class="w-full" />
        <div
          class="mt-4 flex flex-wrap items-center justify-center gap-2 text-xs text-base-content/60"
        >
          <span class="pill bg-white/5 border border-white/10"
            ><span class="h-1.5 w-1.5 rounded-full bg-primary"></span>
            {{ t('hero.songs') }}</span
          >
          <span class="pill bg-white/5 border border-white/10"
            ><span class="h-1.5 w-1.5 rounded-full bg-primary"></span>
            {{ t('hero.albums') }}</span
          >
          <span class="pill bg-white/5 border border-white/10"
            ><span class="h-1.5 w-1.5 rounded-full bg-primary"></span>
            {{ t('hero.playlists') }}</span
          >
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import SearchInput from './SearchInput.vue'
import { useI18n } from '../i18n'

const { t } = useI18n()
const version = ref(localStorage.getItem('version') || '2.4.2')
onMounted(() => {
  const v = localStorage.getItem('version')
  if (v) version.value = v
})
</script>
