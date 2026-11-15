<template>
  <div class="flex flex-col gap-6">
    <div class="flex items-center gap-3">
      <h2 class="text-display text-2xl font-semibold">IA</h2>
      <ExperimentalBadge
        hint="Fonctions IA expérimentales. La qualité dépend de l’analyse locale ; chaque module peut être désactivé."
      />
    </div>
    <p class="text-sm text-muted">
      Choisissez vos fonctions musicales. Vos préférences sont partagées entre
      le web et Android.
    </p>
    <div role="tablist" aria-label="Fonctions IA" class="flex flex-wrap gap-2">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        type="button"
        role="tab"
        :aria-selected="mode === tab.id"
        :aria-controls="`ai-${tab.id}`"
        class="rounded-control border px-4 py-2 text-sm font-semibold"
        :class="
          mode === tab.id
            ? 'border-accent bg-accent/10 text-accent'
            : 'border-line-2 text-muted'
        "
        @click="mode = tab.id"
      >
        {{ tab.label }}
      </button>
    </div>
    <p v-if="failure || musicAI.error.value" role="alert" class="text-danger">
      {{ failure || musicAI.error.value }}
    </p>
    <section :id="`ai-${mode}`" role="tabpanel" class="flex flex-col gap-5">
      <SettingGroup
        :title="
          mode === 'dj' ? 'Votre mode DJ' : 'Vos playlists personnalisées'
        "
        description="Chaque fonction peut être désactivée séparément. Les favoris et les copies de playlists enregistrées sont conservés."
      >
        <label
          v-for="(label, key) in shownFeatures"
          :key="key"
          class="flex items-center justify-between gap-4 border-b border-line-2 py-4 last:border-0"
        >
          <span class="text-sm">{{ label }}</span>
          <input
            type="checkbox"
            :aria-label="label"
            :disabled="busy || !musicAI.preferences.value"
            :checked="musicAI.preferences.value?.[key] || false"
            @change="toggle(key, $event.target.checked)"
          />
        </label>
      </SettingGroup>
      <p v-if="mode === 'playlists'" class="text-sm text-muted">
        Retrouvez vos quatre sélections sous les playlists favorites dans Ma
        musique. Renouvellement à 04 h ; sélection hebdomadaire le lundi à 04 h
        15, heure de Paris.
      </p>
      <RouterLink
        v-if="mode === 'playlists'"
        to="/music-ai"
        class="text-sm font-semibold text-accent"
        >Voir mes playlists personnalisées →</RouterLink
      >
      <template v-else>
        <p class="text-sm text-muted">
          Préparez un set à l’avance ou mixez en direct sur le serveur. En
          direct, le prochain titre et le thème changent à la prochaine
          transition disponible.
        </p>
        <p class="text-sm text-muted">
          L’essai bêta autorise un moteur disponible avant sa qualification
          d’une heure. Il ne garantit pas une lecture continue sans rupture et
          peut être désactivé à tout moment.
        </p>
        <RouterLink to="/music-dj" class="text-sm font-semibold text-accent"
          >Ouvrir le studio DJ →</RouterLink
        >
        <p
          v-if="!enabled('dj_prepared') && !enabled('dj_interactive')"
          class="text-sm text-muted"
        >
          Activez un mode DJ pour ouvrir le studio. L’administrateur doit aussi
          autoriser ce mode sur le serveur.
        </p>
      </template>
      <details
        v-if="isAdmin"
        class="rounded-panel border border-line-2 bg-surface p-5"
      >
        <summary class="cursor-pointer font-semibold">
          Activation sur le serveur
        </summary>
        <p class="my-3 text-sm text-muted">
          Ces interrupteurs s’appliquent à tous les utilisateurs, en plus de
          leurs préférences personnelles.
        </p>
        <label
          v-for="(label, key) in shownFeatures"
          :key="key"
          class="flex items-center justify-between gap-4 py-3"
        >
          <span class="text-sm">{{ label }}</span
          ><input
            type="checkbox"
            :aria-label="`Serveur : ${label}`"
            :disabled="busy || !globalFlags"
            :checked="globalFlags?.[key] || false"
            @change="toggleGlobal(key, $event.target.checked)"
          />
        </label>
        <template v-if="mode === 'playlists'">
          <p v-if="analysis" role="status" class="my-3 text-sm text-muted">
            {{ analysis.analyzed }} titres analysés sur
            {{ analysis.known }} observés.
            {{
              analysis.paused
                ? 'Analyse suspendue.'
                : 'Analyse progressive en arrière-plan.'
            }}
          </p>
          <div class="flex flex-wrap gap-3">
            <UiButton :disabled="busy" @click="analysisAction('status')"
              >Actualiser l’état</UiButton
            >
            <UiButton
              :disabled="busy || analysis?.paused"
              @click="analysisAction('retry')"
              >Relancer les échecs</UiButton
            >
            <UiButton
              v-if="analysis?.paused"
              :disabled="busy"
              @click="analysisAction('resume')"
              >Reprendre l’analyse</UiButton
            >
            <UiButton :disabled="busy" @click="analysisAction('erase')"
              >Effacer les analyses et suspendre</UiButton
            >
          </div>
        </template>
      </details>
      <SettingGroup
        v-if="mode === 'playlists'"
        title="Confidentialité"
        description="Effacer le profil retire les écoutes utilisées pour personnaliser les propositions, sans toucher aux favoris ou aux playlists enregistrées."
      >
        <UiButton :disabled="busy" @click="forget"
          >Effacer mon profil d’écoute</UiButton
        >
        <p v-if="forgotten" role="status" class="mt-3 text-sm">
          Profil d’écoute effacé.
        </p>
      </SettingGroup>
    </section>
    <a
      v-if="musicAI.capabilities.value?.source_available"
      :href="musicAI.sourceUrl"
      class="text-sm text-muted underline"
      >Sources, licences et construction</a
    >
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import ExperimentalBadge from '/src/components/ui/ExperimentalBadge.vue'
import SettingGroup from './SettingGroup.vue'
import UiButton from '/src/components/ui/UiButton.vue'
import MusicDjPanel from '/src/components/library/MusicDjPanel.vue'
import { musicAI } from '/src/model/musicAI'
import { useAuth } from '/src/model/auth'

const route = useRoute()
const { isAdmin } = useAuth()
const mode = ref(route.query.mode === 'dj' ? 'dj' : 'playlists')
const tabs = [
  { id: 'playlists', label: 'Playlists personnalisées' },
  { id: 'dj', label: 'DJ' },
]
const features = {
  personalization: 'Personnalisation et nouvelles écoutes',
  similarity: 'Musiques basées sur un titre',
  daily: 'Mixes du jour',
  weekly: 'Mixes de la semaine',
  external_beta: 'Découverte externe — bêta',
  dj_prepared: 'Sets DJ préparés',
  dj_weekly: 'Sets DJ hebdomadaires personnalisés',
  dj_interactive: 'DJ en temps réel',
  dj_trial: 'Autoriser le DJ non qualifié — essai bêta volontaire',
}
const shownFeatures = computed(() =>
  Object.fromEntries(
    Object.entries(features).filter(
      ([key]) =>
        key.startsWith('dj_') === (mode.value === 'dj') &&
        (key !== 'dj_weekly' ||
          musicAI.capabilities.value?.dj_weekly_sets === true)
    )
  )
)
const busy = ref(false),
  failure = ref(''),
  globalFlags = ref(null),
  analysis = ref(null),
  forgotten = ref(false)
const enabled = (key) => musicAI.capabilities.value?.features?.[key] === true
async function attempt(work) {
  busy.value = true
  failure.value = ''
  try {
    await work()
  } catch (error) {
    failure.value =
      error?.response?.data?.detail || 'La modification n’a pas abouti.'
  } finally {
    busy.value = false
  }
}
const toggle = (key, value) => attempt(() => musicAI.set(key, value))
const toggleGlobal = (key, value) =>
  attempt(async () => {
    await musicAI.setGlobal(key, value)
    globalFlags.value = await musicAI.globalFeatures()
  })
const analysisAction = (action) =>
  attempt(async () => {
    if (action === 'erase') await musicAI.eraseAnalyses()
    if (action === 'resume') await musicAI.resumeAnalysis()
    if (action === 'retry') await musicAI.retryAnalyses()
    analysis.value = await musicAI.analysisStatus()
  })
const forget = () =>
  attempt(async () => {
    await musicAI.forget()
    forgotten.value = true
  })
watch(
  () => route.query.mode,
  (value) => {
    mode.value = value === 'dj' ? 'dj' : 'playlists'
  }
)
watch(
  () => musicAI.account.value,
  () => {
    globalFlags.value = null
    analysis.value = null
    forgotten.value = false
  }
)
watch(
  isAdmin,
  (value) => {
    if (value)
      attempt(async () => {
        globalFlags.value = await musicAI.globalFeatures()
        analysis.value = await musicAI.analysisStatus()
      })
  },
  { immediate: true }
)
onMounted(() => musicAI.refresh())
</script>
