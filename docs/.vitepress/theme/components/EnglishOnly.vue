<template>
  <div class="info custom-block" role="note">
    <p class="custom-block-title">{{ ui.englishOnly }}</p>
  </div>
</template>

<script setup>
import { useUi } from '../composables/ui'

// Shown on a page that has no translation yet: its Markdown file just
// includes the English page (see "Translating the docs" in Contributing).
const { ui } = useUi()
</script>
