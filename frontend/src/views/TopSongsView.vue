<template>
  <div>
    <!-- Loading -->
    <div
      v-if="loading"
      class="mx-auto flex max-w-[1680px] flex-col gap-8 px-4 pt-10 sm:px-6 md:flex-row md:items-end lg:px-10"
    >
      <UiSkeleton
        class="size-48 self-center !rounded-full sm:size-56 md:self-auto"
      />
      <div class="flex flex-1 flex-col gap-3">
        <UiSkeleton class="h-3 w-32" />
        <UiSkeleton class="h-12 w-2/3" />
        <p class="flex items-center gap-2 text-sm text-muted">
          <span
            class="size-4 animate-spin rounded-full border-2 border-accent border-r-transparent"
          />
          {{ t('link.resolving') }}
        </p>
      </div>
    </div>

    <div
      v-else-if="error"
      class="mx-auto max-w-[1680px] px-4 pt-10 sm:px-6 lg:px-10"
    >
      <UiEmpty icon="alert" :title="t('link.failed')" :body="error">
        <UiButton icon="refresh" @click="load">{{
          t('common.retry')
        }}</UiButton>
      </UiEmpty>
    </div>

    <div v-else-if="artist" class="animate-rise">
      <CollectionHero
        :title="t('link.topSongsOf', { artist: artist.name })"
        :kicker="kicker"
        :cover="artist.cover_url"
        :name="artist.name"
        icon="user"
        round
      >
        <template #subtitle>
          <span v-if="artist.songs.length" class="tabular">
            {{
              [t('common.tracks', { count: artist.songs.length }), lengthLabel]
                .filter(Boolean)
                .join(' · ')
            }}
          </span>
        </template>
        <template #actions>
          <template v-if="artist.songs.length">
            <UiButton
              v-if="topSongs.newSongs.length"
              variant="primary"
              size="lg"
              icon="download"
              :loading="topSongs.submitting"
              @click="topSongs.download(topSongs.newSongs)"
            >
              {{
                topSongs.newSongs.length === artist.songs.length
                  ? t('link.downloadAll', { count: topSongs.newSongs.length })
                  : t('link.downloadNew', { count: topSongs.newSongs.length })
              }}
            </UiButton>
            <span
              v-else
              class="inline-flex h-12 items-center gap-2 rounded-control bg-accent/12 px-5 text-[15px] font-semibold text-accent"
            >
              <AppIcon name="check-circle" :size="18" />{{
                t('link.allInLibrary')
              }}
            </span>
            <UiButton
              v-if="
                topSongs.newSongs.length &&
                topSongs.newSongs.length < artist.songs.length
              "
              variant="ghost"
              size="lg"
              @click="topSongs.download(artist.songs)"
            >
              {{ t('link.redownloadAll') }}
            </UiButton>
          </template>
          <UiButton variant="plain" size="lg" icon="arrow-up-right" :href="url">
            <span class="max-sm:sr-only">{{ sourceLabel }}</span>
          </UiButton>
        </template>
      </CollectionHero>

      <div
        class="mx-auto flex max-w-[1680px] flex-col gap-6 px-4 sm:px-6 lg:px-10"
      >
        <TopSongsPanel v-if="artist.songs.length" :state="topSongs" />

        <UiEmpty v-else icon="music" :title="t('link.topSongsEmpty')" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import AppIcon from '/src/components/ui/AppIcon.vue'
import UiButton from '/src/components/ui/UiButton.vue'
import UiEmpty from '/src/components/ui/UiEmpty.vue'
import UiSkeleton from '/src/components/ui/UiSkeleton.vue'
import CollectionHero from '/src/components/library/CollectionHero.vue'
import TopSongsPanel from '/src/components/library/TopSongsPanel.vue'
import API from '/src/model/api'
import { useTopSongs } from '/src/model/topSongs'
import { classifyInput } from '/src/lib/input'
import { splitLength } from '/src/lib/format'
import { useI18n } from '/src/i18n'

const { t } = useI18n()
const route = useRoute()

const artist = ref(null)
const loading = ref(false)
const error = ref('')
// The list, its selection and its downloads - shared with the artist
// page's Top songs tab (see model/topSongs.js).
const topSongs = useTopSongs(artist)

const url = computed(() => String(route.query.url || ''))
const kind = computed(() => classifyInput(url.value))

async function load() {
  if (!url.value) return
  loading.value = true
  error.value = ''
  artist.value = null
  topSongs.reset()
  try {
    const res = await API.artistTopSongs(url.value)
    artist.value = res.data
    topSongs.reset()
  } catch (err) {
    error.value = err?.response?.data?.detail || err?.message || ''
  } finally {
    loading.value = false
  }
}

watch(url, load, { immediate: true })

const sourceLabel = computed(() =>
  kind.value.source === 'spotify'
    ? t('link.openSpotify')
    : t('link.openYoutube')
)

const kicker = computed(() => {
  const source = kind.value.source === 'spotify' ? 'Spotify' : 'YouTube Music'
  return `${source} · ${t('link.topSongs')}`
})

const lengthLabel = computed(() => {
  const total = (artist.value?.songs || []).reduce(
    (sum, song) => sum + (song.duration || 0),
    0
  )
  if (!total) return ''
  const { hours, minutes } = splitLength(total)
  return hours
    ? t('common.lengthHours', { hours, minutes })
    : t('common.lengthMinutes', { minutes })
})
</script>
