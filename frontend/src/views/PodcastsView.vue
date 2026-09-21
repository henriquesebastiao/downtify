<template>
  <div
    class="mx-auto flex max-w-[1680px] flex-col gap-8 px-4 pt-6 sm:px-6 md:pt-8 lg:px-10"
  >
    <PageHeader
      :title="t('podcasts.title')"
      :subtitle="t('podcasts.subtitle')"
    />

    <UiPanel
      :title="t('podcasts.addTitle')"
      :description="t('podcasts.addBody')"
    >
      <form
        class="flex flex-col gap-2 sm:flex-row sm:items-center"
        @submit.prevent="onFind"
      >
        <label
          class="flex h-11 min-w-0 flex-1 items-center gap-3 rounded-control border border-line-2 bg-surface px-3"
        >
          <AppIcon name="search" :size="18" class="text-faint" />
          <span class="sr-only">{{ t('podcasts.findPlaceholder') }}</span>
          <input
            v-model="query"
            type="text"
            :placeholder="t('podcasts.findPlaceholder')"
            class="h-full min-w-0 flex-1 bg-transparent text-sm outline-none placeholder:text-faint"
          />
        </label>
        <UiButton
          type="submit"
          variant="primary"
          icon="search"
          :loading="finding"
          :disabled="!query.trim()"
        >
          {{ t('podcasts.find') }}
        </UiButton>
      </form>

      <p v-if="findError" class="mt-3 text-[13px] text-danger" role="alert">
        {{ findError }}
      </p>

      <ul
        v-if="searchResults.length"
        class="mt-4 flex flex-col gap-1 border-t border-line pt-4"
      >
        <li v-for="result in searchResults" :key="result.feed_url">
          <button
            type="button"
            class="flex w-full items-center gap-3 rounded-[10px] px-2 py-2 text-left hover:bg-surface-2"
            @click="pick(result.feed_url)"
          >
            <CoverArt
              :src="result.artwork_url"
              :name="result.name"
              icon="mic"
              rounded="rounded-[8px]"
              :letter-size="14"
              class="size-11"
            />
            <span class="min-w-0 flex-1">
              <span class="block truncate text-sm font-semibold">{{
                result.name
              }}</span>
              <span class="block truncate text-[13px] text-muted">{{
                result.author
              }}</span>
            </span>
            <AppIcon name="chevron-right" :size="18" class="text-faint" />
          </button>
        </li>
      </ul>

      <div
        v-if="preview"
        class="mt-4 flex flex-col gap-4 border-t border-line pt-4"
      >
        <div class="flex items-center gap-3">
          <CoverArt
            :src="preview.show.artwork_url"
            :name="preview.show.name"
            icon="mic"
            rounded="rounded-[10px]"
            :letter-size="18"
            class="size-14"
          />
          <div class="min-w-0 flex-1">
            <p class="truncate text-base font-semibold">
              {{ preview.show.name }}
            </p>
            <p class="truncate text-[13px] text-muted">
              {{ preview.show.author
              }}{{ preview.show.author && preview.episodes.length ? ' · ' : ''
              }}{{
                preview.episodes.length
                  ? t('common.tracks', { count: preview.episodes.length })
                  : ''
              }}
            </p>
          </div>
        </div>

        <p
          v-if="alreadySubscribed"
          class="flex items-center gap-2 text-[13px] text-muted"
        >
          <AppIcon name="check-circle" :size="16" class="text-accent" />
          {{ t('podcasts.alreadySubscribed') }}
        </p>
        <template v-else>
          <div class="flex flex-wrap items-center gap-2">
            <UiSelect
              v-model="retention"
              :options="retentionOptions"
              :label="t('podcasts.keep')"
            />
            <UiSelect
              v-model="interval"
              :options="intervalChoices"
              :label="t('monitor.interval')"
              icon="clock"
            />
          </div>
          <div class="flex gap-2">
            <UiButton
              variant="primary"
              icon="mic"
              :loading="subscribing"
              @click="onSubscribe"
            >
              {{ t('podcasts.subscribe') }}
            </UiButton>
            <UiButton variant="ghost" @click="preview = null">
              {{ t('common.cancel') }}
            </UiButton>
          </div>
        </template>
      </div>
    </UiPanel>

    <div
      v-if="loading && !podcasts.shows.value.length"
      class="flex flex-col gap-2"
    >
      <UiSkeleton v-for="n in 3" :key="n" class="h-[72px] !rounded-[12px]" />
    </div>

    <UiEmpty
      v-else-if="!podcasts.shows.value.length"
      icon="mic"
      :title="t('podcasts.emptyTitle')"
      :body="t('podcasts.emptyBody')"
    />

    <div
      v-else
      class="grid grid-cols-2 gap-x-4 gap-y-6 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6"
    >
      <MediaTile
        v-for="show in podcasts.shows.value"
        :key="show.id"
        :to="{ name: 'PodcastShow', query: { id: show.id } }"
        :title="show.name"
        :subtitle="showSubtitle(show)"
        :name="show.name"
        :cover="show.artwork_url"
        icon="mic"
        :playable="show.downloaded_count > 0"
        @play="playShow(show)"
      />
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import AppIcon from '/src/components/ui/AppIcon.vue'
import CoverArt from '/src/components/ui/CoverArt.vue'
import UiButton from '/src/components/ui/UiButton.vue'
import UiEmpty from '/src/components/ui/UiEmpty.vue'
import UiPanel from '/src/components/ui/UiPanel.vue'
import UiSelect from '/src/components/ui/UiSelect.vue'
import UiSkeleton from '/src/components/ui/UiSkeleton.vue'
import PageHeader from '/src/components/library/PageHeader.vue'
import MediaTile from '/src/components/library/MediaTile.vue'
import { intervalOptions } from '/src/components/monitor/intervals'
import API from '/src/model/api'
import { usePodcasts } from '/src/model/podcasts'
import { usePlayer } from '/src/model/player'
import { useUi } from '/src/model/ui'
import { episodeToTrack, sortEpisodesByDate } from '/src/lib/podcasts'
import { useI18n } from '/src/i18n'

const { t } = useI18n()
const router = useRouter()
const podcasts = usePodcasts()
const player = usePlayer()
const ui = useUi()

const loading = ref(false)
const query = ref('')
const finding = ref(false)
const findError = ref('')
const searchResults = ref([])
const preview = ref(null)
const alreadySubscribed = ref(false)
const retention = ref(0)
const interval = ref(360)
const subscribing = ref(false)

const retentionOptions = [
  { value: 0, label: t('podcasts.retentionAll') },
  { value: 1, label: t('podcasts.retentionCount', { count: 1 }) },
  { value: 3, label: t('podcasts.retentionCount', { count: 3 }) },
  { value: 5, label: t('podcasts.retentionCount', { count: 5 }) },
  { value: 10, label: t('podcasts.retentionCount', { count: 10 }) },
  { value: 25, label: t('podcasts.retentionCount', { count: 25 }) },
]
const intervalChoices = intervalOptions(t, interval.value)

function showSubtitle(show) {
  return show.author || t('common.tracks', { count: show.episode_count })
}

function looksLikeUrl(text) {
  return /^https?:\/\//i.test(text.trim())
}

async function onFind() {
  const text = query.value.trim()
  if (!text) return
  findError.value = ''
  searchResults.value = []
  preview.value = null
  finding.value = true
  try {
    if (looksLikeUrl(text)) {
      await resolve(text)
    } else {
      const res = await API.searchPodcasts(text)
      searchResults.value = res.data?.results || []
      if (!searchResults.value.length) findError.value = t('podcasts.noResults')
    }
  } catch (err) {
    findError.value = err?.response?.data?.detail || t('podcasts.findFailed')
  } finally {
    finding.value = false
  }
}

async function pick(feedUrl) {
  findError.value = ''
  finding.value = true
  try {
    await resolve(feedUrl)
  } catch (err) {
    findError.value = err?.response?.data?.detail || t('podcasts.findFailed')
  } finally {
    finding.value = false
  }
}

async function resolve(url) {
  const res = await API.resolvePodcast(url)
  preview.value = res.data
  alreadySubscribed.value = Boolean(res.data?.already_subscribed)
  searchResults.value = []
}

async function onSubscribe() {
  if (!preview.value) return
  subscribing.value = true
  try {
    const show = await podcasts.subscribe({
      feed_url: preview.value.show.feed_url,
      name: preview.value.show.name,
      author: preview.value.show.author,
      description: preview.value.show.description,
      artwork_url: preview.value.show.artwork_url,
      source_url: preview.value.show.source_url,
      retention: retention.value,
      interval_minutes: interval.value,
    })
    ui.toast(t('podcasts.subscribed', { name: show.name }), { kind: 'success' })
    query.value = ''
    preview.value = null
    router.push({ name: 'PodcastShow', query: { id: show.id } })
  } catch (err) {
    findError.value = err?.response?.data?.detail || t('podcasts.findFailed')
  } finally {
    subscribing.value = false
  }
}

async function playShow(show) {
  try {
    const res = await API.listPodcastEpisodes(show.id)
    const downloaded = (res.data?.episodes || []).filter((e) => e.filename)
    const tracks = sortEpisodesByDate(downloaded).map((e) =>
      episodeToTrack(e, show)
    )
    if (!tracks.length) return
    player.playList(tracks, {
      context: {
        type: 'podcast',
        title: show.name,
        route: { name: 'PodcastShow', query: { id: show.id } },
      },
    })
  } catch {
    ui.toast(t('toast.actionFailed'), { kind: 'error' })
  }
}

onMounted(async () => {
  loading.value = true
  try {
    await podcasts.load()
  } finally {
    loading.value = false
  }
})
</script>
