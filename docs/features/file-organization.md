---
icon: lucide/file-headphone
---

# File Organization

A new server organizes files by artist and album (`Artist/Album/…`): **Organize by artist** and **Organize by album** are both on by default. Turn them off for the flat layout below. Servers set up before this default keep the choice they had.

## Flat layout (both off)

Single tracks and YouTube searches go directly into the root of the downloads folder. Playlist and album tracks go into a per-playlist or per-album subfolder:

```
downloads/
├── My Playlist/
│   ├── My Playlist.m3u
│   ├── The Night Owls - Do I Still Recall.mp3
│   └── Tame Impala - The Less I Know The Better.mp3
└── The Night Owls - R U Awake.mp3       ← single track
```

## Organize by artist

With **Settings → File organization → Organize by artist** on (the default), to group every track — including playlist and album downloads — under a subfolder named after its album artist (see [Several artists and compilations](#several-artists-and-compilations)):

```
downloads/
├── The Night Owls/
│   ├── The Night Owls - Do I Still Recall.mp3
│   └── The Night Owls - R U Awake.mp3
├── Tame Impala/
│   └── Tame Impala - The Less I Know The Better.mp3
└── Playlists/
    └── My Playlist.m3u
```

This structure is compatible with media servers (Jellyfin, Navidrome, Plex) and library managers (Beets) that expect an `Artist/Song.ext` folder layout.

## Several artists and compilations

A song often credits several artists. Downtify keeps all of them in the file's **Artist** tag, and also writes each one separately to an **ARTISTS** tag (`TXXX:ARTISTS` in MP3), so a player never has to split a name like `Earth, Wind & Fire` on its comma. The folder, though, belongs to a single artist: the **album artist**, or for a compilation the track's first artist.

- The album artist is the artist the source (Spotify, YouTube Music or Deezer) credits for the **album**, the same for every track on it, and it's written to the **Album artist** tag. When the source doesn't say, it's the track's first artist.
- A duo or group is one artist. YouTube Music credits some acts as their members, one per entry (`Henrique & Juliano` comes back as `Henrique` and `Juliano`, on the album and on each track - sometimes in the other order, `Mateus` and `Jorge` for `Jorge & Mateus`). Each credited name links to a YouTube Music channel; when one member's link leads to a channel named after the whole act, made of the names credited next to it, Downtify joins those names back into the act's name: the folder, **Album artist**, **Artist** and **ARTISTS** tags all say `Henrique & Juliano`. A real collaboration (each artist under their own channel) keeps every artist.
- A guest never changes it. *The Girl Is Mine*, with a guest on Michael Jackson's *Thriller*, stays in `Michael Jackson/Thriller/`, and *Lady Marmalade* the single (Christina Aguilera, Lil' Kim, Mýa, P!nk) goes to `Christina Aguilera/`.
- Only an album the source itself credits to **Various Artists** (a soundtrack, a "Now That's What I Call…") is a compilation — unless you [mark it yourself](#marking-an-album-as-various-artists). A single YouTube Music song never is: YouTube Music files the same audio under several releases and may show any of them as its album, often a compilation, so only a whole YouTube Music album download counts. Its tracks get "Various Artists" as their album artist plus the compilation flag (`TCMP` in MP3, `COMPILATION` in FLAC/Ogg/Opus, `cpil` in M4A). That keeps the album whole in Navidrome and other media servers, which group albums by these tags rather than by folder. On disk, though, **Organize by artist** never makes a `Various Artists` folder: each track goes to its own first artist's folder.

```
downloads/
├── Christina Aguilera/
│   ├── Lady Marmalade/
│   │   └── Christina Aguilera, Lil' Kim, Mýa, P!nk - Lady Marmalade.mp3
│   └── Moulin Rouge/                  ← from the soundtrack (a compilation)
│       └── Christina Aguilera, Lil' Kim, Mýa, P!nk - Lady Marmalade.mp3
└── David Bowie/
    └── Moulin Rouge/                  ← same soundtrack
        └── David Bowie - Nature Boy.mp3
```

*Lady Marmalade* from the single and from the *Moulin Rouge* soundtrack are two releases, each filed with its own album. The soundtrack's tracks are spread over their artists' folders, but tagged as one "Various Artists" compilation, so the Library and media servers still show *Moulin Rouge* as one album.

### Marking an album as Various Artists

A source can credit a release to one artist when it belongs to several equally — Deezer lists the *Lady Marmalade* single under Christina Aguilera alone. An admin can fix that from the album's page in the Library, with the **Mark as Various Artists** button next to **Add to queue**.

- Every track of the album gets "Various Artists" as its album artist and the compilation flag. Nothing else in the files changes, and they stay where they are (a compilation's tracks are filed under their own first artist anyway). Each file is rewritten through a working copy, keeps its modification date, and is left untouched if the rewrite fails.
- The album moves to the **Various Artists** artist in the Library, and the page follows it there.
- Downtify remembers the album: a track of it downloaded later is tagged the same way.
- On a compilation the same button reads **Unmark as Various Artists**: it undoes the mark and puts back the album artist the album had. It also works on an album its source made a compilation; then the album artist becomes the artist most of its tracks list first, and later downloads of that album aren't marked again.

Only admins see the button. Media servers pick the change up on their next library scan.

## M3U and artist folders

When *Organize by artist* is on and you download a Spotify playlist with M3U generation also enabled, the M3U is placed in `<downloads>/Playlists/<playlist-name>.m3u` rather than inside the playlist subfolder. This is because the tracks are now spread across multiple artist folders. The relative paths inside the M3U still resolve correctly regardless of where you mount the library.

## Changing the setting

The setting takes effect immediately for all **new** downloads. Existing files already on disk are not moved.

## Deleting a track cleans up empty folders

Deleting a track from the Library page removes its per-playlist, artist or album folder too, once it's empty — and keeps climbing up through any now-empty parent folders (e.g. the artist folder after its last album is gone), stopping at the downloads directory itself, which is never removed. A folder that still holds anything else — another track, an `.m3u`, a `cover.jpg` still in use — is left alone.

## Selecting and deleting several tracks at once

The Library's track list has a checkbox on every track, plus a **Select all** checkbox that selects every track matching the current filter (see [Library page](library-catalog.md#library-page)). **Delete from library** in the selection bar removes all of them in one request (`DELETE /delete/batch`, see [API Reference](../api-reference.md)), with the same per-track cleanup (`.lrc`, orphaned `cover.jpg`, empty folders) as deleting one track at a time.

To delete a whole album or playlist, open it and pick **Delete** from its **⋯** menu. For everything by one artist, type the artist's name in the track list's filter, then **Select all** and delete.
