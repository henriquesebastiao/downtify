<template>
  <!-- A selectable list's number cell (a link's tracks, an artist's top
       songs): the number, turning into play on hover when the song plays -
       from the library once downloaded, else streamed in full from
       YouTube. On a phone, where the number isn't shown, just the play
       button. -->
  <span
    class="flex w-6 shrink-0 items-center justify-center text-[13px] text-faint"
    :class="playable ? '' : 'max-sm:hidden'"
  >
    <EqBars v-if="isCurrent" :size="12" :playing="player.isPlaying.value" />
    <AppIcon
      v-else-if="loading"
      name="refresh"
      :size="14"
      class="animate-spin text-fg"
    />
    <template v-else>
      <span
        class="tabular max-sm:hidden"
        :class="playable ? 'group-hover:hidden' : ''"
        >{{ index + 1 }}</span
      >
      <button
        v-if="playable"
        type="button"
        class="text-fg sm:hidden sm:group-hover:block"
        :aria-label="playLabel"
        @click.stop="toggle"
      >
        <AppIcon name="play" :size="14" />
      </button>
    </template>
  </span>
</template>

<script setup>
import AppIcon from '../ui/AppIcon.vue'
import EqBars from '../ui/EqBars.vue'
import { usePlayer } from '/src/model/player'
import { useSongPlay } from '/src/model/songPlay'

const props = defineProps({
  song: { type: Object, required: true },
  index: { type: Number, required: true },
  // The list's downloaded songs, as library tracks, to queue after this one.
  queue: { type: Array, default: () => [] },
  // The player's "playing from".
  context: { type: Object, default: null },
  // The whole song list, for a mixed queue (downloaded rows from the
  // library, the rest streamed) the player works through to the end.
  songs: { type: Array, default: null },
})

const player = usePlayer()
const { isCurrent, loading, playable, playLabel, toggle } = useSongPlay(props)
</script>
