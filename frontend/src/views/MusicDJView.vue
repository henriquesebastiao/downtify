<template>
  <main class="mx-auto max-w-6xl space-y-6 px-4 py-8 sm:px-6">
    <header class="flex items-start justify-between gap-4">
      <div>
        <h1 class="text-display text-3xl font-bold">
          DJ <span class="text-sm text-accent">Bêta</span>
        </h1>
        <p class="mt-2 text-muted">
          Créez vos mixes avec des transitions adaptées, depuis votre musique ou
          la file en cours.
        </p>
      </div>
      <RouterLink
        to="/settings/ai?mode=dj"
        class="text-sm font-semibold text-accent"
        >Paramètres IA</RouterLink
      >
    </header>
    <section class="rounded-panel border border-line-2 bg-surface p-5">
      <h2 class="text-xl font-semibold">Votre file</h2>
      <UiButton
        class="mt-3"
        :disabled="djController.busy.value || !djController.ready.value"
        @click="djController.startQueue"
        >Activer le DJ sur la file</UiButton
      >
      <p v-if="!djController.ready.value" class="mt-3 text-sm text-muted">
        Activez le DJ dans Paramètres → IA. Un moteur non qualifié reste
        accessible uniquement en essai bêta volontaire.
      </p>
      <p v-if="djController.notice.value" class="mt-3 text-sm" role="status">
        {{ djController.notice.value }}
      </p>
    </section>
    <section
      class="grid grid-cols-2 gap-3 sm:grid-cols-4"
      aria-label="Thèmes du DJ continu"
    >
      <UiButton
        v-for="theme in themes"
        :key="theme[0]"
        :disabled="!djController.ready.value || djController.busy.value"
        @click="djController.startTheme(theme[1], theme[2])"
        >{{ theme[0] }}</UiButton
      >
    </section>
    <p v-if="djController.failure.value" role="alert" class="text-danger">
      {{ djController.failure.value }}
    </p>
    <MusicDjPanel :selection="musicAI.djSelection.value" />
  </main>
</template>
<script setup>
import { onMounted } from 'vue'
import MusicDjPanel from '/src/components/library/MusicDjPanel.vue'
import UiButton from '/src/components/ui/UiButton.vue'
import { musicAI } from '/src/model/musicAI'
import { djController } from '/src/model/djController'
const themes = [
  ['Détente', 'detente', 'library'],
  ['Concentration', 'concentration', 'library'],
  ['Motivation', 'energie', 'library'],
  ['Fête', 'fete', 'library'],
  ['Rap', 'energie', 'rap'],
  ['Rock', 'energie', 'rock'],
  ['Électro', 'fete', 'electro'],
]
onMounted(() => musicAI.refresh())
</script>
