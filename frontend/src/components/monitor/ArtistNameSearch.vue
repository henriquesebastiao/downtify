<template>
  <!-- Artists matching a name typed into the Monitor's Artists box, each
       with its photo, to follow by picking one - never the top result on
       its own, since a famous name easily has namesakes. -->
  <section
    v-if="query"
    class="-mt-3 flex flex-col gap-3 rounded-panel border border-line-2 bg-surface p-4"
    aria-live="polite"
  >
    <div class="flex items-center justify-between gap-3">
      <p class="text-sm font-semibold text-fg">
        {{ t('monitor.searchArtistsFor', { name: query }) }}
      </p>
      <AppIcon
        v-if="loading"
        name="refresh"
        :size="16"
        class="animate-spin text-muted"
      />
    </div>
    <p v-if="failed" class="text-[13px] text-danger" role="alert">
      {{ t('artistSuggestions.lookupFailed') }}
    </p>
    <p
      v-else-if="!loading && searched === query && !candidates.length"
      class="text-[13px] text-muted"
    >
      {{ t('artistSuggestions.notFound', { name: query }) }}
    </p>
    <!-- Shaped like ArtistCandidateList's cards. -->
    <ul
      v-else-if="loading && !candidates.length"
      class="grid gap-3 sm:grid-cols-2"
      aria-busy="true"
    >
      <li v-for="n in 2" :key="n" class="rounded-xl border border-line-2 p-3">
        <div class="flex items-center gap-3">
          <UiSkeleton class="size-16 flex-none !rounded-full" />
          <div class="flex flex-1 flex-col gap-2">
            <UiSkeleton class="h-4 w-2/3" />
            <UiSkeleton class="h-3 w-1/3" />
          </div>
        </div>
        <UiSkeleton class="mt-3 h-8 w-full" />
      </li>
    </ul>
    <template v-else-if="candidates.length">
      <p class="text-[13px] text-muted">
        {{ t('monitor.searchArtistsHelp') }}
      </p>
      <ArtistCandidateList
        :candidates="candidates"
        :busy="busy"
        :chosen="chosen"
        @choose="choose"
      />
    </template>
  </section>
</template>

<script setup>
import { onBeforeUnmount, ref, watch } from 'vue'

import { useI18n } from '/src/i18n'
import monitorAPI from '/src/model/monitor'
import AppIcon from '/src/components/ui/AppIcon.vue'
import UiSkeleton from '/src/components/ui/UiSkeleton.vue'
import ArtistCandidateList from './ArtistCandidateList.vue'

const props = defineProps({
  // The typed name ('' when the box holds a link or nothing).
  query: { type: String, default: '' },
  // A watch is being added: every Follow button waits.
  busy: { type: Boolean, default: false },
})
const emit = defineEmits(['choose'])

const { t } = useI18n()

// Typing pauses this long before a search, so each keystroke isn't one.
const DEBOUNCE_MS = 450

const candidates = ref([])
const loading = ref(false)
const failed = ref(false)
const searched = ref('')
const chosen = ref('')
let timer = null
let latest = 0

async function search(name) {
  const ticket = ++latest
  loading.value = true
  failed.value = false
  try {
    const { data } = await monitorAPI.resolveArtistSuggestion(name)
    if (ticket !== latest) return
    candidates.value = data.candidates || []
  } catch {
    if (ticket !== latest) return
    candidates.value = []
    failed.value = true
  } finally {
    if (ticket === latest) {
      loading.value = false
      searched.value = name
    }
  }
}

function now() {
  clearTimeout(timer)
  if (props.query) search(props.query)
}

watch(
  () => props.query,
  (name) => {
    clearTimeout(timer)
    if (!name) {
      latest++
      candidates.value = []
      loading.value = false
      failed.value = false
      return
    }
    timer = setTimeout(() => search(name), DEBOUNCE_MS)
  },
  { immediate: true }
)

function choose(candidate) {
  chosen.value = candidate.url
  emit('choose', candidate)
}

onBeforeUnmount(() => clearTimeout(timer))

defineExpose({ now })
</script>
