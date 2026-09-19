---
icon: lucide/mic-vocal
---

# Lyrics

Downtify looks lyrics up while a track downloads and embeds them in the file, plus a `.lrc` sidecar when they're time-synced.

## Enabling lyrics

Lyrics are **enabled by default**. Turn them off in **Settings → Tags & lyrics → Download lyrics**.

## Providers and fallback order

Catalogues differ: a song one provider has never heard of is often on another. Downtify therefore keeps an ordered list of providers and tries them one at a time, stopping at the first that has something.

| Provider | Lyrics | Notes |
|----------|--------|-------|
| **[LRCLIB](https://lrclib.net)** | Plain and time-synced | Free community database, no key. Matched on title, primary artist, album and duration. |
| **NetEase Cloud Music** | Usually time-synced | Large catalogue, strong on Asian releases and often on Western ones too. Matched on title, artist and duration; a hit whose artist is spelled differently (traditional vs simplified Chinese, for example) is accepted only when the title and the length both line up. |

In **Settings → Tags & lyrics → Providers** you can drag the providers into the order you prefer, or use the arrows, and switch any of them off. At least one stays on; to stop looking lyrics up entirely, use the **Download lyrics** switch.

::: info What about Genius, Musixmatch and AZLyrics?
They aren't available, and Downtify no longer offers them:

- **AZLyrics** forbids third-party use of its lyrics in the page itself.
- **Musixmatch**'s desktop API answers with an empty token unless you have credentials it doesn't hand out to applications.
- **Genius**' `robots.txt` disallows the search endpoint needed to find a song's page.

Saved settings that still name them keep working: the names are ignored, and a list left with nothing else falls back to the default providers.
:::

## Skipping providers that had nothing

After a lookup, Downtify records for each song which providers answered and which came back empty, in `downtify_library.db` under `/data`.

A provider that had nothing for a song isn't asked about it again for **30 days**, so re-downloads and large library passes don't repeat the same failed lookups. After that it's tried again, since catalogues grow. A provider that *did* have lyrics is never skipped, so a re-downloaded file gets them back.

## Embedding

| Format | Plain lyrics tag | Synced lyrics tag |
|--------|-----------------|------------------|
| MP3 | `USLT` (ID3) | `USLT` with timestamps |
| FLAC | `LYRICS` (Vorbis comment) | `LYRICS` with LRC content |
| M4A | `©lyr` | `©lyr` with LRC content |
| OGG / OPUS | `LYRICS` (Vorbis comment) | `LYRICS` with LRC content |

## Sidecar .lrc file

When synced lyrics are available, Downtify also saves a `.lrc` file next to the audio file with the same base name. This lets media players that support external lyrics files (like Jellyfin or certain portable players) show the time-synced lyrics independently of the embedded tags. The [built-in player](player.md#now-playing) reads it too — unless you [hide the lyrics](player.md#hiding-the-lyrics) there, which only changes what the player shows and leaves the files and this sidecar alone.

Deleting the track from the Library page removes this `.lrc` sidecar along with the audio file, so lyrics never linger as an orphaned file.

## When nothing is found

If no provider has the song, the download continues normally — the audio file is saved without lyrics, and no error is raised.
