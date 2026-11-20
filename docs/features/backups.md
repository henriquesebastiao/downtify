---
icon: lucide/archive
---

# Backups

**Settings → Server → Backups** saves what a Downtify install knows, so it can be brought back after a lost disk, a broken container or a move to a new server. Only admins see it.

## What a backup holds

- **Settings**: everything on the Settings page, as it is. That includes passwords and API keys (slskd, Navidrome, the outbound proxy), so treat a backup file like `settings.json` itself and keep it private.
- **Watches**: every monitored playlist and artist watch, with its check interval, release types, "new releases only", whether it is paused, and the Deezer and MusicBrainz artists it was linked to.
- **The song list**: one record per song in the library, with artist, title, album, album artist, year, track number, duration, ISRC, the Spotify track it was downloaded for (when known) and the audio source that fetched it.

The music files are **not** in a backup: a library is many gigabytes, a backup a few megabytes. If the files are lost, the song list is what lets a restored install download them again.

A backup is one file, `downtify-backup-<date>-<time>.json.gz` (gzip-compressed JSON), in a `backups` folder beside `settings.json` in the data folder (`/data/backups` in Docker).

## Automatic backups and Back up now

Pick **Daily**, **Every 3 days** or **Weekly** (default **Off**), or press **Back up now** at any time. The two newest backups are kept:

1. the new backup is written under a temporary name and flushed to disk;
2. it is read back and compared with what was meant to be written;
3. only then is it renamed into place;
4. and only after that is the oldest deleted.

So the newest one bumps the oldest out, and if anything goes wrong on the way (a full disk, a crash), the two backups you already had are untouched. If a backup fails, the reason is shown under the button.

The two copies sit on the same disk as Downtify. Use **Download** now and then to keep one somewhere else.

## Restoring

Each saved backup has a **Restore** button, and **Choose a backup file…** loads one from your computer — for example a backup downloaded from an old server into a fresh install. Choose what to bring back first:

| Part | What happens |
| --- | --- |
| Settings | The backup's settings replace the current ones, as if saved on the Settings page. |
| Watches | Watches this install doesn't have are added with their options. A watch that already exists is left alone. New watches are checked on the next monitor sweep. |
| Re-download songs missing from the library | Every song in the backup whose file isn't in the library any more is queued for download, like a [CSV import](library-import.md). Songs still on disk are skipped. |

Downloads queued by a restore use the [audio sources](download-settings.md#audio-provider) and limits of the install they run on, so a large restore runs through the queue like any other batch. The result line says how many watches were added and how many songs were missing and queued.

A backup made by a newer Downtify than the one restoring it is refused; update first.
