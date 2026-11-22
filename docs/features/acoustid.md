---
icon: lucide/audio-waveform
---

# Identify Songs by Sound

Downtify can recognise a song by its audio, with [AcoustID](https://acoustid.org/), the free and open fingerprint database behind MusicBrainz Picard. It is meant for older files whose tags Deezer can't place, so they never got an ISRC (see [ISRCs for older songs](library-upgrade.md#isrcs-for-older-songs)): AcoustID confirms what the file is, and when it is sure, Downtify adds the recording's ISRC.

It is off until you turn it on, and it needs your own AcoustID API key (free).

## Turning it on

1. Register an application on [acoustid.org/new-application](https://acoustid.org/new-application) (sign in with a free account; any name and version will do). AcoustID shows the application's **API key**.
2. In **Settings → Tags & lyrics**, in the **Song IDs** group, turn on **Identify songs by sound (AcoustID)** and save the settings.
3. Paste the key into **AcoustID API key**, press **Save key**, then **Test key**. "AcoustID accepted the key." means it works.

Only admins see this. The key is kept in its own file in the data folder (`.acoustid_key`), not in `settings.json`, and is never sent back to the browser: the settings show only its last four characters. **Remove key** deletes it. It isn't part of a [backup](backups.md), so enter it again after a restore on a new server.

::: info Fingerprinting
A fingerprint is made from the first two minutes of each file, on your server: the audio itself is never uploaded, only the fingerprint and the length. Downtify uses `fpcalc` ([Chromaprint](https://acoustid.org/chromaprint)'s tool) when it is installed, otherwise FFmpeg's built-in Chromaprint support, which the Docker image's FFmpeg has. The settings say which one it found. Running outside Docker with an FFmpeg built without Chromaprint, install `fpcalc` (on Debian and Ubuntu, the `libchromaprint-tools` package), or point `DOWNTIFY_FPCALC` at it.
:::

## Looking songs up

In **Library → Upgrade library**, the **Identify songs by sound** card has two buttons:

- **Look up by sound (writes nothing)** scans for files without an ISRC, fingerprints each one and asks AcoustID, then lists the result for every track without changing any file.
- **Add ISRCs by sound** does the same and adds the ISRC of the files AcoustID confirms.

The buttons stay off, with the reason, until AcoustID is turned on, a key is saved and the server can make fingerprints.

Each track's line in the list says what was found:

| Line | Meaning |
| --- | --- |
| `Confirmed by sound (97%); would add ISRC …` | AcoustID is sure the file is the song its tags name, and MusicBrainz has one ISRC for it. **Add ISRCs by sound** writes it. |
| `Confirmed by sound (95%), but no single ISRC; left as it is` | The song is right, but MusicBrainz has no ISRC for it, or several. |
| `Sounds like Artist - Title (96%), not what the tags say; left as it is` | AcoustID knows this audio as another song. Worth a look: the file may be mislabelled, or a cover or remix. Nothing is changed. |
| `No sure match by sound; left as it is` | AcoustID doesn't know the audio well enough. |

## What is written

Only the ISRC tag, through the same verified working copy as every [library upgrade](library-upgrade.md); whatever pointed at the file (playlists, likes, owners) follows it. An ISRC is added only when all of these hold:

- AcoustID's score is at least 90%;
- the recording it names has the file's own artist and title (compared the way the library compares songs) and a length within 3 seconds of the file's;
- the recordings that agree share exactly one ISRC on MusicBrainz.

Anything less leaves the file exactly as it is. MusicBrainz covers some music poorly (many regional and independent releases, Hindi film songs under other spellings), so a weak or ambiguous match is never trusted.

::: warning No MusicBrainz IDs
Downtify never writes MusicBrainz IDs into your files. Navidrome builds its song and album IDs from them, so adding them would make Navidrome see songs it already knows as new ones (losing their plays, stars and playlist places).
:::

## Limits and pace

AcoustID allows three requests a second, and MusicBrainz one; Downtify keeps to both across the whole server and, when either is busy, waits and asks again. A large library takes a while: as with any upgrade you can leave the page, and **Pause** or **Cancel** the run. A file that got no sure answer isn't asked about again until **Don't check a track again for** has passed; a look-up-only run doesn't count, so **Add ISRCs by sound** asks again.
