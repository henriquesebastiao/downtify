---
icon: lucide/image
---

# Playlist cover art

Downtify can save a playlist's own cover next to its [M3U file](m3u-export.md), so media servers and file browsers show the real artwork for the playlist instead of a generic icon.

Off by default. Turn it on in **Settings → Downloads & files → Save playlist cover art**.

## Where the file goes

The cover is written with the **same name and in the same folder as the playlist's M3U**, with a `.jpg` extension instead:

```
<downloads>/<playlist-name>/<playlist-name>.m3u
<downloads>/<playlist-name>/<playlist-name>.jpg
```

With *Organize by artist* or *Organize by album* on, tracks are spread across artist folders and the M3U goes to a central `Playlists/` directory (see [File organization](file-organization.md)) — the cover follows it:

```
<downloads>/Playlists/<playlist-name>.m3u
<downloads>/Playlists/<playlist-name>.jpg
```

::: info It needs the M3U
With **Write M3U playlists** off, no cover is saved either: Downtify places the image by the M3U's path, so without one there is nowhere to put it. The setting is hidden while M3U writing is off.
:::

## Sources and resolution

| Source | Resolution |
|--------|-----------|
| **Spotify** | The largest image its public embed page offers for the playlist — the same one already used for the tracks' cover art |
| **YouTube Music** | Always requested at 1200×1200, independently of [Cover art resolution](download-settings.md#cover-art-resolution), which only affects per-track covers |

Both services serve JPEG for these URLs even when the original artwork was a PNG, so the file is always saved as `.jpg`.

## When it downloads

- **A manual playlist download** — once, right after the playlist finishes (Spotify and YouTube Music links alike).
- **[Playlist Monitor](playlist-monitor.md)** — after the initial backfill when a watch is added, and again on any later sweep that downloaded at least one new track. A sweep that finds nothing new doesn't re-fetch it.

Failing to resolve or download the cover (a network error, a playlist with no artwork) is logged and skipped — it never fails the playlist download itself, which has already succeeded by then.

## Navidrome

Nothing to configure: Navidrome resolves playlist artwork from a **sidecar image** — a file named after the playlist, in the same folder — which is exactly what Downtify writes. As long as Navidrome's music folder covers your downloads folder, the artwork appears on its next scan. No API call from Downtify is involved. See [slskd & Navidrome](slskd-navidrome.md#navidrome).

## Cleanup

Deleting a playlist from the Library page removes its cover along with its M3U and tracks — see [Deleting a playlist](slskd-navidrome.md#deleting-a-playlist).
