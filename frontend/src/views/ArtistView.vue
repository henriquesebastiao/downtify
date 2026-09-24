<template>
  <div>
    <DetailState
      :loaded="library.loaded.value"
      :found="!!artist"
      icon="user"
      :missing="t('artist.notFound')"
    >
      <CollectionHero
        :title="artist.name"
        :kicker="t('artist.kicker')"
        :cover="heroPhoto.cover"
        :cover-fallback="heroPhoto.fallback"
        :banner="artBannerUrl"
        photo-editable
        banner-editable
        :name="artist.name"
        icon="user"
        round
        :social="profile.social"
        :platforms-id="profile.platforms_id"
        @edit-photo="openArtModal('photo')"
        @edit-banner="openArtModal('banner')"
      >
        <template #subtitle>
          {{ facts }}
        </template>
        <template #actions>
          <PlayButton
            :label="t('actions.playItem', { name: artist.name })"
            :playing="isThisPlaying"
            @click="togglePlay"
          />
          <UiIconButton
            icon="shuffle"
            :label="t('actions.shuffle')"
            size="lg"
            round
            :photo="!!artBannerUrl"
            @click="actions.play(allTracks, 0, context, { shuffled: true })"
          />
          <UiButton
            :variant="artBannerUrl ? 'photo' : 'ghost'"
            icon="queue"
            @click="actions.enqueue(allTracks)"
          >
            {{ t('actions.addToQueue') }}
          </UiButton>
          <UiButton
            :variant="artBannerUrl ? 'photo' : 'ghost'"
            icon="search"
            :to="{ name: 'Search', params: { query: artist.name } }"
          >
            {{ t('artist.findMore') }}
          </UiButton>
        </template>
      </CollectionHero>

      <div
        class="mx-auto flex max-w-[1680px] flex-col gap-6 px-4 sm:px-6 lg:px-10"
      >
        <UiTabs class="mt-4" :items="tabs" :model-value="tab" />

        <template v-if="tab === 'albums'">
          <div
            class="grid grid-cols-2 gap-x-5 gap-y-7 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 2xl:grid-cols-6"
          >
            <MediaTile
              v-for="album in artist.albums"
              :key="album.key"
              :to="{
                name: 'Album',
                query: { artist: album.artist, title: album.title },
              }"
              :title="album.title"
              :subtitle="
                [album.year, t('common.tracks', { count: album.tracks.length })]
                  .filter(Boolean)
                  .join(' · ')
              "
              :cover="album.cover"
              :name="album.title"
              @play="playAlbum(album)"
            />
          </div>
        </template>

        <template v-else-if="tab === 'related'">
          <div
            class="grid grid-cols-2 gap-x-5 gap-y-7 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 2xl:grid-cols-6"
          >
            <MediaTile
              v-for="item in relatedArtistItems"
              :key="item.name"
              v-bind="item"
              :playable="false"
            />
          </div>
        </template>

        <template v-else-if="tab === 'topsongs'">
          <div
            v-if="topSongsLoading || !profileReady"
            class="flex flex-col gap-2"
            aria-busy="true"
          >
            <UiSkeleton v-for="n in 5" :key="n" class="h-16 w-full" />
          </div>
          <UiEmpty
            v-else-if="topSongsError"
            icon="alert"
            :title="t('link.failed')"
            :body="topSongsError"
          >
            <UiButton icon="refresh" @click="loadTopSongs(true)">{{
              t('common.retry')
            }}</UiButton>
          </UiEmpty>
          <TopSongsShelf
            v-else-if="topSongsData?.songs.length"
            :data="topSongsData"
            :context="context"
          />
          <UiEmpty v-else icon="music" :title="t('link.topSongsEmpty')" />
        </template>

        <template v-else-if="tab === 'bio'">
          <section class="flex flex-col gap-3">
            <div v-if="profile.genre" class="flex items-center gap-2">
              <span class="text-[13px] text-muted">{{
                t('artistBio.genre')
              }}</span>
              <UiBadge>{{ profile.genre }}</UiBadge>
            </div>
            <p v-if="bioFacts" class="text-[13px] text-muted">
              {{ bioFacts }}
            </p>
            <!-- profile.bio is plain text: a blank line separates
            paragraphs, a single line break stays a line break. -->
            <div
              v-if="bioParagraphs.length"
              class="flex flex-col gap-3 text-[15px] text-fg-3"
            >
              <p
                v-for="(paragraph, i) in bioParagraphs"
                :key="i"
                class="whitespace-pre-line"
              >
                {{ paragraph }}
              </p>
            </div>
            <p v-else class="text-[13px] text-muted">
              {{ t('artistBio.empty') }}
            </p>
          </section>
        </template>

        <TrackList
          v-else
          :tracks="allTracks"
          :context="context"
          :show-added="false"
          :hide-menu="['artist']"
        />
      </div>
    </DetailState>

    <ArtistArtModal
      v-if="artist"
      :open="artModalOpen"
      :initial-tab="artModalInitialTab"
      :artist-name="artist.name"
      :track-files="trackFiles"
      :photo-url="heroPhoto.cover"
      :photo-fallback="heroPhoto.fallback"
      :current-cover="profile.current_cover"
      :current-banner="profile.current_cover_banner"
      :has-photo="!!artPhotoUrl"
      :has-banner="!!artBannerUrl"
      :bio="profile.bio"
      :social="profile.social"
      @close="artModalOpen = false"
      @saved="onArtSaved"
    />
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import UiBadge from '/src/components/ui/UiBadge.vue'
import UiButton from '/src/components/ui/UiButton.vue'
import UiEmpty from '/src/components/ui/UiEmpty.vue'
import UiIconButton from '/src/components/ui/UiIconButton.vue'
import UiSkeleton from '/src/components/ui/UiSkeleton.vue'
import UiTabs from '/src/components/ui/UiTabs.vue'
import ArtistArtModal from '/src/components/library/ArtistArtModal.vue'
import CollectionHero from '/src/components/library/CollectionHero.vue'
import DetailState from '/src/components/library/DetailState.vue'
import MediaTile from '/src/components/library/MediaTile.vue'
import PlayButton from '/src/components/library/PlayButton.vue'
import TopSongsShelf from '/src/components/library/TopSongsShelf.vue'
import TrackList from '/src/components/library/TrackList.vue'
import API from '/src/model/api'
import { useLibrary } from '/src/model/library'
import { usePlayer } from '/src/model/player'
import { useTrackActions } from '/src/model/trackActions'
import { useUi } from '/src/model/ui'
import { sortItems } from '/src/lib/library'
import { splitLength } from '/src/lib/format'
import { proxiedArtistPhotoUrl } from '/src/lib/artistPhotoProxy'
import { versionedArtUrl } from '/src/lib/artistArt'
import { useI18n } from '/src/i18n'

const { t, locale } = useI18n()
const route = useRoute()
const library = useLibrary()
const player = usePlayer()
const actions = useTrackActions()
const ui = useUi()

const artist = computed(() =>
  library.findArtist(String(route.query.name || ''))
)

// Album by album (newest first), then loose tracks.
const allTracks = computed(() => {
  const a = artist.value
  if (!a) return []
  const inAlbums = a.albums.flatMap((album) => album.tracks)
  const seen = new Set(inAlbums.map((track) => track.file))
  const loose = sortItems(
    a.tracks.filter((track) => !seen.has(track.file)),
    'title'
  )
  return [...inAlbums, ...loose]
})

const context = computed(() => ({
  type: 'artist',
  title: artist.value?.name,
  cover: artist.value?.cover,
  route: { name: 'Artist', query: { name: artist.value?.name } },
}))

const facts = computed(() => {
  const a = artist.value
  const { hours, minutes } = splitLength(a.duration)
  return [
    a.albums.length ? t('common.albums', { count: a.albums.length }) : '',
    t('common.tracks', { count: a.tracks.length }),
    hours
      ? t('common.lengthHours', { hours, minutes })
      : t('common.lengthMinutes', { minutes }),
  ]
    .filter(Boolean)
    .join(' · ')
})

// Discography / tracks / related artists / bio, tab-switched the same
// way as LibraryView/QueueView/MonitorView - the active one lives in the
// route's own query string, so it's bookmarkable and survives a refresh.
const TAB_IDS = ['albums', 'tracks', 'topsongs', 'related', 'bio']
const tab = computed(() => {
  const requested = String(route.query.tab || '')
  if (TAB_IDS.includes(requested)) return requested
  return artist.value?.albums.length ? 'albums' : 'tracks'
})
const tabs = computed(() => {
  const a = artist.value
  if (!a) return []
  const list = []
  if (a.albums.length) {
    list.push({
      id: 'albums',
      label: t('library.albums'),
      count: a.albums.length,
      to: { name: 'Artist', query: { name: a.name, tab: 'albums' } },
    })
  }
  list.push({
    id: 'tracks',
    label: t('library.tracks'),
    count: allTracks.value.length,
    to: { name: 'Artist', query: { name: a.name, tab: 'tracks' } },
  })
  // Only for an artist we know on Spotify: their top songs come from it.
  if (spotifyId.value) {
    list.push({
      id: 'topsongs',
      label: t('link.topSongs'),
      // Unknown until the tab has been opened once.
      count: topSongsData.value?.songs.length,
      to: { name: 'Artist', query: { name: a.name, tab: 'topsongs' } },
    })
  }
  if (profile.value.related_artists.length) {
    list.push({
      id: 'related',
      label: t('artist.relatedArtists'),
      count: profile.value.related_artists.length,
      to: { name: 'Artist', query: { name: a.name, tab: 'related' } },
    })
  }
  list.push({
    id: 'bio',
    label: t('artistBio.title'),
    to: { name: 'Artist', query: { name: a.name, tab: 'bio' } },
  })
  return list
})

const isThisPlaying = computed(
  () =>
    player.isPlaying.value &&
    player.context.value?.type === 'artist' &&
    player.context.value?.title === artist.value?.name
)

function togglePlay() {
  if (isThisPlaying.value) player.pause()
  else actions.play(allTracks.value, 0, context.value)
}

function playAlbum(album) {
  actions.play(album.tracks, 0, {
    type: 'album',
    title: album.title,
    subtitle: album.artist,
    cover: album.cover,
    route: {
      name: 'Album',
      query: { artist: album.artist, title: album.title },
    },
  })
}

// ── Artist photo / banner (manual picker, always available here - the
// download_cover_art_artist(_banner) settings only gate the automatic
// first-visit save done by ensure, see downtify/artist_profile.py) ─────
const trackFiles = computed(() =>
  allTracks.value.map((track) => track.file).filter(Boolean)
)
const artPhotoUrl = ref('')
const artBannerUrl = ref('')
// Whether refreshArt has answered for this artist - until it has, they
// might still turn out to have a saved photo, so the proxy isn't asked.
const artLoaded = ref(false)

// The round photo: the artist's saved one; without one, the display-only
// photo from the backend's proxy (never saved), with what the page showed
// before - a track's cover - behind it for an artist the proxy has none
// for. `hasPhoto` below still means a *saved* photo.
const heroPhoto = computed(() => {
  const cover = artist.value?.cover || ''
  if (artPhotoUrl.value) return { cover: artPhotoUrl.value, fallback: '' }
  if (!artLoaded.value || !artist.value?.name) {
    return { cover, fallback: '' }
  }
  return {
    cover: proxiedArtistPhotoUrl(artist.value.name),
    fallback: cover,
  }
})

async function refreshArt() {
  if (!artist.value?.name) {
    artPhotoUrl.value = ''
    artBannerUrl.value = ''
    return
  }
  try {
    const res = await API.getArtistArt(artist.value.name)
    // The saved file keeps the same URL across re-saves (named after the
    // artist, see downtify/artist_profile.py), so a re-upload never changes
    // the <img> src on its own - its version, which does change, goes in.
    artPhotoUrl.value = versionedArtUrl(
      res.data?.photo_url,
      res.data?.photo_version
    )
    artBannerUrl.value = versionedArtUrl(
      res.data?.banner_url,
      res.data?.banner_version
    )
  } catch {
    artPhotoUrl.value = ''
    artBannerUrl.value = ''
  }
  artLoaded.value = true
}

watch(
  () => artist.value?.name,
  () => {
    artLoaded.value = false
    refreshArt()
  },
  { immediate: true }
)

const artModalOpen = ref(false)
const artModalInitialTab = ref('banner')

function openArtModal(tab) {
  artModalInitialTab.value = tab
  artModalOpen.value = true
}

// ── Artist profile (bio, origin, social links, related artists) - bio
// is fetched from Apple Music/Deezer on demand only, never automatically
function blankProfile() {
  return {
    bio: '',
    origin: '',
    born_or_formed: '',
    genre: '',
    is_group: null,
    banner_bg_color: '',
    platforms_id: {},
    social: {
      twitter: '',
      facebook: '',
      website: '',
      instagram: '',
      youtube: '',
    },
    related_artists: [],
    current_cover: '',
    current_cover_banner: '',
  }
}
const profile = ref(blankProfile())
// False until the first ensure of an artist has answered: the Spotify id,
// and with it the Top songs tab, only exists after that.
const profileReady = ref(false)
const spotifyId = computed(() =>
  String(profile.value.platforms_id?.spotify || '')
)

// The saved bio is plain text (see artist_profile._format_bio_text): a
// blank line separates paragraphs, anything within one stays a line break.
const bioParagraphs = computed(() =>
  (profile.value.bio || '')
    .split(/\n\s*\n/)
    .map((paragraph) => paragraph.trim())
    .filter(Boolean)
)

// origin/born_or_formed only ever come from Apple Music (see
// downtify/apple_music.py) and aren't translated text, so they're shown
// as a plain facts line above the bio itself.
const bioFacts = computed(() =>
  [
    profile.value.born_or_formed
      ? t('artistBio.formed', { year: profile.value.born_or_formed })
      : '',
    profile.value.origin,
  ]
    .filter(Boolean)
    .join(' — ')
)

// Names only (see downtify/deezer.py's relatedArtist query) - links to
// the artist page when they're already in this library, otherwise to a
// search for the name instead of a dead link.
//
// A related artist's own saved profile photo (Metadata/ArtistImage/,
// see artist_profile.py) isn't part of the library model itself - same
// bulk lookup LibraryView's artist tiles use, fetched once the Related
// tab is actually viewed, so a picked photo shows up here too instead of
// always falling back to a track's cover.
const relatedArtistPhotos = ref({})
watch(
  () => [tab.value, profile.value.related_artists],
  async ([currentTab, names]) => {
    if (currentTab !== 'related' || !names?.length) return
    try {
      const res = await API.getArtistArtBulk(names)
      relatedArtistPhotos.value = res.data || {}
    } catch {
      relatedArtistPhotos.value = {}
    }
  },
  { immediate: true }
)

const relatedArtistItems = computed(() =>
  profile.value.related_artists.map((name) => {
    const found = library.findArtist(name)
    return {
      to: found
        ? { name: 'Artist', query: { name } }
        : { name: 'Search', params: { query: name } },
      title: name,
      subtitle: found
        ? [
            found.albums.length
              ? t('common.albums', { count: found.albums.length })
              : '',
            t('common.tracks', { count: found.tracks.length }),
          ]
            .filter(Boolean)
            .join(' · ')
        : '',
      // Artists we don't own get a display-only photo from the backend's
      // proxy (never saved); a saved photo, then a library cover, win.
      cover:
        versionedArtUrl(
          relatedArtistPhotos.value[name]?.photo_url,
          relatedArtistPhotos.value[name]?.photo_version
        ) ||
        found?.cover ||
        proxiedArtistPhotoUrl(name),
      name,
      icon: 'user',
      round: true,
    }
  })
)

async function refreshProfile() {
  if (!artist.value?.name) {
    profile.value = blankProfile()
    return
  }
  try {
    // Seeds a brand-new artist's profile on their very first visit - a
    // cheap no-op every time after, once a profile file exists at all.
    const res = await API.ensureArtistProfile(
      artist.value.name,
      locale.value,
      trackFiles.value
    )
    profile.value = res.data || blankProfile()
  } catch {
    profile.value = blankProfile()
  }
}

// refreshArt above runs alongside this and usually answers before the
// ensure has finished saving a brand-new artist's photo/banner, so the art
// is asked for again once it's done - otherwise it'd only show up after a
// reload.
async function seedProfile() {
  profileReady.value = false
  await refreshProfile()
  profileReady.value = true
  await refreshArt()
}

watch(() => artist.value?.name, seedProfile, { immediate: true })

// ── Top songs tab: the artist's first five Spotify top songs, read from
// the file the backend keeps per artist (see the profile_top_songs_* functions in downtify/artist_profile.py).
// Asked for as soon as the artist's Spotify id is known - not only when
// the tab is opened - so the tab's count shows up on its own once the
// backend has the songs, and the list is ready by the time it's clicked.
// A file a week old comes back marked `stale` while the backend refreshes
// it, so it's asked for again until the fresh one arrives. ─────────────────
const topSongsData = ref(null)
const topSongsLoading = ref(false)
const topSongsError = ref('')
// Which artist + Spotify id the data belongs to, and a counter so a slow
// answer for an artist left behind can't overwrite the current one.
let topSongsKey = ''
let topSongsRun = 0
let topSongsTimer = null
// How long, and how many times, to wait for a stale file's refresh.
const TOP_SONGS_POLL_MS = 4000
const TOP_SONGS_POLL_MAX = 8

function stopTopSongsPoll() {
  clearTimeout(topSongsTimer)
  topSongsTimer = null
}

// Swap in the refreshed list in place: rows are keyed by song, so one that
// is downloading or playing keeps its state.
function pollTopSongs(run, name, attempt = 0) {
  stopTopSongsPoll()
  if (attempt >= TOP_SONGS_POLL_MAX) return
  topSongsTimer = setTimeout(async () => {
    if (run !== topSongsRun) return
    try {
      const res = await API.artistTopSongsSaved(name)
      if (run !== topSongsRun) return
      topSongsData.value = res.data
      if (res.data?.stale) pollTopSongs(run, name, attempt + 1)
    } catch {
      // Keep showing what's there; the next visit asks again.
    }
  }, TOP_SONGS_POLL_MS)
}

async function loadTopSongs(force = false) {
  const name = artist.value?.name
  if (!name || !spotifyId.value) return
  const key = `${name}|${spotifyId.value}`
  if (!force && key === topSongsKey) return
  topSongsKey = key
  const run = ++topSongsRun
  stopTopSongsPoll()
  topSongsLoading.value = true
  topSongsError.value = ''
  topSongsData.value = null
  try {
    const res = await API.artistTopSongsSaved(name)
    if (run !== topSongsRun) return
    topSongsData.value = res.data
    if (res.data?.stale) pollTopSongs(run, name)
  } catch (err) {
    if (run !== topSongsRun) return
    topSongsError.value = err?.response?.data?.detail || err?.message || ''
    // Forget the key so opening the tab again tries again.
    topSongsKey = ''
  } finally {
    if (run === topSongsRun) topSongsLoading.value = false
  }
}

// Another artist: drop the previous one's list (and its count in the tab).
watch(
  () => artist.value?.name,
  () => {
    stopTopSongsPoll()
    topSongsKey = ''
    topSongsRun++
    topSongsData.value = null
    topSongsError.value = ''
    topSongsLoading.value = false
  }
)
watch([spotifyId, () => artist.value?.name], () => loadTopSongs(), {
  immediate: true,
})
// Opening the tab retries after a failure (the key is forgotten then); it
// does nothing when the songs are already loaded.
watch(tab, () => {
  if (tab.value === 'topsongs') loadTopSongs()
})
onBeforeUnmount(stopTopSongsPoll)

// ArtistArtModal's single "saved" event covers photo, banner, bio and
// social edits alike - simplest to just refresh both after any of them.
function onArtSaved() {
  refreshArt()
  refreshProfile()
}
</script>
