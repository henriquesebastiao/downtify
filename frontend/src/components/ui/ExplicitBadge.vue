<template>
  <span
    role="img"
    class="shrink-0 rounded-[3px] px-1 text-[9px] leading-[14px] font-bold"
    :class="toneClass"
    :title="t('search.explicit')"
    :aria-label="t('search.explicit')"
    >E</span
  >
</template>

<script setup>
// The "E" next to the title of a song with explicit lyrics, like
// Spotify's. `tone` follows what the row is drawn on: the page (default),
// an accent-coloured row, or the player's dark, artwork-tinted panels.
import { computed } from 'vue'
import { useI18n } from '/src/i18n'

const props = defineProps({
  tone: { type: String, default: 'default' },
})

const { t } = useI18n()

const toneClass = computed(
  () =>
    ({
      default: 'bg-muted text-bg',
      accent: 'bg-on-accent text-accent',
      onDark: 'bg-white/65 text-black',
    })[props.tone] || 'bg-muted text-bg'
)
</script>
