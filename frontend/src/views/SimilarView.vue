<template>
  <div
    class="mx-auto flex max-w-[1680px] flex-col gap-8 px-4 pt-6 sm:px-6 md:pt-8 lg:px-10"
  >
    <PageHeader :title="t('similar.title')" :subtitle="t('similar.subtitle')" />

    <form
      class="flex flex-col gap-2 sm:flex-row sm:items-end"
      @submit.prevent="submit"
    >
      <UiInput
        v-model.trim="artistInput"
        class="sm:flex-1"
        :label="t('similar.artist')"
        :placeholder="t('similar.artistPlaceholder')"
        autocomplete="off"
      />
      <UiInput
        v-model.trim="trackInput"
        class="sm:flex-1"
        :label="t('similar.track')"
        :placeholder="t('similar.trackPlaceholder')"
        autocomplete="off"
      />
      <UiButton
        type="submit"
        variant="primary"
        size="lg"
        icon="search"
        :loading="similar.loading.value"
        :disabled="!canSearch"
      >
        {{ t('similar.searchButton') }}
      </UiButton>
    </form>

    <div v-if="similar.loading.value" class="flex flex-col gap-2">
      <div v-for="n in 6" :key="n" class="flex h-16 items-center gap-3 px-3">
        <UiSkeleton class="size-11 !rounded-[8px]" />
        <div class="flex flex-1 flex-col gap-2">
          <UiSkeleton class="h-3.5 w-1/3" />
          <UiSkeleton class="h-3 w-1/5" />
        </div>
      </div>
    </div>

    <UiEmpty
      v-else-if="similar.error.value"
      icon="alert"
      :title="t('similar.failed')"
      :body="similar.error.value"
    >
      <div class="flex flex-wrap justify-center gap-2">
        <UiButton
          v-if="needsKey"
          variant="primary"
          icon="key"
          :to="{ name: 'Settings', params: { section: 'sources' } }"
        >
          {{ t('similar.openSettings') }}
        </UiButton>
        <UiButton icon="refresh" @click="retry">
          {{ t('common.retry') }}
        </UiButton>
      </div>
    </UiEmpty>

    <UiEmpty
      v-else-if="similar.searched.value && !similar.songs.value.length"
      icon="search"
      :title="t('similar.noResults')"
      :body="t('similar.noResultsHint')"
    />

    <template v-else-if="similar.searched.value">
      <section class="flex flex-col gap-3">
        <h2 class="text-display text-xl font-semibold">
          {{
            t('similar.resultsFor', {
              track: similar.track.value,
              artist: similar.artist.value,
            })
          }}
        </h2>
        <div class="-mx-3 flex flex-col">
          <SimilarTrackRow
            v-for="(song, i) in similar.songs.value"
            :key="`${song.artist}|${song.name}`"
            :song="song"
            :index="i"
          />
        </div>
      </section>
    </template>

    <div v-else class="grid gap-4 md:grid-cols-3">
      <div
        v-for="tip in tips"
        :key="tip.title"
        class="flex flex-col gap-2 rounded-panel border border-line-2 bg-surface p-5"
      >
        <span
          class="flex size-10 items-center justify-center rounded-[10px]"
          :class="tip.tone"
        >
          <AppIcon :name="tip.icon" :size="20" />
        </span>
        <p class="mt-1 text-[15px] font-semibold">{{ tip.title }}</p>
        <p class="text-[13px] text-pretty text-muted">{{ tip.body }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppIcon from '/src/components/ui/AppIcon.vue'
import UiButton from '/src/components/ui/UiButton.vue'
import UiEmpty from '/src/components/ui/UiEmpty.vue'
import UiInput from '/src/components/ui/UiInput.vue'
import UiSkeleton from '/src/components/ui/UiSkeleton.vue'
import PageHeader from '/src/components/library/PageHeader.vue'
import SimilarTrackRow from '/src/components/similar/SimilarTrackRow.vue'
import { useSimilar } from '/src/model/similar'
import { useI18n } from '/src/i18n'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const similar = useSimilar()

const artistInput = ref(similar.artist.value)
const trackInput = ref(similar.track.value)

watch(
  () => similar.songs.value,
  (songs) => similar.lookupSongs(songs)
)

// A track row's Similar button lands here with ?artist=&track=: fill the
// form and search at once. Guarded by what's already searched, so typing
// in the form (which rewrites the same query below) never re-triggers.
function applyQuery() {
  const artist = String(route.query.artist || '').trim()
  const track = String(route.query.track || '').trim()
  if (!artist || !track) return
  if (artist === similar.artist.value && track === similar.track.value) {
    return
  }
  artistInput.value = artist
  trackInput.value = track
  similar.searchFor(artist, track)
}

watch(() => [route.query.artist, route.query.track], applyQuery, {
  immediate: true,
})

const canSearch = computed(
  () =>
    !similar.loading.value &&
    !!artistInput.value.trim() &&
    !!trackInput.value.trim()
)

// Last.fm answers without a key explanation the page can't fix - point at
// Settings instead of just offering a retry.
const needsKey = computed(() =>
  String(similar.error.value || '')
    .toLowerCase()
    .includes('api key')
)

function submit() {
  const artist = artistInput.value.trim()
  const track = trackInput.value.trim()
  if (!artist || !track) return
  // Keep the URL shareable; the watcher above ignores it when it matches
  // what's already searched.
  router.replace({ name: 'Similar', query: { artist, track } })
  similar.searchFor(artist, track)
}

function retry() {
  similar.searchFor(similar.artist.value, similar.track.value)
}

const tips = computed(() => [
  {
    icon: 'wand',
    tone: 'bg-accent/12 text-accent',
    title: t('similar.tipSimilarTitle'),
    body: t('similar.tipSimilarBody'),
  },
  {
    icon: 'key',
    tone: 'bg-spotify/12 text-spotify',
    title: t('similar.tipKeyTitle'),
    body: t('similar.tipKeyBody'),
  },
  {
    icon: 'download',
    tone: 'bg-src-ytm/12 text-src-ytm',
    title: t('similar.tipDownloadTitle'),
    body: t('similar.tipDownloadBody'),
  },
])
</script>
