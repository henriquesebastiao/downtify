---
icon: lucide/cookie
---

# YouTube Cookies

Downtify pulls its audio from YouTube. Most of the time that works anonymously — but not always:

- **Explicit / age-restricted tracks.** YouTube only serves these to a signed-in adult account. Without cookies the download fails.
- **Bot challenges.** On datacenter IPs (VPS, some VPNs) YouTube periodically answers with "Sign in to confirm you're not a bot" instead of audio.

Supplying a `cookies.txt` fixes both: yt-dlp then talks to YouTube as your logged-in browser session does.

## Uploading a cookies.txt (recommended)

1. Install a cookie-export extension: [Get cookies.txt LOCALLY](https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc) (Chrome/Edge) or [cookies.txt](https://addons.mozilla.org/en-US/firefox/addon/cookies-txt/) (Firefox)
2. Open `youtube.com` **logged into your Google account** and export the cookies for that site — the file must be in **Netscape** format
3. In Downtify, open **Settings** (⚙️) → **YouTube cookies** → **Upload cookies.txt**

The file is validated on upload — a file that isn't a Netscape cookie jar is rejected immediately rather than silently breaking every later download. If it contains no `youtube.com` or `google.com` cookies you get a warning, since that usually means it was exported from the wrong tab.

Once uploaded you can **replace** it (upload another file) or **delete** it from the same screen.

::: tip This is the platform-agnostic route
Uploading through the web UI needs no bind mounts, no file paths and no shell — which is what makes it work on Docker Desktop for Windows, where mounting a `cookies.txt` into the container is notoriously awkward.
:::

## Where it's stored

The uploaded file is written to `cookies.txt` inside Downtify's data directory (`/data` by default) — the same volume that holds `settings.json` and the Playlist Monitor database. It therefore **survives container updates**: pulling a new image and recreating the container keeps your cookies, as long as `/data` stays a named volume or bind mount.

## Using an environment variable instead

The pre-existing [`DOWNTIFY_COOKIES_FILE`](../getting-started/environment-variables.md#anti-bot-youtube) variable still works and **takes precedence**:

```yaml
services:
  downtify:
    volumes:
      - ./cookies.txt:/cookies.txt
    environment:
      - DOWNTIFY_COOKIES_FILE=/cookies.txt
```

Mount it writable (no `:ro`) so the keep-alive can save the rotated cookies into it; a read-only file is still used, but goes stale like before.

When it is set, the settings screen shows the cookie section as locked and refuses uploads and deletions — the deployment owns that configuration, and Downtify must not overwrite a file it doesn't manage. Unset the variable (and recreate the container) to manage cookies from the web UI instead.

`DOWNTIFY_COOKIES_FROM_BROWSER` reads cookies straight out of a browser profile, but that requires the browser's cookie store to be reachable *inside* the container, so it's rarely usable in Docker.

## Keeping them working

Exported cookies don't expire on a fixed date. Google's session is a set of cookies that keep changing: the browser tab they came from rotates `__Secure-1PSIDTS`, `SIDCC` and friends every few minutes, and a copy that never learns the new values is eventually refused. yt-dlp then logs "The provided YouTube account cookies are no longer valid". On a VPN or datacenter IP YouTube is stricter, so this can happen within a couple of hours.

Downtify keeps the uploaded file signed in by itself:

- **Every download saves the new values.** yt-dlp gets a private copy of the file for each download; when it finishes, the cookies YouTube changed during it are merged back into the stored `cookies.txt`, without undoing a newer value another download saved meanwhile.
- **A keep-alive refreshes them on a timer.** Every 15 minutes (`DOWNTIFY_COOKIES_REFRESH_MINUTES`, `0` turns it off) Downtify asks Google to rotate the session cookies, the same request the browser makes, opens `youtube.com` with them and saves whatever changed. Even a server that downloads nothing for days keeps a live session.
- **The settings screen shows the result.** **Settings → YouTube cookies** shows *Signed in*, *Signed out*, *No account* (the file has no Google session, only visitor cookies) or *Check failed*, when it was last checked and when YouTube last asked for a bot check. *Check now* runs the keep-alive right away. A new upload is checked a few seconds after it is saved.

What you still have to do:

- **Export from a private/incognito window and close it.** Sign in to YouTube in a private window, open `youtube.com/robots.txt` in that tab, export the cookies, then close the window. A tab you keep using rotates the session itself, and the copy Downtify has is signed out within minutes. Don't use the same account in a normal browser window at the same time if you can avoid it.
- **Upload a new file when the screen says *Signed out*.** Google can still end the session (a password change, "sign out of all devices", a security review). The log says so too: `YouTube cookies are signed out`.
- Some regions require full identity verification on the Google account before YouTube serves age-restricted content at all. Being signed in is not always enough.

::: info Why there is no "Sign in with Google" button
Downtify can't sign in to Google for you. Google blocks scripted and headless browser logins ("This browser or app may not be secure"), asks for 2-step verification and device prompts, and YouTube no longer accepts OAuth from third-party clients like yt-dlp. A login form in Downtify would also mean handing it your Google password. Keeping an exported session alive is the part that can be automated.
:::

::: tip Bot checks without an account
"Sign in to confirm you're not a bot" comes from the IP address, not from missing cookies. If it keeps showing up on a VPN, switching the VPN server or exit country often helps more than new cookies. Cookies used for many downloads also raise the chance of YouTube limiting that account, so a throwaway account is the safer choice.
:::

::: warning Treat the file like a password
A `cookies.txt` contains live session tokens for your Google account. Anyone who can read it can act as you on YouTube. Downtify stores it with owner-only permissions where the filesystem supports it, and never exposes its contents through the API — only whether one is configured, its size, when it changed and whether YouTube still accepts it. Use a throwaway Google account if you'd rather not risk your main one.
:::
