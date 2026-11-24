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
| **[LRCLIB](https://lrclib.net)** | Plain and time-synced | Free community database, no key. Matched on title, primary artist, album and duration; when that finds nothing time-synced, its search is tried too and a hit is accepted on title, artist and length (within a few seconds). |
| **NetEase Cloud Music** | Usually time-synced | Large catalogue, strong on Asian releases and often on Western ones too. Matched on title, artist and duration; a hit whose artist is spelled differently (traditional vs simplified Chinese, for example) is accepted only when the title and the length both line up. |
| **Kugou Music** | Time-synced | Large catalogue, strong on Chinese releases and with many Western ones. Matched like NetEase; the title line and songwriting credits at the top are dropped. |

In **Settings → Tags & lyrics → Providers** you can drag the providers into the order you prefer, or use the arrows, and switch any of them off. At least one stays on; to stop looking lyrics up entirely, use the **Download lyrics** switch. A provider added in an update starts switched off when you had already saved your own list: switch it on there.

### Time-synced lyrics only

**Settings → Tags & lyrics → Time-synced lyrics only** (off by default) keeps only lyrics with timestamps: a provider that only has plain lyrics for a song counts as having nothing, and the next one is asked. [Upgrade library](library-upgrade.md) then also counts a track with only plain lyrics as missing lyrics. Synced lyrics a file already has count either way: a `.lrc` sidecar, lyrics with timestamps embedded in its tags, or an ID3 `SYLT` frame (as files from other apps sometimes have). With the setting on, synced lyrics Downtify finds for a track replace its plain ones, in the `.lrc` sidecar and in the file's own lyrics tag, so players that only read the tags show them synced too. The scan also says how many of the tracks missing lyrics only had plain ones.

### Finding lyrics for tracks that have none

**Library → Upgrade library → Scan and find lyrics** scans the library for tracks without lyrics and looks them up right away, with a progress bar. When it ends, it says how many tracks got lyrics, how many none was found for, and how many failed. See [Upgrade library](library-upgrade.md#while-it-runs).

::: info What about Genius, Musixmatch and AZLyrics?
They aren't available, and Downtify no longer offers them:

- **AZLyrics** forbids third-party use of its lyrics in the page itself.
- **Musixmatch**'s desktop API answers with an empty token unless you have credentials it doesn't hand out to applications.
- **Genius**' `robots.txt` disallows the search endpoint needed to find a song's page.

Saved settings that still name them keep working: the names are ignored, and a list left with nothing else falls back to the default providers.
:::

## Skipping providers that had nothing

After a lookup, Downtify records for each song which providers answered and which came back empty, in `downtify_library.db` under `/data` (on the default SQLite backend; with PostgreSQL, in the PostgreSQL database).

A provider that had nothing for a song isn't asked about it again for **30 days**, so re-downloads and large library passes don't repeat the same failed lookups. After that it's tried again, since catalogues grow. A provider that *did* have lyrics is never skipped, so a re-downloaded file gets them back.

## Embedding

| Format | Plain lyrics tag | Synced lyrics tag |
|--------|-----------------|------------------|
| MP3 | `USLT` (ID3) | `USLT` with timestamps |
| FLAC | `LYRICS` (Vorbis comment) | `LYRICS` with LRC content |
| M4A | `©lyr` | `©lyr` with LRC content |
| OGG / OPUS | `LYRICS` (Vorbis comment) | `LYRICS` with LRC content |

## Sidecar .lrc file

When synced lyrics are available, Downtify also saves a `.lrc` file. By default it sits **next to the audio** with the same base name. In **Settings → Tags & lyrics** you can turn that off and pick a **lyrics folder** instead (default `/data/lyrics`). That folder must be **outside** `/downloads`, the slskd tree, and any extra music folders — the audio's relative path is recreated under it (`Artist/Album/track.lrc`). Media players that read external lyrics (and the [built-in player](player.md#now-playing)) still pick the sidecar up. Changing this setting and running **Sync** on an extra folder copies existing `.lrc` files to the new location; the source file is removed when that tree is writable, and left in place on a read-only mount. A sidecar is written even if lyrics are already embedded in the tags.

Deleting the track from the Library page removes the `.lrc` (beside the file and in the dedicated folder) along with the audio, so lyrics never linger as an orphaned file.

## Adjusting the timing

Lyrics found online are sometimes a little early or late for the audio that was actually downloaded: another edit of the song, a longer intro. To fix a song, play it, open **Now playing → Lyrics** and press the timer button at the top right of the lyrics, **Adjust lyrics timing**:

- **−** shows the lyrics sooner and **+** later, a tenth of a second per press, up to a minute either way. The lyrics follow the new timing right away, so you can try it while the song plays.
- **Save** writes it into the song's files; **Reset** goes back to the saved timing.

Saving rewrites the timestamps themselves, in the `.lrc` sidecar and, when the file's tags hold time-synced lyrics, in those too (MP3 `SYLT` frames included). So the fix also shows in other players that read the `.lrc` or the tags, and in the apps. A read-only file keeps its tags; only the sidecar changes. An `[offset:N]` line in a `.lrc` is folded into the times when you save, and the built-in player honours one meanwhile.

The button only appears for library songs with time-synced lyrics. Any signed-in user can adjust them; the change shows in the [activity log](users.md#activity) as **Lyrics timing adjusted**. The endpoint is [`POST /api/library/lyrics/offset`](../api-reference.md#post-apilibrarylyricsoffset).

## When nothing is found

If no provider has the song, the download continues normally — the audio file is saved without lyrics, and no error is raised.
