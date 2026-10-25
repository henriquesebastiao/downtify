<template>
  <section
    class="grid gap-4 lg:grid-cols-2"
    :aria-label="t('artistSuggestions.title')"
  >
    <div
      v-for="column in columns"
      :key="column.key"
      class="rounded-panel border border-line-2 bg-surface p-4"
    >
      <h2 class="font-semibold">{{ t(column.title) }}</h2>
      <p class="mt-1 text-xs text-muted">{{ t(column.description) }}</p>
      <p v-if="error" class="mt-3 text-sm text-danger" role="alert">
        {{ t('artistSuggestions.failed') }}
      </p>
      <UiButton v-if="error" size="sm" variant="ghost" @click="reset">{{
        t('artistSuggestions.retry')
      }}</UiButton>
      <p
        v-else-if="!pages[column.key].items.length"
        class="mt-4 text-sm text-muted"
      >
        {{
          t(loading ? 'artistSuggestions.loading' : 'artistSuggestions.empty')
        }}
      </p>
      <ul class="mt-3 divide-y divide-line-2">
        <li
          v-for="artist in pages[column.key].items"
          :key="artist.name"
          class="flex items-center justify-between gap-3 py-3"
        >
          <div class="min-w-0">
            <p class="truncate text-sm font-medium">{{ artist.name }}</p>
            <p class="text-xs text-muted">
              {{
                column.key === 'listening'
                  ? t('artistSuggestions.listeningCount', {
                      count: artist.plays,
                    })
                  : t('artistSuggestions.libraryCounts', {
                      tracks: artist.track_count,
                      albums: artist.album_count,
                    })
              }}
            </p>
          </div>
          <UiButton
            size="sm"
            variant="ghost"
            :loading="resolving === artist.name"
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
        :loading="loading"
        @click="more(column.key)"
      >
        {{ t('artistSuggestions.more') }}
      </UiButton>
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
        <p class="mt-1 text-sm text-muted">
          {{ t('artistSuggestions.chooseHelp') }}
        </p>
        <p v-if="lookupFailed" class="mt-2 text-sm text-danger">
          {{ t('artistSuggestions.lookupFailed') }}
        </p>
        <p v-if="followError" class="mt-3 text-sm text-danger" role="alert">
          {{ followError }}
        </p>
        <ul class="mt-4 grid gap-3 sm:grid-cols-2">
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
                class="size-16"
              />
              <div class="min-w-0">
                <p class="truncate font-semibold">{{ candidate.name }}</p>
                <p class="mt-1 text-xs text-muted">
                  {{
                    t('artistSuggestions.catalogue', {
                      source:
                        candidate.source === 'spotify'
                          ? 'Spotify'
                          : 'YouTube Music',
                    })
                  }}
                </p>
              </div>
            </div>
            <div class="mt-3 flex items-center justify-between gap-2">
              <a
                :href="candidate.url"
                target="_blank"
                rel="noopener noreferrer"
                class="text-xs text-muted underline underline-offset-4"
                >{{ t('artistSuggestions.inspect') }}</a
              >
              <UiButton
                size="sm"
                variant="primary"
                :disabled="busy"
                :loading="busy && selectedCandidate === candidate.artist_id"
                @click="choose(candidate)"
                >{{ t('artistSuggestions.followProfile') }}</UiButton
              >
            </div>
          </li>
        </ul>
        <div class="mt-3 flex gap-2">
          <UiButton
            size="sm"
            variant="ghost"
            @click="choose({ name: selection.name, url: '' })"
            >{{ t('artistSuggestions.manual') }}</UiButton
          >
          <UiButton size="sm" variant="ghost" :disabled="busy" @click="close">{{
            t('artistSuggestions.cancel')
          }}</UiButton>
        </div>
      </div>
    </UiModal>
  </section>
</template>

<script setup>
import { onBeforeUnmount, ref, watch } from 'vue'
import UiButton from '/src/components/ui/UiButton.vue'
import UiModal from '/src/components/ui/UiModal.vue'
import CoverArt from '/src/components/ui/CoverArt.vue'
import API from '/src/model/monitor'
import { useI18n } from '/src/i18n'

const props = defineProps({
  revision: { type: String, default: '' },
  busy: { type: Boolean, default: false },
  followError: { type: String, default: '' },
})
const emit = defineEmits(['select'])
const { t } = useI18n()
const columns = [
  {
    key: 'listening',
    title: 'artistSuggestions.listening',
    description: 'artistSuggestions.listeningHelp',
  },
  {
    key: 'library',
    title: 'artistSuggestions.library',
    description: 'artistSuggestions.libraryHelp',
  },
]
const empty = () => ({ items: [], next_offset: null, total: 0 })
const pages = ref({ listening: empty(), library: empty() })
const loading = ref(false)
const error = ref(false)
const resolving = ref('')
const selection = ref(null)
const candidates = ref([])
const selectedCandidate = ref('')
const lookupFailed = ref(false)
let generation = 0
let lookupGeneration = 0
let disposed = false

async function load(key) {
  const current = ++generation
  loading.value = true
  error.value = false
  try {
    const offsets = key
      ? { [`${key}_offset`]: pages.value[key].next_offset }
      : {}
    const { data } = await API.artistSuggestions(offsets)
    if (disposed || current !== generation) return
    if (key) {
      const known = new Set(pages.value[key].items.map((r) => r.name))
      pages.value[key] = {
        ...data[key],
        items: [
          ...pages.value[key].items,
          ...data[key].items.filter((r) => !known.has(r.name)),
        ],
      }
    } else pages.value = data
  } catch {
    if (!disposed && current === generation) error.value = true
  } finally {
    if (!disposed && current === generation) loading.value = false
  }
}

function reset() {
  pages.value = { listening: empty(), library: empty() }
  selection.value = null
  lookupGeneration++
  resolving.value = ''
  load()
}
function more(key) {
  if (!loading.value && pages.value[key].next_offset !== null) load(key)
}
function close() {
  if (!props.busy) selection.value = null
}
function choose(candidate) {
  if (props.busy) return
  const fromDialog = !!selection.value
  selectedCandidate.value = candidate.artist_id || ''
  if (!candidate.url) selection.value = null
  emit('select', { ...candidate, fromDialog })
}
async function resolve(artist) {
  if (props.busy || resolving.value) return
  const current = ++lookupGeneration
  resolving.value = artist.name
  lookupFailed.value = false
  selection.value = null
  candidates.value = []
  try {
    const { data } = await API.resolveArtistSuggestion(artist.name)
    if (disposed || current !== lookupGeneration) return
    if (data.url) choose({ name: artist.name, url: data.url })
    else {
      candidates.value = data.candidates
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
onBeforeUnmount(() => {
  disposed = true
  generation++
  lookupGeneration++
})
</script>
