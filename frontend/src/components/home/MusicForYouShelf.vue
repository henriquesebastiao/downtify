<template>
  <HomeShelf
    v-if="available"
    kind="for-you"
    title="Pour vous"
    :entries="entries"
    :preview-count="4"
    see-all="/music-ai"
    @play="play"
  />
  <p v-if="failure && available" role="status" class="-mt-6 text-sm text-muted">
    {{ failure }}
  </p>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import HomeShelf from './HomeShelf.vue'
import { musicAI } from '/src/model/musicAI'
import { normalizeTrack } from '/src/lib/library'
import { usePlayer } from '/src/model/player'
const recipes = [
  ['detente', 'Détente'],
  ['concentration', 'Concentration'],
  ['energie', 'Motivation'],
  ['calme', 'Calme'],
]
const cards = ref([]),
  failure = ref('')
let generation = 0,
  disposed = false
const available = computed(() =>
  ['daily', 'weekly', 'personalization'].some(
    (key) => musicAI.capabilities.value?.features?.[key]
  )
)
const entries = computed(() =>
  recipes.map(([mood, title]) => {
    const saved = cards.value.find((item) => item.mood === mood) || {
      mood,
      cadence: 'daily',
      count: 0,
      state: 'preparing',
    }
    const card = musicAI.capabilities.value?.features?.daily
      ? saved
      : { ...saved, count: 0, state: 'disabled' }
    return {
      id: mood,
      type: 'playlist',
      title,
      subtitle: card.count
        ? `${card.count} titres · Mix du jour`
        : card.state === 'disabled'
          ? 'À activer dans Paramètres → IA'
          : 'En préparation',
      cover: card.cover_track_ids?.[0]
        ? musicAI.coverUrl(card.cover_track_ids[0])
        : '',
      route: { name: 'MusicAI', query: { cadence: 'daily', mood } },
      playlist: { ...card, title },
    }
  })
)
async function refresh() {
  const mine = ++generation,
    owner = musicAI.account.value
  if (!owner || !available.value) return
  try {
    const value = await musicAI.home()
    if (!disposed && mine === generation && owner === musicAI.account.value) {
      cards.value = value
      failure.value = ''
    }
  } catch {
    if (!disposed && mine === generation)
      failure.value = 'Actualisation différée ; votre musique reste disponible.'
  }
}
async function play(card) {
  const mine = ++generation,
    owner = musicAI.account.value
  try {
    const selected = await musicAI.playlist('daily', card.mood)
    const rows = await musicAI.playable(selected)
    if (!disposed && mine === generation && owner === musicAI.account.value)
      usePlayer().playList(rows.map(normalizeTrack), {
        context: { type: 'playlist', title: card.title },
      })
  } catch {
    if (!disposed && mine === generation)
      failure.value = 'Cette sélection n’est pas disponible pour le moment.'
  }
}
const foreground = () => {
  if (document.visibilityState === 'visible') refresh()
}
watch(
  [
    musicAI.account,
    available,
    () => musicAI.capabilities.value?.features?.daily,
    () => musicAI.capabilities.value?.features?.weekly,
    () => musicAI.capabilities.value?.profile_revision,
  ],
  () => {
    cards.value = []
    refresh()
  },
  { immediate: true }
)
onMounted(() => document.addEventListener('visibilitychange', foreground))
onUnmounted(() => {
  disposed = true
  generation++
  document.removeEventListener('visibilitychange', foreground)
})
</script>
