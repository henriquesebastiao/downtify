// Sidebar tree. `page` is the Markdown file under docs/; titles and icons
// are filled in from each page (see config.mjs), group and page titles are
// translated in locales/<code>.mjs (`nav.groups`, `nav.pages`).
//
// Feature pages are grouped by area. A group with an `icon` is a feature
// area: the home page lists every one of them as a card (HomeFeatures.vue).
export const NAV = [
  { title: 'Home', page: 'index.md' },
  {
    title: 'Getting Started',
    items: [
      { title: 'Overview', page: 'getting-started/index.md' },
      { title: 'Installation', page: 'getting-started/installation.md' },
      { title: 'Docker Compose', page: 'getting-started/docker-compose.md' },
      { title: 'One-Click Install', page: 'getting-started/one-click.md' },
      {
        title: 'Environment Variables',
        page: 'getting-started/environment-variables.md',
      },
      { title: 'Database', page: 'database.md' },
    ],
  },
  { title: 'All Features', page: 'features/index.md' },
  {
    title: 'Find Music',
    icon: 'lucide/compass',
    items: [
      { title: 'Discover', page: 'features/discover.md' },
      { title: 'Charts', page: 'features/charts.md' },
      { title: 'Finder', page: 'features/finder.md' },
      { title: 'Similar', page: 'features/similar.md' },
      { title: 'Top Songs', page: 'features/top-songs.md' },
      { title: 'Support the Artist', page: 'features/support-artists.md' },
    ],
  },
  {
    title: 'Download',
    icon: 'lucide/download',
    items: [
      { title: 'Download Settings', page: 'features/download-settings.md' },
      { title: 'Download Queue', page: 'features/download-queue.md' },
      {
        title: 'Download Exclusions',
        page: 'features/download-exclusions.md',
      },
      { title: 'Library Import (CSV)', page: 'features/library-import.md' },
      { title: 'YouTube Cookies', page: 'features/youtube-cookies.md' },
    ],
  },
  {
    title: 'Library',
    icon: 'lucide/library',
    items: [
      { title: 'Library Catalog', page: 'features/library-catalog.md' },
      {
        title: 'Existing music folders',
        page: 'features/external-library.md',
      },
      { title: 'Upgrade Library', page: 'features/library-upgrade.md' },
      {
        title: 'Identify Songs by Sound',
        page: 'features/acoustid.md',
      },
      { title: 'Replace Audio', page: 'features/replace-audio.md' },
      {
        title: 'Artist Photo, Banner & Bio',
        page: 'features/artist-images.md',
      },
      { title: 'Storage & Usage', page: 'features/storage-usage.md' },
      { title: 'Music Trash', page: 'features/music-trash.md' },
      { title: 'Doctor', page: 'features/doctor.md' },
    ],
  },
  {
    title: 'Tags & Files',
    icon: 'lucide/tag',
    items: [
      { title: 'File Organization', page: 'features/file-organization.md' },
      { title: 'Lyrics', page: 'features/lyrics.md' },
      { title: 'Music Videos', page: 'features/music-videos.md' },
      { title: 'Explicit Marker', page: 'features/explicit-marker.md' },
    ],
  },
  {
    title: 'Playlists',
    icon: 'lucide/list-music',
    items: [
      { title: 'Playlist Monitor', page: 'features/playlist-monitor.md' },
      { title: 'Playlist display names', page: 'features/playlist-names.md' },
      { title: 'Favorite playlists', page: 'features/playlist-favorites.md' },
      {
        title: 'Hidden playlist songs',
        page: 'features/hidden-playlist-songs.md',
      },
      {
        title: 'Collaborative playlists',
        page: 'features/collaborative-playlists.md',
      },
      {
        title: 'Playlist order & repeated songs',
        page: 'features/playlist-order.md',
      },
      { title: 'Playlist Cover Art', page: 'features/playlist-cover-art.md' },
      { title: 'M3U Export', page: 'features/m3u-export.md' },
      {
        title: 'Import existing playlists',
        page: 'features/external-playlists.md',
      },
    ],
  },
  {
    title: 'Listening',
    icon: 'lucide/headphones',
    items: [
      { title: 'Built-in Player', page: 'features/player.md' },
      {
        title: 'Volume normalization',
        page: 'features/playback-normalization.md',
      },
      { title: 'Liked Songs', page: 'features/liked-songs.md' },
      { title: 'Podcasts', page: 'features/podcasts.md' },
      { title: 'Mobile Apps', page: 'features/mobile-apps.md' },
      { title: 'Install as an App (PWA)', page: 'features/pwa.md' },
    ],
  },
  {
    title: 'Sources & Integrations',
    icon: 'lucide/plug',
    items: [
      { title: 'SoundCloud', page: 'features/soundcloud.md' },
      { title: 'Deemix', page: 'features/deemix.md' },
      { title: 'slskd & Navidrome', page: 'features/slskd-navidrome.md' },
      { title: 'Ratings from Deezer', page: 'features/navidrome-ratings.md' },
      { title: 'Aurral', page: 'features/aurral.md' },
    ],
  },
  {
    title: 'Server & Accounts',
    icon: 'lucide/server',
    items: [
      { title: 'Users & Sign-in', page: 'features/users.md' },
      { title: 'Storage Quotas', page: 'features/storage-quotas.md' },
      { title: 'Server Settings', page: 'features/server.md' },
      { title: 'Backups', page: 'features/backups.md' },
      { title: 'Notifications', page: 'features/notifications.md' },
      { title: 'Library-only mode', page: 'features/library-only.md' },
      { title: 'Outbound Proxy', page: 'features/outbound-proxy.md' },
      { title: 'Update Notifications', page: 'features/updates.md' },
      {
        title: 'Internationalization',
        page: 'features/internationalization.md',
      },
    ],
  },
  { title: 'How It Works', page: 'how-it-works.md' },
  { title: 'Troubleshooting', page: 'troubleshooting.md' },
  { title: 'API Reference', page: 'api-reference.md' },
  { title: 'Mobile Client Contract', page: 'mobile-client-contract.md' },
  { title: 'Contributing', page: 'contributing.md' },
  { title: 'Changelog', page: 'changelog.md' },
]
