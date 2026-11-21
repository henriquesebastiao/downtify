---
layout: home
title: Downtify
titleTemplate: "Self-hosted Spotify downloader and music player"
description: "Self-hosted Spotify downloader with a built-in player. Paste a Spotify, YouTube Music, Deezer or SoundCloud link and get tagged MP3 or FLAC files. No API keys."
icon: lucide/house
hero:
  eyebrow: Self-hosted music downloader
  headline:
    - Paste a link.
    - Get the music.
  lead: A self-hosted music downloader with a player built in. Paste a Spotify, YouTube Music, Deezer or SoundCloud link and get a perfectly tagged library, ready to play in your browser, on your phone or in your media server.
  note: No Spotify account, no API keys, no Premium.
  actions:
    - text: Get started
      link: /getting-started/installation/
      primary: true
    - text: Source on GitHub
      link: https://github.com/henriquesebastiao/downtify
      icon: github
  shields:
    - alt: Release
      src: https://img.shields.io/github/v/release/henriquesebastiao/downtify?color=1AD05C&label=release
      link: https://github.com/henriquesebastiao/downtify/releases
    - alt: Docker pulls
      src: https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fghcr-badge.elias.eu.org%2Fapi%2Fhenriquesebastiao%2Fdowntify%2Fdowntify&query=downloadCount&label=docker%20pulls&color=1AD05C
      link: https://github.com/henriquesebastiao/downtify/pkgs/container/downtify
    - alt: GitHub stars
      src: https://img.shields.io/github/stars/henriquesebastiao/downtify?style=flat&label=stars&color=1AD05C
      link: https://star-history.com/#henriquesebastiao/downtify&Date
    - alt: License
      src: https://img.shields.io/github/license/henriquesebastiao/downtify?color=1AD05C
      link: https://github.com/henriquesebastiao/downtify/blob/main/LICENSE
video:
  src: /assets/media/downtify-demo.mp4
  poster: /assets/media/downtify-demo-poster.webp
  label: 'Downtify in 44 seconds: paste a playlist link, download it in one click, keep it in sync and play it with synced lyrics, on the desktop and on a phone.'
why:
  - icon: link
    title: One link is all it takes
    text: Paste a song, an album, a whole playlist or an artist from Spotify, YouTube Music, Deezer or SoundCloud, or just type what you want to hear. Downtify finds the audio and brings it home.
    link: /how-it-works/
  - icon: tag
    title: Files worth keeping
    text: Every file carries its cover art, every credited artist, the album, year, track number and lyrics, time-synced when they exist. MP3, FLAC, M4A, OGG or Opus, or the source audio exactly as it came.
    link: /features/download-settings/
  - icon: music
    title: Your own streaming service
    text: A full player in the browser, with synced lyrics, karaoke, a queue, liked songs, playlists and podcasts. Apps for Android and iOS take your library with you, offline too.
    link: /features/player/
  - icon: radar
    title: Set it and forget it
    text: Watch playlists and artists. New songs and new releases download on their own, on the schedule you choose.
    link: /features/playlist-monitor/
  - icon: server
    title: Made for your home server
    text: One Docker image for amd64 and arm64, SQLite or PostgreSQL, accounts for everyone at home with optional single sign-on, and playlists that Jellyfin, Navidrome and Plex pick up.
    link: /getting-started/
  - icon: shield
    title: No strings attached
    text: No Spotify API key, no developer account, no Premium. The app has no ads, no analytics and nothing behind a paywall. It is free and open source.
    link: /contributing/
showcase:
  - shot: now-playing
    label: Now playing
    caption: Lyrics follow the song, line by line, next to the cover and what's up next.
    alt: The full-screen Now Playing view, with the album cover, time-synced lyrics with the current line highlighted, and the queue.
  - shot: karaoke
    label: Karaoke
    caption: Big lyrics that fill in as each line is sung, ready to open on a second screen.
    alt: The karaoke view, with large lyrics filling in over a moving background in the colors of the cover.
  - shot: home
    label: Home
    caption: Paste a link or search for something new, and pick up where you left off.
    alt: The home page, with a box to paste a link or search, library statistics, the album being played and recently added albums.
  - shot: library
    label: Library
    caption: Albums, artists, playlists and tracks, sorted and filtered your way.
    alt: The Library page, with a grid of album covers and tabs for albums, artists, playlists and tracks.
  - shot: playlist
    label: Playlists
    caption: Playlists of your own, with their own cover, to play, share or download as a ZIP.
    alt: A playlist page, with its cover, its buttons and its songs with album, format and release date.
  - shot: phones
    label: On your phone
    caption: The same app on your phone, installable from the browser.
    alt: Downtify on three phones, showing the home page, Now Playing and the Library.
pipeline:
  - icon: link
    title: Paste a link
    text: Spotify, YouTube Music, Deezer or SoundCloud. Or just type a song.
  - icon: search
    title: Find the audio
    text: The closest match on YouTube Music, checked by length. Other sources if you want them.
  - icon: download
    title: Download & tag
    text: yt-dlp and ffmpeg fetch it. Cover art, lyrics and tags go into the file.
  - icon: music
    title: Play anywhere
    text: In the browser, on your phone, or in Jellyfin, Navidrome and Plex.
quickStart:
  - text: Installation guide
    link: /getting-started/installation/
    primary: true
  - text: Docker Compose
    link: /getting-started/docker-compose/
  - text: One-click install
    link: /getting-started/one-click/
apps:
  - icon: smartphone
    title: Downtify for Android
    text: The official app. It finds your server on your network, streams in original quality on Wi-Fi and a smaller one on mobile data, keeps songs offline and works with Android Auto. Still in testing, on GitHub Releases and Obtainium.
    link: https://github.com/henriquesebastiao/downtify-android
  - icon: tablet-smartphone
    title: Downtify for iOS
    text: Built by a community member for iPhone and iPad (iOS 17 or later), with offline songs and lock-screen controls. The public beta is on TestFlight.
    link: https://github.com/michaelmoskie/Downtify-IOS-Client
community:
  - text: Star on GitHub
    link: https://github.com/henriquesebastiao/downtify
    icon: star
    primary: true
  - text: Sponsor
    link: https://github.com/sponsors/henriquesebastiao
    icon: heart
  - text: Translate
    link: /features/internationalization/
    icon: languages
  - text: Contribute
    link: /contributing/
    icon: git-pull-request
---

## Why Downtify

<HomeHighlights :items="$frontmatter.why" />

## A closer look

<HomeShowcase :items="$frontmatter.showcase" />

## How it works

Downtify needs no Spotify API key and never downloads from Spotify. It reads what a link points to from public sources, picks the YouTube Music audio whose length matches best, downloads it with `yt-dlp`, converts it with `ffmpeg` and tags it with `mutagen`, all in one Docker container. YouTube steps in when nothing matches well, and SoundCloud, Soulseek and Deemix join in if you turn them on. [Every step, in detail](how-it-works.md).

<HomePipeline :steps="$frontmatter.pipeline" />

## What you can paste

| Source        | What works                         | Example                             |
| ------------- | ---------------------------------- | ----------------------------------- |
| Spotify       | Tracks, albums, playlists, artists | `open.spotify.com/playlist/…`       |
| YouTube Music | Songs, albums, playlists, artists  | `music.youtube.com/playlist?list=…` |
| YouTube       | Videos                             | `youtube.com/watch?v=…`             |
| Deezer        | Tracks, albums, playlists, artists | `deezer.com/album/…`                |
| SoundCloud    | Tracks                             | `soundcloud.com/artist/track`       |
| Search        | Whatever you would type            | `The Night Owls Do I Still Recall`  |
| CSV           | Library exports                    | Soundiiz, TuneMyMusic, Exportify    |

## Everything it does

Every feature has its own page, with every option explained. [All features at a glance](features/index.md).

<HomeFeatures />

## Up and running in a minute

```bash
docker run -d -p 8000:8000 --name downtify \
  -v /path/to/music:/downloads \
  -v downtify_data:/data \
  --restart unless-stopped \
  ghcr.io/henriquesebastiao/downtify
```

Open [`localhost:8000`](http://localhost:8000), sign in as **admin** with the password **downtify** and paste a link. Change that password in **Settings → General** right away. Your music lands in `/path/to/music`, tags and all.

<HomeActions :actions="$frontmatter.quickStart" />

## Questions people ask

::: details Do I need a Spotify account, Premium or an API key?
No. Downtify reads track, album and playlist details from Spotify's public embed pages, so it needs no credentials of any kind, and the audio never comes from Spotify. See [How it works](how-it-works.md).
:::

::: details Where does the audio come from, and how good is it?
From YouTube Music by default: the result whose length matches the song best, with YouTube as a fallback. Pick MP3, FLAC, M4A, OGG or Opus at the bitrate you want, or keep the best audio the source has without re-encoding it. Lossless files come from sources you add yourself: your own [Soulseek (slskd)](features/slskd-navidrome.md) server, whose files keep their original format, or a [Deemix](features/deemix.md) server. See [Download settings](features/download-settings.md).
:::

::: details Does it work with Jellyfin, Navidrome or Plex?
Yes. Files are tagged the way media servers expect, filed in `Artist/Album/` folders, and every playlist gets a standard M3U file they pick up. Navidrome can also get its playlists synced and ratings set from Deezer. See [File organization](features/file-organization.md) and [M3U export](features/m3u-export.md).
:::

::: details Will it run on a Raspberry Pi or a NAS?
The image is built for both `amd64` and `arm64`, and Umbrel, CasaOS and HomeDock OS install it in one click. See [One-click install](getting-started/one-click.md).
:::

::: details YouTube says "Sign in to confirm you're not a bot". What now?
Upload a `cookies.txt` in **Settings → YouTube cookies**; Downtify then keeps that session signed in on its own. If YouTube still rate-limits you, raise _Pause between downloads_, lower _Parallel downloads_, then try `DOWNTIFY_FORCE_IPV4=1`. See [Troubleshooting](troubleshooting.md) and [YouTube cookies](features/youtube-cookies.md).
:::

## Take it with you

<HomeHighlights :items="$frontmatter.apps" />

Any other client can use the same API: see the [mobile client contract](mobile-client-contract.md).

<div class="home-cta">

## Made in the open

Downtify is free and open source. More than 35 people have contributed code, community translators brought it to 13 languages, and many features began as an idea someone opened as an issue. If it has earned a place on your server, star it on GitHub, tell a friend who self-hosts, or sponsor its development: it helps pay for the time that goes into every release.

<HomeActions :actions="$frontmatter.community" />

</div>
