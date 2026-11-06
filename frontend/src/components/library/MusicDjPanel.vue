<template>
  <section
    v-if="enabled"
    class="rounded-panel border border-line-2 bg-surface p-5"
  >
    <h2 class="text-lg font-semibold">Votre set DJ</h2>
    <p class="my-3 text-sm text-muted">
      Un mix préparé à partir de vos fichiers locaux, avec progression d’énergie
      et transitions adaptées à l’analyse. Vos fichiers originaux sont
      conservés.
    </p>
    <p v-if="!ready" role="status">
      <template v-if="mode === 'interactive'">
        Le direct n’est pas disponible. Il nécessite une validation continue
        d’une heure sur ce serveur.
      </template>
      <template v-else>
        Le moteur DJ se prépare ou est indisponible. La lecture classique reste
        disponible.
      </template>
    </p>
    <form
      class="flex flex-wrap items-center gap-3"
      @submit.prevent="create(false)"
    >
      <select
        v-model="mode"
        aria-label="Mode DJ"
        class="rounded border border-line-2 bg-surface p-2"
      >
        <option v-if="preparedEnabled" value="prepared">Set préparé</option>
        <option v-if="interactiveEnabled" value="interactive">
          Direct interactif
        </option>
      </select>
      <select
        v-model="theme"
        aria-label="Thème du set DJ"
        class="rounded border border-line-2 bg-surface p-2"
      >
        <option v-for="(label, key) in moods" :key="key" :value="key">
          {{ label }}
        </option>
      </select>
      <label class="flex items-center gap-2"
        >Titres
        <input
          v-model.number="count"
          type="number"
          min="2"
          max="40"
          required
          aria-label="Nombre de titres DJ"
          class="w-20 rounded border border-line-2 bg-surface p-2"
        />
      </label>
      <label v-if="selection.length >= 2" class="flex items-center gap-2"
        ><input v-model="useSelection" type="checkbox" />Utiliser la sélection
        affichée ({{ Math.min(40, selection.length) }} titres)</label
      >
      <UiButton type="submit" :disabled="busy || !ready">{{
        mode === 'prepared' ? 'Préparer le set' : 'Démarrer le direct'
      }}</UiButton>
      <label v-if="mode === 'interactive'" class="flex items-center gap-2"
        ><input v-model="continuous" type="checkbox" />Prolonger le mix en
        continu</label
      >
      <UiButton
        v-if="isAdmin && mode === 'interactive' && !ready"
        type="button"
        :disabled="busy"
        @click="create(true)"
      >
        Lancer une validation locale d’une heure
      </UiButton>
    </form>
    <p class="my-2 text-sm text-muted">
      Un seul rendu à la fois sur le serveur. Vous pouvez continuer à écouter
      pendant la préparation.
    </p>
    <p v-if="failure" role="alert" class="text-red-500">{{ failure }}</p>
    <p v-if="notice" role="status">{{ notice }}</p>
    <ul class="mt-4 flex flex-col gap-4">
      <li
        v-for="session in shownSessions"
        :key="session.id"
        class="border-t border-line-2 pt-4"
      >
        <div class="flex items-center justify-between gap-3">
          <strong
            >{{ moods[session.theme] }} ·
            {{ session.track_count ?? session.tracks.length }} titres</strong
          >
          <span role="status">{{ stateLabel(session) }}</span>
          <UiButton
            v-if="
              isAdmin &&
              interactiveEnabled &&
              session.mode === 'interactive' &&
              ['stopped', 'failed', 'cancelled', 'ready'].includes(
                session.state
              ) &&
              session.tracks.length >= 2
            "
            :disabled="busy"
            @click="create(true, session)"
            >Revalider ce set</UiButton
          >
          <UiButton
            v-if="session.state !== 'deleting'"
            :disabled="busy"
            @click="discard(session)"
            >Supprimer ce set</UiButton
          >
          <UiButton
            v-if="active(session) || session.state === 'queued'"
            :disabled="busy"
            @click="stop(session)"
            >Arrêter le rendu</UiButton
          >
        </div>
        <progress
          v-if="['preparing', 'rendering'].includes(session.state)"
          :value="session.progress || 0"
          max="1"
          class="mt-3 w-full"
          aria-label="Préparation du set"
        />
        <template
          v-if="
            session.media_url &&
            (session.mode === 'prepared'
              ? session.state === 'ready'
              : ['playing', 'paused'].includes(session.state))
          "
        >
          <MusicDjAudio
            :ref="audioRef(session.id)"
            :session="session"
            @play="playing(session.id)"
            @error="failure = $event"
            @validation="proofs[session.id] = $event"
            @diagnostic="diagnostics[session.id] = $event"
          />
          <div
            v-if="session.mode === 'interactive' && active(session)"
            class="my-3 flex flex-wrap gap-3"
          >
            <UiButton
              :disabled="busy"
              @click="
                control(
                  session,
                  session.state === 'paused' ? 'resume' : 'pause'
                )
              "
            >
              {{
                session.state === 'paused'
                  ? 'Reprendre le direct'
                  : 'Mettre le direct en pause'
              }}
            </UiButton>
            <UiButton :disabled="busy" @click="control(session, 'next')"
              >Prochain titre</UiButton
            >
            <select
              v-model="replacements[session.id]"
              aria-label="Remplacer le prochain titre"
              class="bg-surface p-2"
            >
              <option
                v-for="track in session.tracks"
                :key="track.id"
                :value="track.id"
              >
                {{ track.title }} · {{ track.artist }}
              </option>
            </select>
            <UiButton
              :disabled="busy || !replacements[session.id]"
              @click="
                control(session, 'replace', { id: replacements[session.id] })
              "
              >Remplacer le suivant</UiButton
            >
            <select
              v-model="themes[session.id]"
              aria-label="Nouveau thème DJ"
              class="bg-surface p-2"
            >
              <option v-for="(label, key) in moods" :key="key" :value="key">
                {{ label }}
              </option>
            </select>
            <UiButton
              :disabled="busy || !themes[session.id]"
              @click="control(session, 'theme', { theme: themes[session.id] })"
              >Changer le thème</UiButton
            >
            <p role="status">
              Prochaine transition modifiable dans environ
              {{
                Math.ceil(
                  Math.max(0, session.next_mutable_at - session.position)
                )
              }}
              s.
            </p>
            <p v-if="session.commands?.[0]?.effective_at" role="status">
              Modification appliquée à la transition dans environ
              {{
                Math.ceil(
                  Math.max(
                    0,
                    session.commands[0].effective_at - session.position
                  )
                )
              }}
              s.
            </p>
            <p v-if="session.commands?.[0]?.accepted === false" role="alert">
              {{ session.commands[0].reason }}
            </p>
          </div>
          <p v-if="proofs[session.id]" role="status">
            Validation :
            {{ Math.floor(proofs[session.id].continuous_seconds / 60) }} min
            continues ·
            {{
              proofs[session.id].total_interruptions ??
              proofs[session.id].interruptions
            }}
            remise(s) à zéro.
          </p>
          <p
            v-if="isAdmin && proofs[session.id]?.reader_events"
            class="text-sm text-muted"
            role="status"
          >
            Incidents du lecteur : attente
            {{ proofs[session.id].reader_events.waiting }} · saut
            {{ proofs[session.id].reader_events.seeking }} · pause
            {{ proofs[session.id].reader_events.pause }} · manque de tampon
            {{ proofs[session.id].reader_events.stalled }}. Notifications réseau
            avec tampon conservé :
            {{ proofs[session.id].reader_events.buffered_stall }}.
          </p>
          <details
            v-if="isAdmin && diagnostics[session.id]"
            class="text-sm text-muted"
          >
            <summary>Diagnostic du lecteur</summary>
            <p>
              Segment : premier octet
              {{ diagnostics[session.id].segment_first_byte_ms }} ms ·
              chargement {{ diagnostics[session.id].segment_load_ms }} ms ·
              maximum {{ diagnostics[session.id].max_segment_load_ms }} ms ·
              tampon {{ diagnostics[session.id].buffered_seconds }} s · latence
              {{ diagnostics[session.id].latency_seconds }} s.
            </p>
            <p>Incidents HLS : {{ diagnostics[session.id].errors }}.</p>
            <p v-if="diagnostics[session.id].last_error">
              Dernier incident : {{ diagnostics[session.id].last_error.type }} ·
              {{ diagnostics[session.id].last_error.detail }} · HTTP
              {{ diagnostics[session.id].last_error.http_status || '—' }} ·
              fatal {{ diagnostics[session.id].last_error.fatal }} · position
              {{ diagnostics[session.id].last_error.position }} s.
            </p>
            <p v-if="diagnostics[session.id].last_network_error">
              Dernière erreur réseau :
              {{ diagnostics[session.id].last_network_error.detail }} · HTTP
              {{
                diagnostics[session.id].last_network_error.http_status || '—'
              }}.
            </p>
          </details>
          <ol class="flex flex-col gap-2">
            <li
              v-for="row in session.timeline"
              :key="`${row.id}:${row.start}`"
              class="text-sm"
            >
              <button
                type="button"
                class="underline"
                :disabled="session.mode === 'interactive'"
                @click="seek(session.id, row.start)"
              >
                {{ time(row.start) }} · {{ title(session, row.id) }}
              </button>
              <span v-if="row.transition" class="ml-2 text-muted">{{
                row.transition.reason
              }}</span>
            </li>
          </ol>
        </template>
        <p v-if="session.state === 'failed'" class="mt-2 text-sm">
          Le rendu n’a pas abouti. Essayez une autre sélection ou vérifiez
          l’espace du cache DJ.
        </p>
      </li>
    </ul>
  </section>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { v4 as uuidv4 } from 'uuid'
import UiButton from '/src/components/ui/UiButton.vue'
import MusicDjAudio from '/src/components/library/MusicDjAudio.vue'
import { musicAI } from '/src/model/musicAI'
import { usePlayer } from '/src/model/player'
import { djController } from '/src/model/djController'

const props = defineProps({ selection: { type: Array, default: () => [] } })
const player = usePlayer()
const theme = ref('fete')
const count = ref(
  props.selection.length >= 2 ? Math.min(40, props.selection.length) : 12
)
const useSelection = ref(props.selection.length >= 2)
const sessions = ref([])
const busy = ref(false)
const failure = ref('')
const notice = ref('')
const mode = ref('prepared')
const continuous = ref(true)
const replacements = ref({})
const themes = ref({})
const proofs = ref({})
const diagnostics = ref({})
const preparedEnabled = computed(
  () => musicAI.capabilities.value?.features?.dj_prepared === true
)
const interactiveEnabled = computed(
  () => musicAI.capabilities.value?.features?.dj_interactive === true
)
const isAdmin = computed(
  () => musicAI.capabilities.value?.administrator === true
)
const enabled = computed(
  () => preparedEnabled.value || interactiveEnabled.value
)
const ready = computed(() =>
  mode.value === 'interactive'
    ? djController.ready.value
    : preparedEnabled.value &&
      musicAI.capabilities.value?.dj?.prepared_ready === true
)
const shownSessions = computed(() =>
  sessions.value.filter((session) =>
    session.mode === 'prepared'
      ? preparedEnabled.value
      : interactiveEnabled.value
  )
)
const moods = {
  calme: 'Calme',
  concentration: 'Concentration',
  energie: 'Énergie',
  fete: 'Fête',
  melancolie: 'Mélancolie',
  detente: 'Détente',
}
const players = new Map()
const audioRefs = new Map()
let timer,
  polling = false,
  disposed = false
let pendingRequest = null
const active = (session) =>
  ['preparing', 'rendering', 'playing', 'paused'].includes(session.state)
const time = (seconds) =>
  `${Math.floor(seconds / 60)}:${String(Math.floor(seconds % 60)).padStart(2, '0')}`
const title = (session, id) => {
  const row = session.tracks.find((track) => track.id === id)
  return row ? `${row.title} · ${row.artist}` : 'Titre'
}
const stateLabel = (session) =>
  session.mode === 'interactive' && session.state === 'ready'
    ? 'Terminé'
    : {
        queued: 'En attente',
        preparing: 'Analyse',
        rendering: 'Mixage',
        playing: 'Direct en cours',
        paused: 'Direct en pause',
        ready: 'Prêt à écouter',
        failed: 'Échec du rendu',
        stopped: 'Arrêté',
        cancelled: 'Annulé',
        deleting: 'Suppression en cours',
      }[session.state] || session.state
function register(id, node) {
  if (node) players.set(id, node)
  else {
    players.delete(id)
    audioRefs.delete(id)
  }
}
function audioRef(id) {
  if (!audioRefs.has(id)) audioRefs.set(id, (node) => register(id, node))
  return audioRefs.get(id)
}
function playing(id) {
  failure.value = ''
  player.pause()
  for (const [key, node] of players) if (key !== id) node.pause()
}
function seek(id, seconds) {
  const node = players.get(id)
  node?.seek(seconds)
}
function pauseAll() {
  for (const node of players.values()) node.pause()
}
async function refresh() {
  if (disposed || polling || !enabled.value || !musicAI.account.value) return
  const owner = musicAI.account.value
  polling = true
  try {
    const value = await musicAI.djSessions()
    if (!disposed && owner === musicAI.account.value && enabled.value)
      sessions.value = value
  } catch (error) {
    if (!disposed && owner === musicAI.account.value)
      failure.value = error?.response?.data?.detail || 'État DJ indisponible.'
  } finally {
    polling = false
  }
}
async function create(validation = false, reuse = null) {
  if (busy.value) return
  busy.value = true
  failure.value = ''
  notice.value = ''
  try {
    const selection = {
      mode: reuse ? 'interactive' : mode.value,
      trial:
        !validation &&
        (reuse ? 'interactive' : mode.value) === 'interactive' &&
        musicAI.capabilities.value?.dj?.interactive_ready !== true &&
        musicAI.capabilities.value?.features?.dj_trial === true,
      theme: reuse?.theme || theme.value,
      count: reuse
        ? Math.min(12, reuse.tracks.length)
        : validation
          ? 12
          : count.value,
      continuous:
        validation ||
        ((reuse ? 'interactive' : mode.value) === 'interactive' &&
          continuous.value),
      ids: reuse
        ? reuse.tracks.slice(0, validation ? 12 : 40).map((row) => row.id)
        : !validation && useSelection.value
          ? props.selection.slice(0, 40).map((row) => row.id)
          : [],
    }
    const intent = JSON.stringify([validation, selection])
    if (pendingRequest?.intent !== intent)
      pendingRequest = { intent, id: uuidv4() }
    await (validation ? musicAI.validateDj : musicAI.createDj)({
      ...selection,
      request_id: pendingRequest.id,
    })
    pendingRequest = null
    await refresh()
  } catch (error) {
    failure.value =
      error?.response?.data?.detail || 'Impossible de préparer ce set.'
  } finally {
    busy.value = false
  }
}
async function control(session, action, payload = {}) {
  if (
    djController.session.value?.id === session.id &&
    ['pause', 'resume', 'next'].includes(action)
  ) {
    if (action === 'pause') player.pause()
    else if (action === 'resume') player.play()
    else player.next()
    return
  }
  busy.value = true
  if (action === 'pause') players.get(session.id)?.pause()
  try {
    const result = await musicAI.commandDj(session.id, {
      request_id: uuidv4(),
      action,
      payload,
    })
    notice.value = result.accepted
      ? `Commande reçue. Délai estimé : ${Math.ceil(result.effective_after_seconds || 0)} s.`
      : 'La prochaine transition est déjà engagée.'
    if (action === 'resume') players.get(session.id)?.start()
    await refresh()
  } catch {
    failure.value = 'La commande n’a pas abouti.'
  } finally {
    busy.value = false
  }
}
async function stop(session) {
  busy.value = true
  try {
    if (djController.session.value?.id === session.id) await djController.stop()
    else await musicAI.stopDj(session.id)
    await refresh()
  } catch {
    failure.value = 'Impossible d’arrêter le rendu.'
  } finally {
    busy.value = false
  }
}
async function discard(session) {
  busy.value = true
  players.get(session.id)?.pause()
  players.get(session.id)?.unload()
  try {
    await musicAI.discardDj(session.id)
    await refresh()
  } catch {
    failure.value = 'Impossible de supprimer ce set.'
  } finally {
    busy.value = false
  }
}
watch(
  () => [preparedEnabled.value, interactiveEnabled.value],
  () => {
    if (mode.value === 'prepared' && !preparedEnabled.value)
      mode.value = 'interactive'
    if (mode.value === 'interactive' && !interactiveEnabled.value)
      mode.value = 'prepared'
    for (const session of sessions.value)
      if (
        !(session.mode === 'prepared'
          ? preparedEnabled.value
          : interactiveEnabled.value)
      )
        players.get(session.id)?.unload()
  },
  { immediate: true }
)
watch(
  () => [musicAI.account.value, enabled.value],
  () => {
    pauseAll()
    sessions.value = []
    failure.value = ''
    notice.value = ''
    pendingRequest = null
    refresh()
  }
)
onMounted(() => {
  refresh()
  let tick = 0
  timer = setInterval(() => {
    tick++
    if (
      tick % 5 === 0 ||
      sessions.value.some(
        (s) => active(s) || ['queued', 'deleting'].includes(s.state)
      )
    )
      refresh()
  }, 3000)
})
onUnmounted(() => {
  disposed = true
  clearInterval(timer)
  players.clear()
  audioRefs.clear()
})
</script>
