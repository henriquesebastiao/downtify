// The projected karaoke window (karaoke.html): a page of its own, so it
// never loads the player and can't play, save or count anything itself.
import { createApp } from 'vue'
import KaraokeStage from './components/player/KaraokeStage.vue'

import './index.css'

createApp(KaraokeStage).mount('#app')
