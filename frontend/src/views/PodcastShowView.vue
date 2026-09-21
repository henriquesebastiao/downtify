<template>
  <div>
    <DetailState
      :loaded="loaded"
      :found="!!show"
      icon="mic"
      :missing="t('podcasts.notFound')"
    >
      <CollectionHero
        :title="show.name"
        :kicker="t('podcasts.kicker')"
        :cover="show.artwork_url"
        :name="show.name"
        icon="mic"
      >
        <template #subtitle>
          {{ show.author }}{{ show.author ? ' · ' : ''
          }}{{ t('common.tracks', { count: episodes.length }) }}
        </template>
        <template #actions>
          <PlayButton
            :label="t('actions.playItem', { name: show.name })"
            :playing="isThisPlaying"
            :disabled="!downloadedEpisodes.length"
            @click="togglePlay"
          />
          <UiSelect
            v-model="retention"
            :options="retentionOptions"
            :label="t('podcasts.keep')"
            @update:model-value="onRetentionChange"
          />
          <UiSwitch
            :model-value="show.enabled !== false"
            :aria-label="t('monitor.colActive')"
            @update:model-value="onToggleEnabled"
          />
          <UiMenu :items="menu" :label="t('common.more')" size="lg" />
        </template>
      </CollectionHero>

      <div
        class="mx-auto flex max-w-[1680px] flex-col gap-6 px-4 sm:px-6 lg:px-10"
      >
        <p v-if="show.description" class="max-w-3xl text-pretty text-muted">
          {{ show.description }}
        </p>

        <UiEmpty
          v-if="!episodes.length"
          icon="mic"
          :title="t('podcasts.noEpisodesTitle')"
          :body="t('podcasts.noEpisodesBody')"
        />

        <ul v-else class="-mx-2 flex flex-col">
          <li
            v-for="episode in episodes"
            :key="episode.id"
            class="flex items-center gap-3 rounded-[10px] px-2 py-2.5 hover:bg-surface-2"
          >
            <button
              v-if="episode.filename"
              type="button"
              class="flex size-10 shrink-0 items-center justify-center rounded-full bg-accent text-on-accent"
              :aria-label="t('actions.playItem', { name: episode.title })"
              @click="playEpisode(episode)"
            >
              <AppIcon
                :name="
                  isThisEpisode(episode) && player.isPlaying.value
                    ? 'pause'
                    : 'play'
                "
                :size="16"
              />
            </button>
            <UiIconButton
              v-else
              icon="download"
              :label="t('podcasts.download')"
              :loading="downloading.has(episode.id)"
              @click="download(episode)"
            />

            <div class="min-w-0 flex-1">
              <p class="truncate text-sm font-semibold">
                {{ episode.title }}
              </p>
              <p
                class="flex flex-wrap items-center gap-x-2 text-[13px] text-muted"
              >
                <span v-if="episode.published_at">{{
                  timeAgo(episode.published_at, locale)
                }}</span>
                <span v-if="episode.duration_seconds">{{
                  formatDuration(episode.duration_seconds)
                }}</span>
                <span
                  v-if="episode.played"
                  class="flex items-center gap-1 text-accent"
                >
                  <AppIcon name="check" :size="12" />{{ t('podcasts.played') }}
                </span>
                <span v-else-if="hasResumePosition(episode)">
                  {{
                    t('podcasts.resumeAt', {
                      time: formatDuration(episode.position_seconds),
                    })
                  }}
                </span>
              </p>
            </div>

            <UiMenu :items="episodeMenu(episode)" :label="t('common.more')" />
          </li>
        </ul>
      </div>
    </DetailState>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppIcon from '/src/components/ui/AppIcon.vue'
import UiIconButton from '/src/components/ui/UiIconButton.vue'
import UiEmpty from '/src/components/ui/UiEmpty.vue'
import UiMenu from '/src/components/ui/UiMenu.vue'
import UiSelect from '/src/components/ui/UiSelect.vue'
import UiSwitch from '/src/components/ui/UiSwitch.vue'
import CollectionHero from '/src/components/library/CollectionHero.vue'
import DetailState from '/src/components/library/DetailState.vue'
import PlayButton from '/src/components/library/PlayButton.vue'
import API from '/src/model/api'
import { usePodcasts } from '/src/model/podcasts'
import { usePlayer } from '/src/model/player'
import { useUi } from '/src/model/ui'
import { formatDuration, timeAgo } from '/src/lib/format'
import {
  episodeToTrack,
  hasResumePosition,
  sortEpisodesByDate,
} from '/src/lib/podcasts'
import { useI18n } from '/src/i18n'

const { t, locale } = useI18n()
const route = useRoute()
const router = useRouter()
const podcasts = usePodcasts()
const player = usePlayer()
const ui = useUi()

const loaded = ref(false)
const show = ref(null)
const episodes = ref([])
const downloading = ref(new Set())
const retention = ref(0)

const showId = computed(() => String(route.query.id || ''))

const retentionOptions = [
  { value: 0, label: t('podcasts.retentionAll') },
  { value: 1, label: t('podcasts.retentionCount', { count: 1 }) },
  { value: 3, label: t('podcasts.retentionCount', { count: 3 }) },
  { value: 5, label: t('podcasts.retentionCount', { count: 5 }) },
  { value: 10, label: t('podcasts.retentionCount', { count: 10 }) },
  { value: 25, label: t('podcasts.retentionCount', { count: 25 }) },
]

const downloadedEpisodes = computed(() =>
  episodes.value.filter((e) => e.filename)
)

const isThisPlaying = computed(
  () =>
    player.isPlaying.value &&
    player.context.value?.type === 'podcast' &&
    String(player.context.value?.route?.query?.id) === showId.value
)

function isThisEpisode(episode) {
  return player.currentTrack.value?.podcastEpisodeId === episode.id
}

async function load() {
  loaded.value = false
  try {
    const res = await API.listPodcastEpisodes(showId.value)
    show.value = res.data?.show || null
    episodes.value = sortEpisodesByDate(res.data?.episodes || [])
    retention.value = show.value?.retention ?? 0
  } catch {
    show.value = null
  } finally {
    loaded.value = true
  }
}

function trackList() {
  return sortEpisodesByDate(downloadedEpisodes.value).map((e) =>
    episodeToTrack(e, show.value)
  )
}

function contextFor() {
  return {
    type: 'podcast',
    title: show.value.name,
    route: { name: 'PodcastShow', query: { id: show.value.id } },
  }
}

function togglePlay() {
  if (isThisPlaying.value) {
    player.pause()
    return
  }
  const tracks = trackList()
  if (!tracks.length) return
  player.playList(tracks, { context: contextFor() })
  seekToResume(episodes.value.find((e) => e.filename))
}

function seekToResume(episode) {
  if (episode && hasResumePosition(episode)) {
    setTimeout(() => player.seek(episode.position_seconds), 300)
  }
}

function playEpisode(episode) {
  if (isThisEpisode(episode)) {
    player.toggle()
    return
  }
  if (!episode.filename) return
  const index = downloadedEpisodes.value.findIndex((e) => e.id === episode.id)
  const tracks = sortEpisodesByDate(downloadedEpisodes.value)
    .slice(index)
    .map((e) => episodeToTrack(e, show.value))
  player.playList(tracks, { context: contextFor() })
  seekToResume(episode)
}

async function download(episode) {
  downloading.value = new Set([...downloading.value, episode.id])
  try {
    const res = await API.downloadPodcastEpisode(episode.id)
    Object.assign(episode, res.data)
  } catch {
    ui.toast(t('podcasts.downloadFailed'), { kind: 'error' })
  } finally {
    const next = new Set(downloading.value)
    next.delete(episode.id)
    downloading.value = next
  }
}

async function removeDownload(episode) {
  const ok = await ui.confirm({
    title: t('confirm.removeEpisodeTitle', { name: episode.title }),
    body: t('confirm.removeEpisodeBody'),
    confirmLabel: t('podcasts.removeDownload'),
    danger: true,
  })
  if (!ok) return
  try {
    await API.deletePodcastEpisode(episode.id)
    episode.filename = null
    episode.downloaded_at = null
    episode.dismissed = true
  } catch {
    ui.toast(t('toast.actionFailed'), { kind: 'error' })
  }
}

async function togglePlayed(episode) {
  const before = episode.played
  episode.played = !before
  try {
    await API.setPodcastPlayback(episode.id, { played: episode.played })
  } catch {
    episode.played = before
    ui.toast(t('toast.actionFailed'), { kind: 'error' })
  }
}

function episodeMenu(episode) {
  const items = []
  if (episode.filename) {
    items.push({
      label: episode.played
        ? t('podcasts.markUnplayed')
        : t('podcasts.markPlayed'),
      icon: episode.played ? 'check-circle' : 'check',
      action: () => togglePlayed(episode),
    })
    items.push({ divider: true })
    items.push({
      label: t('podcasts.removeDownload'),
      icon: 'trash',
      danger: true,
      action: () => removeDownload(episode),
    })
  } else {
    items.push({
      label: t('podcasts.download'),
      icon: 'download',
      action: () => download(episode),
    })
  }
  return items
}

async function onRetentionChange(value) {
  if (!(await podcasts.updateShow(show.value, { retention: value }))) {
    ui.toast(t('toast.actionFailed'), { kind: 'error' })
    retention.value = show.value.retention
  }
}

async function onToggleEnabled(value) {
  if (!(await podcasts.updateShow(show.value, { enabled: value }))) {
    ui.toast(t('toast.actionFailed'), { kind: 'error' })
  }
}

async function unsubscribe(keepFiles) {
  const ok = await ui.confirm({
    title: t('confirm.unsubscribeTitle', { name: show.value.name }),
    body: keepFiles
      ? t('confirm.unsubscribeKeepBody')
      : t('confirm.unsubscribeBody'),
    confirmLabel: t('podcasts.unsubscribe'),
    danger: true,
  })
  if (!ok) return
  try {
    await podcasts.unsubscribe(show.value, { keepFiles })
    router.push({ name: 'Podcasts' })
  } catch {
    ui.toast(t('toast.actionFailed'), { kind: 'error' })
  }
}

const menu = computed(() => [
  {
    label: t('podcasts.unsubscribeKeepFiles'),
    icon: 'mic',
    action: () => unsubscribe(true),
  },
  { divider: true },
  {
    label: t('podcasts.unsubscribe'),
    icon: 'trash',
    danger: true,
    action: () => unsubscribe(false),
  },
])

watch(showId, load)
onMounted(load)
</script>
