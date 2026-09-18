<template>
  <div
    class="relative isolate shrink-0 overflow-hidden"
    :class="[round ? 'rounded-full' : rounded, shadow ? 'shadow-cover' : '']"
    :style="{ backgroundColor: placeholder }"
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
      @error="failed = true"
    />
    <div
      v-if="showFallback"
      class="absolute inset-0 flex items-center justify-center"
      :class="round ? '' : 'items-end justify-start p-[8%]'"
    >
      <AppIcon
        v-if="!letters"
        :name="icon"
        :size="iconSize"
        class="text-white/35"
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
})

const failed = ref(false)
const ready = ref(false)
watch(
  () => props.src,
  () => {
    failed.value = false
    ready.value = false
  }
)

// A real cover always wins: a playlist with its own artwork shows it
// instead of a grid of the tracks it happens to contain.
const mosaic = computed(() => (props.src ? [] : props.covers.filter(Boolean)))
const imageSrc = computed(() => props.src || mosaic.value[0] || '')
const letters = computed(() => initials(props.name))
const showFallback = computed(
  () => mosaic.value.length < 4 && (!imageSrc.value || failed.value)
)
// Placeholder tint derived from the name, so an album without art keeps
// the same colour everywhere.
const placeholder = computed(
  () => `oklch(0.42 0.07 ${hueFor(props.name || props.alt)})`
)
</script>
