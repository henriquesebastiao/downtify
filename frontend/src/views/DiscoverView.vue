<template>
  <div
    class="mx-auto flex max-w-[1680px] flex-col gap-8 px-4 pt-6 pb-10 sm:px-6 md:pt-8 lg:px-10"
  >
    <PageHeader :title="t('discover.title')" :subtitle="t('discover.subtitle')">
      <UiButton variant="ghost" icon="eye" @click="hiddenOpen = true">
        {{
          t('discover.hiddenButton', { count: discover.blocked.value.length })
        }}
      </UiButton>
      <UiButton
        icon="refresh"
        :loading="discover.loading.value"
        :disabled="!canSuggest"
        @click="refresh"
      >
        {{ t('discover.refresh') }}
      </UiButton>
    </PageHeader>

    <div
      v-if="!library.loaded.value || (discover.loading.value && !items.length)"
      class="grid grid-cols-2 gap-x-5 gap-y-7 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 2xl:grid-cols-6"
      aria-busy="true"
    >
      <div v-for="n in 12" :key="n" class="flex flex-col gap-2.5">
        <UiSkeleton class="aspect-square w-full rounded-full" />
        <UiSkeleton class="mx-auto h-4 w-2/3" />
      </div>
    </div>

    <UiEmpty
      v-else-if="!canSuggest"
      icon="sparkle"
      :title="t('discover.emptyLibraryTitle')"
      :body="t('discover.emptyLibraryBody')"
    >
      <UiButton icon="search" :to="{ name: 'Search' }">
        {{ t('discover.findMusic') }}
      </UiButton>
    </UiEmpty>

    <UiEmpty
      v-else-if="discover.error.value && !items.length"
      icon="alert"
      :title="t('discover.failed')"
      :body="discover.error.value"
    >
      <UiButton icon="refresh" @click="refresh">{{
        t('common.retry')
      }}</UiButton>
    </UiEmpty>

    <UiEmpty
      v-else-if="discover.loaded.value && !items.length"
      icon="sparkle"
      :title="t('discover.noneTitle')"
      :body="t('discover.noneBody')"
    />

    <template v-else-if="items.length">
      <p
        v-if="discover.partial.value"
        class="flex items-center gap-2 text-[13px] text-muted"
        role="status"
      >
        <AppIcon name="info" :size="16" />
        {{ t('discover.partial') }}
      </p>

      <section class="flex flex-col gap-4">
        <div class="flex items-end justify-between gap-3">
          <h2 class="text-display text-xl font-semibold">
            {{ t('discover.artistsTitle') }}
          </h2>
          <UiButton
            v-if="items.length > ARTISTS_SHOWN"
            size="sm"
            variant="ghost"
            @click="showAllArtists = !showAllArtists"
          >
            {{
              showAllArtists
                ? t('discover.showLess')
                : t('discover.showAll', { count: items.length })
            }}
          </UiButton>
        </div>
        <div :class="GRID">
          <MediaTile
            v-for="item in shownArtists"
            :key="item.name"
            :to="artistRoute(item)"
            :title="item.name"
            :subtitle="because(item)"
            :cover="item.picture_url || proxiedArtistPhotoUrl(item.name)"
            :name="item.name"
            icon="user"
            round
            :playable="false"
          >
            <template #overlay>
              <UiMenu
                :items="menuFor(item)"
                :label="t('discover.moreFor', { name: item.name })"
              >
                <template #trigger>
                  <button
                    type="button"
                    class="flex size-9 items-center justify-center rounded-full bg-black/55 text-white backdrop-blur transition-colors hover:bg-black/75"
                    :aria-label="t('discover.moreFor', { name: item.name })"
                  >
                    <AppIcon name="more" :size="18" />
                  </button>
                </template>
              </UiMenu>
            </template>
          </MediaTile>
        </div>
      </section>

      <section
        v-for="shelf in shelves"
        :key="shelf.id"
        class="flex flex-col gap-4"
      >
        <div>
          <h2 class="text-display text-xl font-semibold">{{ shelf.title }}</h2>
          <p class="mt-1 text-[13px] text-muted">{{ shelf.body }}</p>
        </div>
        <div
          v-if="discover.collectionsLoading.value && !shelf.items.length"
          :class="GRID"
          aria-busy="true"
        >
          <div v-for="n in 6" :key="n" class="flex flex-col gap-2.5">
            <UiSkeleton class="aspect-square w-full" />
            <UiSkeleton class="h-4 w-2/3" />
          </div>
        </div>
        <div v-else :class="GRID">
          <MediaTile
            v-for="item in shelf.items"
            :key="item.spotify_id"
            :to="{ name: 'Link', query: { url: item.url } }"
            :title="item.name"
            :subtitle="shelf.subtitle(item)"
            :cover="item.cover_url"
            :name="item.name"
            :icon="shelf.icon"
            :playable="false"
          />
        </div>
      </section>

      <p
        v-if="discover.collectionsError.value"
        class="flex items-center gap-2 text-[13px] text-muted"
        role="status"
      >
        <AppIcon name="info" :size="16" />
        {{ t('discover.collectionsFailed') }}
      </p>
      <p class="text-[13px] text-faint">{{ t('discover.poweredBy') }}</p>
    </template>

    <UiModal
      :open="hiddenOpen"
      :title="t('discover.hiddenTitle')"
      :description="t('discover.hiddenBody')"
      @close="hiddenOpen = false"
    >
      <div class="flex flex-col gap-4 px-5 py-4 sm:px-6">
        <form class="flex items-end gap-2" @submit.prevent="blockTyped">
          <UiInput
            v-model="typedName"
            class="min-w-0 flex-1"
            :label="t('discover.hideByName')"
            :placeholder="t('discover.hideByNamePlaceholder')"
          />
          <UiButton type="submit" icon="plus" :disabled="!typedName.trim()">
            {{ t('discover.hide') }}
          </UiButton>
        </form>

        <ul v-if="discover.blocked.value.length" class="-mx-2 flex flex-col">
          <li
            v-for="row in discover.blocked.value"
            :key="row.name"
            class="flex items-center gap-3 rounded-[10px] px-2 py-2 hover:bg-surface-2"
          >
            <CoverArt
              :src="proxiedArtistPhotoUrl(row.name)"
              :name="row.name"
              icon="user"
              round
              :letter-size="14"
              class="size-10"
            />
            <span class="min-w-0 flex-1 truncate text-sm font-semibold">{{
              row.name
            }}</span>
            <UiButton size="sm" variant="ghost" @click="unhide(row.name)">
              {{ t('discover.unhide') }}
            </UiButton>
          </li>
        </ul>
        <p v-else class="text-sm text-muted">{{ t('discover.hiddenEmpty') }}</p>

        <div class="flex flex-col gap-2 border-t border-line pt-4">
          <p class="text-[13px] text-muted">{{ t('discover.listensBody') }}</p>
          <div>
            <UiButton
              size="sm"
              variant="ghost"
              icon="trash"
              @click="forgetListens"
            >
              {{ t('discover.clearListens') }}
            </UiButton>
          </div>
        </div>
      </div>
    </UiModal>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import AppIcon from '/src/components/ui/AppIcon.vue'
import CoverArt from '/src/components/ui/CoverArt.vue'
import UiButton from '/src/components/ui/UiButton.vue'
import UiEmpty from '/src/components/ui/UiEmpty.vue'
import UiInput from '/src/components/ui/UiInput.vue'
import UiMenu from '/src/components/ui/UiMenu.vue'
import UiModal from '/src/components/ui/UiModal.vue'
import UiSkeleton from '/src/components/ui/UiSkeleton.vue'
import PageHeader from '/src/components/library/PageHeader.vue'
import MediaTile from '/src/components/library/MediaTile.vue'
import { useDiscover } from '/src/model/discover'
import { useLibrary } from '/src/model/library'
import { useLikes } from '/src/model/likes'
import { useUi } from '/src/model/ui'
import {
  collectionsPayload,
  deezerArtistUrl,
  joinNames,
  libraryPayload,
} from '/src/lib/discover'
import { proxiedArtistPhotoUrl } from '/src/lib/artistPhotoProxy'
import { useI18n } from '/src/i18n'
import { useRouter } from 'vue-router'

const { t, locale } = useI18n()
const router = useRouter()
const ui = useUi()
const library = useLibrary()
const likes = useLikes()
const discover = useDiscover()

const GRID =
  'grid grid-cols-2 gap-x-5 gap-y-7 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 2xl:grid-cols-6'
// Artists shown before "Show all": two rows on a wide screen.
const ARTISTS_SHOWN = 12

const items = computed(() => discover.items.value)
const canSuggest = computed(() => library.artists.value.length > 0)
const showAllArtists = ref(false)
const shownArtists = computed(() =>
  showAllArtists.value ? items.value : items.value.slice(0, ARTISTS_SHOWN)
)

// A suggested artist opens their Spotify page (releases, and top songs to
// preview) when the search found it; otherwise a search for the name.
function artistRoute(item) {
  const url = discover.artistUrls.value[item.name]
  return url
    ? { name: 'Link', query: { url } }
    : { name: 'Search', params: { query: item.name } }
}

const shelves = computed(() =>
  [
    {
      id: 'albums',
      title: t('discover.albumsTitle'),
      body: t('discover.albumsBody'),
      icon: 'disc',
      items: discover.albums.value,
      subtitle: (item) => [item.artist, item.year].filter(Boolean).join(' · '),
    },
    {
      id: 'more',
      title: t('discover.moreAlbumsTitle'),
      body: t('discover.moreAlbumsBody'),
      icon: 'disc',
      items: discover.moreAlbums.value,
      subtitle: (item) => [item.artist, item.year].filter(Boolean).join(' · '),
    },
    {
      id: 'playlists',
      title: t('discover.playlistsTitle'),
      body: t('discover.playlistsBody'),
      icon: 'playlist',
      items: discover.playlists.value,
      subtitle: (item) =>
        item.reason === 'radio'
          ? t('discover.radioFor', { name: item.artist })
          : t('discover.essentialsOf', { name: item.artist }),
    },
  ].filter((shelf) => shelf.items.length || discover.collectionsLoading.value)
)

const hiddenOpen = ref(false)
const typedName = ref('')

async function refresh() {
  if (!canSuggest.value) return
  await discover.load(libraryPayload(library.artists.value, likes.liked.value))
  // Built on the artists just ranked (cached on the server), so after them.
  discover.loadCollections(
    collectionsPayload(
      library.artists.value,
      library.albums.value,
      library.playlists.value,
      likes.liked.value
    )
  )
}

function because(item) {
  return item.because?.length
    ? t('discover.because', { names: joinNames(item.because, locale.value) })
    : ''
}

function menuFor(item) {
  const deezerUrl = deezerArtistUrl(item)
  return [
    {
      label: t('discover.findSongs'),
      icon: 'search',
      action: () =>
        router.push({ name: 'Search', params: { query: item.name } }),
    },
    {
      label: t('discover.openDeezer'),
      icon: 'deezer',
      hidden: !deezerUrl,
      action: () => window.open(deezerUrl, '_blank', 'noopener'),
    },
    { divider: true },
    {
      label: t('discover.notInterested'),
      icon: 'x',
      danger: true,
      action: () => hide(item.name),
    },
  ]
}

async function hide(name) {
  if (await discover.block(name)) {
    ui.toast(t('discover.hidden', { name }), {
      action: { label: t('discover.undo'), run: () => unhide(name) },
    })
  } else {
    ui.toast(t('discover.actionFailed'), { kind: 'error' })
  }
}

async function unhide(name) {
  if (await discover.unblock(name)) refresh()
  else ui.toast(t('discover.actionFailed'), { kind: 'error' })
}

async function blockTyped() {
  const name = typedName.value.trim()
  if (!name) return
  if (await discover.block(name)) typedName.value = ''
  else ui.toast(t('discover.actionFailed'), { kind: 'error' })
}

async function forgetListens() {
  const ok = await ui.confirm({
    title: t('discover.clearListensTitle'),
    body: t('discover.clearListensBody'),
    confirmLabel: t('discover.clearListens'),
    danger: true,
  })
  if (!ok) return
  if (await discover.clearListens()) {
    ui.toast(t('discover.listensCleared'), { kind: 'success' })
    refresh()
  } else {
    ui.toast(t('discover.actionFailed'), { kind: 'error' })
  }
}

onMounted(() => discover.loadBlocked())

// First visit: suggest as soon as the library is known. Coming back keeps
// the last list (the server caches Deezer's answers for a week anyway).
watch(
  () => library.loaded.value,
  (ready) => {
    if (ready && !discover.loaded.value) refresh()
  },
  { immediate: true }
)
</script>
