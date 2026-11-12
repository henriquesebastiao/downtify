---
title: Library-only mode
icon: lucide/library
---

# Library-only mode

An administrator can enable **Settings → General → Use only the library**.
The default is off. This is a server-wide music policy for every account,
browser and paired Android app.

Search matches the titles, artists and albums of the accessible server library.
The existing screens, navigation and player keep their layout. Search,
Discover and Charts use local tracks, albums, artists and playlists. Similar
tracks are ranked from saved artist, album and (when available) genre tags:
this is a metadata match, not an acoustic analysis. The seed and duplicate
recordings are excluded; an unknown seed or a library without related tracks
returns an empty result without falling back to an external radio service.
The existing library visibility rules still apply. Local music folders added
to the server are part of the library, including read-only mounts.

External music search, link resolution, previews, streams (including stream
cache files), downloads, replacements and online library upgrades are refused.
Automatic watched playlists and Spotify cache warming stop fetching, without
deleting subscriptions, changing their last-check time or consuming their
pending work. They resume when the mode is disabled. This setting does not
delete audio or clear the library, and it does not start any new downloads.

## Switching safely

Finish active downloads, checks or online upgrades before enabling the mode.
Activation returns HTTP 409 while external music work is in progress; it does
not cancel that work or partially save the setting. Save again after it ends.
The saved JSON setting is `library_only` and accepts only a boolean.

The server enforces the policy immediately. Current clients receive a
`music_policy_changed` WebSocket event and refresh the policy periodically
(15 seconds) and on reconnect. They drop external search results and stream
queue entries; local playback and the order of remaining local tracks are
preserved. Previously buffered external audio stops when the client receives
the policy. Old clients cannot use the server's external music endpoints,
but only updated clients can clear audio they have already buffered.

## Android and connection requirements

The app reads `library_only` from `GET /api/server/info` and retains it with
the paired server information. Missing fields on older servers mean off.
The Android app searches its synced library, receives local similar-track
results and can still play files downloaded from that library.

The phone needs a connection to its server to stream library files or request
similar tracks. Keeping files on the phone is the separate offline-download
feature. This mode does not turn the server into an Internet firewall: update
checks and other non-music administration remain separate.

## API compatibility

`POST /api/settings/update` accepts `{"library_only": true}` (admin only).
`GET /api/settings` returns the persisted boolean. `GET /api/server/info`
adds the same boolean without changing `api_version`.

Search and similar-track routes keep their response containers. Local song
rows carry `source: "library"`, `file` and `song_id: "library:<file>"`; `url`
is empty and no external preview is included. Use the existing library file
or match it to the mobile sync feed, never resolve the row through a provider.
The artist/album search endpoints return local cards in the same response
shapes; the cards open the existing library artist and album pages.
Blocked external music endpoints return HTTP 409 with an explanatory detail.
Disabling the setting restores their previous behavior and provider settings.
