<template>
  <template v-for="(item, index) in items" :key="`${index}:${item.name}`">
    <template v-if="index">, </template>
    <RouterLink
      v-if="item.to"
      :to="item.to"
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
// Library page. With `onlyKnown`, only the artists that have one get that
// link (see groupArtists in lib/library.js: a guest credit alone makes no
// page, and a song may not be in the Library yet); with `searchMissing`
// the rest link to a search for them, else they stay plain text.
import { computed, onMounted } from 'vue'
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
  // With `onlyKnown`: the other artists link to a search for them.
  searchMissing: { type: Boolean, default: false },
  linkClass: { type: String, default: 'hover:text-fg hover:underline' },
})

const emit = defineEmits(['navigate'])
const library = useLibrary()

// Who's in the Library: the artists index, fetched once (shared by every
// row) - outside the Library page it may not be loaded yet.
onMounted(() => {
  if (props.onlyKnown) library.ensureArtists().catch(() => {})
})

const items = computed(() =>
  artistLinkItems(props.artists, {
    fallback: props.fallback,
    plain: props.plain,
    hasPage: props.onlyKnown ? library.hasArtistPage : null,
    searchMissing: props.searchMissing,
  })
)
</script>
