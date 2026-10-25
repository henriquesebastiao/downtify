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
            :disabled="!!resolving"
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
    <div
      v-if="selection"
      class="rounded-panel border border-line-2 bg-surface p-4 lg:col-span-2"
      aria-live="polite"
    >
      <h3 class="font-semibold">
        {{ t('artistSuggestions.choose', { name: selection.name }) }}
      </h3>
      <p class="mt-1 text-sm text-muted">
        {{ t('artistSuggestions.chooseHelp') }}
      </p>
      <p v-if="lookupFailed" class="mt-2 text-sm text-danger">
        {{ t('artistSuggestions.lookupFailed') }}
      </p>
      <ul class="mt-3 flex flex-wrap gap-2">
        <li v-for="candidate in candidates" :key="candidate.artist_id">
          <UiButton size="sm" variant="ghost" @click="choose(candidate)"
            >{{ candidate.name }} ·
            {{ candidate.artist_id.slice(-6) }}</UiButton
          >
          <a
            :href="candidate.url"
            target="_blank"
            rel="noopener noreferrer"
            class="px-2 text-xs text-muted underline"
            >{{ t('artistSuggestions.inspect') }}</a
          >
        </li>
      </ul>
      <div class="mt-3 flex gap-2">
        <UiButton
          size="sm"
          variant="ghost"
          @click="choose({ name: selection.name, url: '' })"
          >{{ t('artistSuggestions.manual') }}</UiButton
        >
        <UiButton size="sm" variant="ghost" @click="selection = null">{{
          t('artistSuggestions.cancel')
        }}</UiButton>
      </div>
    </div>
  </section>
</template>

<script setup>
import { onBeforeUnmount, ref, watch } from 'vue'
import UiButton from '/src/components/ui/UiButton.vue'
import API from '/src/model/monitor'
import { useI18n } from '/src/i18n'

const props = defineProps({ revision: { type: String, default: '' } })
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
function choose(candidate) {
  selection.value = null
  emit('select', candidate)
}
async function resolve(artist) {
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
