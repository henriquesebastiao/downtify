---
icon: lucide/trash-2
---

# Music Trash

With the **music trash** on, removing songs from the library no longer deletes them: an admin moves them to the trash, where they are kept for **30 days** and can be restored — at the same place, with the same likes, playlists and offline copies in the apps — until then. After that the worker deletes them for good.

The trash is **off** unless whoever runs the server turns it on. Without it, deleting a song deletes the file at once, as it always has.

## Turning it on

For the usual install — the songs live in the downloads folder — set one environment variable and recreate the container:

```yaml
services:
  downtify:
    environment:
      - DOWNTIFY_TRASH=true
```

The trash then covers the downloads folder (`/downloads`), and Downtify moves the files itself. To cover other folders as well (the [slskd folder](slskd-navidrome.md), [existing music folders](external-library.md)), or to have the files moved by a separate process, use a [configuration file](#the-configuration-file) instead.

While the trash is on:

- Only **admins** remove songs, and only through the trash: other accounts no longer get a delete button for songs, even ones they downloaded.
- **Deleting a playlist keeps its songs** in the library, as deleting a playlist you made always did.
- A song that isn't in a folder the trash covers can't be removed (`This song’s folder isn’t covered by the trash`). Add its folder to the configuration file.

Turning the trash off again brings permanent deletion back. Songs still in the trash stay where they are (in `.downtify-trash`, see [Where the files go](#where-the-files-go)) and out of the library: turn it back on to restore them.

## Moving songs to the trash

On the web, **Move to trash** is in each song's menu, in the selection bar of the Library's Songs tab, and in an album's menu. In the [Android app](mobile-apps.md) it's in a song's **⋮** menu, for an admin's paired phone.

Before anything moves, the server checks the exact files — this can take a moment on a big selection or slow storage — and the confirmation lists them. Confirming moves exactly those files:

- the song's audio file, and its own lyrics files next to it (`.lrc`, `.txt`, `.srt` with the same name) or in the [lyrics folder](lyrics.md) when the `.lrc` is kept there;
- **not** another copy of the same song in another format (an MP3 next to a FLAC stays), and when such a copy shares the lyrics file, the lyrics file stays too;
- **not** the folder's cover art or anything else other songs use.

The songs leave the library for everyone right away, while they are still *Waiting to move*. Up to 200 songs go at once. A song someone is playing can't be moved until it's paused, and nothing moves while the [library upgrade](library-upgrade.md) runs: the move waits for both.

A song whose tags say too little to recognise it again — no Spotify, Deezer or YouTube id, no ISRC, and not all of title, artist and album — can't go to the trash (`This song’s tags are too thin…`): fix its tags first.

## The Trash page

Admins open **Trash** from the button at the top of the Library page (or from the app's side menu). It lists what is in the trash, newest first, with a search box, and for each song:

| State | Meaning |
|-------|---------|
| **Waiting to move** | Confirmed; the worker hasn't moved it yet. Already out of the library |
| **Moving** | Being moved |
| **In the trash** | Moved. Shows until when it is kept |
| **Waiting to restore** / **Restoring** | On its way back |
| **Stopped — files kept** | Something went wrong (the message says what); nothing was deleted |

**Restore** (one song, or the selected ones) puts the files back where they were. The song comes back with the same library id, so likes, playlists and the apps' offline copies find it again. A song that hasn't moved yet (*Waiting to move*, or stopped before moving) can be restored too: that only brings it back into the library.

Restoring never overwrites anything: when a file has appeared at the old place meanwhile, the song stays in the trash and says so. Move or rename that file, then try again.

**Try again** resumes a stopped operation, after you've fixed what the message pointed at (storage not mounted, a file changed…). An interrupted move or restore — the server stopped halfway — resumes by itself when it starts again.

There is no way to empty the trash early: songs leave it only by being restored or when their 30 days are up.

## Kept out of downloads

A song in the trash is skipped by every download — the queue, [Playlist Monitor](playlist-monitor.md), artist watches — and a download of it ends with `In the music trash: an admin has to allow it again`. It is recognised by its provider ids or by its exact title, artists and album, so another edition of it isn't affected.

That stays true after its 30 days, so a monitored playlist doesn't bring back a song you removed. The Trash page's **Kept out of downloads** view lists these songs; **Allow downloads** lets the next sync fetch it again (it doesn't start a download). Restoring a song lifts it too.

## Where the files go

A song moves to a `.downtify-trash` folder at the top of its library folder (for example `/downloads/.downtify-trash/<id>/`), readable only by Downtify's user, with an empty `.ignore` file so that Jellyfin skips it. Downtify's own scans, players, streams and the apps never show what's in it.

Moves are renames on the same disk — nothing is copied — that never replace an existing file, and each file is checked against what was confirmed (size and SHA-256) before it moves, before it comes back and before it is deleted. A file that changed in between stops the operation and is kept. This needs Linux and a filesystem with atomic renames that don't replace (`renameat2` with `RENAME_NOREPLACE`: ext4, XFS, Btrfs, tmpfs, ZFS…); elsewhere the trash refuses to move anything (`This storage can’t move files safely`).

Don't delete the database in `/data` or go back to a Downtify version without the trash while songs are in it: the database is what knows where each one came from.

## The configuration file

`DOWNTIFY_TRASH_CONFIG` names a JSON file (inside the container) that lists each folder the trash covers; it wins over `DOWNTIFY_TRASH`.

```json
{
  "version": 1,
  "worker": "embedded",
  "roots": {
    "downloads": { "path": "/downloads" },
    "slskd": { "path": "/slskd" },
    "nas": {
      "path": "/music/nas",
      "marker": ".downtify-nas",
      "marker_value": "living-room-nas"
    }
  }
}
```

| Key | Description |
|-----|-------------|
| `version` | Always `1` |
| `worker` | `embedded` (default): Downtify moves the files itself. `external`: only a [separate worker](#a-separate-worker) does |
| `roots` | The folders, each under a name of your choice. `path` is absolute and must be the folder as Downtify sees it — the downloads folder, the slskd folder or one of the extra music folders — and can't be a symbolic link itself |
| `marker`, `marker_value` | Optional, for removable or network storage: a file in that folder and its expected content. While the file is missing or different (the disk isn't mounted, another one is), nothing in that folder moves |

A configuration that can't be read stops the server at start, with the reason in the log, rather than bring permanent deletion back.

## A separate worker

With `"worker": "external"`, Downtify only records what to do and never touches the files: its container can mount the music read-only, and a separate process — with only the music folders and `/data` mounted, no network, no Docker socket — does the moves, restores and expiries:

```sh
python -m downtify.trash_worker \
  --config /config/trash.json \
  --database /data/downtify_library.db \
  --auth-database /data/downtify_auth.db \
  --limit 5
```

Each run handles at most `--limit` operations (1–20), prints what it did as JSON (`{"processed": 1, "succeeded": 1, "failed": 0}`) and exits; schedule it every minute or so (a systemd timer, cron, a Kubernetes CronJob). It checks again that whoever asked is still an admin, reading the accounts database read-only, and two runs never work at once. Run it from the same Downtify version as the server, and only while nothing else rewrites the same files.

## API

The web app and the Android app use the same endpoints under `/api/v1/library/trash` — see [Music trash](../api-reference.md#music-trash) in the API reference.
