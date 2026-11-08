<template>
  <section v-if="items.length" class="flex flex-col gap-4">
    <component
      :is="collapsible ? 'button' : 'div'"
      :type="collapsible ? 'button' : undefined"
      :aria-expanded="collapsible ? expanded : undefined"
      class="flex items-center gap-2 text-left"
      @click="collapsible && (open = !open)"
    >
      <AppIcon
        v-if="collapsible"
        name="chevron-right"
        :size="18"
        class="text-faint transition-transform"
        :class="expanded ? 'rotate-90' : ''"
      />
      <h2 class="text-display text-lg font-bold">{{ title }}</h2>
      <span class="tabular text-[13px] text-muted">{{ items.length }}</span>
    </component>
    <p v-if="hint && expanded" class="-mt-2 text-[13px] text-muted">
      {{ hint }}
    </p>

    <div
      v-if="expanded"
      class="grid grid-cols-2 gap-x-5 gap-y-7 sm:grid-cols-3 md:grid-cols-4 xl:grid-cols-6"
    >
      <MediaTile
        v-for="item in shown"
        :key="item.key"
        :to="{ name: 'Playlist', query: { name: item.name } }"
        :title="item.title"
        :subtitle="subtitleFor(item)"
        :cover="item.cover"
        :covers="item.covers"
        :name="item.title"
        icon="playlist"
        :playable="itemTrackCount(item) > 0"
        @play="$emit('play', item)"
      >
        <template #badge>
          <span
            v-if="item.isNew"
            class="absolute top-2.5 right-2.5 rounded-full bg-accent px-2 py-0.5 text-[11px] font-bold text-on-accent"
          >
            {{ t('sharing.new') }}
          </span>
          <span
            v-else-if="item.followed"
            class="absolute top-2.5 right-2.5 flex items-center gap-1 rounded-full bg-black/60 px-2 py-0.5 text-[11px] font-semibold text-white backdrop-blur"
          >
            <AppIcon name="heart" :size="11" />{{ t('sharing.following') }}
          </span>
        </template>
        <template #overlay>
          <UiMenu :items="menuFor(item)" :label="t('common.more')">
            <template #trigger>
              <button
                type="button"
                class="flex size-9 items-center justify-center rounded-full bg-black/55 text-white backdrop-blur transition-colors hover:bg-black/75"
                :aria-label="t('common.more')"
              >
                <AppIcon name="more" :size="18" />
              </button>
            </template>
          </UiMenu>
        </template>
      </MediaTile>
    </div>
    <UiButton
      v-if="expanded && items.length > shown.length"
      variant="ghost"
      class="self-center"
      @click="limit += PAGE"
    >
      {{ t('sharing.showMore', { count: items.length - shown.length }) }}
    </UiButton>
  </section>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useLocalStorage } from '@vueuse/core'
import AppIcon from '../ui/AppIcon.vue'
import UiButton from '../ui/UiButton.vue'
import UiMenu from '../ui/UiMenu.vue'
import MediaTile from './MediaTile.vue'
import { itemTrackCount } from '/src/lib/library'
import { usePlaylistActions } from '/src/model/playlistActions'
import { useI18n } from '/src/i18n'

// Other people's playlists, a section of the Library's playlists tab:
// "Shared with me" is always open, "Public playlists" folds away.
const props = defineProps({
  title: { type: String, required: true },
  hint: { type: String, default: '' },
  items: { type: Array, required: true },
  collapsible: { type: Boolean, default: false },
  // Remembered per section (collapsible ones only).
  storageKey: { type: String, default: 'downtify-shared-playlists-open' },
  // A search in progress opens a folded section.
  searching: { type: Boolean, default: false },
})
defineEmits(['play'])

const PAGE = 36
const { t } = useI18n()
const actions = usePlaylistActions()
const open = useLocalStorage(props.storageKey, false)
const limit = ref(PAGE)

const expanded = computed(
  () => !props.collapsible || open.value || props.searching
)
const shown = computed(() => props.items.slice(0, limit.value))

function subtitleFor(item) {
  return [item.owner, t('common.tracks', { count: itemTrackCount(item) })]
    .filter(Boolean)
    .join(' · ')
}

function menuFor(item) {
  return actions.menuFor(item)
}
</script>
