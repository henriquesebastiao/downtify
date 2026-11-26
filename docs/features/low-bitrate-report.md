---
icon: lucide/gauge
---

# Low-bitrate Report

Older downloads can be low quality: a 128 kbps rip, 160 kbps audio from YouTube, a 192 kbps file someone sent you. The **low-bitrate report** lists those files and offers a better copy of each from Soulseek (slskd). **Nothing is replaced until you approve it**, and every replaced file goes to the [music trash](music-trash.md), so you can undo it.

Only admins can use it (see [Users & Sign-in](users.md#admins-and-users)). Finding copies needs [slskd](slskd-navidrome.md); replacing needs the [music trash](music-trash.md) to be on.

## Opening the report

In the **Library**, open **Upgrade library** and press **Open the report** under **Low-bitrate report**.

The report lists every lossy file under **256 kbps** (change it with **List files**: under 128, 160, 192, 256 or 320 kbps), lowest bitrate first. Each row shows the bitrate, format, size and, when Downtify knows, where the file came from (YouTube, SoundCloud, Soulseek…). Lossless files (FLAC) are never listed, and neither are files whose bitrate can't be read.

Opening the report reads your library and writes nothing.

## Finding better copies

Press **Find** on a file, or select several and press **Find better copies**. Downtify searches Soulseek the same way a download does: the same searches, the same matching on title, artist and length, the same peers. It writes nothing; it only lists what it found under the file.

Copies are offered in this order:

1. **MP3 at 320 kbps** (a VBR MP3 such as LAME V0 counts too), marked **Best**.
2. **MP3 at 256 kbps or more.**
3. **Other lossy formats** (`.m4a`, `.ogg`, `.opus`) at 256 kbps or more.
4. Files that **don't list a bitrate** — Downtify checks the real bitrate after downloading and refuses the copy if it isn't better.

A copy is only offered when it's better than the file you have. Lossless copies (FLAC) are left out unless you turn on **Also offer lossless (FLAC)** before searching, and a format in **Formats to avoid** ([Download settings](download-settings.md)) is never offered.

Each copy shows its quality, size, how far its length is from your file's, and which peer shares it (and how long their queue is, when they're busy). The best one is picked for you; pick another if you prefer.

## Replacing

Press **Replace** on a file, or select several and press **Replace selected files**, then confirm. Each replacement is a job in the **Queue** and uses the same download slots as everything else (**Parallel downloads**).

For each file, Downtify:

1. Downloads the copy you picked from Soulseek.
2. Checks it: it must be readable audio, about as long as your file (within 5 seconds), and really better than your file. If not, nothing changes and the row says why.
3. Writes it **beside** your file, with your file's tags, cover, lyrics (and `.lrc` file) and date, so it doesn't show up as "recently added". It's named like the old file plus ` (HQ)` — `Halo (HQ).mp3` — or keeps the old name when the format changed (`Halo.m4a` → `Halo.mp3`).
4. Moves everything that pointed at the old file onto the new one, the same way the [Doctor merges duplicates](doctor.md): playlists and M3U files, likes, ratings, Playlist Monitor records and the mobile apps.
5. Moves the old file to the **music trash**.

If Retry is pressed in the Queue for a failed replacement, the same copy is tried again — it never downloads the song as a new track.

## Undoing a replacement

Open the **Trash** (Library → Trash, or **Open the trash** on the report) and restore the old file. It comes back under its old name, next to the new copy; delete the new copy from the Library if you don't want it.

## Good to know

- Search results are kept while the server runs; after a restart, or after 6 hours, search again before replacing.
- The music trash only takes files it can identify (an ID, or title, artist and album tags). A file it can't take is refused before anything is downloaded.
- In [library-only mode](library-only.md), searching and replacing are off; the report itself still works.
