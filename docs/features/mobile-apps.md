---
icon: lucide/smartphone
---

# Mobile Apps

Downtify can serve apps on your phone: they browse and stream the library straight from your server, and keep songs on the phone for offline listening. Everything an app needs is set up in **Settings → Apps**: pairing phones and the server's name. Who may use the server at all is set by the accounts in [Users & Sign-in](users.md).

## Pairing a phone

1. Open **Settings → Apps** and press **Pair a phone**.
2. In the app, choose **Scan the code** and point the camera at the QR code — or type the 8-character code shown under it (`K7QM-2XPD`; case and dashes don't matter).
3. The dialog confirms when the phone is paired, and it shows up under **Paired apps**.

The phone is paired to **your account**: it plays as you, and it shows up in your activity. Anyone with an account can pair their own phones.

A code works **once**, for **five minutes**, and trying wrong codes is rate-limited. The phone gets a key of its own that it keeps; the server only stores a hash of it.

**Paired apps** lists your phones (an admin sees everyone's, with whose each is) with their platform, when it was last seen and from which address. **Unpair** stops a phone at once — its next request fails, an open connection is closed, and links it shared (see [Casting](#casting)) stop working. To use it again, pair it again.

## What a paired app may do

Paired apps can browse, play, like, keep songs offline and ask the server to download music — but not change settings, credentials or delete files; that needs the web page, signed in as an admin.

**Settings → Apps → Sign out everywhere** unpairs every app of yours and signs you out of every browser, this one included. Signing in, accounts and a forgotten password are in [Users & Sign-in](users.md).

## Finding the server on your network

The server announces itself on the local network (mDNS / Bonjour, as `_downtify._tcp`), so an app lists it under **Found on this network** — name, address and version — without typing anything. The name is the one set under **Settings → Apps → Server name** (the machine's hostname until you change it).

::: info Docker's default network hides the announcement
In Docker's default *bridge* network, the announcement stays inside Docker and phones don't see it. Either run the container with `network_mode: host` (see [Docker Compose](../getting-started/docker-compose.md#finding-the-server-from-the-apps)), or type the server's address into the app — everything else works the same.
:::

Set `DOWNTIFY_DISCOVERY=false` to stop announcing.

## Streaming quality

Apps play the files as they are (**Original**) or ask the server for a smaller copy: Opus, AAC or MP3 at 96–320 kbps — useful on mobile data. The server makes that copy with ffmpeg the first time a song is played that way (a few seconds for a typical song) and keeps it, so seeking works like in any file and the next play is instant.

- A file that's already small enough (a lossy file at or below the requested bitrate) is streamed as it is, never re-encoded.
- Copies are kept in `/data/transcode_cache`, 2 GB at most by default; the least recently played go first. At most two are made at a time. Both limits are [environment variables](../getting-started/environment-variables.md#mobile-apps-and-sign-in).
- If the phone gives up while a copy is being made, the server stops making it.

## Casting

Apps can send a song to a Chromecast or other player that fetches audio on its own. The app gets a link from the server that works for that one song for a limited time (an hour by default) and only while the phone stays paired; no key of the phone's goes into it.

## Behind a reverse proxy

If Downtify sits behind nginx, Caddy, Traefik or similar (for HTTPS, or to reach it from outside):

- **Pass the WebSocket through.** `/api/ws` needs the `Upgrade`/`Connection` headers forwarded (Caddy and Traefik do this by default; nginx needs `proxy_set_header Upgrade $http_upgrade; proxy_set_header Connection "upgrade";`).
- **Pass Range requests through** unchanged, and don't buffer audio responses (nginx: `proxy_buffering off;` for `/api/v1/` and `/downloads/`), or seeking and large files suffer.
- **Tell Downtify which proxy to trust.** Set `DOWNTIFY_TRUSTED_PROXIES` to the proxy's address (e.g. `172.18.0.0/16`). Only then does Downtify use `X-Forwarded-For` for the client's address (rate limits, "last seen" in Paired apps) and `X-Forwarded-Proto`/`X-Forwarded-Host` to mark the sign-in cookie secure and check where requests come from. Without it, those headers are ignored — anyone could send them.
- **Use HTTPS** when the server is reachable from outside: the password and the apps' keys travel with every request.

## For app developers

The whole flow an app follows — discovery, pairing, syncing the library, streaming, reporting plays — is in the [mobile client contract](../mobile-client-contract.md), and every endpoint is in the [API reference](../api-reference.md#server-and-sign-in).
