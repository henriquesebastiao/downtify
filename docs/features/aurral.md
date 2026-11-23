---
icon: lucide/plug
---

# Aurral

[Aurral](https://github.com/lklynet/aurral) is a self-hosted app that finds new music, gets it and plays it from its own library. Its **Downtify plugin** adds Downtify as one of Aurral's download sources: Aurral asks Downtify for a song or an album, Downtify fetches it the way it fetches its own downloads (YouTube Music, slskd, SoundCloud, Deezer through Deemix, with covers, lyrics and tags), and Aurral takes the finished files into its own library.

It is **optional and off by default**. Until an admin turns it on, Downtify answers Aurral with "turned off" and nothing else changes.

## Turning it on

1. In Downtify, open **Settings → Apps → Aurral** (admins only).
2. Turn on **Let Aurral download through Downtify** and save.
3. Press **Make a key** and copy the key. It is shown once. It is a [paired-app](users.md) key: it is listed under **Paired apps** as "Aurral", where you can revoke it.
4. In Aurral, open **Settings → Plugins**, install the **Downtify** plugin from `https://github.com/lklynet/aurral-plugins`, and enter Downtify's address (like `http://192.168.1.10:8611`) and the key.
5. Press **Test** in Aurral, then turn the plugin on.

Downtify then shows up among Aurral's download sources, and Aurral's source priority decides when it is tried.

## What a hand-over download does

| Step      | What happens                                                                                                                                                                                                                                                      |
| --------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Search    | Aurral sends the artist and title (or album). Downtify searches YouTube Music, as its own search does, and answers with titles, artists, albums and lengths. When only YouTube sources are on, it also says the format and bitrate from **Settings → Downloads**. |
| Download  | Aurral picks a result. Downtify downloads it with your audio sources, formats, covers, lyrics and tag settings. With slskd on and nothing on YouTube Music, slskd is searched by name, as in Downtify's own search.                                               |
| Hand-over | Aurral checks every 15 seconds. When the file is ready, Aurral fetches it, checks it like any download, and files it in its own library.                                                                                                                          |
| Clean-up  | Downtify deletes the hand-over folder as soon as Aurral has the files, or when Aurral cancels.                                                                                                                                                                    |

A hand-over download stays out of Downtify's own library:

- It is saved to its own folder, `aurral-handover` beside `settings.json` (`/data/aurral-handover` in Docker), never to the music folder.
- It isn't added to the library listing, playlists, Navidrome, the download log or Artist Watch.
- A song Downtify already has is handed over from the library as it is. It isn't downloaded again, and the library file is never changed or deleted.
- With slskd, the file is copied out of slskd's folder, and slskd's own copy is left where slskd put it.
- Hand-over downloads share **Parallel downloads** with Downtify's own queue, so Aurral never makes Downtify download more at once than you allowed.
- Anything left behind is deleted after 26 hours, and on every start. A download Downtify was working on when it restarted is reported as gone, and Aurral moves on to its next source.

**Library-only mode** turns hand-over off too, like every other download.

## For developers

The plugin talks to these routes with the key as `Authorization: Bearer`. Everything but the first answers `409` while hand-over is off.

| Route                                                 | What it does                                                                                                                           |
| ----------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| `GET /api/aurral`                                     | `{enabled, version, library_only, format, bitrate}`                                                                                    |
| `GET /api/aurral/search/tracks?artist=&title=&album=` | Up to 20 track results: `id`, `title`, `artist`, `album`, `durationMs`, `format`, `bitrate`, `data`                                    |
| `GET /api/aurral/search/albums?artist=&title=`        | Up to 20 album results: `id`, `title`, `artist`, `year`, `data`                                                                        |
| `POST /api/aurral/jobs`                               | `{song}` (a track result's `data.song`) or `{album_url}` (an album result's `data.url`): starts a job                                  |
| `GET /api/aurral/jobs/{id}`                           | `status` (`queued`, `downloading`, `done` or `failed`), `message`, `total`, `finished`, `failed` and `files` (`index`, `name`, `size`) |
| `GET /api/aurral/jobs/{id}/files/{index}`             | One finished file                                                                                                                      |
| `DELETE /api/aurral/jobs/{id}`                        | Cancels the job or says its files were taken; its folder is deleted                                                                    |
| `POST /api/aurral/key`                                | Admins, from the browser: a new key, shown once                                                                                        |

A job belongs to the account whose key started it; another account gets `404`.
