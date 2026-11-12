---
icon: lucide/audio-lines
---

# Volume normalization

Songs come from many sources and are mastered at very different levels, so one song can be much louder than the next. **Volume normalization** plays each song at a similar loudness. It is off by default, and your audio files are never changed: the server only measures them, and the player turns each song up or down while it plays.

## Turning it on

In the web app, open **Settings → General** (`/settings`) and switch on **Normalize playback volume** in the **Volume normalization** group. The choice is yours alone: it follows your account to other browsers and doesn't change anything for anyone else.

When enabled, **Playback level** offers **Normal**, **Louder** and **Maximum**. This level choice is remembered in the current browser and is independent of the phone's choice. Normal keeps the existing target; the other choices raise it within each song's measured peak limit. The playing song changes level smoothly, without waiting for another track or running analysis again. Some songs therefore sound similar in Louder and Maximum when little peak headroom is available.

While a song plays, the line under the switch says what was applied to it:

| Message | Meaning |
|---------|---------|
| Measured volume applied to the current song. | The song has a measurement and plays at its normalized level |
| No measurement for this song yet: original level kept. | It hasn't been analyzed (or it changed since) — see [Analyzing the library](#analyzing-the-library) |
| Silent song: original level kept. | There was nothing loud enough to measure |
| Normalization unavailable: original level kept. | The browser has no Web Audio, or the server didn't answer in time |

Switched on mid-song, the current song is leveled at once, with a short fade. Songs that aren't in the library (previews and streams of songs you haven't downloaded) always play at their original level.

The Android app has its own switch: **Settings → Playback → Normalize volume**. It applies from the next song and uses the same measurements, including for offline copies downloaded whole while the measurement already existed.

## How the level is chosen

Each song gets one constant gain for its whole length — there is no compression, and quiet and loud passages inside a song keep their balance:

- The targets are **-18 LUFS** (Normal), **-12 LUFS** (Louder) and **-6 LUFS** (Maximum) integrated loudness; the measured peak limit can keep a song below the selected target.
- A quiet song is turned up by **at most 12 dB**.
- The gain never pushes the song's peak above **-1 dBTP**, so it doesn't clip. The peak is measured on the song resampled to 192 kHz, which also catches peaks between samples.

So a very quiet or very dynamic song can stay below the target. The web player applies the gain together with the [equalizer](player.md#equalizer); both use the Web Audio API, with the same [browser limits](player.md#browser-support) — on an iPhone or iPad, playback with the screen locked may stop while either is on.

## Analyzing the library

Measuring takes reading every song once, so it only happens when an admin asks for it. Admins see the analysis controls in the same **Volume normalization** group:

- **Analyze library** queues every song in the library. A song whose measurement is still valid is skipped, so running it again later (after new downloads, say) only measures songs that are new, moved, replaced or changed, and those that failed before.
- **Pause analysis** lets the songs being measured finish, then stops. **Resume analysis** continues where it left off.
- The counter shows how many songs are analyzed and how many failed (a file FFmpeg can't decode, or one that changed while it was being read).

Analysis runs in the background with FFmpeg at a low priority: at most two songs at a time, fewer when the container has less than two CPUs (its CPU quota and affinity are respected), each with a single thread. It never starts on its own, not even after a restart — an interrupted analysis is kept and waits for **Resume analysis**.

A measurement belongs to the file as it was measured (its size, modification time and inode). When a file is replaced or rewritten — by a [library upgrade](library-upgrade.md), [replacing its audio](replace-audio.md) or by hand — the old measurement no longer applies, the song plays at its original level, and the next **Analyze library** measures it again.

## For developers

A track's measurement is `GET /api/library/loudness?file=` for the web app and `GET /api/v1/tracks/{id}/loudness` for the apps; analysis is controlled with `GET /api/library/loudness/status` and `POST /api/library/loudness/{start,pause,resume}` (admins). See the [API reference](../api-reference.md#playback-normalization) and the [mobile client contract](../mobile-client-contract.md).
