import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'

import { usePlayer } from './player'
import { useSettingsManager } from './settings'
import { miniPlayerVisibility } from './miniPlayerVisibility'

// Session-only: collapsing the bar reopens it on the next visit rather
// than staying hidden forever because of one earlier dismissal.
const collapsed = ref(false)

export function useMiniPlayer() {
  const player = usePlayer()
  const sm = useSettingsManager()
  const route = useRoute()

  const visibility = computed(() =>
    miniPlayerVisibility({
      enabled: sm.settings.value.mini_player_enabled,
      hasCurrentTrack: !!player.currentTrack.value,
      isPlayerRoute: route.name === 'Player',
      collapsed: collapsed.value,
    })
  )

  const showBar = computed(() => visibility.value.showBar)
  const showRestoreButton = computed(() => visibility.value.showRestoreButton)

  return { collapsed, showBar, showRestoreButton }
}
