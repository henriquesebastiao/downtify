---
icon: lucide/stethoscope
---

# Doctor

New Downtify versions fix problems **from then on**: slskd transfers are now removed after they are imported, a playlist's cover sits next to its M3U, Navidrome playlists are synced. Files and playlists an older version wrote keep the old shape, though — the second copy of every Soulseek download, the M3U left at its old location, the Navidrome playlist that shows up twice. **Settings → Doctor** finds that leftover state and repairs what it can *prove* is safe, so a library started on an old version catches up with the new one.

Only admins see it.

## Health check

**Run health check** looks at everything below and changes nothing. It runs in the background; leaving the page doesn't stop it, and the last result is shown again when you come back.

Each section below folds open on its own; its header says what it found (**All good**, **3 to merge**, …) so you can see at a glance where there is work. The page remembers which sections you left open.

A repair can change what another section found: merging duplicate songs rewrites playlists and may remove the library file a slskd leftover was matched to, deleting slskd leftovers changes the song counts, merging playlists changes Navidrome's. After a repair, every section it may have changed is marked **Out of date** and its repairs are locked until you **Check again**, so nothing acts on findings that are no longer true. The server refuses those repairs too, not only the page.

## AI helper

Going through every finding by hand is a lot of reading, and the checks below are strict yes-or-no rules. The **AI helper** lets an AI assistant such as Claude do that reading with you. Tell it in plain words what you want ("these are all the same road-trip mix, keep one", "keep the album version of these songs, not the remixes"). It compares, explains each finding, and suggests what to do. The decisions stay yours. It covers every section: [duplicate playlists](#duplicate-playlists), [duplicate songs](#duplicate-songs), [songs downloaded again under a new Spotify ID](#downloaded-again-under-a-new-spotify-id), [slskd leftovers](#slskd-leftovers) and [Navidrome](#navidrome).

It is meant for the occasional clean-up, not to run all the time:

- **Start AI helper** turns it on and shows a new key. **Stop** turns it off, and the key stops working.
- It also stops by itself after 2 hours without a request from the assistant, and whenever Downtify restarts. Its suggestions are forgotten on a restart.

### Connecting an assistant

The helper is an [MCP](https://modelcontextprotocol.io) server at `/api/doctor/ai/mcp`, on the same address as Downtify. While it runs, the section shows a ready-to-copy setup for each app, with the key already filled in:

| App | How it connects |
|---|---|
| Claude Code | One `claude mcp add` command in a terminal, on a computer that can reach the server (your home network or Tailscale is enough) |
| Claude Desktop | A few lines for `claude_desktop_config.json`, using the small `mcp-remote` bridge (needs Node.js on that computer); restart Claude Desktop afterwards |
| Claude on the web or phone, ChatGPT | Only when the server can be reached from the internet over HTTPS, for example with Tailscale Funnel or Cloudflare Tunnel. ChatGPT needs its developer mode, which isn't on every plan |

Below that is a first message to paste into the chat to get started. Keep the key to yourself: while the helper runs, whoever has it can change your library.

### What the assistant can do

- Read what the last health check found and run a new one.
- **Duplicate playlists:** list every playlist, read one's songs, and compare 2 to 20 playlists song by song (what's in all of them, what's only in one). It suggests a merge, or that a group is **Different playlists**. A merge is still only possible under the usual rule (80% of the smaller playlist's songs in the larger one), and playlists you made in the Library are never merged.
- **Duplicate songs:** the check's groups, and a search of the whole library, so it also finds remixes, live and sped-up versions that the check never groups (their length differs). For each file it can read the tags, ISRC, lyrics, length, format, source and playlists, check whether two files hold the very same audio, and look the song up on MusicBrainz (official releases, lengths, ISRCs). It suggests **Keep one copy**, which works like **Keep the selected copy**: everything that used the other copies moves to the kept one first, then they go to the music trash, or are deleted for good when the trash is off. Or it suggests **Different songs**. With the music trash on, it checks each copy first: a copy the trash can't identify (no Spotify, Deezer or YouTube ID, no ISRC, and not all of its title, artist and album tags) can't be removed, so the assistant says so before suggesting instead of letting **Apply** stop on it.
- **Downloaded again under a new Spotify ID:** the whole list, fixed with **Keep one copy**.
- **slskd leftovers:** run the slskd check (new downloads wait meanwhile, as when you run it here) and suggest deleting leftovers. Only those verified to hold the same audio as a library file can be deleted.
- **Navidrome:** the problems found and the page's own plan. It suggests deleting playlists the check flagged, and only those, and turning on M3U import.

Every suggestion comes with a reason written for you. They appear under **The assistant's suggestions**, one group per section, as the same cards as the rest of the Doctor: playlists with their covers and song counts, songs with a player for each copy and the one that is kept, the slskd files with the library file each matches, the Navidrome playlists that go. **Apply** runs one. A section's **Apply all** runs its suggestions together, merging songs one after the other. **Dismiss** drops one. Applying works exactly like deciding on the page yourself: the same checks, backups and music trash. Afterwards the sections it changed are **Out of date** until they are checked again, and their waiting suggestions wait for that, so it's one section at a time.

**Let the assistant apply what you agree to in the chat** lets the assistant press Apply for you, once you said yes in the chat. It is off every time the helper starts. While it is off, the assistant can only suggest.

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

**What's in slskd's folder** (shown after a health check) explains why a file browser shows the folder bigger than the storage page does. Every file in it is one of: a **library song** (what the storage page counts), a **leftover** (what the check above compares), **audio Downtify doesn't know** (never imported, or kept after an import failed — counted nowhere else), or **another file** (covers, lyrics, anything that isn't a song), with the largest of the last two listed by name. It only reads the folder. Sizes count 1 GB as 1024³ bytes; some file browsers count 1000³, so the same folder can show a bigger number there.

Audio hashes are cached in `/data/doctor/audio_hashes.db` (SQLite; with PostgreSQL, in the PostgreSQL database), so checking again after a few new downloads only reads the new files.

## Duplicate playlists

Two M3U files that hold one playlist: the same name in two places — typically `Playlists/<name>.m3u` from before the M3U moved into the playlist's own folder (or after **Organize by artist/album** was switched) — or nearly the same songs under two names, a playlist renamed on Spotify.

Names count as the same once case, accents, punctuation and emoji are set aside, so `DAMNN...its already 3am🥵` and the `DAMNNits already 3am` folder written for it are one name. Two differently named playlists count as the same songs only when at least 80% of *each* one is in the other, and a playlist joins such a group only when it matches every playlist already in it — a 50-song mix that is almost all inside a 7,000-song liked-songs backup is not a copy of it. **Same name** and **Same songs** filter the list by why a group was found.

Decide as you look through the groups: **Merge** or **Different playlists** on each, then **Apply changes** once. All the merges run as one job, with a single Navidrome rescan at the end. Groups marked as different playlists stop being listed; **List them again** brings them back.

**Merge** keeps the file Downtify writes today, puts every song of both in it once (the larger playlist's order first), copies the cover next to it if it had none, and removes the other file and its cover. Both files are copied to `/data/doctor/backups/<date>/` first. Playlists are only merged when at least 80% of the smaller one's songs are in the larger one; otherwise they may be different playlists and the button stays off. Playlists you created in the Library are never merged.

**Choose playlists yourself** lists every M3U, so two that the check didn't pair can be compared and merged under the same rule.

Each M3U that has a cover shows it; click it to see it larger.

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

## Formats to convert

Files already in the library in a format you don't want: a FLAC from before your format rules were set, say, which can take ten times the space of an MP3 320. Pick the formats (FLAC is picked to start with) and **Find files** lists every library file in them, biggest first, with its size now and as an MP3 at your Downloads quality. Nothing changes yet.

**Convert** turns each file into an MP3 beside it, at the Downloads quality (320 kbps unless you chose less), with the same title, artists, album, numbers, date, genre, ISRC, cover and lyrics; an `.lrc` file has the same name and keeps working. The MP3 is checked to be as long as the original, then takes over everything that pointed at the original, as **Keep the selected copy** does for a duplicate, and the original goes to the music trash when it is on. A file that can't be converted is left as it was, with the reason. The run can be stopped between files.

A lossless file (FLAC, WAV, AIFF, APE, WavPack) converted to MP3 320 sounds the same: that is how good MP3s are made. A lossy one (M4A, OGG, Opus) converted again loses a little, so pick those only when you need the space. Merge duplicate songs first, so each song is converted once. To keep such files from coming back, set **Formats to avoid** in the download settings.

## Downloaded again under a new Spotify ID

Spotify sometimes replaces a playlist's track with the same song under a new ID — a re-release, a remaster, a regional version. Downtify remembers a monitored playlist's tracks by ID, so the replacement looks new and is downloaded again, though nobody changed the playlist. The check lists songs a monitored playlist holds under several IDs in several files.

## API

All admin-only, under `/api/doctor`: `GET /api/doctor` (the running or last job and the last result of each kind), `POST /scan`, `POST /cancel`, `POST /slskd/scan`, `GET /slskd/files`, `POST /slskd/clean`, `POST /slskd/release`, `POST /playlists/preview`, `POST /playlists/merge`, `POST /navidrome/repair`, `POST /duplicates/merge` (`keep`, `remove`), `POST /duplicates/keep` (`files`) and `POST /duplicates/keep/reset`. One Doctor job runs at a time. `GET /api/doctor` also lists the sections that are out of date (`stale`); their repairs answer `409` with `rescan_first` until they are checked again.

The [AI helper](#ai-helper), also admin-only: `GET /api/doctor/ai` (whether it runs, its key and its suggestions), `POST /ai/start`, `POST /ai/stop`, `PUT /ai/settings` (`can_apply`), `POST /ai/apply` and `POST /ai/dismiss` (`ids`), and `POST /ai/clear`. The assistant itself talks to `/api/doctor/ai/mcp` (MCP over HTTP, one JSON answer per `POST`), which takes the helper's key as `Authorization: Bearer` instead of a sign-in.
