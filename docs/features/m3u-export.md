---
icon: lucide/list-music
---

# M3U Export

Downtify automatically generates a standard `EXTM3U` playlist file whenever a Spotify playlist is downloaded — either manually or via the [Playlist Monitor](playlist-monitor.md).

## File location

| Situation | M3U path |
|-----------|---------|
| Playlist downloaded normally | `<downloads>/<playlist-name>/<playlist-name>.m3u` |
| Playlist downloaded with *Organize by artist* enabled | `<downloads>/Playlists/<playlist-name>.m3u` |

When *Organize by artist* is on, tracks are spread across multiple artist folders, so the M3U is placed in a central `Playlists/` directory instead of the playlist subfolder.

[Liked songs](liked-songs.md) are written to `Playlists/Downtify Liked Songs.m3u` too, whatever the layout and whether or not *Write M3U playlists* is on.

## Relative paths

Track paths inside the M3U are written **relative to the M3U file itself**, not as absolute paths. This means the same file works whether it is read from inside the Downtify container (`/downloads/…`) or from another consumer that mounts the same library at a different root — for example Jellyfin under `/nas/music/…`. Just point your media server at the same library mount and the playlist will appear as a single unit.

## Enabling / disabling

M3U generation is controlled by **Settings → Downloads & files → Write M3U playlists** (on by default). Turning it off skips M3U creation entirely; the rest of the download flow is unchanged.

## Cover art

Right below that setting, **Save playlist cover art** (on by default) writes the playlist's own cover image next to its M3U, under the same name — before the tracks, so the folder looks like the playlist from the start. Downtify then shows that artwork for the playlist instead of a grid of its track covers. A playlist you create in the Library gets a mosaic of up to four track covers written the same way. See [Playlist cover art](playlist-cover-art.md).

## When it is written

The M3U is rewritten **after every track finishes downloading**, so the playlist file grows as the download progresses instead of appearing all at once at the end. This applies to playlist and album downloads, [CSV imports](library-import.md) and [Playlist Monitor](playlist-monitor.md#m3u-integration) sweeps alike.

That means the playlist is playable from the moment the first track lands, you can see the sync is working as it goes, and a single slow or hung download can never keep the M3U — or the tracks that already finished — from showing up.

A final rewrite runs once the whole run completes. It resolves every track against the filesystem (rather than the in-memory list of what this run downloaded), so it also picks up files from earlier runs and corrects anything that changed on disk mid-run.

Every write lists tracks in **playlist order**, not in the order downloads happened to finish, so a partially-written M3U is still correctly ordered.

::: info Tracks already on disk
Tracks downloaded by an earlier run stay in the M3U throughout — they're included from the first write, not only added by the final one.
:::

## Regeneration

The M3U is regenerated fresh on every run — re-pasting the same playlist URL produces a complete, in-order file including any tracks that were missing on earlier runs.

Tracks that failed to download or had no YouTube Music match are silently skipped.

## Compatibility

The generated file uses:

- UTF-8 encoding, no BOM
- LF line endings
- The standard `#EXTM3U` / `#EXTINF` format

This is compatible with Jellyfin, Navidrome, Plex, VLC, Kodi, Sonos and any other player or media server that consumes standard M3U playlists.

## Playlists you create

**Library → Playlists → New playlist** writes the same kind of M3U under `Playlists/`, with an extra `#EXTDOWNTIFY:manual` line so Downtify can tell it apart from a downloaded Spotify/YouTube playlist. You can rename it, and add or remove songs (including ones from [extra folders](external-library.md)). Deleting that playlist, deleting a track, or unmapping an extra folder updates the M3U; the audio is only deleted when you delete the track itself or an imported playlist.

### Adding songs to a playlist

Admins can put songs in one of these playlists, or in a new one, from several places:

- **A song's ⋯ menu** (in any track list) → **Add to playlist**.
- **Select several songs** in the Library and press **Add to playlist**.
- **An album's ⋯ menu** → **Add to playlist** adds every song of the album.
- **An artist's ⋯ menu** (on the artist's page) → **Add to playlist** adds everything the artist has in your library, album by album.

Each menu lists your playlists and a **New playlist…** entry that creates one with those songs already in it. A song a playlist already has is skipped, and the confirmation says how many were really added (or that they were all there already). A playlist holds at most 500 songs.
