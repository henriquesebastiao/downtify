---
icon: lucide/share-2
---

# slskd & Navidrome

Two optional integrations for self-hosted libraries:

- **[slskd](https://github.com/slskd/slskd)** — download tracks from the Soulseek network through your own slskd server, as an extra audio source next to YouTube Music and YouTube.
- **[Navidrome](https://www.navidrome.org/)** — mirror the playlists you download into Navidrome, so they show up in any Subsonic client.

Both are off by default and configured in **Settings**.

## Audio sources and fallback order

**Settings → Audio source** is an ordered list. Tap a source to add or remove it; with more than one selected, use the arrows to reorder them. Each track tries the sources in that order and stops at the first one that yields audio:

| Source | What it does |
|--------|-------------|
| **YouTube Music** | The default. Searches YouTube Music, falling back to standard YouTube when there's no acceptable match — see [How it works](../how-it-works.md#fallback-to-standard-youtube). |
| **YouTube** | Searches standard YouTube only. |
| **slskd** | Searches Soulseek through slskd and downloads the best matching file. |

Enabling slskd puts it first in the list. If slskd ends up being the only source, YouTube Music and YouTube are still tried after it, so a track slskd can't find still downloads. The download queue shows which source served each track.

## slskd

### Setup

1. Run slskd and create an API key for Downtify (see slskd's documentation).
2. Mount slskd's download folder into the Downtify container — the same host folder slskd writes to. See [Docker Compose → With slskd](../getting-started/docker-compose.md#with-slskd-soulseek).
3. In **Settings → slskd (Soulseek)**, enable slskd and fill in:
    - **slskd URL** — e.g. `http://slskd:5030` when both containers share a Docker network.
    - **API key**.
    - **Download folder** — the path *inside the Downtify container* where that folder is mounted (default `/slskd`), not the host path.

Saving is rejected with an error message if slskd is enabled without a URL or API key.

### How a track is matched

Downtify searches slskd with the track's title and artist and ranks the results by how well the file name and duration match the track. Among equally good matches it prefers MP3, then FLAC, and it skips files that report a bitrate below 256 kbps. It tries up to five candidates, one after another. When a transfer finishes, Downtify checks the file's tags and duration against the track before keeping it.

If nothing acceptable turns up, the transfer doesn't finish within **Total timeout**, or it sits queued on the remote peer without progress for longer than **Queued timeout**, Downtify moves on to the next audio source.

### Leave files in place

With **Leave slskd files in place** on (the default), the downloaded file stays in the slskd folder: Downtify writes the metadata, cover art and lyrics into it there and registers it in the library under a `slskd/…` path. The Library, player and M3U files use that path, and it's served through `/media/slskd/…`.

Turn it off to copy the file next to your other downloads instead, following your filename template and [file organization](file-organization.md) settings.

::: info
slskd files keep their original format — they aren't transcoded to the format chosen in Settings.
:::

## Navidrome

### Setup

1. Make sure Navidrome's music folder includes Downtify's downloads folder (and the slskd folder, if you leave slskd files in place). Navidrome can only add tracks to a playlist once it has scanned them.
2. In **Settings → Navidrome**, enable Navidrome and enter its URL, username and password.
3. Optionally, add an **admin** username and password. Downtify then asks Navidrome to scan the library before matching new tracks, instead of waiting for Navidrome's own scheduled scan.

### Playlist sync

With **Create playlists in Navidrome** on, Downtify creates (or updates) a Navidrome playlist with the same name after:

- a Spotify playlist download finishes,
- a [Playlist Monitor](playlist-monitor.md) sweep adds tracks,
- tracks are deleted from the Library, or [library paths are fixed](library-catalog.md#fix-library-paths).

Tracks are matched to Navidrome songs by path first, then by tags. **Make Navidrome playlists public** controls the playlist's visibility in Navidrome.

::: warning Files whose tags don't match the playlist are deleted
When a playlist is refreshed (after deletes, **Fix library paths**, or **Download missing** on an already complete playlist), a library file registered for a Spotify track is **deleted from disk** if its embedded title/artist clearly don't match that track — Downtify treats it as a wrong download. Keep this in mind if you edit tags by hand.
:::

### Playlist cover art

Nothing to set up: with [Save playlist cover art](playlist-cover-art.md) on, Navidrome picks up the `.jpg` Downtify writes next to the playlist's M3U as a **sidecar image** — its own way of resolving playlist artwork — as long as its music folder covers that file. Downtify makes no API call for it.

## Playlist downloads

The **Library** page lists the Spotify playlists you've downloaded through Downtify under **Playlist downloads**. Expand it to see, for each playlist, how many tracks are in your library against the current Spotify track list. From there you can:

- **Download missing** — queue only the tracks not in your library yet.
- **Play** the tracks already downloaded.
- Expand a playlist to see and download individual missing tracks.
- **Delete** the playlist — see below.

### Deleting a playlist

Deleting a playlist (from this panel, or with **Delete playlist** next to the Library's playlist filter) removes from disk every track registered to it — **including tracks other playlists also contain** — plus its M3U file and the [cover art](playlist-cover-art.md) saved beside it, and stops tracking it. Other playlists that shared those tracks get their M3U and Navidrome playlist rewritten in the background.
