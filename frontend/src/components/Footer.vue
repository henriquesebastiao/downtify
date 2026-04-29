<template>
  <footer class="mt-auto px-6 py-6 text-center text-sm text-base-content/60">
    <a
      class="font-semibold text-primary hover:underline"
      href="https://github.com/henriquesebastiao/downtify"
      target="_blank"
      rel="noopener"
      >Downtify</a
    >
    <span class="mx-2 opacity-50">·</span>
    <span>{{ t('footer.tagline') }}</span>
  </footer>
</template>

<script setup>
import { useI18n } from '../i18n'
const { t } = useI18n()
</script>
