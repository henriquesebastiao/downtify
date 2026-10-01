---
icon: lucide/folder-plus
---

# Existing music folders

Downtify's Library is built from the files it downloaded — plus any **extra folders** you point it at. Those folders are not copied into `/downloads`. Downtify reads each file's tags (title, artist, album, track number, year), skips songs you already have, and files the rest under the matching artist in the Library and the player.

## Add folders

1. Mount the host folder into the container (Docker). The path you type in Settings is **inside the container**, the same rule as [slskd's download folder](slskd-navidrome.md).
2. Open **Settings → Library**.
3. Under **Existing music folders**, add one or more paths (for example `/music/collection`). The field suggests directories as you type.
4. **Save** if you want them kept without syncing yet, or press **Sync folders** — that saves the list and scans immediately.

```yaml
services:
  downtify:
    volumes:
      - ./downloads:/downloads
      - /path/on/host/to/mp3s:/music/collection
      - downtify_data:/data
```

Then the folder in Settings is `/music/collection`.

::: warning Files stay where they are
Sync does not copy files into `/downloads`. When the folder is writable it **does** write into those files the same extras a download would: lyrics (and a `.lrc` sidecar — next to the file or in the folder you chose in Settings), a cover if the file has none, and genre from iTunes when it can. A later Sync writes a missing sidecar even if lyrics are already in the tags, and **moves** an existing `.lrc` to the location currently chosen in Settings when that source file is writable. Deleting a track from the Library still deletes that file on disk.
:::

::: tip Read-only mounts
Mount the collection `:ro` if you do not want Downtify to rewrite the MP3s. Sync still indexes them. Put `.lrc` files in the [lyrics folder](lyrics.md#sidecar-lrc-file) (turn **Keep .lrc next to the audio** off). Missing covers are saved under `/data/cover_cache` (the Library's cover endpoint), not into the MP3. iTunes genre is stored in Downtify's library metadata database, not in the file. A `.lrc` already sitting beside a read-only file is **copied** into the lyrics folder and left in place.
:::

## What Sync does

1. Walks every configured folder for playable audio (the same formats as the rest of the library: MP3, M4A, FLAC, OGG, WAV, AAC, OPUS).
2. Reads embedded tags. A file with no title/artist falls back to `Artist - Title` in the filename, same as other library rows.
3. **Skips** a file when the library already has that song (same artist + title, and length within a few seconds when both are known) — whether it was downloaded by Downtify or came from another extra folder.
4. **Matches artists** to names already in the library (`The Beatles` and `Beatles` become one artist). Names that don't match a known artist show up as a new artist. New artists are queued for the same profile seeding (photo/bio when those settings are on) as a finished download.
5. **Tags like a download** when the folder is writable. For each imported track it uses the same lyrics providers, cover lookup (only when the file has no artwork) and iTunes genre lookup a download would. Lyrics go into the file; a `.lrc` sidecar is written next to the audio or in the [lyrics folder](lyrics.md#sidecar-lrc-file) you chose in Settings. Cover and genre follow [Download settings](download-settings.md) (`download_cover_art`, `download_lyrics`). On a **read-only** mount the MP3 is not rewritten: a missing cover is stored under `/data/cover_cache`, genre is stored in the library catalog, and `.lrc` files go to the lyrics folder if you chose one. Lookups run in batches of **Parallel downloads**; a **Pause between sync lookups** in Settings → Downloads & files waits between those batches so large folders don't hit provider rate limits.
6. Invalidates the library path cache so the Library page and player see the result without waiting for the usual short scan TTL.

Sync runs **in the background**. You can leave Settings; coming back while it is still working shows that it is still syncing. When it has finished, Settings shows the **last sync log** (imported / duplicate / error, plus lyrics/cover notes).

Run **Sync folders** again after you drop more files into those folders. Saving the folder list without Sync still includes them on the next library scan (about a minute, or the next download/delete).

Removing a folder from the list **unmaps** it: those tracks leave the Library and the player, and Downtify-made extras (`.lrc` sidecars, cached covers) are deleted. The audio files on disk stay put.

Folders that don't exist or aren't readable are reported after Sync; the others are still scanned.

## Library paths

Extra-folder files use a virtual path `ext/<id>/…` (the id is a hash of the folder path, so the list can be reordered). The player and `GET /media/…` use that path, like `slskd/…` for Soulseek files left in place.

A folder that already sits **inside** `/downloads` (or the slskd source folder) is ignored here — that tree is already the library.

## API

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/library/external/sync` | Start a background scan. Optional body `{folders: ["/path", …]}` is saved first. |
| `GET` | `/api/library/external/sync` | Running job, or the last finished log. |
| `POST` | `/api/library/external/unmap` | Drop one folder from the library without deleting the audio. |

See the [API reference](../api-reference.md#post-apilibraryexternalsync) for the response shape.
