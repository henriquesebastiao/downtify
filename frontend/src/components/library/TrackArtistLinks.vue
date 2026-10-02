<template>
  <template v-for="(item, index) in items" :key="`${index}:${item.name}`">
    <template v-if="index">, </template>
    <RouterLink
      v-if="item.linked"
      :to="{ name: 'Artist', query: { name: item.name } }"
      :class="linkClass"
      @click.stop="emit('navigate')"
      @dblclick.stop
      >{{ item.name }}</RouterLink
    >
    <template v-else>{{ item.name }}</template>
  </template>
</template>

<script setup>
// A track's credited artists, comma-separated, each one a link to their own
// Library page - every credited artist has one (see groupArtists in
// lib/library.js). For a song not in the Library yet (`onlyKnown`), only
// the artists the Library already has are links; the rest stay plain text.
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { useLibrary } from '/src/model/library'
import { artistLinkItems } from '/src/lib/library'

const props = defineProps({
  artists: { type: Array, default: () => [] },
  // Shown when there are no artists to list.
  fallback: { type: String, default: '' },
  // No links at all (e.g. a list that turns artist links off).
  plain: { type: Boolean, default: false },
  // Link only the artists that already have a Library page.
  onlyKnown: { type: Boolean, default: false },
  linkClass: { type: String, default: 'hover:text-fg hover:underline' },
})

const emit = defineEmits(['navigate'])
const library = useLibrary()

const items = computed(() =>
  artistLinkItems(props.artists, {
    fallback: props.fallback,
    plain: props.plain,
    hasPage: props.onlyKnown ? (name) => !!library.findArtist(name) : null,
  })
)
</script>
