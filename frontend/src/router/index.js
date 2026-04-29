import { createWebHistory, createRouter } from 'vue-router'
import Home from '/src/views/Front.vue'
import Search from '/src/views/Search.vue'
import Download from '/src/views/Download.vue'
import List from '/src/views/Downloads.vue'
import Monitor from '/src/views/Monitor.vue'
import Player from '/src/views/Player.vue'
import config from '/src/config'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: Home,
  },
  {
    path: '/search/:query',
    name: 'Search',
    component: Search,
  },
  {
    path: '/download',
    name: 'Download',
    component: Download,
  },
  {
    path: '/list',
    name: 'List',
    component: List,
  },
  {
    path: '/monitor',
    name: 'Monitor',
    component: Monitor,
  },
  {
    path: '/player',
    name: 'Player',
    component: Player,
  },
]

const router = createRouter({
  history: createWebHistory(config.BASEURL),
  routes,
})

export default router
