---
icon: lucide/sparkles
---

# Features

Downtify covers everything you need to build and maintain a local music library from Spotify.

## Overview

| Feature | What it does |
|---------|-------------|
| [Download Settings](download-settings.md) | Choose format (MP3/FLAC/M4A/OGG/OPUS), bitrate, parallel downloads and delay between downloads |
| [Playlist Monitor](playlist-monitor.md) | Watch Spotify or YouTube Music playlists and artists, and auto-download new tracks and releases |
| [Top Songs](top-songs.md) | Paste an artist link and download their most popular songs, optionally as a playlist |
| [Library Import (CSV)](library-import.md) | Import a library export from Soundiiz, TuneMyMusic or Exportify and queue the whole thing |
| [Built-in Player](player.md) | Play your library in the browser: queue management, synced lyrics, sleep timer, keyboard and media keys |
| [Liked songs](liked-songs.md) | Heart a song to like it; a playlist of everything you have liked appears on its own |
| [Podcasts](podcasts.md) | Subscribe to a show by RSS feed, Spotify link or name; new episodes download and tag on their own |
| [slskd & Navidrome](slskd-navidrome.md) | Download from Soulseek through slskd, mirror playlists into Navidrome, and track playlist downloads |
| [Library catalog & path sync](library-catalog.md) | How Downtify tracks library files and playlists, and fixing paths after moving files |
| [Upgrade library](library-upgrade.md) | Scan music you already downloaded and repair small covers, missing lyrics and incomplete tags |
| [M3U Export](m3u-export.md) | Auto-generated playlist files for Jellyfin, Navidrome, Plex and any media app |
| [Playlist cover art](playlist-cover-art.md) | Save the playlist's own cover image alongside its M3U file |
| [Artist photo, banner & bio](artist-images.md) | Pick a real photo and banner for an artist from YouTube Music, Deezer, Spotify or your own upload, and fetch their biography from Deezer on demand |
| [File Organization](file-organization.md) | Flat layout or per-artist subfolders |
| [Lyrics](lyrics.md) | Automatically download and embed lyrics (plain and time-synced) |
| [YouTube Cookies](youtube-cookies.md) | Upload a `cookies.txt` from the web UI to download explicit/age-restricted tracks |
| [Internationalization](internationalization.md) | English plus seven more languages out of the box |
| [Update Notifications](updates.md) | Hourly check against GitHub Releases; a notice appears in the sidebar when a newer version is out |

## Input types

Downtify accepts several input types in the search bar:

| Input | Example |
|-------|---------|
| Spotify track URL | `https://open.spotify.com/track/…` |
| Spotify album URL | `https://open.spotify.com/album/…` |
| Spotify playlist URL | `https://open.spotify.com/playlist/…` |
| YouTube / YouTube Music URL | `https://www.youtube.com/watch?v=…` |
| YouTube Music playlist URL | `https://music.youtube.com/playlist?list=…` |
| Free-text search | `The Night Owls Do I Still Recall` |

Free-text searches are sent directly to YouTube Music — no Spotify link required.
