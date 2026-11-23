---
icon: lucide/sparkles
---

# Features

Everything Downtify does, grouped by area as in the sidebar. Every feature has its own page, with every option explained.

## Find music

| Feature | What it does |
|---------|-------------|
| [Discover](discover.md) | Artists, albums and playlists you don't have yet, suggested from your library, likes and listening; hide the ones you don't want |
| [Charts](charts.md) | Browse Deezer's global chart and download whatever is trending |
| [Finder](finder.md) | Search Deezer, then browse an artist, their albums and any album's tracks in columns |
| [Similar](similar.md) | Name an artist or a track; YouTube Music answers with similar tracks that play in full and download, no key needed |
| [Top Songs](top-songs.md) | Paste an artist link and download their most popular songs, optionally as a playlist |
| [Support the Artist](support-artists.md) | Find where to buy a song, album or artist: the iTunes Store item with its price, Bandcamp and Qobuz, the artist's website |

## Download

| Feature | What it does |
|---------|-------------|
| [Download Settings](download-settings.md) | Choose format (MP3/FLAC/M4A/OGG/OPUS), bitrate, parallel downloads and the pause between downloads |
| [Download Queue](download-queue.md) | Pause downloads before changing settings or updating: running ones finish, nothing new starts, and the waiting songs survive a restart |
| [Download exclusions](download-exclusions.md) | Stop retrying a song that keeps failing, and cap how long a download may keep trying |
| [Library Import (CSV)](library-import.md) | Import a library export from Soundiiz, TuneMyMusic or Exportify and queue the whole thing |
| [YouTube Cookies](youtube-cookies.md) | Upload a `cookies.txt` from the web app to get past YouTube's bot checks and download age-restricted tracks |

## Library

| Feature | What it does |
|---------|-------------|
| [Library catalog & path sync](library-catalog.md) | How Downtify tracks library files and playlists, playlists you create in the Library, and fixing paths after moving files |
| [Existing music folders](external-library.md) | Point Downtify at folders of audio you already have; Sync reads tags, matches artists and skips songs already in the library |
| [Upgrade library](library-upgrade.md) | Scan music you already downloaded and repair small covers, missing lyrics and incomplete tags |
| [Identify Songs by Sound](acoustid.md) | Recognise older files by their audio with AcoustID (opt-in) and add their ISRC when the match is certain |
| [Replace Audio](replace-audio.md) | Wrong song or version? Pick the right one on YouTube Music or YouTube; the file keeps its name, tags and playlists |
| [Artist photo, banner & bio](artist-images.md) | Pick a real photo and banner for an artist from YouTube Music, Deezer, Spotify or your own upload, and fetch their bio, origin and links from Apple Music and Deezer, automatically or on demand |
| [Storage & Usage](storage-usage.md) | See how big the library is and how fast it grows, which source each part came from, how downloads ended, and what duplicates, slskd copies and leftovers take up |
| [Music Trash](music-trash.md) | Optional: removed songs wait 30 days in a trash, ready to be restored with their likes and playlists |
| [Doctor](doctor.md) | Find what older versions left behind, such as second copies of Soulseek downloads or duplicate Navidrome playlists, and repair what is safe |

## Tags & files

| Feature | What it does |
|---------|-------------|
| [File Organization](file-organization.md) | `Artist/Album` folders or a flat layout, and how songs with several artists and compilations are filed |
| [Lyrics](lyrics.md) | Automatically download and embed lyrics (plain and time-synced); `.lrc` next to the file or in a folder you choose |
| [Explicit Marker](explicit-marker.md) | The "E" next to songs with explicit lyrics - in search, the Library and the player - and in the file's tags |

## Playlists

| Feature | What it does |
|---------|-------------|
| [Playlist Monitor](playlist-monitor.md) | Watch Spotify, Deezer and YouTube Music playlists and artists, and download new tracks and releases on a schedule |
| [Playlist display names](playlist-names.md) | Rename how an imported or synchronized playlist is shown, without touching its source or its sync |
| [Favorite playlists](playlist-favorites.md) | Pin playlists to the top of your lists and the home screen, on the web and in the apps |
| [Hidden playlist songs](hidden-playlist-songs.md) | Take songs you don't want out of a downloaded or watched playlist and keep them out; the files stay in your library |
| [Collaborative playlists](collaborative-playlists.md) | Let some of the people you share a Library playlist with add and remove its songs; renaming, sharing and deleting stay yours |
| [Playlist order & repeated songs](playlist-order.md) | Put the songs of a Library playlist in any order, and play a song more than once in it |
| [Playlist cover art](playlist-cover-art.md) | Save the playlist's own cover next to its M3U file, or upload your own for a playlist you created |
| [M3U Export](m3u-export.md) | Auto-generated playlist files for Jellyfin, Navidrome, Plex and any media app |
| [Import existing playlists](external-playlists.md) | Bring the M3U and M3U8 playlists in your music folders into the Library, pointing at the files you already have |

## Listening

| Feature | What it does |
|---------|-------------|
| [Built-in Player](player.md) | Play your library in the browser: synced lyrics, karaoke, an editable queue, a sleep timer, keyboard shortcuts and media keys |
| [Volume normalization](playback-normalization.md) | Play every song at a similar loudness, from measurements an admin starts; audio files are never changed |
| [Liked songs](liked-songs.md) | Heart a song to like it; a playlist of everything you have liked appears on its own |
| [Podcasts](podcasts.md) | Subscribe to a show by RSS feed, Spotify link or name; new episodes download and tag on their own |
| [Mobile Apps](mobile-apps.md) | Sign in from the Android and iOS apps, or pair them by QR code, and stream the library to them (original or transcoded) |
| [Install as an App](pwa.md) | Add Downtify to your phone's home screen, where it opens full-screen like a native app |

## Sources & integrations

| Feature | What it does |
|---------|-------------|
| [SoundCloud](soundcloud.md) | Paste SoundCloud track links, and use SoundCloud as an audio source for songs missing elsewhere |
| [Deemix](deemix.md) | Use your own Deemix server and Deezer account as an audio source |
| [slskd & Navidrome](slskd-navidrome.md) | Download from Soulseek through slskd, mirror playlists into Navidrome, and track playlist downloads |
| [Ratings from Deezer](navidrome-ratings.md) | Give your Navidrome songs 0–5 stars from how popular they are on Deezer |
| [Aurral](aurral.md) | Let Aurral use Downtify as a download source: it asks, Downtify downloads, Aurral files the result in its own library |

## Server & accounts

| Feature | What it does |
|---------|-------------|
| [Users & Sign-in](users.md) | Username and password sign-in (`admin` / `downtify` on a new server), admin and normal user accounts, per-user preferences, and an activity log of sign-ins and what everyone plays |
| [Server Settings](server.md) | The port Downtify listens on, changed from Settings (admins), with a restart right away if you like |
| [Backups](backups.md) | Save the settings, the watches and the list of songs, on a schedule or on demand, to bring them back after a lost disk or on a new server |
| [Notifications](notifications.md) | Messages about long tasks (Doctor, Library upgrade, ratings, backups) and downloads on Discord, ntfy, Gotify or a webhook, with Discord commands such as `/status` |
| [Library-only mode](library-only.md) | Keep every account and app to the music already in the library: no outside search, streams or downloads |
| [Outbound Proxy](outbound-proxy.md) | Send Downtify's outbound traffic through an HTTP, HTTPS or SOCKS5 proxy |
| [Update Notifications](updates.md) | Hourly check against GitHub Releases; a notice appears in the sidebar when a newer version is out, and a "What's new" summary after you update |
| [Internationalization](internationalization.md) | The app in 13 languages and the documentation in nearly all of them, and how to add yours |

## Input types

Downtify accepts several input types in the search bar:

| Input | Example |
|-------|---------|
| Spotify track, album, playlist or artist URL | `https://open.spotify.com/track/…` |
| YouTube / YouTube Music URL | `https://www.youtube.com/watch?v=…` |
| YouTube Music playlist or artist URL | `https://music.youtube.com/playlist?list=…` |
| Deezer track, album, playlist or artist URL | `https://www.deezer.com/track/…` |
| SoundCloud track URL ([details](soundcloud.md)) | `https://soundcloud.com/artist/track` |
| Free-text search | `The Night Owls Do I Still Recall` |

Free-text searches are sent directly to YouTube Music — no Spotify link required.
