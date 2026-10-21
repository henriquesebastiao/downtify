<template>
  <div>
    <DetailState
      :loaded="library.loaded.value"
      :found="!!playlist"
      icon="playlist"
      :missing="t('playlists.notFound')"
    >
      <CollectionHero
        :title="playlist.title"
        :kicker="t('playlists.kicker')"
        :covers="playlist.covers"
        :cover="playlist.cover"
        :name="playlist.title"
        :icon="playlist.liked ? 'heart' : 'playlist'"
        :symbol="playlist.liked"
      >
        <template #subtitle>
          <span
            v-if="batch"
            class="mr-1 inline-flex translate-y-0.5 items-center gap-1.5 font-semibold text-spotify"
          >
            <AppIcon name="spotify" :size="14" />Spotify
          </span>
          {{ facts }}
          <template v-if="sharingLine"> · {{ sharingLine }}</template>
        </template>
        <template #actions>
          <PlaylistStatus
            v-if="batch?.expected_count"
            :playlist="playlist"
            class="w-full max-w-sm basis-full"
          />
          <PlayButton
            :label="t('actions.playItem', { name: playlist.title })"
            :playing="isThisPlaying"
            :disabled="!playlist.tracks.length"
            @click="togglePlay"
          />
          <UiIconButton
            icon="shuffle"
            :label="t('actions.shuffle')"
            size="lg"
            round
            :disabled="!playlist.tracks.length"
            @click="playlistActions.play(playlist, { shuffled: true })"
          />
          <UiButton
            v-if="batch?.missing_count"
            variant="primary"
            icon="download"
            @click="playlistActions.downloadMissing(playlist)"
          >
            {{ t('playlists.downloadMissing', { count: batch.missing_count }) }}
          </UiButton>
          <UiButton
            v-if="playlist.manual && playlist.mine"
            variant="secondary"
            icon="plus"
            @click="playlistActions.openAddSongs(playlist)"
          >
            {{ t('playlists.addSongs') }}
          </UiButton>
          <UiButton
            v-if="playlist.manual && playlist.mine"
            variant="ghost"
            icon="pencil"
            @click="playlistActions.rename(playlist)"
          >
            {{ t('playlists.rename') }}
          </UiButton>
          <UiButton
            v-if="!playlist.mine && playlist.visibility === 'public'"
            :variant="playlist.followed ? 'secondary' : 'primary'"
            :icon="playlist.followed ? 'heart' : 'heart-outline'"
            @click="playlistActions.setFollowing(playlist, !playlist.followed)"
          >
            {{
              playlist.followed ? t('sharing.following') : t('sharing.follow')
            }}
          </UiButton>
          <UiButton
            v-if="!playlist.mine"
            variant="secondary"
            icon="copy"
            @click="playlistActions.copy(playlist)"
          >
            {{ t('sharing.saveCopy') }}
          </UiButton>
          <UiButton
            v-if="canShare"
            variant="ghost"
            :icon="
              playlist.visibility === 'public'
                ? 'globe'
                : playlist.visibility === 'shared'
                  ? 'users'
                  : 'share'
            "
            @click="playlistActions.openShare(playlist)"
          >
            {{ t('sharing.share') }}
          </UiButton>
          <UiButton
            v-if="canDetach"
            variant="ghost"
            icon="link"
            @click="playlistActions.detach(playlist)"
          >
            {{ t('sharing.detach') }}
          </UiButton>
          <UiButton
            v-if="playlist.tracks.length"
            variant="ghost"
            icon="zip"
            class="max-sm:hidden"
            @click="actions.downloadZip(playlist.tracks)"
          >
            {{ t('library.downloadZip') }}
          </UiButton>
          <UiMenu :items="menu" :label="t('common.more')" size="lg" />
        </template>
      </CollectionHero>

      <div
        class="mx-auto flex max-w-[1680px] flex-col gap-10 px-4 sm:px-6 lg:px-10"
      >
        <div v-if="playlist.tracks.length" class="flex flex-col gap-3">
          <div class="flex justify-end">
            <TrackSortSelect v-model="trackSort" playlist-order />
          </div>
          <TrackList
            v-model:sort="trackSort"
            :tracks="sortedTracks"
            :context="playlistActions.contextFor(playlist)"
          />
        </div>
        <UiEmpty
          v-else
          icon="download"
          :title="t('playlists.nothingYet')"
          :body="
            playlist.manual
              ? t('playlists.nothingYetManualHint')
              : t('playlists.nothingYetHint')
          "
        />

        <UiPanel
          v-if="batch?.missing_count"
          :title="t('playlists.missingTitle', { count: batch.missing_count })"
          :description="t('playlists.missingHint')"
        >
          <template #actions>
            <UiButton
              v-if="!missing.length"
              variant="ghost"
              size="sm"
              :loading="loadingMissing"
              @click="loadMissing"
            >
              {{ t('playlists.showMissing') }}
            </UiButton>
          </template>
          <ul v-if="missing.length" class="-mx-2 flex flex-col">
            <li
              v-for="song in missing"
              :key="song.song_id"
              class="flex h-14 items-center gap-3 rounded-[10px] px-2 hover:bg-surface-2"
            >
              <CoverArt
                :src="song.cover_url"
                :name="song.album_name || song.name"
                rounded="rounded-[6px]"
                :letter-size="12"
                class="size-10"
              />
              <div class="min-w-0 flex-1">
                <p class="truncate text-sm font-semibold">{{ song.name }}</p>
                <p class="truncate text-[13px] text-muted">
                  {{ (song.artists || []).join(', ') || song.artist }}
                </p>
              </div>
              <DownloadState :song="song" />
            </li>
          </ul>
        </UiPanel>
      </div>
    </DetailState>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useLocalStorage } from '@vueuse/core'
import { useRoute, useRouter } from 'vue-router'
import AppIcon from '/src/components/ui/AppIcon.vue'
import CoverArt from '/src/components/ui/CoverArt.vue'
import UiButton from '/src/components/ui/UiButton.vue'
import UiEmpty from '/src/components/ui/UiEmpty.vue'
import UiIconButton from '/src/components/ui/UiIconButton.vue'
import UiMenu from '/src/components/ui/UiMenu.vue'
import UiPanel from '/src/components/ui/UiPanel.vue'
import CollectionHero from '/src/components/library/CollectionHero.vue'
import DetailState from '/src/components/library/DetailState.vue'
import PlayButton from '/src/components/library/PlayButton.vue'
import PlaylistStatus from '/src/components/library/PlaylistStatus.vue'
import TrackList from '/src/components/library/TrackList.vue'
import TrackSortSelect from '/src/components/library/TrackSortSelect.vue'
import DownloadState from '/src/components/search/DownloadState.vue'
import API from '/src/model/api'
import { useAccount } from '/src/model/account'
import { useLibrary } from '/src/model/library'
import { usePlayer } from '/src/model/player'
import { usePlaylistActions } from '/src/model/playlistActions'
import { useTrackActions } from '/src/model/trackActions'
import { sortTracks } from '/src/lib/library'
import { splitLength } from '/src/lib/format'
import { useI18n } from '/src/i18n'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const library = useLibrary()
const player = usePlayer()
const actions = useTrackActions()
const playlistActions = usePlaylistActions()
const account = useAccount()

const playlist = computed(() =>
  library.findPlaylist(String(route.query.name || ''))
)
const batch = computed(() => playlist.value?.batch || null)

// How the songs are ordered: the playlist's own order until picked
// otherwise (remembered for every playlist).
const trackSort = useLocalStorage('downtify-playlist-track-sort', {
  key: 'order',
  dir: 'asc',
})
const sortedTracks = computed(() =>
  sortTracks(playlist.value?.tracks || [], trackSort.value)
)

const canShare = computed(
  () =>
    playlist.value?.mine &&
    !playlist.value.liked &&
    account.playlistSharing.value
)
// An imported playlist can be turned into an editable one.
const canDetach = computed(
  () =>
    playlist.value?.mine &&
    !playlist.value.liked &&
    !playlist.value.manual &&
    playlist.value.fileCount > 0
)

// "by ana", or how the user's own playlist is shared.
const sharingLine = computed(() => {
  const p = playlist.value
  if (!p || p.liked) return ''
  if (!p.mine) return t('sharing.by', { owner: p.owner })
  if (p.visibility === 'public') return t('sharing.public')
  if (p.visibility === 'shared') {
    return t('sharing.sharedWithCount', { count: p.sharedWith.length })
  }
  return ''
})

const facts = computed(() => {
  const p = playlist.value
  const { hours, minutes } = splitLength(p.duration)
  return [
    t('common.tracks', { count: p.tracks.length || p.fileCount || 0 }),
    p.duration
      ? hours
        ? t('common.lengthHours', { hours, minutes })
        : t('common.lengthMinutes', { minutes })
      : '',
  ]
    .filter(Boolean)
    .join(' · ')
})

const isThisPlaying = computed(
  () =>
    player.isPlaying.value &&
    player.context.value?.type === 'playlist' &&
    player.context.value?.title === playlist.value?.title
)

function togglePlay() {
  if (isThisPlaying.value) player.pause()
  else playlistActions.play(playlist.value, { tracks: sortedTracks.value })
}

const menu = computed(() =>
  playlistActions.menuFor(playlist.value).map((item) =>
    item.icon === 'trash'
      ? {
          ...item,
          action: async () => {
            if (await playlistActions.remove(playlist.value)) {
              router.push({ name: 'Library', params: { tab: 'playlists' } })
            }
          },
        }
      : item
  )
)

const missing = ref([])
const loadingMissing = ref(false)

async function loadMissing() {
  if (!batch.value) return
  loadingMissing.value = true
  try {
    const res = await API.getPlaylistBatchDetails(
      batch.value.spotify_playlist_id
    )
    missing.value = (res.data?.missing_tracks || []).map((song) => ({
      ...song,
      downtify_playlist_url: batch.value.playlist_url,
    }))
  } finally {
    loadingMissing.value = false
  }
}

watch(
  () => String(route.query.name || ''),
  async (name) => {
    missing.value = []
    await library.loadPlaylistTracks(name)
    // Opening a playlist shared with the user clears its "new" marker.
    playlistActions.markSeen(library.findPlaylist(name))
  },
  { immediate: true }
)

// The liked songs playlist goes when the last heart is removed: leave the
// page rather than show "not found" for something that was just here.
watch(playlist, (now, before) => {
  if (before?.liked && !now && library.loaded.value) {
    router.replace({ name: 'Library', params: { tab: 'playlists' } })
  }
})
</script>
