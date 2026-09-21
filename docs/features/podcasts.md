---
icon: lucide/mic
---

# Podcasts

Subscribe to a show and its new episodes download on their own — no re-pasting a link every week. Podcasts are handled end to end differently from music: an episode is already a finished audio file sitting at an RSS `<enclosure>` URL, so there is no YouTube matching or transcoding involved, just a download and a tag write.

Open **Podcasts** from the sidebar (on phones: **More → Podcasts**).

## Subscribing

Paste one of these into the **Add a podcast** box, or type a name to search:

| Input | What happens |
|-------|--------------|
| A podcast's RSS feed URL | Fetched and parsed directly |
| A Spotify show link (`open.spotify.com/show/…`) | The show's name is read from Spotify, then matched to its public RSS feed through the iTunes podcast directory |
| A Spotify episode link (`open.spotify.com/episode/…`) | Same as a show link, and the specific episode is highlighted if its title can be matched into the feed |
| A show's name (free text) | Searched in the iTunes podcast directory |

::: info Spotify-exclusive shows can't be downloaded
A show that only exists on Spotify (no public feed) is reported as such — Downtify does not guess or fall back to something else. Search for the show by name to double-check before assuming it's exclusive.
:::

Before confirming, you choose:

- **Keep** — see [How many episodes are downloaded](#how-many-episodes-are-downloaded) below.
- **Interval** — how often the feed is checked for new episodes, from every 15 minutes to once a month. Subscriptions are checked on the same schedule and by the same background sweep as [Playlist Monitor](playlist-monitor.md) watches — they're just another kind of watch to it.

## How many episodes are downloaded

The **Keep** setting has two distinct behaviors, chosen once per show:

- **Every new episode** — downloads only the single newest episode right away (subscribing isn't an invitation to pull a show's entire back catalog), then downloads whatever new episodes appear on every check after that. Nothing is ever deleted automatically.
- **Latest *N* episodes** — a rolling window. After every check (including the first), the *N* most recently published episodes are downloaded, and any older downloaded episode is removed to make room. Raising *N* later makes those removed episodes downloadable again; an episode you removed yourself with **Remove download** is never brought back this way — see [Removing episodes](#removing-episodes).

Change **Keep** and the interval any time from the show's page.

## Episodes

A show's page lists its episodes, newest first, each with its publish date and duration. An episode not covered by the retention policy still shows up here — tap **Download** to grab just that one, no matter how old.

### Removing episodes

Each episode's **⋯** menu has **Remove download**, which deletes the file but keeps the episode in the list. Two ways an episode's file goes away, with different outcomes:

| How | Comes back automatically? |
|-----|----|
| Retention rolled it out (an older episode past the "keep latest N" window) | Yes, if you raise **Keep** again |
| You chose **Remove download** yourself | No — download it again by hand any time |

### Marking played

Use an episode's **⋯** menu to mark it played or unplayed by hand, or just let it play through — an episode within the last few seconds of its length is marked played on its own.

## Playing episodes

Episodes play through the same built-in player as music, with a few differences that only show up on a podcast episode:

- **Skip 15s back / 30s forward** in place of shuffle and repeat, which don't apply to a single episode.
- **Playback speed** (0.75× to 2×), next to the sleep timer.
- **Resume position** is saved to the server every ~10 seconds of playback and once more when you pause, so closing the tab — or opening Downtify on another device — picks the episode back up close to where you left it. A show's episode list shows a "Resume at …" hint for anything partway through.

The heart (liked songs) and "go to album/artist" don't apply to episodes and don't show up on one.

## Library

Podcasts have their own place — they never show up as tracks, albums or artists in the **Library**, and an [Upgrade library](library-upgrade.md) run leaves them alone entirely (an episode has no Spotify track id to refresh tags from, and no separate lyrics to look for).

Episode files still sit under the same downloads volume, in `Podcasts/<Show>/<date> - <Episode>.<ext>`, so any media server pointed at your library sees them too.

## Tags

Downtify writes what podcast apps and media servers already read for an episode: title, the show as album, the show's author as artist, the publish year, episode/season numbers, the show's own artwork (the larger of the feed's own image and iTunes', same idea as [cover art for music](download-settings.md#cover-art-resolution)), and the episode description as a comment. Show notes are stored as plain text — Downtify strips HTML from them rather than rendering it.

## Good to know

- **No video podcasts.** An episode whose only enclosure is a video file is skipped entirely; only audio is supported.
- **No chapters.** Feeds that include chapter markers don't get them in Downtify yet.
- **Not mirrored into Navidrome.** Unlike playlists, podcast subscriptions aren't pushed into a Navidrome library — episodes are plain files your media server already sees on its own.
- Unsubscribing (**⋯ → Unsubscribe**) removes downloaded episodes by default; choose **Unsubscribe, keep downloaded episodes** to leave the files in place.

## API

`POST /api/podcasts/resolve`, `GET /api/podcasts/search`, `POST /api/podcasts/subscribe`, `GET/PATCH/DELETE /api/podcasts/shows/{id}`, `GET /api/podcasts/shows/{id}/episodes`, `POST /api/podcasts/episodes/{id}/download`, `DELETE /api/podcasts/episodes/{id}`, and `PUT /api/podcasts/episodes/{id}/playback`. See the [API reference](../api-reference.md#podcasts).
