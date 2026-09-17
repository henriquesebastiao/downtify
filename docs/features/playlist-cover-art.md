---
icon: lucide/image
---

# Playlist Cover Art

Downtify can save a playlist's own cover art next to its [M3U file](m3u-export.md), so media servers and file browsers show real artwork for the playlist folder instead of a generic icon.

## Enabling

Off by default. Turn it on in **Settings → Playlists → Download playlist cover art**.

## File location

The cover is written with the **same name and location as the playlist's M3U file**, just with a `.jpg` extension instead:

```
<downloads>/<playlist-name>/<playlist-name>.m3u
<downloads>/<playlist-name>/<playlist-name>.jpg
```

Or, with *Organize by artist*/*Organize by album* enabled (see [File Organization](file-organization.md)):

```
<downloads>/Playlists/<playlist-name>.m3u
<downloads>/Playlists/<playlist-name>.jpg
```

If M3U generation is turned off (**Settings → Playlists → Generate M3U file for playlists**), the cover isn't downloaded either — Downtify needs to know where the M3U landed to place the cover beside it.

## Sources and resolution

| Source | Resolution |
|--------|-----------|
| Spotify | The largest image Spotify's public embed page offers for the playlist — the same size already used for track-level cover art. |
| YouTube Music | Always requested at the maximum size (1200×1200), independent of the **[Cover art resolution](download-settings.md#cover-art-resolution)** setting — that setting only affects per-track covers. |

Both sources only ever serve JPEG for these URLs (even when the original artwork was a PNG), so the file is always saved as `.jpg`.

## When it downloads

- **Manual playlist download** — once, right after the playlist finishes downloading (Spotify or YouTube Music playlist links).
- **[Playlist Monitor](playlist-monitor.md)** — after the initial backfill when a watch is added, and again on any later sweep that downloads at least one new track. A sweep that finds nothing new doesn't re-fetch the cover.

A failure to resolve or download the cover (network issue, no cover art available) is logged and skipped — it never fails the playlist download itself.

## Navidrome

If you [mirror playlists into Navidrome](slskd-navidrome.md#navidrome), no extra configuration is needed: Navidrome resolves playlist artwork from a **sidecar image** — a file with the same name as the playlist, in the same folder — which is exactly what Downtify writes. As long as Navidrome's music folder includes your downloads folder, the cover shows up automatically.

## Cleanup

Deleting a playlist from the Library page removes its cover art file along with its M3U and tracks (see [Deleting a playlist](slskd-navidrome.md#deleting-a-playlist)).
