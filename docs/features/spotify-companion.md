---
icon: lucide/radio-tower
---

# Spotify companion

Spotify builds some playlists for one listener: Daily Mixes, Discover Weekly, Release Radar, the mood, genre, decade and artist mixes, and the radios. One link shows every signed-in listener their own songs, and someone who isn't signed in gets a generic list. Downtify reads Spotify without an account, so on its own it can only follow that generic list (see [Spotify mixes made for you](playlist-monitor.md#spotify-mixes-made-for-you)).

The **Spotify companion** is an optional browser extension that fixes this. It runs in a browser where *you* are signed in to Spotify: your own computer, or a browser container on your server. It reads your version of each mix and sends the song list to Downtify. With it, watching your mixes downloads the songs Spotify picked for you.

It's off until an admin turns it on under **Settings → Apps → Spotify companion**.

## What stays where

- **Your Spotify sign-in never leaves that browser.** Downtify never asks for your Spotify password or cookies. The extension doesn't read them either. To read a mix, it borrows the short-lived token the open Spotify web player uses for its own requests, and asks Spotify for that one playlist, the same request the player makes when you open it.
- **What Downtify receives:** song lists, plus your Spotify account's id and display name, so it can tell when the browser is signed in to someone else.
- The extension signs in to Downtify with a key, a paired app called **Spotify companion** under **Settings → Apps → Paired apps**, where you can revoke it.

## Set it up

1. In Downtify, open **Settings → Apps → Spotify companion** and turn on **Read personal mixes with the companion**.
2. Click **Download the companion**. The ZIP contains the extension with this server's address and a new key already filled in. Keep it private: the key lets anyone with it use Downtify as an app. Each download makes a new key.
3. Unzip it (on Windows: right-click, **Extract All**), and load the folder it makes, the one with `manifest.json` in it, into a Chromium browser (Chrome, Brave, Edge, Chromium): open the extensions page, turn on **Developer mode**, and choose **Load unpacked**.
4. Its settings page opens. Check the Downtify address (it's the one your browser used; another device may need the server's network address, such as `http://192.168.1.20:8000`), then click **Save** and allow access to that address.
5. Sign in to Spotify in that browser. The companion keeps a pinned Spotify tab open for this.

Within a minute, **Status** on the settings card shows **Ready**, the account it's signed in to, and when it last checked in. Personal mix watches on the Monitor page now show **Your version** instead of **Personal mix**.

### On your server, in a browser container

The companion only reads while its browser runs. For a browser that's always on, run one in a container next to Downtify, on the same server or another machine on your network. This example uses the [linuxserver/chromium](https://docs.linuxserver.io/images/docker-chromium/) image, which shows its desktop in a web page so you can sign in to Spotify once:

```yaml
services:
  spotify-browser:
    image: lscr.io/linuxserver/chromium:latest
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=Etc/UTC # your time zone
      # A password for the web desktop: it holds your Spotify sign-in.
      - CUSTOM_USER=me
      - PASSWORD=change-me
      - CHROME_CLI=--load-extension=/companion
    volumes:
      - ./spotify-browser:/config # the browser profile, kept across restarts
      - ./downtify-companion:/companion:ro # the unzipped extension
    ports:
      - 3011:3001 # the web desktop (HTTPS)
    shm_size: 1gb
    restart: unless-stopped
```

Open `https://<server>:3011`, sign in to Spotify in that browser, open the extension's settings page from its extensions menu, check the Downtify address and click **Save**. The container needs about 0.5 to 1 GB of memory. Keep its port on your home network only.

::: info An existing browser for other tools
A browser that n8n or an AI agent already drives can work too, if it's Chromium (Google Chrome 137 and later ignore `--load-extension`), keeps its profile across restarts, and you can sign in to Spotify in it. A fully headless browser has no screen to sign in on, and an agent driving it might navigate the Spotify tab away. A container of its own is simpler.
:::

### With an AI agent on your server

If an AI agent runs on your server (Hermes, OpenClaw, Claude Code, n8n's AI agent…), it can do the setup. Under **Settings → Apps → Spotify companion**, **Set up with an AI agent** makes instructions to paste into it. Fill in **Address the browser will use** first if the browser will run in a container or on another machine (the server's network address, such as `http://192.168.1.20:8000`, not `localhost`).

The instructions hold a private link that works for 24 hours. With it, the agent can:

- **download the extension**, with the address and a key already in it, and download it again for a different address (the key stays the same; it's listed as **Spotify companion (AI setup)** under **Paired apps**);
- **run it in a browser on the server**, either the browser container above or a headless Chromium it already has (Chromium, Brave or Edge, with its own kept profile; Google Chrome 137 and later can't load it);
- **check how it's doing**, with a status that has no names or keys in it, until it says `ready`.

The ZIP lets the extension reach Downtify from the start, so nobody has to click **Save** in a browser with no screen.

You still sign in to Spotify yourself. The instructions tell the agent never to type, ask for or copy your Spotify password, cookies or tokens. For a headless browser, they explain two ways to sign in yourself: inspect its Spotify tab from your own Chrome (`chrome://inspect` over an SSH tunnel), or open the same profile once with a screen.

The link ends after a day or when Downtify restarts. Make new instructions to get another one.

## When it reads

Downtify decides what is read and when, so the browser never looks like a script hammering Spotify:

- **Time slots:** reads happen only inside the slots you set, each with its days, start and end time. A slot may run past midnight. Two slots, 09:00 to 12:00 and 18:00 to 23:00 every day, come set up.
- **Seats:** how many mixes a slot may read. When they're used up, the rest wait for the next slot.
- **Kinds:** a slot can take only some kinds of mix: **Daily Mixes**, **Discover Weekly and Release Radar**, or **Other mixes and radios**.
- **One at a time, spread out:** one read runs at any moment. The next waits until the reads left in the slot are spread evenly over what's left of it, with some jitter, never closer than **Shortest gap between reads** and never more than 30 minutes apart. The first read of a slot starts a little after it opens. A mix of more than 100 songs is read in pages, with a short pause between them.
- **Only what's due:** a mix is read once its watch's check interval has passed, so a Daily Mix set to **Every day** is read once a day. Discover Weekly and Release Radar are read once a week, after Spotify refreshes them: Monday and Friday morning. The most overdue mix goes first.
- **Check now** on a mix puts it at the front of the queue, even between slots. It still waits its turn and the gap, then the check runs. Checking many at once queues them all, one at a time.

To change how often many mixes are checked, use **Select** on the Monitor page and set their interval together.

A read costs Spotify one request per 100 songs. The extension also checks which account it's signed in to (the web player's own account query) at most every half hour, and right before each read. About 100 mixes read once a day is a few hundred requests spread over the day, fewer than an evening of using the web player.

If Spotify answers "too many requests", the companion stops reading for an hour.

## When it can't read

With the companion on, a personal mix is **never** read signed out. When the companion can't read, the mixes wait. Their badge on the Monitor page says **On hold**, and the settings card says why:

| Status | What it means | What to do |
| --- | --- | --- |
| **Signed out of Spotify** | The browser's Spotify sign-in ended. | Sign in to Spotify in that browser again. |
| **Another account** | The browser is signed in to a different Spotify account than the first one it read for. | Sign back in to yours, or click **Read for … instead** to switch. |
| **Not heard from** | The extension hasn't checked in for a few minutes: its browser is closed or can't reach Downtify. | Start the browser, or check the address on the extension's settings page. |
| **No Spotify tab** | No Spotify web player is open to read with. | Turn on **Keep a Spotify tab open** in the extension, or open one. |

The companion keeps one pinned Spotify tab of its own and never opens a tab per mix: reads go straight to Spotify's API, not through a page. After a browser restart it reuses its pinned tab, and it closes extra pinned Spotify tabs so they never pile up. It only reloads its own tab, never one of yours, and never while it's playing, so on your own computer you can keep listening in it.

With [notifications](notifications.md) set up, the **Spotify companion** event tells you when it was signed out, switched account, or hasn't been heard from for **Tell me after it has been quiet for** hours (6 by default). It tells you again when everything is back. The event is on by default for channels you set up from now on. For an existing channel, tick it under **What to send**.

## Turning it off

Switch **Read personal mixes with the companion** off and Downtify goes back to reading these mixes signed out, with the **Personal mix** warning. Revoke the key under **Paired apps** and remove the extension from the browser. Songs already downloaded stay in your library.
