<template>
  <div class="not-doc my-8">
    <div
      role="tablist"
      :aria-label="ui.screenshots"
      class="mx-auto flex w-fit max-w-full flex-wrap justify-center gap-1 rounded-[14px] border border-line-2 bg-surface p-1.5"
      @keydown="onKey"
    >
      <button
        v-for="(item, i) in items"
        :id="`${id}-tab-${i}`"
        :key="item.shot"
        ref="tabs"
        type="button"
        role="tab"
        :aria-selected="i === active"
        :aria-controls="`${id}-panel-${i}`"
        :tabindex="i === active ? 0 : -1"
        class="h-9 rounded-[10px] px-3.5 text-[13px] transition-colors"
        :class="
          i === active
            ? 'bg-accent font-semibold text-on-accent'
            : 'font-medium text-muted hover:bg-surface-2 hover:text-fg'
        "
        @click="active = i"
      >
        {{ item.label }}
      </button>
    </div>
    <div
      v-for="(item, i) in items"
      v-show="i === active"
      :id="`${id}-panel-${i}`"
      :key="item.shot"
      role="tabpanel"
      :aria-labelledby="`${id}-tab-${i}`"
      class="mt-4"
    >
      <figure class="flex flex-col items-center gap-2">
        <img
          :src="SHOTS[item.shot].dark"
          :alt="item.alt"
          :width="SHOTS[item.shot].size[0]"
          :height="SHOTS[item.shot].size[1]"
          :class="SHOTS[item.shot].light ? 'theme-dark' : ''"
          class="h-auto w-full"
          :style="{ maxWidth: SHOTS[item.shot].width }"
          loading="lazy"
          decoding="async"
        />
        <img
          v-if="SHOTS[item.shot].light"
          :src="SHOTS[item.shot].light"
          :alt="item.alt"
          :width="SHOTS[item.shot].size[0]"
          :height="SHOTS[item.shot].size[1]"
          class="theme-light h-auto w-full"
          :style="{ maxWidth: SHOTS[item.shot].width }"
          loading="lazy"
          decoding="async"
        />
        <figcaption
          class="max-w-[620px] text-center text-[14.5px] leading-relaxed text-muted"
        >
          {{ item.caption }}
        </figcaption>
      </figure>
    </div>
  </div>
</template>

<script setup>
import { nextTick, ref, useId } from 'vue'
import { useUi } from '../composables/ui'
// The README's screenshots (assets/readme/ at the repository root), so the
// two always show the same build. Light variants follow the docs' theme.
import homeDark from '../../../../assets/readme/home-dark.png'
import homeLight from '../../../../assets/readme/home-light.png'
import karaoke from '../../../../assets/readme/karaoke.png'
import libraryDark from '../../../../assets/readme/library-dark.png'
import libraryLight from '../../../../assets/readme/library-light.png'
import nowPlaying from '../../../../assets/readme/now-playing.png'
import phones from '../../../../assets/readme/phones.png'
import playlistDark from '../../../../assets/readme/playlist-dark.png'
import playlistLight from '../../../../assets/readme/playlist-light.png'

// `size`: the image's own pixels, so the page keeps its place while the
// image loads.
const WINDOW = [1748, 1181]
const SHOTS = {
  'now-playing': { dark: nowPlaying, size: WINDOW },
  karaoke: { dark: karaoke, size: WINDOW },
  home: { dark: homeDark, light: homeLight, size: WINDOW },
  library: { dark: libraryDark, light: libraryLight, size: WINDOW },
  playlist: { dark: playlistDark, light: playlistLight, size: WINDOW },
  phones: { dark: phones, size: [1662, 1198], width: '860px' },
}

// items: [{ shot, label, caption, alt }], `shot` a key of SHOTS.
const props = defineProps({ items: { type: Array, required: true } })

const { ui } = useUi()
const id = useId()
const active = ref(0)
const tabs = ref([])

function onKey(event) {
  const last = props.items.length - 1
  const moves = {
    ArrowRight: active.value === last ? 0 : active.value + 1,
    ArrowLeft: active.value === 0 ? last : active.value - 1,
    Home: 0,
    End: last,
  }
  if (!(event.key in moves)) return
  event.preventDefault()
  active.value = moves[event.key]
  nextTick(() => tabs.value[active.value]?.focus())
}
</script>
