<template>
  <div
    class="mx-auto flex max-w-[1680px] flex-col gap-4 px-4 pt-6 sm:px-6 md:pt-8 lg:px-10"
  >
    <!-- Path bar, like Finder's: back to the search, then the artist and
         the album open in the columns below. -->
    <nav
      class="flex min-w-0 items-center gap-1.5 text-[13px] text-muted"
      :aria-label="t('finder.path')"
    >
      <RouterLink
        :to="searchLocation"
        class="flex shrink-0 items-center gap-1.5 font-semibold hover:text-fg"
      >
        <AppIcon name="sparkle" :size="15" />{{ t('nav.discover') }}
      </RouterLink>
      <template v-if="artist.data.value">
        <AppIcon name="chevron-right" :size="14" class="shrink-0 text-faint" />
        <button
          type="button"
          class="min-w-0 truncate hover:text-fg"
          :class="albumId ? '' : 'font-semibold text-fg'"
          @click="selectAlbum('')"
        >
          {{ artist.data.value.name }}
        </button>
      </template>
      <template v-if="albumId && album.data.value">
        <AppIcon name="chevron-right" :size="14" class="shrink-0 text-faint" />
        <span class="min-w-0 truncate font-semibold text-fg">{{
          album.data.value.name
        }}</span>
      </template>
    </nav>

    <!-- The column view: one column after another on a wide screen; on a
         narrow one they sit side by side too, a swipe apart. -->
    <div
      ref="columnsEl"
      class="relative flex h-[calc(100dvh-17rem)] min-h-[480px] snap-x snap-mandatory overflow-x-auto overflow-y-hidden rounded-panel border border-line-2 bg-surface/50 md:h-[calc(100dvh-12.5rem)] lg:grid lg:grid-cols-[minmax(260px,300px)_minmax(280px,340px)_minmax(0,1fr)] lg:overflow-hidden"
      :class="
        resizing >= 0
          ? 'cursor-col-resize select-none'
          : 'transition-[grid-template-columns] duration-200 ease-out'
      "
      :style="columnsStyle"
    >
      <!-- Wide screens: a grip on each open column's right edge, dragged
           (or moved with the arrow keys) to resize it; a double click puts
           the default widths back. -->
      <div
        v-for="grip in grips"
        :key="grip.index"
        role="separator"
        aria-orientation="vertical"
        tabindex="0"
        :aria-label="t('finder.resizeColumn')"
        :title="t('finder.resizeHint')"
        class="group absolute inset-y-0 z-20 hidden w-3 -translate-x-1/2 cursor-col-resize touch-none justify-center outline-none lg:flex"
        :style="{ left: `${grip.left}px` }"
        @pointerdown="startResize(grip.index, $event)"
        @dblclick="widths = null"
        @keydown.left.prevent="nudge(grip.index, -16)"
        @keydown.right.prevent="nudge(grip.index, 16)"
      >
        <span
          class="h-full w-0.5 transition-colors group-hover:bg-accent/60 group-focus-visible:bg-accent"
          :class="resizing === grip.index ? 'bg-accent' : ''"
        />
      </div>

      <!-- 1 · The artist -->
      <section
        ref="artistEl"
        class="flex shrink-0 snap-start flex-col overflow-y-auto border-r border-line lg:w-auto"
        :class="collapsed[0] ? 'w-[76px]' : 'w-[86vw] sm:w-[320px]'"
        :aria-label="t('finder.artistColumn')"
      >
        <header
          class="sticky top-0 z-10 border-b border-line bg-bg/90 px-3 py-3 backdrop-blur"
        >
          <div
            class="flex items-center px-1"
            :class="collapsed[0] ? 'justify-center' : 'justify-between'"
          >
            <h3 v-if="!collapsed[0]" class="text-sm font-semibold">
              {{ t('finder.artistColumn') }}
            </h3>
            <UiIconButton
              :icon="collapsed[0] ? 'chevron-right' : 'chevron-left'"
              :label="
                collapsed[0]
                  ? t('finder.expandColumn')
                  : t('finder.collapseColumn')
              "
              size="sm"
              :aria-expanded="!collapsed[0]"
              @click="toggleColumn(0)"
            />
          </div>
        </header>

        <!-- Collapsed: just the pictures - the artist, their popular
             tracks' covers and the related artists - each still doing what
             its full row does. -->
        <template v-if="collapsed[0]">
          <div
            v-if="artist.data.value"
            class="flex flex-col items-center gap-2 py-3"
          >
            <CoverArt
              v-bind="artistPhoto(artist.data.value)"
              :name="artist.data.value.name"
              round
              icon="user"
              :letter-size="14"
              :title="artist.data.value.name"
              class="size-11"
            />
            <template v-if="artist.data.value.top_songs?.length">
              <span class="my-1 h-px w-8 bg-line" aria-hidden="true" />
              <button
                v-for="song in artist.data.value.top_songs"
                :key="song.song_id"
                type="button"
                class="rounded-[8px] p-1 transition-colors disabled:cursor-default"
                :class="
                  song.song_id === trackId
                    ? 'bg-accent'
                    : 'hover:bg-surface-2 disabled:hover:bg-transparent'
                "
                :title="song.name"
                :aria-label="song.name"
                :disabled="!song.deezer_album_id"
                @click="selectTrack(song)"
              >
                <CoverArt
                  :src="deezerImage(song.cover_url)"
                  :name="song.album_name || song.name"
                  rounded="rounded-[6px]"
                  :letter-size="11"
                  class="size-10"
                />
              </button>
            </template>
            <template v-if="artist.data.value.related?.length">
              <span class="my-1 h-px w-8 bg-line" aria-hidden="true" />
              <RouterLink
                v-for="other in artist.data.value.related"
                :key="other.artist_id"
                :to="browseLocation('artist', other)"
                class="rounded-full p-1 transition-colors hover:bg-surface-2"
                :title="other.name"
                :aria-label="other.name"
              >
                <CoverArt
                  v-bind="artistPhoto(other)"
                  :name="other.name"
                  round
                  icon="user"
                  :letter-size="12"
                  class="size-10"
                />
              </RouterLink>
            </template>
          </div>
          <div
            v-else-if="artist.loading.value"
            class="flex flex-col items-center gap-3 py-3"
          >
            <UiSkeleton class="size-11 !rounded-full" />
            <UiSkeleton
              v-for="n in 5"
              :key="n"
              class="size-10 !rounded-[6px]"
            />
          </div>
        </template>

        <template v-else>
          <div
            v-if="artist.loading.value"
            class="flex flex-col items-center gap-3 p-5"
          >
            <UiSkeleton class="size-36 !rounded-full" />
            <UiSkeleton class="h-5 w-2/3" />
            <UiSkeleton class="h-3 w-1/2" />
            <UiSkeleton class="mt-4 h-24 w-full" />
          </div>
          <FinderColumnEmpty
            v-else-if="artist.error.value"
            icon="alert"
            :title="t('finder.failed')"
            :body="artist.error.value"
          >
            <UiButton size="sm" icon="refresh" @click="loadArtist">{{
              t('common.retry')
            }}</UiButton>
          </FinderColumnEmpty>
          <FinderColumnEmpty
            v-else-if="!artist.data.value"
            icon="user"
            :title="t('finder.noArtist')"
          />
          <div v-else class="flex flex-col gap-6 p-5">
            <div class="flex flex-col items-center gap-3 text-center">
              <CoverArt
                v-bind="artistPhoto(artist.data.value)"
                :name="artist.data.value.name"
                round
                icon="user"
                shadow
                :letter-size="44"
                class="size-36"
              />
              <div class="min-w-0">
                <h2 class="text-display text-2xl font-bold text-balance">
                  {{ artist.data.value.name }}
                </h2>
                <p
                  v-if="artist.data.value.album_count"
                  class="mt-1 text-[13px] text-muted"
                >
                  {{
                    t('common.albums', { count: artist.data.value.album_count })
                  }}
                </p>
              </div>
            </div>

            <section v-if="artist.data.value.bio" class="flex flex-col gap-2">
              <h3 class="eyebrow">{{ t('finder.about') }}</h3>
              <p
                class="text-[13px] leading-relaxed whitespace-pre-line text-fg-3"
                :class="bioOpen ? '' : 'line-clamp-6'"
              >
                {{ artist.data.value.bio }}
              </p>
              <button
                type="button"
                class="self-start text-[13px] font-semibold text-muted hover:text-fg"
                @click="bioOpen = !bioOpen"
              >
                {{ bioOpen ? t('finder.showLess') : t('finder.showMore') }}
              </button>
            </section>

            <section
              v-if="artist.data.value.top_songs?.length"
              class="flex flex-col gap-1"
            >
              <h3 class="eyebrow pb-1">{{ t('finder.popular') }}</h3>
              <button
                v-for="song in artist.data.value.top_songs"
                :key="song.song_id"
                type="button"
                class="-mx-2 flex items-center gap-2.5 rounded-[8px] px-2 py-1.5 text-left transition-colors hover:bg-surface-2 disabled:cursor-default disabled:hover:bg-transparent"
                :class="song.song_id === trackId ? 'bg-surface-2' : ''"
                :disabled="!song.deezer_album_id"
                @click="selectTrack(song)"
              >
                <CoverArt
                  :src="deezerImage(song.cover_url)"
                  :name="song.album_name || song.name"
                  rounded="rounded-[6px]"
                  :letter-size="11"
                  class="size-9"
                />
                <span class="min-w-0 flex-1">
                  <span
                    class="block truncate text-[13px] font-semibold"
                    :class="song.song_id === trackId ? 'text-accent' : ''"
                    >{{ song.name }}</span
                  >
                  <span class="block truncate text-xs text-muted">{{
                    song.album_name
                  }}</span>
                </span>
              </button>
            </section>

            <section
              v-if="artist.data.value.related?.length"
              class="flex flex-col gap-1"
            >
              <h3 class="eyebrow pb-1">{{ t('finder.related') }}</h3>
              <RouterLink
                v-for="other in artist.data.value.related"
                :key="other.artist_id"
                :to="browseLocation('artist', other)"
                class="-mx-2 flex items-center gap-2.5 rounded-[8px] px-2 py-1.5 transition-colors hover:bg-surface-2"
              >
                <CoverArt
                  v-bind="artistPhoto(other)"
                  :name="other.name"
                  round
                  icon="user"
                  :letter-size="12"
                  class="size-9"
                />
                <span
                  class="min-w-0 flex-1 truncate text-[13px] font-semibold"
                  >{{ other.name }}</span
                >
              </RouterLink>
            </section>
          </div>
        </template>
      </section>

      <!-- 2 · Their discography -->
      <section
        ref="albumsEl"
        class="flex shrink-0 snap-start flex-col overflow-y-auto border-r border-line lg:w-auto"
        :class="collapsed[1] ? 'w-[76px]' : 'w-[86vw] sm:w-[340px]'"
        :aria-label="t('finder.discography')"
      >
        <header
          class="sticky top-0 z-10 flex flex-col gap-2 border-b border-line bg-bg/90 px-3 py-3 backdrop-blur"
        >
          <div
            class="flex items-center gap-2 px-1"
            :class="collapsed[1] ? 'justify-center' : ''"
          >
            <template v-if="!collapsed[1]">
              <h3 class="text-sm font-semibold">
                {{ t('finder.discography') }}
              </h3>
              <span
                v-if="albums.data.value?.length"
                class="tabular mr-auto text-xs text-faint"
                >{{ visibleAlbums.length }}</span
              >
            </template>
            <UiIconButton
              :icon="collapsed[1] ? 'chevron-right' : 'chevron-left'"
              :label="
                collapsed[1]
                  ? t('finder.expandColumn')
                  : t('finder.collapseColumn')
              "
              size="sm"
              :class="collapsed[1] ? '' : 'ml-auto'"
              :aria-expanded="!collapsed[1]"
              @click="toggleColumn(1)"
            />
          </div>
          <UiChips
            v-if="!collapsed[1] && typeChips.length > 2"
            v-model="typeFilter"
            :items="typeChips"
          />
        </header>

        <!-- Collapsed: just the covers, the selected one framed. -->
        <template v-if="collapsed[1]">
          <div
            v-if="albums.loading.value"
            class="flex flex-col items-center gap-3 py-3"
          >
            <UiSkeleton
              v-for="n in 8"
              :key="n"
              class="size-12 !rounded-[6px]"
            />
          </div>
          <ul v-else class="flex flex-col items-center gap-1 py-2">
            <li v-for="item in visibleAlbums" :key="item.album_id">
              <button
                type="button"
                class="rounded-[9px] p-1 transition-colors"
                :class="
                  item.album_id === albumId ? 'bg-accent' : 'hover:bg-surface-2'
                "
                :title="item.name"
                :aria-label="item.name"
                :aria-current="item.album_id === albumId ? 'true' : undefined"
                :data-album-id="item.album_id"
                @click="selectAlbum(item.album_id)"
              >
                <CoverArt
                  :src="deezerImage(item.cover_url)"
                  :name="item.name"
                  rounded="rounded-[6px]"
                  icon="disc"
                  :letter-size="14"
                  class="size-12"
                />
              </button>
            </li>
          </ul>
        </template>

        <template v-else>
          <div v-if="albums.loading.value" class="flex flex-col gap-1 p-1.5">
            <div
              v-for="n in 8"
              :key="n"
              class="flex items-center gap-3 px-2 py-2"
            >
              <UiSkeleton class="size-12 !rounded-[6px]" />
              <div class="flex flex-1 flex-col gap-2">
                <UiSkeleton class="h-3.5 w-2/3" />
                <UiSkeleton class="h-3 w-1/3" />
              </div>
            </div>
          </div>
          <FinderColumnEmpty
            v-else-if="albums.error.value"
            icon="alert"
            :title="t('finder.failed')"
            :body="albums.error.value"
          >
            <UiButton size="sm" icon="refresh" @click="loadAlbums">{{
              t('common.retry')
            }}</UiButton>
          </FinderColumnEmpty>
          <FinderColumnEmpty
            v-else-if="artistId && albums.data.value && !visibleAlbums.length"
            icon="disc"
            :title="t('finder.noAlbums')"
          />
          <ul v-else class="flex flex-col gap-0.5 p-1.5">
            <li v-for="item in visibleAlbums" :key="item.album_id">
              <button
                type="button"
                class="flex w-full items-center gap-3 rounded-[10px] px-2 py-2 text-left transition-colors"
                :class="
                  item.album_id === albumId
                    ? 'bg-accent text-on-accent'
                    : 'hover:bg-surface-2'
                "
                :aria-current="item.album_id === albumId ? 'true' : undefined"
                :data-album-id="item.album_id"
                @click="selectAlbum(item.album_id)"
              >
                <CoverArt
                  :src="deezerImage(item.cover_url)"
                  :name="item.name"
                  rounded="rounded-[6px]"
                  icon="disc"
                  :letter-size="14"
                  class="size-12"
                />
                <span class="min-w-0 flex-1">
                  <span class="flex items-center gap-1.5">
                    <span class="truncate text-sm font-semibold">{{
                      item.name
                    }}</span>
                    <span
                      v-if="item.explicit"
                      class="shrink-0 rounded-[3px] px-1 text-[9px] leading-[14px] font-bold"
                      :class="
                        item.album_id === albumId
                          ? 'bg-on-accent text-accent'
                          : 'bg-muted text-bg'
                      "
                      :title="t('search.explicit')"
                      >E</span
                    >
                  </span>
                  <span
                    class="block truncate text-xs"
                    :class="
                      item.album_id === albumId
                        ? 'text-on-accent/80'
                        : 'text-muted'
                    "
                    >{{ albumMeta(item) }}</span
                  >
                </span>
                <AppIcon
                  name="chevron-right"
                  :size="15"
                  class="shrink-0 opacity-60"
                />
              </button>
            </li>
          </ul>
        </template>
      </section>

      <!-- 3 · One album's tracks -->
      <section
        ref="tracksEl"
        class="flex w-[92vw] shrink-0 snap-start flex-col overflow-y-auto sm:w-[560px] lg:w-auto"
        :aria-label="t('finder.tracksColumn')"
      >
        <FinderColumnEmpty
          v-if="!albumId"
          icon="disc"
          :title="t('finder.pickAlbum')"
          :body="t('finder.pickAlbumHint')"
        />
        <div v-else-if="album.loading.value" class="flex flex-col gap-5 p-5">
          <div class="flex items-end gap-4">
            <UiSkeleton class="size-36 !rounded-cover" />
            <div class="flex flex-1 flex-col gap-2">
              <UiSkeleton class="h-3 w-16" />
              <UiSkeleton class="h-6 w-2/3" />
              <UiSkeleton class="h-3 w-1/2" />
            </div>
          </div>
          <div v-for="n in 6" :key="n" class="flex h-12 items-center gap-3">
            <UiSkeleton class="size-10 !rounded-[8px]" />
            <UiSkeleton class="h-3.5 w-1/2" />
          </div>
        </div>
        <FinderColumnEmpty
          v-else-if="album.error.value"
          icon="alert"
          :title="t('finder.failed')"
          :body="album.error.value"
        >
          <UiButton size="sm" icon="refresh" @click="loadAlbum">{{
            t('common.retry')
          }}</UiButton>
        </FinderColumnEmpty>
        <div v-else-if="album.data.value" class="flex flex-col gap-5 p-5">
          <div class="flex flex-col gap-4 sm:flex-row sm:items-end">
            <CoverArt
              :src="deezerImage(album.data.value.cover_url)"
              :name="album.data.value.name"
              icon="disc"
              shadow
              :letter-size="40"
              class="size-36 sm:size-40"
            />
            <div class="min-w-0 flex-1">
              <p class="eyebrow">
                {{ typeLabel(album.data.value.release_type) }}
              </p>
              <h2
                class="text-display text-2xl font-bold text-balance sm:text-3xl"
              >
                {{ album.data.value.name }}
              </h2>
              <p class="mt-1 text-[13px] text-muted">{{ albumSummary }}</p>
              <div class="mt-3 flex flex-wrap gap-2">
                <UiButton
                  size="sm"
                  variant="primary"
                  icon="download"
                  :loading="downloadingAlbum"
                  :disabled="!album.data.value.tracks?.length"
                  @click="downloadAlbum"
                  >{{ t('finder.downloadAlbum') }}</UiButton
                >
                <UiButton
                  v-if="album.data.value.url"
                  size="sm"
                  icon="arrow-up-right"
                  :href="album.data.value.url"
                  >{{ t('link.openDeezer') }}</UiButton
                >
              </div>
            </div>
          </div>

          <!-- Like Finder's preview pane: everything else Deezer says
               about the album. -->
          <dl
            v-if="albumInfo.length"
            class="grid grid-cols-[auto_minmax(0,1fr)] gap-x-4 gap-y-1.5 rounded-[12px] bg-surface-2/60 p-4 text-[13px]"
          >
            <template v-for="row in albumInfo" :key="row.label">
              <dt class="text-faint">{{ row.label }}</dt>
              <dd class="text-fg-3">{{ row.value }}</dd>
            </template>
          </dl>

          <FinderColumnEmpty
            v-if="!album.data.value.tracks?.length"
            icon="music"
            :title="t('link.empty')"
          />
          <TrackDownPlayList
            v-else
            :songs="album.data.value.tracks"
            :queue="albumQueue"
            :collection-name="album.data.value.name"
            :toolbar-mode="TOOLBAR_NONE"
            :marked-key="trackId"
            hide-album
          />
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
// The Finder's column view, after macOS Finder's: the artist, their
// discography and one album's tracks side by side, from Deezer alone -
// opened from a Finder search result (see DiscoverHubView). Which artist, album
// and track are open lives in the URL (`?artist=&album=&track=`, Deezer
// ids), so it survives a reload and the back button walks back through
// the artists visited. Picking an album replaces the URL rather than
// adding to the history, the way clicking around in Finder does.
import { computed, nextTick, ref, shallowRef, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useElementSize, useMediaQuery } from '@vueuse/core'
import AppIcon from '/src/components/ui/AppIcon.vue'
import CoverArt from '/src/components/ui/CoverArt.vue'
import UiButton from '/src/components/ui/UiButton.vue'
import UiChips from '/src/components/ui/UiChips.vue'
import UiIconButton from '/src/components/ui/UiIconButton.vue'
import UiSkeleton from '/src/components/ui/UiSkeleton.vue'
import FinderColumnEmpty from '/src/components/finder/FinderColumnEmpty.vue'
import TrackDownPlayList, {
  TOOLBAR_NONE,
} from '/src/components/library/TrackDownPlayList.vue'
import { useDownloadManager } from '/src/model/download'
import { useFinder } from '/src/model/finder'
import { useLibrary } from '/src/model/library'
import { useSongStarter } from '/src/model/songPlay'
import { useUi } from '/src/model/ui'
import {
  COLUMN_MIN,
  browseLocation,
  clampColumnWidths,
  matchesReleaseType,
  releaseTypes,
} from '/src/lib/finder'
import { knownArtistPhoto } from '/src/lib/artistPhotoProxy'
import { deezerImage } from '/src/lib/deezerImage'
import { splitLength } from '/src/lib/format'
import { playableQueue } from '/src/lib/topSongs'
import { useI18n } from '/src/i18n'

const { t, locale } = useI18n()

// An artist's photo: the one saved in the library when there is one, else
// the Deezer picture this page already has (medium size) - relayed by the
// photo proxy without a search by name, and loaded directly if the proxy
// can't answer. As CoverArt's `src`/`fallback`.
function artistPhoto(artist) {
  const photo = knownArtistPhoto(artist?.name, deezerImage(artist?.cover_url))
  return { src: photo.cover, fallback: photo.fallback }
}
const route = useRoute()
const router = useRouter()
const finder = useFinder()
const library = useLibrary()
const dm = useDownloadManager()
const ui = useUi()

const artistId = computed(() => String(route.query.artist || ''))
const albumId = computed(() => String(route.query.album || ''))
const trackId = computed(() => String(route.query.track || ''))

const columnsEl = ref(null)
const artistEl = ref(null)
const albumsEl = ref(null)
const tracksEl = ref(null)

// ── Column widths ─────────────────────────────────────────────────────
// Deliberately this page's state alone - never saved anywhere (no local
// or session storage): a reload, or leaving the Finder, puts the default
// widths back, and both columns open. Only wide screens have grips; a
// narrow one swipes instead (but can still retract a column).
//
// [artist, discography] in px as last dragged - either may be null (never
// dragged: the grid's own default) - or null altogether.
const widths = ref(null)
// Whether the artist/discography column is retracted to its pictures.
const collapsed = ref([false, false])
const resizing = ref(-1) // the grip being dragged, -1 for none
const isWide = useMediaQuery('(min-width: 1024px)')
const { width: columnsWidth } = useElementSize(columnsEl)
const { width: artistWidth } = useElementSize(artistEl, undefined, {
  box: 'border-box',
})
const { width: albumsWidth } = useElementSize(albumsEl, undefined, {
  box: 'border-box',
})

// A retracted column: one cover (48px) and its padding.
const COLLAPSED_WIDTH = 76
// The grid's own width for an open column nobody dragged (its CSS class).
const DEFAULT_COLUMNS = ['minmax(260px, 300px)', 'minmax(280px, 340px)']

function toggleColumn(index) {
  const next = [...collapsed.value]
  next[index] = !next[index]
  collapsed.value = next
  // The discography turned from rows into covers (or back): keep the
  // selected album in sight.
  if (index === 1) nextTick(revealSelectedAlbum)
}

// A retracted column takes no more than its pictures need.
function columnMins() {
  return COLUMN_MIN.map((min, i) =>
    i < 2 && collapsed.value[i] ? COLLAPSED_WIDTH : min
  )
}

const columnsStyle = computed(() => {
  if (!isWide.value) return undefined
  if (!widths.value && !collapsed.value.some(Boolean)) return undefined
  const current = [0, 1].map((i) =>
    collapsed.value[i] ? COLLAPSED_WIDTH : (widths.value?.[i] ?? null)
  )
  // Clamped against the room there is now, so a narrower window never
  // squeezes the tracks column below its minimum.
  const sized = current.includes(null)
    ? current
    : clampColumnWidths(current, columnsWidth.value, columnMins())
  const tracks = sized.map((width, i) =>
    width === null ? DEFAULT_COLUMNS[i] : `${width}px`
  )
  return { gridTemplateColumns: `${tracks[0]} ${tracks[1]} minmax(0, 1fr)` }
})

// Where the grips sit: the right edges of the first two columns - only an
// open column has one.
const grips = computed(() =>
  [
    { index: 0, left: artistWidth.value },
    { index: 1, left: artistWidth.value + albumsWidth.value },
  ].filter((grip) => !collapsed.value[grip.index])
)

function resizeTo(next) {
  const sized = clampColumnWidths(next, columnsWidth.value, columnMins())
  // A retracted column keeps the width it had open, for when it's
  // expanded again.
  widths.value = sized.map((width, i) =>
    collapsed.value[i] ? (widths.value?.[i] ?? null) : width
  )
}

function startResize(index, event) {
  if (event.button !== 0) return
  const grip = event.currentTarget
  const startX = event.clientX
  const from = [artistWidth.value, albumsWidth.value]
  resizing.value = index
  grip.setPointerCapture(event.pointerId)
  const move = (e) => {
    const next = [...from]
    next[index] += e.clientX - startX
    resizeTo(next)
  }
  const stop = () => {
    resizing.value = -1
    grip.removeEventListener('pointermove', move)
    grip.removeEventListener('pointerup', stop)
    grip.removeEventListener('pointercancel', stop)
  }
  grip.addEventListener('pointermove', move)
  grip.addEventListener('pointerup', stop)
  grip.addEventListener('pointercancel', stop)
}

function nudge(index, delta) {
  const next = [artistWidth.value, albumsWidth.value]
  next[index] += delta
  resizeTo(next)
}

// One column's data: what's shown, whether it's on its way, and why it
// failed. A later load wins over an earlier one still in flight; an answer
// already fetched (see model/finder's `peek`) shows at once.
function useColumn(fetch, peek) {
  const data = ref(null)
  const loading = ref(false)
  const error = ref('')
  let serial = 0

  async function load(...args) {
    const mine = ++serial
    error.value = ''
    const known = args[0] ? peek(...args) : undefined
    data.value = known ?? null
    loading.value = false
    if (!args[0] || known) return
    loading.value = true
    try {
      const value = await fetch(...args)
      if (mine === serial) data.value = value
    } catch (err) {
      if (mine === serial) {
        error.value = err?.response?.data?.detail || err?.message || ''
      }
    } finally {
      if (mine === serial) loading.value = false
    }
  }

  return { data, loading, error, load }
}

const artist = useColumn(finder.artist, (...args) =>
  finder.peek('artist', ...args)
)
const albums = useColumn(finder.artistAlbums, (...args) =>
  finder.peek('albums', ...args)
)
const album = useColumn(finder.album, (...args) =>
  finder.peek('album', ...args)
)

function loadArtist() {
  return artist.load(artistId.value, locale.value)
}

async function loadAlbums() {
  const id = artistId.value
  await albums.load(id)
  // Another artist was opened meanwhile: that load takes it from here.
  if (artistId.value !== id || !albums.data.value) return
  await nextTick()
  revealSelectedAlbum()
  finder.fillTrackCounts(albums.data.value, () => artistId.value === id)
}

async function loadAlbum() {
  await album.load(albumId.value)
  await nextTick()
  if (!revealMarkedTrack() && tracksEl.value) tracksEl.value.scrollTop = 0
  playPickedTrack()
}

// A popular track, once picked, starts playing as soon as its album is on
// screen - streamed in full, or the song itself once it's downloaded,
// like a double click on its row. One-shot: dropped once it starts, or
// when another album or artist is picked first.
const startSong = useSongStarter()
const pickedTrack = shallowRef(null)

function playPickedTrack() {
  const song = pickedTrack.value
  if (!song || song.song_id !== trackId.value) return
  const loaded = album.data.value
  if (!loaded || String(loaded.album_id) !== albumId.value) return
  pickedTrack.value = null
  // The album's own row when it has the track (same song, plus its
  // number); the popular track itself otherwise.
  const row = (loaded.tracks || []).find(
    (item) => item.song_id === song.song_id
  )
  startSong(row || song, {
    queue: albumQueue.value,
    songs: loaded.tracks || undefined,
  })
}

// Smooth, unless the system asks for less motion.
function scrollBehavior() {
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches
    ? 'auto'
    : 'smooth'
}

// Glides `container` alone - never the page, as `scrollIntoView` would,
// sideways too on a phone - until `el` sits in the middle of it, the way
// Finder brings what's selected into view. Left alone when `el` is already
// in full sight (below `topInset`, a sticky header's height), so a row near
// the top doesn't push the column's header away.
function scrollWithin(container, el, { topInset = 0 } = {}) {
  if (!container || !el) return
  const box = container.getBoundingClientRect()
  const row = el.getBoundingClientRect()
  const top = box.top + topInset
  if (row.top >= top && row.bottom <= box.bottom) return
  const room = box.bottom - top
  container.scrollTo({
    top: container.scrollTop + row.top - top - (room - row.height) / 2,
    behavior: scrollBehavior(),
  })
}

// The track the view was opened on (or a popular track just picked).
function revealMarkedTrack() {
  const marked = tracksEl.value?.querySelector('[data-marked]')
  scrollWithin(tracksEl.value, marked)
  return !!marked
}

const bioOpen = ref(false)
const typeFilter = ref('all')

watch(
  artistId,
  () => {
    bioOpen.value = false
    typeFilter.value = 'all'
    pickedTrack.value = null
    loadAlbums()
  },
  { immediate: true }
)
watch([artistId, locale], loadArtist, { immediate: true })
watch(albumId, loadAlbum, { immediate: true })
// Another popular track of the album already open: no reload, just a
// scroll to it.
watch(trackId, () => nextTick(revealMarkedTrack))

// The selected album, brought into view in its column - below the
// column's sticky header.
function revealSelectedAlbum() {
  if (!albumId.value || !albumsEl.value) return
  const row = albumsEl.value.querySelector(`[data-album-id="${albumId.value}"]`)
  const header = albumsEl.value.querySelector('header')
  scrollWithin(albumsEl.value, row, { topInset: header?.offsetHeight || 0 })
}

// On a narrow screen only one or two columns fit: slide over to the
// tracks once an album is picked.
function revealTracks() {
  const columns = columnsEl.value
  if (!columns || !tracksEl.value) return
  if (columns.scrollWidth <= columns.clientWidth) return
  columns.scrollTo({
    left: tracksEl.value.offsetLeft,
    behavior: scrollBehavior(),
  })
}

function selectAlbum(id) {
  pickedTrack.value = null
  const query = { artist: artistId.value }
  if (id) query.album = id
  router.replace({ name: 'FinderBrowse', query })
  if (id) nextTick(revealTracks)
}

// A popular track opens on its own album, pointing at the track: the album
// glides into view in the discography, the track in the tracks column
// (once they're loaded, if the album is new - see loadAlbum).
async function selectTrack(song) {
  const id = song.deezer_album_id
  if (!id) return
  // An album the release-type chips are hiding couldn't be shown.
  const row = (albums.data.value || []).find((item) => item.album_id === id)
  if (row && !matchesReleaseType(row, typeFilter.value)) {
    typeFilter.value = 'all'
  }
  pickedTrack.value = song
  await router.replace({
    name: 'FinderBrowse',
    query: { artist: artistId.value, album: id, track: song.song_id },
  })
  await nextTick()
  revealSelectedAlbum()
  revealTracks()
  // Its album already open (or cached): nothing left to wait for.
  playPickedTrack()
}

// Back to the search (or the artist's songs) this was opened from, when
// there was one - else to Discover's suggestions.
const searchLocation = computed(() => ({
  name: 'Discover',
  query: finder.lastSearchQuery(),
}))

function typeLabel(type) {
  const key = {
    album: 'search.typeAlbum',
    single: 'search.typeSingle',
    ep: 'search.typeEp',
    compilation: 'finder.typeCompilation',
  }[String(type || '').toLowerCase()]
  return key ? t(key) : type || t('search.typeAlbum')
}

const typeChips = computed(() => {
  const list = albums.data.value || []
  return [
    { id: 'all', label: t('search.all'), count: list.length },
    ...releaseTypes(list).map(({ id, count }) => ({
      id,
      label: typeLabel(id),
      count,
    })),
  ]
})

const visibleAlbums = computed(() =>
  (albums.data.value || []).filter((item) =>
    matchesReleaseType(item, typeFilter.value)
  )
)

function trackCountOf(item) {
  return item.track_count ?? finder.trackCounts[item.album_id]
}

function albumMeta(item) {
  const count = trackCountOf(item)
  return [
    typeLabel(item.release_type),
    item.year,
    count !== undefined && count !== null ? t('common.tracks', { count }) : '…',
  ]
    .filter(Boolean)
    .join(' · ')
}

function lengthLabel(seconds) {
  const { hours, minutes } = splitLength(seconds)
  if (!hours && !minutes) return ''
  return hours
    ? t('common.lengthHours', { hours, minutes })
    : t('common.lengthMinutes', { minutes })
}

const albumSummary = computed(() => {
  const a = album.data.value
  if (!a) return ''
  return [
    a.artist,
    a.year,
    t('common.tracks', { count: a.track_count || a.tracks?.length || 0 }),
    lengthLabel(a.duration),
  ]
    .filter(Boolean)
    .join(' · ')
})

function longDate(value) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value || '')) return value || ''
  try {
    return new Intl.DateTimeFormat(locale.value, { dateStyle: 'long' }).format(
      new Date(`${value}T00:00:00`)
    )
  } catch {
    return value
  }
}

const albumInfo = computed(() => {
  const a = album.data.value
  if (!a) return []
  // Everyone credited but the album's own artist (already in the title).
  const credits = (a.contributors || [])
    .filter((person) => person.name !== a.artist)
    .map((person) => person.name)
  return [
    { label: t('finder.released'), value: longDate(a.release_date) },
    { label: t('finder.label'), value: a.label },
    { label: t('finder.genres'), value: (a.genres || []).join(', ') },
    { label: t('finder.credits'), value: credits.join(', ') },
    { label: 'UPC', value: a.upc },
  ].filter((row) => row.value)
})

// Downloaded tracks play from the library, in the album's order.
const albumQueue = computed(() =>
  playableQueue(album.data.value?.tracks || [], library.findTrack)
)

const downloadingAlbum = ref(false)

async function downloadAlbum() {
  const a = album.data.value
  if (!a?.tracks?.length) return
  downloadingAlbum.value = true
  try {
    const count = await dm.fromSongs(a.tracks)
    ui.toast(t('toast.queuedTracks', { count, name: a.name }), {
      kind: 'success',
      action: {
        label: t('nav.queue'),
        run: () => router.push({ name: 'Queue' }),
      },
    })
  } catch (err) {
    ui.toast(err?.response?.data?.detail || t('toast.actionFailed'), {
      kind: 'error',
    })
  } finally {
    downloadingAlbum.value = false
  }
}
</script>
