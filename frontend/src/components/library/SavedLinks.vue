<template>
  <section v-if="items.length" class="flex flex-col gap-4">
    <div class="flex items-center gap-2">
      <h2 class="text-display text-lg font-bold">
        {{ t('savedLinks.title') }}
      </h2>
      <span class="tabular text-[13px] text-muted">{{ items.length }}</span>
    </div>
    <p class="-mt-2 text-[13px] text-muted">{{ t('savedLinks.hint') }}</p>

    <div
      class="grid grid-cols-2 gap-x-5 gap-y-7 sm:grid-cols-3 md:grid-cols-4 xl:grid-cols-6"
    >
      <MediaTile
        v-for="link in shown"
        :key="link.url"
        :to="{ name: 'Link', query: { url: link.url } }"
        :title="link.name || t('link.untitled')"
        :subtitle="savedLinkSubtitle(link, t)"
        :cover="link.cover"
        :name="link.name"
        :icon="link.kind === 'album' ? 'disc' : 'playlist'"
        :playable="false"
      >
        <template #overlay>
          <UiMenu :items="menuFor(link)" :label="t('common.more')">
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
      v-if="items.length > shown.length"
      variant="ghost"
      class="self-center"
      @click="limit += PAGE"
    >
      {{ t('sharing.showMore', { count: items.length - shown.length }) }}
    </UiButton>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import AppIcon from '../ui/AppIcon.vue'
import UiButton from '../ui/UiButton.vue'
import UiMenu from '../ui/UiMenu.vue'
import MediaTile from './MediaTile.vue'
import { filterItems } from '/src/lib/library'
import { savedLinkSubtitle } from '/src/lib/savedLinks'
import { useSavedLinks } from '/src/model/savedLinks'
import { useUi } from '/src/model/ui'
import { useI18n } from '/src/i18n'

// Playlist and album links saved from their link page (issue #731), a
// section of the Library's playlists tab. Each opens the live link page;
// nothing here is downloaded. Hidden while there are none.
const props = defineProps({
  // The playlists tab's filter, matched against the names.
  filter: { type: String, default: '' },
})

const PAGE = 36
const { t } = useI18n()
const ui = useUi()
const savedLinks = useSavedLinks()
const limit = ref(PAGE)

onMounted(savedLinks.load)

const items = computed(() =>
  filterItems(savedLinks.links.value, props.filter, ['name'])
)
const shown = computed(() => items.value.slice(0, limit.value))

function menuFor(link) {
  return [
    {
      label: t('savedLinks.remove'),
      icon: 'trash',
      danger: true,
      action: () => remove(link),
    },
  ]
}

async function remove(link) {
  const name = link.name || t('link.untitled')
  try {
    await savedLinks.remove(link.url)
  } catch (err) {
    ui.toast(err?.response?.data?.detail || t('toast.actionFailed'), {
      kind: 'error',
    })
    return
  }
  ui.toast(t('savedLinks.removed', { name }), {
    action: {
      label: t('common.undo'),
      run: () =>
        savedLinks
          .save(link)
          .catch(() => ui.toast(t('toast.actionFailed'), { kind: 'error' })),
    },
  })
}
</script>
