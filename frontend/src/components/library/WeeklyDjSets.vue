<template>
  <section
    v-if="enabled"
    class="my-6 rounded-panel border border-line-2 bg-surface p-5"
  >
    <div class="flex items-center justify-between gap-3">
      <h2 class="text-lg font-semibold">Pour vous DJ</h2>
      <RouterLink v-if="featured" to="/music-ai" class="text-accent"
        >Tous les sets →</RouterLink
      >
    </div>
    <p class="my-3 text-sm text-muted">
      Vos sets audio de la semaine, adaptés à vos sélections.
    </p>
    <p v-if="failure" role="status">{{ failure }}</p>
    <p v-if="!weekly && !failure" role="status">Chargement des sets…</p>
    <ul class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <li
        v-for="card in cards"
        :key="card.key"
        class="rounded border border-line-2 p-3"
      >
        <img
          v-if="card.session?.cover_ids?.[0]"
          :src="musicAI.coverUrl(card.session.cover_ids[0])"
          alt=""
          loading="lazy"
          class="mb-2 aspect-square w-full rounded object-cover"
        />
        <h3 class="font-semibold">
          {{
            card.session?.title ||
            `Set DJ · ${labels[card.theme] || card.theme}`
          }}
        </h3>
        <p class="my-2 text-sm" role="status">{{ status(card.session) }}</p>
        <p v-if="card.session" class="text-sm text-muted">
          {{ card.session.track_count || 0 }} titres ·
          {{ Math.floor((card.session.duration || 0) / 60) }} min
        </p>
        <progress
          v-if="preparing(card.session)"
          :value="card.session.progress || 0"
          max="1"
          aria-label="Préparation du set"
          class="my-2 w-full"
        />
        <template v-if="card.session?.state === 'ready'">
          <MusicDjAudio :session="card.session" />
          <form
            v-if="
              musicAI.capabilities.value?.dj_asset_copies &&
              !card.session.immutable_copy
            "
            @submit.prevent="save(card.session)"
          >
            <label class="text-sm"
              >Nom de la copie<input
                v-model="names[card.session.id]"
                required
                maxlength="160"
                class="my-2 w-full rounded border border-line-2 bg-surface p-2"
            /></label>
            <UiButton
              type="submit"
              :disabled="busy || !names[card.session.id]?.trim()"
              >Enregistrer une copie</UiButton
            >
          </form>
        </template>
        <UiButton
          v-else-if="!preparing(card.session)"
          :disabled="busy || !musicAI.capabilities.value?.dj?.prepared_ready"
          @click="prepare(card.theme)"
          >Préparer {{ labels[card.theme] || card.theme }}</UiButton
        >
      </li>
    </ul>
  </section>
</template>
<script setup>
import { computed, onUnmounted, ref, watch } from 'vue'
import { v4 as uuidv4 } from 'uuid'
import { musicAI } from '/src/model/musicAI'
import MusicDjAudio from './MusicDjAudio.vue'
import UiButton from '/src/components/ui/UiButton.vue'
const props = defineProps({ featured: Boolean })
const weekly = ref(null),
  names = ref({}),
  busy = ref(false),
  failure = ref('')
const labels = {
  rock: 'Rock',
  rap: 'Rap & Hip-Hop',
  pop: 'Pop',
  electro: 'Électro',
  calme: 'Calme',
  concentration: 'Concentration',
  energie: 'Motivation',
  fete: 'Fête',
  melancolie: 'Mélancolie',
  detente: 'Détente',
}
const enabled = computed(() => musicAI.weeklySetsEnabled())
const cards = computed(() => {
  const value = weekly.value
  if (!value) return []
  const selected = props.featured
    ? value.featured
        .map((theme) => value.cards.find((card) => card.theme === theme))
        .filter(Boolean)
        .slice(0, 4)
    : value.cards
  const copies = props.featured
    ? []
    : (value.copies || []).map((session) => ({
        theme: session.weekly_theme || session.theme,
        session,
      }))
  return [...selected, ...copies].map((card) => ({
    ...card,
    key: card.session?.id || card.theme,
  }))
})
let disposed = false,
  generation = 0,
  timer,
  pending
const preparing = (session) =>
  ['queued', 'preparing', 'rendering'].includes(session?.state)
function status(session) {
  if (session?.state === 'ready')
    return session.immutable_copy
      ? 'Copie enregistrée · audio conservé'
      : 'Prêt à écouter'
  if (preparing(session))
    return session.state === 'queued'
      ? 'En attente · priorité à votre bibliothèque et à la lecture'
      : `En préparation · ${Math.round((session.progress || 0) * 100)} %`
  if (session?.state === 'expired') return 'À préparer à nouveau'
  if (session?.state === 'failed')
    return 'La préparation a échoué. Vous pouvez réessayer.'
  return 'Pas encore préparé'
}
async function refresh() {
  clearTimeout(timer)
  const owner = musicAI.account.value,
    mine = generation
  if (disposed || !enabled.value || !owner) return
  try {
    const value = await musicAI.weeklySets()
    if (!disposed && mine === generation && owner === musicAI.account.value) {
      weekly.value = value
      for (const card of value?.cards || [])
        if (card.session && names.value[card.session.id] === undefined)
          names.value[card.session.id] =
            `Mon set ${labels[card.theme] || card.theme}`
    }
  } catch {
    if (!disposed && mine === generation)
      failure.value =
        'Les sets de la semaine sont temporairement indisponibles.'
  } finally {
    if (!disposed && mine === generation && enabled.value)
      timer = setTimeout(
        refresh,
        document.visibilityState === 'visible' &&
          weekly.value?.cards.some((card) => preparing(card.session))
          ? 10000
          : 60000
      )
  }
}
async function action(intent, work) {
  if (busy.value || !enabled.value) return
  const owner = musicAI.account.value,
    mine = generation
  busy.value = true
  failure.value = ''
  const key = JSON.stringify(intent)
  if (pending?.key !== key) pending = { key, request: uuidv4() }
  try {
    await work(pending.request)
    if (owner !== musicAI.account.value || mine !== generation || disposed)
      return
    pending = null
    await refresh()
  } catch (error) {
    if (owner !== musicAI.account.value || mine !== generation || disposed)
      return
    failure.value =
      error.response?.status === 507
        ? 'Espace ou limite de copies atteint sur le serveur.'
        : 'La demande n’a pas abouti. Actualisez ou réessayez.'
    if (error.response?.status >= 400 && error.response?.status < 500)
      pending = null
  } finally {
    if (mine === generation) busy.value = false
  }
}
const prepare = (theme) =>
  action(['prepare', theme], (request) => musicAI.prepareWeekly(theme, request))
const save = (session) => {
  const name = names.value[session.id]?.trim()
  if (name)
    return action(['copy', session.id, name], (request) =>
      musicAI.copyDj(session.id, name, request)
    )
}
watch(
  [
    musicAI.account,
    enabled,
    () => musicAI.capabilities.value?.profile_revision,
  ],
  () => {
    generation++
    weekly.value = null
    names.value = {}
    pending = null
    busy.value = false
    failure.value = ''
    refresh()
  },
  { immediate: true }
)
onUnmounted(() => {
  disposed = true
  generation++
  clearTimeout(timer)
})
</script>
