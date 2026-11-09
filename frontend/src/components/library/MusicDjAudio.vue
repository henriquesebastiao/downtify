<template>
  <button
    type="button"
    class="my-3 rounded-control border border-line-2 px-4 py-2 font-semibold hover:bg-accent/10"
    @click="start"
  >
    {{
      player.dj.value?.id === session.id
        ? 'Ouvrir le lecteur DJ'
        : 'Écouter dans le lecteur'
    }}
  </button>
</template>
<script setup>
import { usePlayer } from '/src/model/player'
import { djController } from '/src/model/djController'
import { useNowPlaying } from '/src/model/ui'
const props = defineProps({ session: { type: Object, required: true } })
const player = usePlayer(),
  nowPlaying = useNowPlaying()
async function start() {
  if (player.dj.value?.id !== props.session.id)
    await djController.listen(props.session)
  nowPlaying.open()
}
function pause() {
  if (player.dj.value?.id === props.session.id) player.pause()
}
function unload() {
  if (player.dj.value?.id === props.session.id) player.detachDj()
}
function seek(seconds) {
  if (
    player.dj.value?.id === props.session.id &&
    props.session.mode === 'prepared'
  )
    player.seek(seconds - (player.dj.value.row?.start || 0))
}
defineExpose({ start, pause, unload, seek })
</script>
