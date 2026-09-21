// Sidebar tree — same sections and order the zensical site had.
// `page` is the Markdown file under docs/; titles and icons are filled in
// from each page (see config.mjs).
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
    ],
  },
  {
    title: 'Features',
    items: [
      { title: 'Overview', page: 'features/index.md' },
      { title: 'Download Settings', page: 'features/download-settings.md' },
      { title: 'Playlist Monitor', page: 'features/playlist-monitor.md' },
      { title: 'Top Songs', page: 'features/top-songs.md' },
      { title: 'Library Import (CSV)', page: 'features/library-import.md' },
      { title: 'Built-in Player', page: 'features/player.md' },
      { title: 'Liked Songs', page: 'features/liked-songs.md' },
      { title: 'Podcasts', page: 'features/podcasts.md' },
      { title: 'slskd & Navidrome', page: 'features/slskd-navidrome.md' },
      { title: 'Library Catalog', page: 'features/library-catalog.md' },
      { title: 'Upgrade Library', page: 'features/library-upgrade.md' },
      { title: 'M3U Export', page: 'features/m3u-export.md' },
      { title: 'Playlist Cover Art', page: 'features/playlist-cover-art.md' },
      { title: 'File Organization', page: 'features/file-organization.md' },
      { title: 'Lyrics', page: 'features/lyrics.md' },
      { title: 'YouTube Cookies', page: 'features/youtube-cookies.md' },
      {
        title: 'Internationalization',
        page: 'features/internationalization.md',
      },
      { title: 'Install as an App (PWA)', page: 'features/pwa.md' },
      { title: 'Update Notifications', page: 'features/updates.md' },
    ],
  },
  { title: 'How It Works', page: 'how-it-works.md' },
  { title: 'Troubleshooting', page: 'troubleshooting.md' },
  { title: 'API Reference', page: 'api-reference.md' },
  { title: 'Contributing', page: 'contributing.md' },
  { title: 'Changelog', page: 'changelog.md' },
]
