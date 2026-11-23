---
icon: lucide/circle-pause
---

# Download Queue

Everything you download goes through the **Queue** page: what is downloading (**In progress**), what is **Waiting** for a free slot, what is **Done** and what **Failed**. How many songs download at once is [Parallel downloads](download-settings.md#parallel-downloads). A song only moves to **In progress** once it has a slot: a single song you download, and a failed song you **Retry** (or every one at once with **Retry failed**), waits in **Waiting** like the rest.

## Pausing and resuming

**Pause downloads**, at the top of the Queue page, stops the queue from starting anything new — handy before you change settings, look into a problem, or update and restart Downtify while a long queue is waiting.

- Downloads already running finish normally; nothing is cancelled. Until the last of them is done, the page reads **Pausing downloads…** with how many are left.
- Then it reads **Downloads paused**: no new downloads will start until resumed. The waiting songs stay queued, in the same order, they read **Paused**, and the Queue badge in the sidebar turns grey.
- **Resume downloads** carries on with the waiting songs, with the settings and the [audio source order](download-settings.md#audio-provider) as they are by then.
- Songs added while the queue is paused join it and wait too. A waiting song you remove (or **Clear queue**) never starts.
- [Playlist Monitor](playlist-monitor.md) sweeps wait as well, before each track, and so do [Replace Audio](replace-audio.md) jobs.
- New watch checks and reconciliation sweeps wait before starting. Podcast monitoring stops between episodes; manual episode downloads wait too. Active work finishes normally.
- Library improvement receives its native pause and finishes its current track. Resume improvement separately in its existing screen after resuming the global queue. New runs and crash recovery respect the global pause.

Everyone sees whether the queue is paused; only an admin can pause or resume it, since it holds everyone's downloads.

The same global control is available at the top of Settings → Downloads & files (`/settings/files`) and in Playlist Monitor (`/monitor`), next to Check all. Both read the confirmed server state. They require an administrator's web session; a paired phone token does not grant server administration. On a lost confirmation, use Check status before sending another change.

## Why slskd wasn't used

With [slskd](slskd-navidrome.md) first in the source order, a song it can't serve is downloaded by the next source (YouTube Music, YouTube…) or not at all. For an admin, the **Why slskd wasn't used** panel next to the queue counts why that happened, as bars, most frequent first:

| Reason                                                                    | What it means                                                                        |
| ------------------------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| **Nobody shared it**                                                      | No user had the song with a free upload slot                                         |
| **No file matched the song**                                              | Files came back, but none matched the title, artist and length                       |
| **Match below the minimum score**                                         | A close file scored below the threshold that keeps remixes and live versions out     |
| **Blocked by quality rules**                                              | Matching files failed the format or bitrate rules (Settings → Audio sources → slskd) |
| **Search / Download ran out of time**                                     | The search or the transfer took longer than the slskd timeouts                       |
| **Transfers failed**                                                      | Every file picked was refused or never arrived complete                              |
| **Wrong song in the file**                                                | The downloaded file's tags named another song; it was kept in slskd's folder         |
| **Couldn't reach slskd** / **Search didn't start** / **slskd not set up** | slskd itself wasn't available                                                        |

Click a reason to see what to change and the latest songs it happened to, with details such as the best match's score or how many files the quality rules turned down. The line below says what was used instead. Songs slskd served, and songs already in the library, aren't counted. **Reset** starts the count over, so after changing a setting the next downloads show whether it helped. Songs and files are not touched.

## Which watch is downloading a song

A song the [Playlist Monitor](playlist-monitor.md) downloads says which watch it is for: under its title, **From …** with the playlist's cover or the artist's photo. Click it to open that watch's page, where you can pause it or stop watching. The **Downloading for watches** panel next to the queue lists every watch with songs in the queue — how many, and how many are still to go — with a link to the original playlist or artist. It's the quickest way to find the generated mix or playlist that keeps bringing in songs you don't listen to.

Songs you download yourself show no watch.

## Restarting or updating

The queue outlives a restart, a crash or a container update. The songs that were waiting — and the ones that were mid-download when Downtify stopped, which start over — are queued again on the next start, and a paused queue comes back paused. The songs that **Failed** come back in that tab with their error, so **Retry failed** still works after an update (they never retry on their own); removing them or **Clear queue** forgets them. So with a long queue:

1. **Pause downloads** and wait for **Downloads paused**.
2. Restart or update Downtify, change what you needed to.
3. **Resume downloads**.

When the songs of a playlist download finish after a restart, its [M3U](m3u-export.md) and Navidrome playlist are refreshed once, as at the end of the original download.

::: info What isn't kept

- Finished songs: after a restart the queue lists what is still to do and what failed.
- [Replace Audio](replace-audio.md) jobs: replace the song again.
- In [library-only mode](library-only.md) nothing is started: the saved songs wait for a start with it off.
  :::

## API

[`GET /api/queue/state`](../api-reference.md#get-apiqueuestate), [`POST /api/queue/pause`](../api-reference.md#post-apiqueuepause) and [`POST /api/queue/resume`](../api-reference.md#post-apiqueueresume); every change is also a `queue_state` [WebSocket](../api-reference.md#websocket) frame.
