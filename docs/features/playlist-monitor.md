---
icon: lucide/eye
---

# Playlist Monitor

The Playlist Monitor watches your favourite Spotify, public Deezer and YouTube Music playlists — and the artists you follow — and automatically downloads new tracks and new releases as they appear, hands-free.

There are two kinds of watch, each on its own tab of the Monitor page (**Playlists** and **Artists**, at `/monitor/playlists` and `/monitor/artists`):

| Watch | Paste | Downloads |
|-------|-------|-----------|
| **Playlist** | A Spotify, public Deezer or YouTube Music playlist URL | Every track in the playlist, then any track added later |
| **Artist** | A Spotify **artist** URL, or a YouTube Music artist URL | The artist's whole discography, then every new release |

Every watch shows the link it follows under its name, and a **Spotify**, **Deezer** or **YouTube Music** badge naming the service it was added from.

See [Artist Watch](#artist-watch) for how artist watches work.

Watches belong to whoever created them: each account follows its own playlists and artists (the same URL watched twice sweeps twice), and a sweep attributes its downloads to the watch owner. An admin sees every watch.

## How it works

Downtify keeps a background task running every 60 seconds. On each sweep it checks every enabled watch to see if it is due for inspection (based on its configured interval). When a *playlist* is due, Downtify:

1. Fetches the full track list from Spotify, Deezer or YouTube Music
2. Compares it against the set of tracks already downloaded
3. Downloads any new tracks using the same pipeline as a manual download
4. Updates the M3U file for the playlist (if M3U generation is enabled)

The first check, which starts as soon as you add the watch, downloads everything already in the playlist; later checks download only what was added since. "Already downloaded" is tracked in a small SQLite database (`downtify_monitor.db` under `/data`), not by checking the downloads folder — so moving a downloaded file elsewhere on disk (into your own library layout, another drive, wherever) does **not** make Downtify think it's missing and re-download it on the next check.

A separate sweep runs every hour and checks whether each downloaded track's file is still there. Genuinely deleted files (as opposed to ones you moved) are forgotten at that point, so the track becomes eligible for download again — on the next watch check after that hourly sweep, not instantly.

A watch is never checked twice at the same time. Adding a watch starts its first check immediately; if that check is still downloading when the next scheduled sweep comes around, the sweep skips the watch instead of starting a second, overlapping download of the same tracks.

## Adding a playlist

1. Open **Monitor** from the sidebar (on phones: **More → Monitor**) and stay on the **Playlists** tab
2. Paste a playlist URL:
    - Spotify: `https://open.spotify.com/playlist/…`
    - Public Deezer playlist: `https://www.deezer.com/playlist/…` (locale-prefixed links also work)
    - YouTube Music: `https://music.youtube.com/playlist?list=…` (a `www.youtube.com/playlist?list=…` link works too)
3. Choose a check interval (from 15 minutes to once a month)
4. Click **Watch playlist**

Each tab has its own box. Pasting an artist link into the Playlists tab (or a playlist link into Artists) doesn't add anything: the page says what kind of link it is and offers to move it to the right tab.

You can also start watching from a playlist's page: paste its link in the search bar and use **Watch for new tracks** (or **Watch for new releases** on a YouTube Music artist). Downloaded playlists in the Library offer the same action in their **⋯** menu. Watches added this way use a 6-hour interval — change it on the Monitor page.

## Deezer playlists

Public Deezer playlists are watched like any other: paste the link on the **Playlists** tab, use **Watch for new tracks** on the playlist's page, or pick **Watch for new tracks** in the **⋯** menu of a playlist card in [Charts](charts.md). No Deezer account is needed, and every track is fetched, however long the playlist is. The songs download through your [audio sources](download-settings.md) like any other Deezer link, and the playlist gets its M3U file, cover art and Library entry as a Spotify one does — even with M3U files turned off, the Library keeps track of which songs belong to it. Only public playlists can be watched, and a Deezer **artist** link can be downloaded but not watched.

## YouTube Music playlists

Use a YouTube Music playlist for songs that aren't on Spotify: remixes, live sets, covers, uploads by promo channels. Each track is downloaded from **the exact video in the playlist**. Downtify doesn't search for it again, so what you get is what you added to the playlist.

- **All tracks are fetched**, however long the playlist is. Deleted or private videos are skipped.
- **Songs YouTube Music greys out are still downloaded.** Playlists made by converters and importers (Soundiiz, TuneMyMusic and the like) often list songs as plain YouTube uploads that YouTube Music shows as unavailable and gives no song id. Downtify finds the video from the entry's thumbnail and downloads it like any other, so such a playlist doesn't come out empty. A video that has really been deleted or made private can't be downloaded: when YouTube Music flags it as such it is skipped, and when it gives nothing but a thumbnail the track shows as failed in the queue.
- **Artist and title come from the video title.** Many playlist entries are uploads credited to the channel that posted them (e.g. `MrSuicideSheep`), and the real credit is in the title, like `Bronze Whale - Patterns`. For anything that isn't a catalogue release, Downtify splits `Artist - Title` into the file name and tags. It also drops suffixes like `(Official Video)` or `[Lyrics]`. A part after the dash that names a version (`Yellow - Live at Glastonbury`) stays in the title. Catalogue tracks (official audio, or anything filed under an album) keep YouTube Music's own artist and title.
- **Not every `list=` link is a playlist.** An album's `OLAK5uy_…` link is still downloaded as an album. A `watch?v=…&list=…` link is the one song that was playing. A radio mix (`list=RD…`) has no fixed track list and can't be watched.

## Artist Watch

Instead of building a playlist per artist, paste an artist link and Downtify follows their whole catalogue. Add one from the **Artists** tab of the Monitor page — paste the URL, pick an interval, click **Watch artist**. Artist watches show a release count instead of a track count.

Accepted URLs:

- A Spotify artist URL (`https://open.spotify.com/artist/…`)
- A YouTube Music artist URL, by channel (`https://music.youtube.com/channel/UC…`) or by handle (`https://music.youtube.com/@HenriqueeJuliano`)

A handle is resolved to the artist's channel when you add the watch, so the same artist pasted by handle and by channel URL is recognized as one watch. A handle that doesn't belong to a YouTube Music artist is rejected.

On each sweep Downtify lists the artist's discography, compares it against the releases it has already processed, and downloads every track of anything new. A steady-state sweep costs a single request — tracklists are only fetched for releases it hasn't seen before.

::: info Why the discography comes from YouTube Music
Spotify's public embed exposes an artist's name and a top-tracks preview, but **not** their discography — reading that would need Spotify API credentials, which Downtify deliberately doesn't use. So a Spotify artist link is resolved to its name and matched to the same artist on YouTube Music, which is also where the audio is fetched from. The upside: every release Downtify can see is one it can actually download. The trade-off: the link follows the YouTube Music artist with exactly that name (case and punctuation aside), YouTube Music's best match when several share it. For a common name, check that the watch is the artist you meant, and paste the YouTube Music artist URL directly if it isn't. A Spotify artist whose exact name no YouTube Music artist has can only be added that way: Downtify doesn't guess.
:::

::: warning The first sweep downloads the whole back catalogue
Adding an artist queues **every** release they have, which for a prolific artist can be hundreds of albums and singles. Set **[Delay between downloads](download-settings.md#delay-between-downloads)** before adding a batch of artists, or you're very likely to get rate-limited — or turn on **New releases only** (below) to skip the back catalogue entirely.
:::

### Choosing what to download

Below the link box on the **Artists** tab (and in a watch's **Edit** dialog) two options decide what an artist watch downloads:

| Option | What it does |
|--------|--------------|
| **Download: Albums / Singles / EPs** | Only releases of the ticked kinds are downloaded. All three are on by default; at least one has to stay on. The kind is YouTube Music's own label for each release — a release it doesn't label counts as an album. |
| **New releases only** | Everything the artist has already released when the watch starts is skipped; only what comes out after that is downloaded. Off by default. |

How they behave when you change them later:

- **Turning a kind on** downloads that kind's releases the next time the watch is checked — its back catalogue too, unless **New releases only** is on (then only the ones released since the watch started, or since the option was turned on). Releases of a kind that is off are never recorded, so nothing is lost by switching a kind off for a while.
- **Turning New releases only on** for an existing watch records everything out at that point as skipped; releases already downloaded stay as they are.
- **Turning it off** downloads the releases it skipped (of the ticked kinds) on the next check.
- Saving either option in the **Edit** dialog checks the watch right away, instead of waiting for its next scheduled check.

"Skipping" the existing releases needs one successful look at the artist's discography: if YouTube Music returns an empty list (which is more often a hiccup than an artist with nothing out), nothing is recorded and the next check tries again, so a bad answer can never make the back catalogue download later. Pointing a **New releases only** watch at a different artist skips that artist's back catalogue the same way.

The Monitor list shows a watch's filters under its link when they're not the defaults (e.g. **Albums** · **New only**).

A release is only recorded as processed once every one of its tracks is accounted for, so a track that fails on a transient error is retried on the next sweep rather than being skipped forever. Tracks that already downloaded are never fetched twice.

Artist watches don't generate M3U files — the tracks are laid out by your [file organization](file-organization.md) settings rather than as a playlist.

### Suggested artists

Under the list of artist watches, the **Artists** tab suggests artists to follow, in two lists:

| List | Who is in it |
|------|--------------|
| **Based on your listening** | The artists you play the most: your own listens, the ones [Discover](discover.md) counts. Recent plays count more: a play's weight halves every 45 days, so an artist you played a lot last year ranks below one you play every day now. |
| **Based on your library** | The artists with the most tracks, then albums, in the library you can see. |

Artists you already watch (paused watches too) and compilation names such as **Various Artists** are left out. Each list shows 20 artists at a time; **Show more** loads the next ones. The lists are your own, an admin's too: another account's listens never show up. An artist an admin hid from users stays out of a user's lists, as it does out of their Library.

Loading the lists searches nothing. **Follow** looks the name up on YouTube Music, where an artist watch follows the artist:

- when exactly one artist there has that name, the watch is added right away, with the interval and the **Download** / **New releases only** options set in the box above;
- otherwise (namesakes, or no artist with exactly that name) a dialog shows the YouTube Music artists found, each with its photo and a link to its profile. Pick one with **Follow this artist**, or choose **Paste a link** to paste the artist's link in the box above yourself.

Suggestions only pick which artist to watch: the songs still download from your [audio sources](download-settings.md) as usual.

### From an artist's Library page

An artist's page in the Library (`/library/artist`) has a **Watch artist** button, so you can follow an artist you already have without looking up their link. It looks the name up on YouTube Music the same way **Follow** does above:

- when exactly one artist there has that name, the watch is added right away. It is checked daily and has **New releases only** on, since the library already holds their earlier music;
- otherwise (namesakes, no artist with exactly that name, or the lookup failed) a dialog shows the YouTube Music artists found, each with its photo and a link to its profile, plus a box for a Spotify or YouTube Music artist link. The **Download** and **New releases only** options at the top apply to whichever you follow.

Once the server has added the watch, the button turns into a **Monitor** link, where you change the interval and options; a refusal (the artist is already watched, say) shows in the dialog instead. It isn't shown in [library-only mode](library-only.md) or on the **Various Artists** page.

## Check intervals

| Label | Minutes | Best for |
|-------|---------|----------|
| Every 15 min | 15 | Frequently updated playlists |
| Every 30 min | 30 | |
| Every hour | 60 (default) | Most playlists |
| Every 3 hours | 180 | |
| Every 6 hours | 360 | |
| Every 12 hours | 720 | |
| Every day | 1 440 | Slowly changing playlists |
| Every week | 10 080 | Playlists updated weekly |
| Every 2 weeks | 20 160 | |
| Every month | 43 200 | Archive or rarely updated playlists |

You can change the interval of an existing playlist at any time from the monitor card without removing and re-adding it.

## Managing monitored playlists

Each tab lists only its own kind of watch. Above the list:

- **Filter** — type part of a name or of the link (e.g. a playlist id) to narrow the list
- **All / Paused** — show only paused watches
- **Check all now** — check every active watch in the current tab
- A strip with how many songs came in over the chosen period (**7 days**, **30 days** or **90 days**) and, across every watch, how many songs they hold, the space those take **On disk** and how many are **In more than one watch** — see [Activity and storage per watch](#activity-and-storage-per-watch)

On each row:

- **Active** switch — pause or resume the watch without removing it
- **Checks** — how often it's checked
- **Check now** (↻) — check it immediately, outside the schedule
- **Activity** — new songs over the chosen period, the average per week and whether that pace is rising or falling; click it to open the watch's own page
- **Storage** — the space taken by the songs only this watch holds, plus how many it shares with other watches
- **Edit** (✎) — see and change the watch's link, interval and active state (see [Editing a watch](#editing-a-watch))
- **⋯** — **Activity and songs** (the watch's own page), pause/resume, copy the link, open the original, or **Stop watching** (the record is deleted; downloaded files are kept)

**Activity** and **Storage** are columns like the others: hide or resize them from **Columns**.

### Editing a watch

Click a watch's name or its **Edit** button. The dialog shows the full link being followed, with **Copy link** and **Open original**, plus when the watch was added, when it was last checked and how many tracks or releases it has. You can change:

- **Link** — must be the same kind of link (a playlist for a playlist watch, an artist for an artist watch):
    - Another link to the **same** playlist or artist (for example with a different `?si=` share code, or the YouTube Music link instead of the `www.youtube.com` one) only updates the stored address. Nothing else changes.
    - A link to a **different** playlist or artist points the watch at it. The watch keeps its interval and active state, but takes the new name and starts over: its download or release history is cleared and, if it's active, it's checked straight away. Tracks already in your library aren't downloaded again, and files from the previous target stay where they are.
    - A link to something that's already watched is refused.
- **Check every** and **Active**.

This is handy for "live" playlists that get replaced: open the watch to check which playlist it really follows, and paste the new one if it changed.

## Sorting

The **Sort by** control above the list orders the current tab by:

| Field | Notes |
|-------|-------|
| Date added | Default — newest first |
| Name | Alphabetical |
| Last checked | Most recently checked first; never-checked watches last |
| Check frequency | Least frequent (longest interval) first |
| Number of tracks / releases | Most first |
| Recent activity | New songs over the chosen period |
| Average rate | New songs per day over the period |
| Storage growth | Space taken by the new songs of the period |
| Storage only in it | Space taken by the songs no other watch holds |
| Songs downloaded | Songs on disk that the watch itself downloaded |

The button next to it flips between ascending and descending order. The choice is remembered in the browser, and it only changes the list — not check order or scheduling.

## Choosing a daily sync time

By default, a playlist checked every day (or week / 2 weeks / month) syncs at whatever time it was originally added or last checked — there's no guaranteed time of day. To pin day-or-longer syncs to a specific hour (e.g. run overnight at 3 AM instead of whenever), set the `DOWNTIFY_MONITOR_SYNC_TIME` environment variable together with `TZ`. See [Environment Variables](../getting-started/environment-variables.md#playlist-monitor) for the full reference.

- Only affects intervals of a full day or more — shorter intervals (15 min – 12 h) are unaffected, since anchoring them to a single daily time would break their cadence.
- The very first check after adding a playlist always runs immediately, regardless of this setting.

## Per-track metadata enrichment

Spotify playlist embed entries are missing the release year and use the playlist cover art instead of the per-track album cover. Downtify re-fetches each new track individually to get the correct cover and year before downloading — falling back to the playlist-level data if the per-track fetch fails. YouTube Music playlist entries skip this step: each one already carries its own video's metadata.

## M3U integration

The playlist's M3U is rewritten **after every track finishes**, so it grows as the sweep downloads rather than appearing only once everything is done. The playlist is playable from the first track onwards, and a slow or hung download further down the list never holds up the tracks that already landed. A final rewrite at the end of the sweep re-resolves everything against the filesystem.

Manual playlist/album downloads and CSV imports behave the same way. See [M3U Export](m3u-export.md#when-it-is-written) for details.

With [Save playlist cover art](playlist-cover-art.md) on, the cover is fetched once per sweep that has tracks to download — before the first of them, so the folder looks like the playlist while it fills up. A sweep that finds nothing new doesn't re-fetch it.

## What happens to songs that leave a playlist

Live playlists (Spotify's *Top 50*, *Discover Weekly*, editorial charts) change every week. Downtify treats a watch as a **source of new music**, never as something that governs what you keep:

- **Downloaded audio files are never deleted by a watch.** Not when a track leaves the playlist, not when it leaves every playlist you watch, not when the playlist itself shrinks, and not when you press **Stop watching**.
- **Only the playlist follows the playlist.** On each sweep the [M3U file](m3u-export.md) is rewritten from the playlist's current tracks, in its current order, so a track that dropped out disappears from the M3U. Its file stays in the folder, and stays in your library, searchable and playable — including through Navidrome, Jellyfin or anything else pointed at the same folder.
- **A track that is in no playlist at all is still a track.** Nothing sweeps for "orphaned" files.

That makes a chart playlist usable as a discovery feed: new songs arrive automatically, and what they leave behind accumulates as your library.

```
Top 50 - USA        →  new song appears   →  Downtify downloads it
                    →  song drops out     →  M3U updated, file kept
```

The only things that delete audio are ones you ask for explicitly: **Delete** on a track or a selection in the Library, deleting a playlist from the Library (which does delete its tracks — it asks first), or removing files yourself from the filesystem.

To take a song you don't want out of the playlist, and keep it out on every sweep, hide it: see [Hidden playlist songs](hidden-playlist-songs.md). Its file stays in your library.

::: info Deleting a watch vs. deleting a playlist
**Stop watching** (in the watch's ⋯ menu) only forgets the watch: nothing on disk changes. **Delete** on a playlist in the **Library** page is the destructive one — it removes that playlist's tracks, its M3U and its catalog entry.
:::

If a file does disappear — you moved it out of the downloads folder, or deleted it by hand — an hourly sweep notices and forgets Downtify's record of it, so the next check of a watch that still lists the track downloads it again. A file merely *moved* inside the downloads folder is still found and is not re-downloaded.

## Storage

Monitor state is stored in a SQLite database at `/data/downtify_monitor.db`. The database records:

- Each watch (kind, Spotify or YouTube Music playlist ID or YouTube Music channel ID, name, URL, interval, enabled state, last check time). Whether a watch is Spotify or YouTube Music is read from its stored URL, so no extra column is needed.
- Every track successfully downloaded per watch, including the filename on disk
- For artist watches, the releases already processed, so a sweep only fetches tracklists for genuinely new ones — including the ones **New releases only** skipped, marked as such so turning it off can bring them back — plus the watch's release kinds and whether it's new-releases-only
- Each track a watch added (`watch_events`): when, the file, which audio provider fetched it, whether the watch downloaded it or found it already in the library, and whether it came with the watch's first check. These rows keep the watch's id, name and owner as they were, and outlive the watch: stopping or retargeting a watch keeps them, so its songs still say where they came from
- The tracks each watch keeps failing to download (`watch_failures`), until one succeeds, leaves the playlist or the watch is retargeted

Databases created before Artist Watch are migrated automatically on startup; existing rows keep working as playlist watches. Tracks recorded before Downtify kept the history above are added to it once, on the first start, with an unknown outcome (**Before tracking**) — the ones from a watch's first day counted as its first check.

## Activity and storage per watch

The Monitor page and each watch's own page (**Activity and songs** in a watch's **⋯** menu, or a click on its **Activity**) tell which watches make your library grow — handy with many watches, or to find out why a generated mix brought in songs you didn't expect.

**What counts as activity.** Only songs a watch actually added count: the ones it downloaded. Songs it found already in your library (another watch, or a download of your own, had them) are counted apart as **Already in library**, and so is the backfill of its first check, when it downloads whatever the playlist already had. So a static playlist reads as idle even though its first check downloaded 300 songs, and a mix that adds 15 songs a week reads as 15 a week. Tracks recorded before Downtify kept this history count as added, and the page says how many of them there are.

Over the chosen period (7, 30 or 90 days, remembered in the browser) a watch shows:

| Number | What it is |
|--------|------------|
| New songs | Songs it added in the period |
| A day / A week / A month | The average pace over the period — or since the watch started, if that's more recent |
| Trend | Whether the pace is rising (**Adding more lately**), falling (**Adding less lately**) or steady, from the new songs per day (7 days) or per week (30 and 90 days); **Too new to tell** while there are fewer than three of those to compare |
| Storage growth | Space taken by the period's new songs that are still on disk |

**Storage.** One file is stored once, however many watches hold it, and the numbers say so: **Only in this watch** is the space of the songs no other watch holds (what stopping the watch and deleting its songs would free), **Shared** the songs other watches hold too, and the strip on the Monitor page counts every file once. Other accounts' watches count when telling whether a file is shared, but aren't named.

A watch's page also shows:

- **Songs on disk**, **Downloaded by it**, **Already in library** and **Failing** — how its songs got there, and how many keep failing to download (listed further down, with the number of tries and the last error)
- **Where the audio came from** — YouTube Music, YouTube, Soulseek (slskd) or Deemix, per song on disk
- **Songs from this watch** — every song it holds, newest first, including ones that have since left the playlist, with filters (**Last 30 days** — or whichever period is chosen — **Downloaded by it**, **Already in library**, **Before tracking**). Select songs to play them, queue them, add them to a playlist, save them as a ZIP or delete them — for example to clean up what a mix brought in over the last week
- **Open in Library** (the playlist's page, or the artist's for an artist watch), **Open original** and **Check now**

The watch's id (`#12`) is shown next to its name, so two watches of the same link — two accounts following one playlist, say — can be told apart.

## Where a song came from

**Where it came from** in a song's menu (anywhere in the Library) tells which watch first downloaded it, when, and with which provider — **First check** when it came with the watch's backfill — and lists every watch that holds it now, each with its id, owner (for an admin), when it got the song and how: **Downloaded it**, **Already in library** or **Before tracking**. It's one file: watches that share a song all point at the same copy.

From there, **Activity and songs** opens the watch's page and **Open in Library** its playlist. A watch that was stopped, or now follows another link, is still named as the origin of the songs it downloaded. For a song recorded before this history existed, the first watch that recorded it is shown, marked **Probably**. A song no watch downloaded (one you downloaded yourself) says so.

A user sees their own watches by name; a song another account's watch downloaded says only that, and when.
