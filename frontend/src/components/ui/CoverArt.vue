<template>
  <div
    class="relative isolate shrink-0 overflow-hidden"
    :class="[round ? 'rounded-full' : rounded, shadow ? 'shadow-cover' : '']"
    :style="{ background: placeholder }"
  >
    <div
      v-if="mosaic.length >= 4"
      class="grid size-full grid-cols-2 grid-rows-2"
    >
      <img
        v-for="(url, i) in mosaic.slice(0, 4)"
        :key="i"
        :src="url"
        alt=""
        loading="lazy"
        decoding="async"
        class="size-full object-cover"
      />
    </div>
    <img
      v-else-if="imageSrc && !failed"
      :src="imageSrc"
      :alt="alt"
      loading="lazy"
      decoding="async"
      class="size-full object-cover transition-opacity duration-300"
      :class="ready ? 'opacity-100' : 'opacity-0'"
      @load="ready = true"
      @error="onImageError"
    />
    <div
      v-if="showFallback"
      class="absolute inset-0 flex items-center justify-center"
      :class="round || symbol ? '' : 'items-end justify-start p-[8%]'"
    >
      <AppIcon
        v-if="!letters"
        :name="icon"
        :size="iconSize"
        :class="symbol ? 'text-white/90' : 'text-white/35'"
      />
      <span
        v-else
        class="text-display leading-none font-bold text-white/25 select-none"
        :style="{ fontSize: `${letterSize}px` }"
        >{{ letters }}</span
      >
    </div>
    <slot />
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import AppIcon from './AppIcon.vue'
import { hueFor, initials } from '/src/lib/format'

const props = defineProps({
  src: { type: String, default: '' },
  covers: { type: Array, default: () => [] },
  alt: { type: String, default: '' },
  name: { type: String, default: '' },
  icon: { type: String, default: 'music' },
  round: { type: Boolean, default: false },
  rounded: { type: String, default: 'rounded-cover' },
  shadow: { type: Boolean, default: false },
  letterSize: { type: Number, default: 48 },
  iconSize: { type: Number, default: 28 },
  // The icon on a fixed tile, whatever art or name there is — for
  // collections that are recognised by what they are, like liked songs.
  symbol: { type: Boolean, default: false },
  // Optional second image tried once `src` fails to load, before giving up
  // on the initials: for a `src` that may simply not exist (an artist photo
  // from a proxy), with a picture known to. Unset = today's behaviour.
  fallback: { type: String, default: '' },
})

const failed = ref(false)
const ready = ref(false)
const usingFallback = ref(false)
watch(
  () => props.src,
  () => {
    failed.value = false
    ready.value = false
    usingFallback.value = false
  }
)

function onImageError() {
  if (props.fallback && !usingFallback.value) {
    usingFallback.value = true
    ready.value = false
    return
  }
  failed.value = true
}

// A real cover always wins: a playlist with its own artwork shows it
// instead of a grid of the tracks it happens to contain.
const mosaic = computed(() =>
  props.symbol || props.src ? [] : props.covers.filter(Boolean)
)
const imageSrc = computed(() => {
  if (props.symbol) return ''
  if (usingFallback.value) return props.fallback
  return props.src || mosaic.value[0] || ''
})
const letters = computed(() => (props.symbol ? '' : initials(props.name)))
const showFallback = computed(
  () => mosaic.value.length < 4 && (!imageSrc.value || failed.value)
)
// Placeholder tint derived from the name, so an album without art keeps
// the same colour everywhere.
const placeholder = computed(() =>
  props.symbol
    ? 'linear-gradient(135deg, oklch(0.5 0.17 305), oklch(0.62 0.14 245))'
    : `oklch(0.42 0.07 ${hueFor(props.name || props.alt)})`
)
</script>
