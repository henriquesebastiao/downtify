---
icon: lucide/shield-alert
---

# Explicit Marker

A song with explicit lyrics — language not meant for children — carries a small **E** next to its title, like on Spotify. It shows up wherever you meet the song, before and after you download it, and it stays with the file.

## Where you see it

- **Search results, pasted links, Charts and the Finder** — on any song the service says is explicit. You can tell before you download.
- **The Library** — in the Tracks tab, on album, artist and playlist pages, and in the "add songs" picker.
- **The player** — next to the title in the player bar, in **Now playing** and in **Up next**.

Hover over the **E** (or let a screen reader read it) to see "Explicit".

## Where the mark comes from

The service you download from decides it: Spotify, YouTube Music and Deezer each flag their explicit songs, and Downtify uses what the one you picked says. When Downtify downloads a song from YouTube Music, the mark describes the **video it actually downloads**: if the song is explicit on Spotify but Downtify matched a clean edit, the file is not marked, and if Spotify calls it clean but the match is explicit, it is.

A song the service doesn't flag gets no mark at all — which is not the same as being certified clean, and Downtify never writes a "clean" mark.

## In the file

The mark is written into the file's tags, the way iTunes does it, so media servers and players that understand it can use it too. Navidrome reads exactly these tags as a track's explicit status.

| Format | Tag |
|--------|-----|
| MP3 | `ITUNESADVISORY` text frame (`TXXX`), value `1` |
| FLAC, OGG, OPUS | `ITUNESADVISORY` comment, value `1` |
| M4A | `rtng` atom, value `1` |

Files you already had are read the same way: anything marked `1` (or the older `4`) by iTunes, MusicBrainz Picard or another tagger shows the **E** too, including songs from [extra folders](external-library.md).

::: info Songs downloaded before this version
Files Downtify wrote before the marker existed have nothing in their tags, so they show no **E**, even when the song is explicit. Download the song again with [Replace audio](replace-audio.md) or from scratch to mark it. A file keeps its mark when [Upgrade library](library-upgrade.md) or Replace audio rewrites it: the mark is only ever added, never cleared.
:::

The first time the Library loads after updating, Downtify reads every file's tags again to look for the mark, like it did when it learned to show codec and genre. On a big library on a slow disk that takes a moment, once.

## For app developers

The [mobile client contract](../mobile-client-contract.md) and the [API reference](../api-reference.md#get-tracks) describe the `explicit` field: `true` on explicit tracks, absent otherwise.
