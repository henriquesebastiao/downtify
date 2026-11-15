<template>
  <section class="flex flex-col gap-7">
    <div class="flex flex-wrap items-start justify-between gap-4">
      <div>
        <h1 class="text-display text-3xl font-bold">Pour vous</h1>
        <p class="mt-2 text-sm text-muted">
          Vos mixes du jour et de la semaine, à partir de votre musique et de
          vos goûts.
        </p>
      </div>
      <RouterLink to="/settings/ai" class="text-sm font-semibold text-accent"
        >Préférences IA</RouterLink
      >
    </div>
    <p v-if="failure || indexFailure" role="alert" class="text-danger">
      {{ failure || indexFailure }}
    </p>
    <div class="flex flex-wrap items-center gap-3">
      <div
        v-if="enabled('daily') || enabled('weekly')"
        role="tablist"
        aria-label="Renouvellement des mixes"
        class="flex gap-2"
      >
        <button
          v-for="item in cadences.filter((item) => enabled(item.id))"
          :key="item.id"
          type="button"
          role="tab"
          :aria-selected="cadence === item.id"
          :disabled="busy"
          class="rounded-control border px-4 py-2 text-sm font-semibold"
          :class="
            cadence === item.id
              ? 'border-accent bg-accent/10 text-accent'
              : 'border-line-2 text-muted'
          "
          @click="chooseCadence(item.id)"
        >
          {{ item.label }}
        </button>
      </div>
      <UiButton
        v-if="enabled('personalization')"
        :disabled="busy || !musicAI.capabilities.value?.model.ready"
        @click="forYou"
        >À écouter maintenant</UiButton
      >
      <UiButton :disabled="indexLoading" icon="refresh" @click="loadIndex"
        >Actualiser</UiButton
      >
      <UiButton
        v-if="
          musicAI.capabilities.value?.playlist_refresh &&
          (enabled('daily') || enabled('weekly'))
        "
        :disabled="busy || indexLoading"
        @click="renew"
        >Renouveler mes mixes</UiButton
      >
      <UiButton v-if="tracks.length" :disabled="busy" @click="clearSelection"
        >← Tous mes mixes</UiButton
      >
    </div>
    <p v-if="renewalMessage" role="status" class="text-muted">
      {{ renewalMessage }}
    </p>
    <p
      v-if="indexLoading && !playlists.length"
      role="status"
      class="text-muted"
    >
      Vos playlists arrivent…
    </p>
    <div
      v-if="cards.length && !tracks.length"
      class="grid grid-cols-2 gap-4 lg:grid-cols-3 xl:grid-cols-4"
    >
      <article
        v-for="card in cards"
        :key="`${card.cadence}:${card.mood}:${card.period}`"
        class="group overflow-hidden rounded-panel border border-line-2 bg-surface transition hover:border-accent/50"
      >
        <button
          type="button"
          class="w-full text-left"
          :disabled="busy"
          :aria-label="`Ouvrir ${mixTitle(card)}`"
          @click="open(card)"
        >
          <div
            class="relative flex aspect-[1.25] flex-col justify-between overflow-hidden bg-gradient-to-br p-5 text-white"
            :class="moods[card.mood]?.color"
          >
            <div
              class="absolute -right-8 -bottom-10 size-40 rounded-full border-[20px] border-white/10"
              aria-hidden="true"
            />
            <span
              class="relative text-xs font-semibold uppercase tracking-[.16em]"
              >{{
                card.cadence === 'daily' ? 'Mix du jour' : 'Mix de la semaine'
              }}</span
            >
            <div class="relative">
              <AppIcon name="wand" :size="25" class="mb-3 opacity-80" /><strong
                class="text-display text-2xl font-bold sm:text-3xl"
                >{{ moods[card.mood]?.label }}</strong
              >
            </div>
          </div>
          <div class="p-4">
            <h2 class="truncate font-semibold">{{ mixTitle(card) }}</h2>
            <p class="mt-1 text-xs text-muted">
              {{ card.count }} titres ·
              {{ card.cadence === 'daily' ? 'Chaque jour' : 'Chaque semaine' }}
            </p>
          </div>
        </button>
      </article>
    </div>
    <div
      v-else-if="
        !tracks.length &&
        !indexLoading &&
        !indexFailure &&
        (enabled('daily') || enabled('weekly'))
      "
      class="rounded-panel border border-line-2 bg-surface p-6"
    >
      <h2 class="font-semibold">Vos mixes se préparent</h2>
      <p class="mt-2 text-sm text-muted">
        Ils apparaîtront ici après l’analyse initiale et leur génération. Votre
        musique reste disponible dans la bibliothèque.
      </p>
    </div>
    <p
      v-if="
        !enabled('daily') && !enabled('weekly') && !enabled('personalization')
      "
      class="text-muted"
    >
      Les fonctions Pour vous sont désactivées. Vous pouvez les choisir dans
      Paramètres → IA.
    </p>
    <section
      v-if="tracks.length"
      class="flex flex-col gap-4 rounded-panel border border-line-2 bg-surface p-4 sm:p-6"
    >
      <div>
        <p class="text-xs font-semibold uppercase tracking-wider text-accent">
          Votre sélection
        </p>
        <h2 class="mt-1 text-display text-2xl font-semibold">{{ title }}</h2>
        <p class="mt-1 text-sm text-muted">
          {{ tracks.length }} titres · bibliothèque locale
        </p>
      </div>
      <div class="flex flex-wrap gap-3">
        <UiButton
          variant="primary"
          :disabled="busy"
          icon="play"
          @click="play(tracks[0])"
          >Tout écouter</UiButton
        >
        <UiButton :disabled="busy" @click="shuffleAll">Mélanger</UiButton>
        <UiButton :disabled="busy" icon="plus" @click="enqueueAll"
          >Ajouter à la file</UiButton
        >
        <UiButton
          v-if="
            tracks.length >= 2 &&
            (enabled('dj_prepared') || enabled('dj_interactive'))
          "
          :disabled="busy"
          @click="mix"
          >Mixer cette sélection</UiButton
        >
      </div>
      <ul class="divide-y divide-line-2">
        <li
          v-for="row in tracks"
          :key="row.id"
          class="flex flex-wrap items-center gap-3 py-3"
        >
          <div class="min-w-0 flex-1">
            <strong class="block truncate text-sm">{{ row.title }}</strong
            ><span class="text-xs text-muted">{{ row.artist }}</span>
          </div>
          <span class="hidden text-xs text-muted sm:block">{{
            row.reason
          }}</span>
          <UiButton :disabled="busy" @click="play(row)">Écouter</UiButton
          ><UiButton :disabled="busy" @click="play(row, true)"
            >Ajouter</UiButton
          >
        </li>
      </ul>
      <form class="flex flex-wrap items-center gap-3" @submit.prevent="save">
        <input
          v-model="name"
          required
          maxlength="160"
          aria-label="Nom de la playlist"
          placeholder="Nom de la playlist"
          class="min-w-0 flex-1 rounded-control border border-line-2 bg-bg p-3 text-sm"
        />
        <UiButton type="submit" :disabled="busy || !name.trim()"
          >Enregistrer une copie stable</UiButton
        >
      </form>
      <p class="text-xs text-muted">
        Une copie enregistrée reste à vous et ne sera pas remplacée au prochain
        renouvellement.
      </p>
      <p v-if="saved" role="status" class="text-sm text-accent">{{ saved }}</p>
    </section>
  </section>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import AppIcon from '/src/components/ui/AppIcon.vue'
import UiButton from '/src/components/ui/UiButton.vue'
import { musicAI } from '/src/model/musicAI'
import { usePlayer } from '/src/model/player'
import { readMixIndex } from '/src/model/musicAiRead'
import { normalizeTrack } from '/src/lib/library'
import { useLibrary } from '/src/model/library'
import { useTrackActions } from '/src/model/trackActions'

const router = useRouter(),
  library = useLibrary(),
  actions = useTrackActions()
const route = useRoute()
const playlists = ref([]),
  tracks = ref([]),
  cadence = ref('daily'),
  title = ref(''),
  name = ref(''),
  source = ref('personalization')
const busy = ref(false),
  indexLoading = ref(false),
  failure = ref(''),
  indexFailure = ref(''),
  saved = ref(''),
  renewalMessage = ref('')
let serial = 0,
  indexSerial = 0,
  disposed = false,
  timer
const cadences = [
  { id: 'daily', label: 'Mixes du jour' },
  { id: 'weekly', label: 'Mixes de la semaine' },
]
const moods = {
  calme: { label: 'Calme', color: 'from-indigo-700 to-violet-700' },
  concentration: {
    label: 'Concentration',
    color: 'from-slate-800 to-indigo-700',
  },
  energie: { label: 'Motivation', color: 'from-orange-700 to-rose-800' },
  fete: { label: 'Fête', color: 'from-fuchsia-800 to-purple-800' },
  melancolie: { label: 'Mélancolie', color: 'from-blue-800 to-slate-700' },
  detente: { label: 'Détente', color: 'from-teal-800 to-emerald-800' },
  rock: { label: 'Rock', color: 'from-red-900 to-red-700' },
  rap: { label: 'Rap & Hip-Hop', color: 'from-yellow-900 to-amber-700' },
  electro: { label: 'Électro', color: 'from-sky-900 to-blue-700' },
  pop: { label: 'Pop', color: 'from-pink-900 to-rose-700' },
}
const enabled = (key) => musicAI.capabilities.value?.features?.[key] === true
const cards = computed(() =>
  playlists.value.filter(
    (row) =>
      row.cadence === cadence.value && enabled(row.cadence) && moods[row.mood]
  )
)
const mixTitle = (card) =>
  `${card.cadence === 'daily' ? 'Mix du jour' : 'Mix de la semaine'} · ${moods[card.mood]?.label || ''}`
async function loadIndex() {
  const mine = ++indexSerial,
    owner = musicAI.account.value
  if (!owner || (!enabled('daily') && !enabled('weekly'))) {
    playlists.value = []
    indexLoading.value = false
    return
  }
  indexLoading.value = true
  indexFailure.value = ''
  const current = () =>
    !disposed &&
    mine === indexSerial &&
    owner === musicAI.account.value &&
    (enabled('daily') || enabled('weekly'))
  try {
    const value = await readMixIndex(() => musicAI.playlists(), current)
    if (current() && value) playlists.value = value
  } catch {
    if (!disposed && mine === indexSerial && owner === musicAI.account.value)
      indexFailure.value =
        'Les playlists ne sont pas disponibles pour le moment.'
  } finally {
    if (mine === indexSerial) indexLoading.value = false
  }
}
async function run(fetch, apply) {
  const mine = ++serial,
    owner = musicAI.account.value
  busy.value = true
  failure.value = ''
  try {
    const value = await fetch()
    if (!disposed && mine === serial && owner === musicAI.account.value)
      apply(value)
  } catch (error) {
    if (!disposed && mine === serial && owner === musicAI.account.value)
      failure.value =
        error?.response?.data?.detail || 'Cette action n’a pas abouti.'
  } finally {
    if (mine === serial) busy.value = false
  }
}
function select(rows, label, feature) {
  tracks.value = rows
  title.value = label
  name.value = label
  source.value = feature
  saved.value = ''
  if (!rows.length)
    failure.value =
      'Ce mix ne contient plus de titres disponibles. Actualisez vos playlists.'
}
function clearSelection() {
  tracks.value = []
  saved.value = ''
  title.value = ''
}
function chooseCadence(value) {
  cadence.value = value
  clearSelection()
}
const renew = () =>
  run(
    () => musicAI.renewPlaylists(crypto.randomUUID()),
    () => {
      ++indexSerial
      playlists.value = []
      clearSelection()
      renewalMessage.value =
        'Renouvellement demandé. Vos nouveaux mixes se préparent ; actualisez dans un instant. Les copies enregistrées restent à vous.'
    }
  )
const open = (card) =>
  run(
    () => musicAI.playlist(card.cadence, card.mood),
    (rows) => select(rows, mixTitle(card), card.cadence)
  )
const forYou = () =>
  run(
    () => musicAI.recommendations(),
    (rows) => select(rows, 'À écouter maintenant', 'personalization')
  )
const play = (row, queue = false) =>
  run(
    () => musicAI.playable(queue ? [row] : tracks.value),
    (rows) => {
      const resolved = rows.map(normalizeTrack)
      if (queue) actions.enqueue(resolved)
      else
        actions.play(
          resolved,
          tracks.value.findIndex((item) => item.id === row.id)
        )
    }
  )
const enqueueAll = () =>
  run(
    () => musicAI.playable(tracks.value),
    (rows) => actions.enqueue(rows.map(normalizeTrack))
  )
const shuffleAll = () =>
  run(
    () => musicAI.playable(tracks.value),
    (rows) =>
      usePlayer().playList(rows.map(normalizeTrack), {
        shuffled: true,
        context: { type: 'playlist', title: title.value },
      })
  )
const save = () =>
  run(
    () => musicAI.save(name.value.trim(), tracks.value, source.value),
    (value) => {
      saved.value = `Playlist enregistrée : ${value.name}`
      library.load({ force: true })
    }
  )
function mix() {
  musicAI.selectForDj(tracks.value)
  router.push('/music-dj')
}
watch(
  () => [
    route.query.mood,
    route.query.cadence,
    musicAI.account.value,
    enabled('daily'),
    enabled('weekly'),
  ],
  () => {
    const mood = String(route.query.mood || ''),
      value = String(route.query.cadence || 'daily')
    if (moods[mood] && enabled(value)) {
      cadence.value = value
      open({ mood, cadence: value })
    }
  },
  { immediate: true }
)
watch(
  [
    () => musicAI.account.value,
    () => musicAI.capabilities.value?.features?.daily,
    () => musicAI.capabilities.value?.features?.weekly,
  ],
  () => {
    if (!enabled(cadence.value))
      cadence.value = enabled('daily') ? 'daily' : 'weekly'
    loadIndex()
  },
  { immediate: true }
)
watch(
  () => musicAI.account.value,
  () => {
    serial++
    tracks.value = []
    playlists.value = []
    saved.value = ''
    renewalMessage.value = ''
    failure.value = ''
    indexFailure.value = ''
    busy.value = false
  }
)
watch(
  () => enabled(source.value),
  (value) => {
    if (!value) {
      serial++
      tracks.value = []
      saved.value = ''
      busy.value = false
    }
  }
)
onMounted(() => {
  musicAI.refresh()
  loadIndex()
})
onUnmounted(() => {
  disposed = true
  serial++
  indexSerial++
  clearInterval(timer)
})
</script>
