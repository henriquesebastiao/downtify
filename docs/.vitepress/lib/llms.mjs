// /llms.txt: what Downtify is and where each topic lives, in the Markdown
// format AI assistants look for (https://llmstxt.org). Written by the
// build (config.mjs `buildEnd`) from the sidebar, so it never goes stale.

const FACTS = [
  'Free and open source (AGPL-3.0), self-hosted, one Docker image for amd64 and arm64.',
  'Takes Spotify, YouTube Music and Deezer links (tracks, albums, playlists, artists), SoundCloud track links or a plain search, and CSV exports from Soundiiz, TuneMyMusic and Exportify.',
  "Needs no Spotify account, API key or Premium: track details come from public pages, and the audio is the closest YouTube Music match by length (YouTube as a fallback; SoundCloud, the user's own Soulseek (slskd) or Deemix server are optional sources).",
  'Writes MP3, FLAC, M4A, OGG or Opus (or keeps the source audio), with cover art, every credited artist, album, year, track number, the explicit mark and plain or time-synced lyrics (LRCLIB, NetEase, Kugou).',
  'Plays the library too: a web player with synced lyrics and karaoke, liked songs, playlists, podcasts, an installable web app, and Android and iOS apps.',
  'Keeps Spotify, Deezer and YouTube Music playlists, and Spotify and YouTube Music artists, in sync (Playlist Monitor), and writes M3U playlists that Jellyfin, Navidrome and Plex pick up.',
  'Accounts for several people, with OpenID Connect sign-in; SQLite or PostgreSQL.',
]

/**
 * `nav`: the sidebar tree (nav.mjs); `titles`: English `nav` titles;
 * `url(page)` and `describe(page)` give a page's address and summary.
 */
export function llmsText({
  site,
  nav,
  titles,
  url,
  describe,
  summary,
  version,
}) {
  const line = ({ page, title }) =>
    `- [${titles.pages[page] || title}](${url(page)}): ${describe(page)}`
  const out = [
    '# Downtify',
    '',
    `> ${summary}`,
    '',
    ...FACTS.map((fact) => `- ${fact}`),
    '',
    `Current version: ${version}. Quick start:`,
    '',
    '```bash',
    'docker run -d -p 8000:8000 --name downtify \\',
    '  -v /path/to/music:/downloads -v downtify_data:/data \\',
    '  ghcr.io/henriquesebastiao/downtify',
    '```',
    '',
    'Then open http://localhost:8000 and sign in as admin / downtify.',
    '',
    `Source code: https://github.com/henriquesebastiao/downtify · Documentation: ${site}`,
  ]
  let loose = []
  const flush = () => {
    if (!loose.length) return
    out.push('', '## Documentation', '', ...loose.map(line))
    loose = []
  }
  for (const entry of nav) {
    if (!entry.items) {
      loose.push(entry)
      continue
    }
    flush()
    const heading = titles.groups[entry.title] || entry.title
    out.push('', `## ${heading}`, '', ...entry.items.map(line))
  }
  flush()
  return `${out.join('\n')}\n`
}
