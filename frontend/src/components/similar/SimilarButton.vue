<template>
  <button
    v-if="artist && title"
    type="button"
    class="flex size-8 shrink-0 items-center justify-center rounded-control text-faint transition-colors hover:bg-surface-2 hover:text-fg lg:opacity-0 lg:group-hover:opacity-100"
    :title="t('similar.findSimilar')"
    :aria-label="t('similar.findSimilar')"
    @click.stop="go"
  >
    <AppIcon name="wand" :size="16" />
  </button>
</template>

<script setup>
// "What sounds like this?" on any track row, next to its download
// button (phones included): opens the Similar page already searching
// for this artist and title (via ?artist=&track=). Hidden when there is
// nothing to search for.
import { useRouter } from 'vue-router'
import AppIcon from '../ui/AppIcon.vue'
import { useI18n } from '/src/i18n'

const props = defineProps({
  artist: { type: String, default: '' },
  title: { type: String, default: '' },
})

const { t } = useI18n()
const router = useRouter()

function go() {
  const artist = String(props.artist || '').trim()
  const title = String(props.title || '').trim()
  if (!artist || !title) return
  router.push({ name: 'Similar', query: { artist, track: title } })
}
</script>
