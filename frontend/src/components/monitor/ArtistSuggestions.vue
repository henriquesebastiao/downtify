<template>
  <section
    class="flex flex-col gap-3"
    :aria-label="t('artistSuggestions.title')"
  >
    <div
      v-if="error"
      class="flex flex-wrap items-center gap-3 rounded-panel border border-line-2 bg-surface px-4 py-3"
      role="alert"
    >
      <p class="text-sm text-danger">{{ t('artistSuggestions.failed') }}</p>
      <UiButton size="sm" variant="ghost" icon="retry" @click="reset">
        {{ t('artistSuggestions.retry') }}
      </UiButton>
    </div>
    <div class="grid gap-4 lg:grid-cols-2">
      <div
        v-for="column in columns"
        :key="column.key"
        class="rounded-panel border border-line-2 bg-surface p-4"
      >
        <h2 class="font-semibold">{{ t(column.title) }}</h2>
        <p class="mt-1 text-xs text-muted">
          {{ t(column.help, { days: halfLife }) }}
        </p>
        <p
          v-if="!shown(column.key).length && !error"
          class="mt-4 text-sm text-muted"
        >
          {{
            t(loading ? 'artistSuggestions.loading' : 'artistSuggestions.empty')
          }}
        </p>
        <ul class="mt-3 divide-y divide-line-2">
          <li
            v-for="artist in shown(column.key)"
            :key="artist.name"
            class="flex items-center justify-between gap-3 py-3"
          >
            <div class="min-w-0">
              <p class="truncate text-sm font-medium">{{ artist.name }}</p>
              <p class="text-xs text-muted">{{ counts(column.key, artist) }}</p>
            </div>
            <UiButton
              size="sm"
              variant="ghost"
              icon="user"
              :loading="
                resolving === artist.name || (busy && following === artist.name)
              "
              :disabled="!!resolving || busy"
              @click="resolve(artist)"
            >
              {{ t('artistSuggestions.follow') }}
            </UiButton>
          </li>
        </ul>
        <UiButton
          v-if="pages[column.key].next_offset !== null"
          size="sm"
          variant="ghost"
          :loading="loading === column.key"
          :disabled="!!loading"
          @click="more(column.key)"
        >
          {{ t('artistSuggestions.more') }}
        </UiButton>
      </div>
    </div>

    <UiModal
      :open="!!selection"
      :title="
        selection ? t('artistSuggestions.choose', { name: selection.name }) : ''
      "
      width="sm:max-w-2xl"
      @close="close"
    >
      <div v-if="selection">
        <p v-if="lookupFailed" class="text-sm text-danger">
          {{ t('artistSuggestions.lookupFailed') }}
        </p>
        <p v-else-if="!candidates.length" class="text-sm text-muted">
          {{ t('artistSuggestions.notFound', { name: selection.name }) }}
        </p>
        <p v-else class="text-sm text-muted">
          {{ t('artistSuggestions.chooseHelp', { name: selection.name }) }}
        </p>
        <p
          v-if="submitted && followError"
          class="mt-3 text-sm text-danger"
          role="alert"
        >
          {{ followError }}
        </p>
        <ul
          v-if="candidates.length"
          class="mt-4 grid max-h-[60vh] gap-3 overflow-y-auto sm:grid-cols-2"
        >
          <li
            v-for="candidate in candidates"
            :key="candidate.artist_id"
            class="rounded-xl border border-line-2 bg-surface-2 p-3"
          >
            <div class="flex items-center gap-3">
              <CoverArt
                :src="candidate.image_url || ''"
                :name="candidate.name"
                :alt="candidate.name"
                round
                icon="user"
                :letter-size="24"
                class="size-16 flex-none"
              />
              <div class="min-w-0">
                <p class="truncate font-semibold">{{ candidate.name }}</p>
                <a
                  :href="candidate.url"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="mt-1 inline-block text-xs text-muted underline underline-offset-4"
                  >{{ t('artistSuggestions.inspect') }}</a
                >
              </div>
            </div>
            <UiButton
              size="sm"
              variant="primary"
              class="mt-3 w-full"
              :disabled="busy"
              :loading="busy && chosen === candidate.url"
              @click="choose(candidate)"
            >
              {{ t('artistSuggestions.followProfile') }}
            </UiButton>
          </li>
        </ul>
        <div class="mt-4 flex flex-wrap justify-end gap-2">
          <UiButton
            size="sm"
            variant="ghost"
            icon="link"
            :disabled="busy"
            @click="pasteLink"
          >
            {{ t('artistSuggestions.manual') }}
          </UiButton>
          <UiButton size="sm" variant="ghost" :disabled="busy" @click="close">
            {{ t('artistSuggestions.cancel') }}
          </UiButton>
        </div>
      </div>
    </UiModal>
  </section>
</template>

<script setup>
// Artists to follow, under the Monitor page's Artists tab: from the user's
// own listens and from the library (GET /api/monitor/artist-suggestions).
// Loading them searches nothing; clicking Follow asks the server which
// YouTube Music artist the name is (…/resolve) and hands the link to the
// page (`select`), which adds the watch as for a pasted link. Namesakes, or
// no artist with that exact name, open a dialog to pick one instead.
import { onBeforeUnmount, ref, watch } from 'vue'
import UiButton from '/src/components/ui/UiButton.vue'
import UiModal from '/src/components/ui/UiModal.vue'
import CoverArt from '/src/components/ui/CoverArt.vue'
import API from '/src/model/monitor'
import { useI18n } from '/src/i18n'
import {
  appendSuggestionPage,
  emptySuggestionPage,
} from '/src/lib/artistSuggestions'

const props = defineProps({
  // Changes when the user's watches do: the lists are loaded again.
  revision: { type: String, default: '' },
  // A watch is being added (the page's link box).
  busy: { type: Boolean, default: false },
  // Why adding the last one failed, shown in the dialog.
  followError: { type: String, default: '' },
})
const emit = defineEmits(['select'])
const { t } = useI18n()

const columns = [
  {
    key: 'listening',
    title: 'artistSuggestions.listening',
    help: 'artistSuggestions.listeningHelp',
  },
  {
    key: 'library',
    title: 'artistSuggestions.library',
    help: 'artistSuggestions.libraryHelp',
  },
]
const pages = ref({
  listening: emptySuggestionPage(),
  library: emptySuggestionPage(),
})
const halfLife = ref(45)
// '' when idle, 'all' for the first page of both, else the list whose
// next page is loading.
const loading = ref('')
const error = ref(false)
// The suggestion being looked up, and the one being followed.
const resolving = ref('')
const following = ref('')
// Suggestions followed while the page is open. The watch is named after
// the YouTube Music artist, which may spell the name otherwise
// (`Henrique e Juliano` / `Henrique & Juliano`), so the server would
// still suggest it.
const followed = ref(new Set())
// The dialog: the suggestion, the artists to pick from, the picked link.
const selection = ref(null)
const candidates = ref([])
const lookupFailed = ref(false)
const chosen = ref('')
const submitted = ref(false)
let generation = 0
let lookupGeneration = 0
let disposed = false

function shown(list) {
  return pages.value[list].items.filter((row) => !followed.value.has(row.name))
}

function counts(list, artist) {
  if (list === 'listening') {
    return t('artistSuggestions.listens', { count: artist.plays })
  }
  const tracks = t('artistSuggestions.tracks', { count: artist.track_count })
  return artist.album_count
    ? `${tracks} · ${t('artistSuggestions.albums', { count: artist.album_count })}`
    : tracks
}

async function load(list = '') {
  const current = ++generation
  loading.value = list || 'all'
  error.value = false
  try {
    const offsets = list
      ? { [`${list}_offset`]: pages.value[list].next_offset }
      : {}
    const { data } = await API.artistSuggestions(offsets)
    if (disposed || current !== generation) return
    halfLife.value = data.half_life_days ?? halfLife.value
    pages.value = list
      ? {
          ...pages.value,
          [list]: appendSuggestionPage(pages.value[list], data[list]),
        }
      : { listening: data.listening, library: data.library }
  } catch {
    if (!disposed && current === generation) error.value = true
  } finally {
    if (!disposed && current === generation) loading.value = ''
  }
}

function reset() {
  pages.value = {
    listening: emptySuggestionPage(),
    library: emptySuggestionPage(),
  }
  selection.value = null
  lookupGeneration++
  resolving.value = ''
  load()
}

function more(list) {
  if (!loading.value && pages.value[list].next_offset !== null) load(list)
}

function close() {
  if (!props.busy) selection.value = null
}

function choose(candidate) {
  if (props.busy) return
  submitted.value = !!selection.value
  if (selection.value) following.value = selection.value.name
  chosen.value = candidate.url
  emit('select', {
    name: candidate.name,
    url: candidate.url,
    fromDialog: submitted.value,
  })
}

function pasteLink() {
  if (props.busy) return
  selection.value = null
  emit('select', { name: '', url: '', fromDialog: false })
}

async function resolve(artist) {
  if (props.busy || resolving.value) return
  const current = ++lookupGeneration
  resolving.value = artist.name
  lookupFailed.value = false
  submitted.value = false
  selection.value = null
  candidates.value = []
  try {
    const { data } = await API.resolveArtistSuggestion(artist.name)
    if (disposed || current !== lookupGeneration) return
    if (data.url) {
      following.value = artist.name
      choose({ name: artist.name, url: data.url })
    } else {
      candidates.value = data.candidates || []
      selection.value = artist
    }
  } catch {
    if (!disposed && current === lookupGeneration) {
      lookupFailed.value = true
      selection.value = artist
    }
  } finally {
    if (!disposed && current === lookupGeneration) resolving.value = ''
  }
}

watch(() => props.revision, reset, { immediate: true })
watch(
  () => props.busy,
  (busy, was) => {
    if (busy || !was) return
    if (following.value && !props.followError) {
      followed.value = new Set([...followed.value, following.value])
    }
    following.value = ''
  }
)
onBeforeUnmount(() => {
  disposed = true
  generation++
  lookupGeneration++
})
</script>
