<template>
  <UiIconButton
    :icon="liked ? 'heart' : 'heart-outline'"
    :label="liked ? t('likes.unlike') : t('likes.like')"
    :size="size"
    :active="liked"
    toggle
    :disabled="!file"
    :class="popping ? 'like-pop' : ''"
    @click.stop="onClick"
  />
</template>

<script setup>
import { computed, ref } from 'vue'
import UiIconButton from '../ui/UiIconButton.vue'
import { useLikes } from '/src/model/likes'
import { useI18n } from '/src/i18n'

const props = defineProps({
  // The track's library path, as `GET /tracks` reports it.
  file: { type: String, default: '' },
  size: { type: String, default: 'sm' },
})

const { t } = useI18n()
const likes = useLikes()
const liked = computed(() => likes.isLiked(props.file))
const popping = ref(false)

function onClick() {
  // Only a tap pops the heart: a list full of songs that were already
  // liked must not all animate when it first appears.
  if (!liked.value) {
    popping.value = true
    setTimeout(() => (popping.value = false), 300)
  }
  likes.toggle(props.file)
}
</script>

<style scoped>
/* Not for people who asked for less motion. */
@media (prefers-reduced-motion: no-preference) {
  .like-pop {
    animation: like-pop var(--dur-slow) var(--ease-out-soft);
  }
}

@keyframes like-pop {
  0% {
    transform: scale(0.8);
  }
  55% {
    transform: scale(1.12);
  }
  100% {
    transform: scale(1);
  }
}
</style>
