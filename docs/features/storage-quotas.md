---
icon: lucide/gauge
---

# Storage Quotas

On a server shared by a family, a school or a group of friends, one account can otherwise fill the disk. **Storage quotas** let an admin cap how much each user may download. Admins are never limited: they manage the server, and its disk.

## Setting quotas

In **Settings → Users** (admins):

- **Storage quotas → Default quota** applies to every user without a quota of their own. Type a size in GB and press **Save**; leave it empty for no limit. With no default and no quotas of their own, nothing is limited — which is how a server starts.
- **Edit** a user and pick their **Storage quota**:
  - **Default** — they follow the default quota (the hint underneath says which).
  - **Unlimited** — no limit for them, whatever the default.
  - **Custom** — a quota of their own, in GB.

Each user's line in the list shows how much of their quota they use (`quota 1.2 GB of 2.0 GB`), and an **Out of space** badge once they have none left. A role change to admin lifts the limit; making them a user again brings back the quota they had.

GB here means 1024³ bytes, the same unit the rest of the app shows sizes in.

## What counts

What counts against a quota is the size on disk of the songs an account downloaded — the files as they are after conversion and tagging, read from the Library listing, so it is what is really there. It is the same figure as the size under each account in [Per-account usage](users.md#per-account-usage).

- A song two users downloaded is stored once but counts for **both**: each of them asked for it.
- Songs a [playlist or artist watch](playlist-monitor.md) brings in, files added to the folder by hand and songs from [extra music folders](external-library.md) belong to no account, so they count for nobody.
- A deleted song stops counting as soon as the Library no longer lists it.

Everyone sees their own usage in **Settings → General → Account**, under **Storage**: what they downloaded, the quota, the space left and a bar that turns amber from 90 % and red when the quota is reached. Paired apps can read the same numbers from [`GET /api/me/storage`](../api-reference.md#get-apimestorage).

## When the quota is reached

A download is refused while its account has no space left — the message says how much is used and how much is left:

> Storage quota reached: 2.0 GB of 2.0 GB used, 0 B left. Delete some of your downloads or ask an admin for more space.

The check runs when a download is asked for (a song, an album, a playlist, a CSV import) and again when each queued song starts, so a long playlist stops at the quota instead of running past it. A song's size isn't known before it is downloaded, so a download that started with space left still finishes: usage can go past the quota by up to one song per [parallel download](download-settings.md). A song that was already in the library is not downloaded again and is shared as usual.

When a song is asked for by several accounts at once, it is downloaded as long as one of them still has space.

## Freeing space

- **Delete your own downloads.** Deleting a song you downloaded frees its size from your quota (see [Deleting songs](users.md#deleting-songs) — when someone else downloaded it too, it stays in the library but stops counting for you).
- **Reset usage** (admins). **Edit** a user and press **Reset usage**: Downtify forgets which songs they downloaded, so their usage starts from zero. No file is deleted. Those songs then belong to nobody, so the user can no longer delete them as their downloader, and with [a library for each user](users.md#a-library-for-each-user) on they leave that user's library.
- **Give more space** by raising their quota, the default, or making them unlimited.

## API

`GET /api/me/storage`, `GET /api/users/storage`, `PUT /api/users/storage/default`, `PUT /api/users/{id}/storage` and `POST /api/users/{id}/storage/reset` — see the [API reference](../api-reference.md#get-apimestorage). A refused download answers `507` with the message above.
