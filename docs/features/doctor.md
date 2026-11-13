---
icon: lucide/stethoscope
---

# Doctor

New Downtify versions fix problems **from then on**: slskd transfers are now removed after they are imported, a playlist's cover sits next to its M3U, Navidrome playlists are synced. Files and playlists an older version wrote keep the old shape, though — the second copy of every Soulseek download, the M3U left at its old location, the Navidrome playlist that shows up twice. **Settings → Doctor** finds that leftover state and repairs what it can *prove* is safe, so a library started on an old version catches up with the new one.

Only admins see it.

## Health check

**Run health check** looks at everything below and changes nothing. It runs in the background; leaving the page doesn't stop it, and the last result is shown again when you come back.

## slskd leftovers

Older versions copied each finished Soulseek download into the library and left the original in slskd's folder, so every song took twice the space. **Pause downloads and check**:

1. pauses the download queue and waits for running downloads to finish, so nothing is written while files are compared;
2. lists the files in slskd's folder that no library song, playlist, monitored playlist or M3U points at (with **Leave files in the slskd folder** on, that folder *is* the library, and there is nothing to clean);
3. compares each one with library files that could be the same song — same artist and title, or the same length and format — by their **audio only**.

Downtify rewrites the tags and cover of what it imports, so the two files never have the same bytes; their audio is untouched. The Doctor has `ffmpeg` hash the audio packets of both files (no decoding, tags and artwork ignored). A leftover is **Identical in the library** only when a library file outside slskd's folder has bit-identical audio. Everything else is kept and shown with why:

- **Similar, not identical** — something looks like it, but the audio differs (another rip, a live version);
- **Not in the library** — nothing looks like it;
- **Unreadable** — `ffmpeg` couldn't read it;
- **Changed recently** — modified in the last 15 minutes, so slskd may still be writing it.

**Delete identical copies** removes only those. Right before each one goes, it is checked again: same size and modification time as when it was compared, and its library twin still there. Emptied folders are removed, downloads resume, and Navidrome is asked to rescan. **Keep them and resume downloads** gives the queue back without deleting anything; so does doing nothing for an hour.

Audio hashes are cached in `/data/doctor/audio_hashes.db`, so checking again after a few new downloads only reads the new files.

## Duplicate playlists

Two M3U files that hold one playlist: the same name in two places — typically `Playlists/<name>.m3u` from before the M3U moved into the playlist's own folder (or after **Organize by artist/album** was switched) — or nearly the same songs under two names, a playlist renamed on Spotify.

**Merge** keeps the file Downtify writes today, puts every song of both in it once (the larger playlist's order first), copies the cover next to it if it had none, and removes the other file and its cover. Both files are copied to `/data/doctor/backups/<date>/` first. Playlists are only merged when at least 80% of the smaller one's songs are in the larger one; otherwise they may be different playlists and the button stays off. Playlists you created in the Library are never merged.

**Choose playlists yourself** lists every M3U, so two that the check didn't pair can be compared and merged under the same rule.

## Navidrome

What Navidrome — and every app connected to it, like Symfonium — actually shows. It needs the [Navidrome admin login](slskd-navidrome.md#navidrome): only an admin can see the playlists Navidrome imported and which file each came from.

Navidrome turns every M3U file in its music folder into a playlist of its own, with the cover image beside it, and owned by its admin. With **Create playlists in Navidrome** on, Downtify *also* creates the same playlist through the API — so each one shows up twice: the imported one with the cover, and Downtify's with no cover. The check reports:

- **Duplicates** — playlists one name folds to, with the reason: an imported M3U and Downtify's copy, an M3U imported twice, or Downtify's playlist created twice;
- **M3U gone** — imported playlists whose M3U no longer exists. Navidrome never removes those itself, even after a full scan;
- **Missing songs** — imported playlists with fewer songs than their M3U. Navidrome skips lines that point outside its music folder — songs left in slskd's folder when that folder isn't part of Navidrome's library, for instance — and says how many are outside;
- **Duplicate songs in Navidrome** — songs listed more than once (same artist and title, lengths within 2 seconds), and how many of the copies are in an `slskd` folder.

**Fix** deletes the playlists marked *will be removed*: Downtify's copy of a playlist Navidrome imports (unless the copy has songs the import is missing), extra copies Downtify created, and imports whose M3U is gone. It then turns on **Let Navidrome import the M3U playlists** (Settings → Navidrome) so Downtify stops creating the copy again, has Navidrome rescan, and lists the playlists again to report what is left. Only playlists the last health check flagged can be deleted.

## Duplicate songs

Downtify's own view, the same as [Storage & Usage](storage-usage.md#could-be-cleaned-up): **Same file** and **Likely the same song**. Each group lists its copies with their format, size, length, where they came from, their own title and album tags, and the playlists they are in. Each copy has a player, with seeking, so you can listen before you decide.

Deleting one copy of a duplicate from the Library isn't enough: the playlists, likes and monitored playlists that used it now point at nothing, so the song looks missing and a monitored playlist downloads it again. **Keep the selected copy** merges instead. Everything that used the other copies moves to the one you keep first: the M3U files (your own playlists too, where the song then appears once), the playlist catalog, the Spotify track index, likes and owners for every account, songs hidden from a playlist, the offline copies in the mobile apps, and Playlist Monitor's downloaded tracks, artist releases and history. Then the other copies are removed: to the [music trash](music-trash.md) when it is on (a copy it can't take, in a folder it doesn't cover or playing right now, stops the merge before anything changes), for good otherwise. The result says which playlists were updated and checks that nothing still points at a removed copy. A copy hidden from the Library doesn't hide the one you keep.

**Keep all, they're different** is for look-alikes that really are different recordings: an edit, a live take, a parody under the original's name. The Doctor stops listing them until another copy turns up; **List them again** brings back every group kept this way.

## Downloaded again under a new Spotify ID

Spotify sometimes replaces a playlist's track with the same song under a new ID — a re-release, a remaster, a regional version. Downtify remembers a monitored playlist's tracks by ID, so the replacement looks new and is downloaded again, though nobody changed the playlist. The check lists songs a monitored playlist holds under several IDs in several files.

## API

All admin-only, under `/api/doctor`: `GET /api/doctor` (the running or last job and the last result of each kind), `POST /scan`, `POST /cancel`, `POST /slskd/scan`, `GET /slskd/files`, `POST /slskd/clean`, `POST /slskd/release`, `POST /playlists/preview`, `POST /playlists/merge`, `POST /navidrome/repair`, `POST /duplicates/merge` (`keep`, `remove`), `POST /duplicates/keep` (`files`) and `POST /duplicates/keep/reset`. One Doctor job runs at a time.
