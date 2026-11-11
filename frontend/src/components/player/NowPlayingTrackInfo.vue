<template>
  <div class="min-w-0">
    <div class="flex min-w-0 items-center gap-2.5">
      <h2
        class="text-display truncate font-bold"
        :class="compact ? 'text-[15px] leading-tight' : 'now-playing-title'"
      >
        {{ track.title }}
      </h2>
      <ExplicitBadge v-if="track.explicit" tone="onDark" />
    </div>
    <p
      class="truncate text-white/70"
      :class="compact ? 'mt-0.5 text-[13px] leading-tight' : 'mt-1 text-base'"
    >
      <TrackArtistLinks
        v-if="track.artists?.length && !track.isPodcast"
        :artists="track.artists"
        only-known
        search-missing
        link-class="hover:text-white hover:underline"
        @navigate="emit('navigate')"
      />
      <template v-else>{{ track.artist }}</template>
    </p>
  </div>
</template>

<script setup>
import ExplicitBadge from '../ui/ExplicitBadge.vue'
import TrackArtistLinks from '../library/TrackArtistLinks.vue'

defineProps({
  track: { type: Object, required: true },
  // One-line-height sizes, for the Now playing header.
  compact: { type: Boolean, default: false },
})

const emit = defineEmits(['navigate'])
</script>
