import { createWebHistory, createRouter } from 'vue-router'
import config from '/src/config'
import HomeView from '/src/views/HomeView.vue'

const LIBRARY_TABS = 'tracks|albums|artists|playlists'
const CHARTS_TABS = 'tracks|albums|artists|playlists'

const routes = [
  { path: '/', name: 'Home', component: HomeView },
  {
    path: '/search/:query?',
    name: 'Search',
    component: () => import('/src/views/SearchView.vue'),
  },
  {
    // A pasted Spotify / YouTube Music link, resolved before downloading.
    path: '/link',
    name: 'Link',
    component: () => import('/src/views/LinkView.vue'),
  },
  {
    // An artist's most popular songs, to pick from before downloading.
    path: '/link/top-songs',
    name: 'TopSongs',
    component: () => import('/src/views/TopSongsView.vue'),
  },
  {
    path: '/queue/:tab(active|queued|done|failed|all)?',
    name: 'Queue',
    // Switching tabs keeps the page (and the mounted queue list).
    meta: { viewKey: 'queue' },
    component: () => import('/src/views/QueueView.vue'),
  },
  {
    path: `/library/:tab(${LIBRARY_TABS})?`,
    name: 'Library',
    component: () => import('/src/views/LibraryView.vue'),
  },
  {
    // Library maintenance: scan what's on disk and repair it.
    path: '/library/upgrade',
    name: 'Upgrade',
    component: () => import('/src/views/UpgradeView.vue'),
  },
  {
    path: '/library/album',
    name: 'Album',
    component: () => import('/src/views/AlbumView.vue'),
  },
  {
    path: '/library/artist',
    name: 'Artist',
    component: () => import('/src/views/ArtistView.vue'),
  },
  {
    path: '/library/playlist',
    name: 'Playlist',
    component: () => import('/src/views/PlaylistView.vue'),
  },
  {
    path: '/monitor/:tab(playlists|artists)?',
    name: 'Monitor',
    // Switching tabs keeps the page (and what was typed in it).
    meta: { viewKey: 'monitor' },
    component: () => import('/src/views/MonitorView.vue'),
  },
  {
    // Discover and the Finder on one page: the Finder's search box on top,
    // Discover's suggestions below - or, while a search is on (`?q=`), what
    // the Finder found (see DiscoverHubView).
    path: '/discover',
    name: 'Discover',
    component: () => import('/src/views/DiscoverHubView.vue'),
  },
  {
    // What a Finder result opens: artist, albums and one album's tracks
    // side by side (`?artist=&album=&track=`, Deezer ids). A page of its
    // own, the columns need its whole height. One path, so moving between
    // artists doesn't remount the page.
    path: '/discover/finder/browse',
    name: 'FinderBrowse',
    component: () => import('/src/views/FinderBrowseView.vue'),
  },
  {
    path: '/podcasts',
    name: 'Podcasts',
    component: () => import('/src/views/PodcastsView.vue'),
  },
  {
    path: '/podcasts/show',
    name: 'PodcastShow',
    component: () => import('/src/views/PodcastShowView.vue'),
  },
  {
    // Deezer's own "what's trending" chart: tracks, albums, artists and
    // playlists, one tab each.
    path: `/charts/:tab(${CHARTS_TABS})?`,
    name: 'Charts',
    component: () => import('/src/views/ChartsView.vue'),
  },
  {
    // Tracks similar to one track, via YouTube Music's radio mix.
    path: '/similar',
    name: 'Similar',
    component: () => import('/src/views/SimilarView.vue'),
  },
  {
    path: '/settings/:section?',
    name: 'Settings',
    component: () => import('/src/views/SettingsView.vue'),
  },
  // 2.x paths, kept so bookmarks and the PWA start URL still work.
  { path: '/download', redirect: { name: 'Queue' } },
  { path: '/player', redirect: { name: 'Home', query: { np: '1' } } },
  { path: '/:pathMatch(.*)*', redirect: { name: 'Home' } },
]

const router = createRouter({
  history: createWebHistory(config.BASEURL),
  routes,
  scrollBehavior(to, from, saved) {
    // Opening/closing Now playing (?np=1) mustn't move the page.
    if (to.path === from.path) return false
    return saved || { top: 0 }
  },
})

export default router
