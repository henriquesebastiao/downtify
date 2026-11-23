---
icon: lucide/bell
---

# Notifications

**Settings → Notifications** (`/settings/notifications`) sends messages about Downtify's long tasks and downloads to Discord, [ntfy](https://ntfy.sh), [Gotify](https://gotify.net) or any webhook. On Discord a bot can also answer commands such as `/status` and `/queue`, so you can check on a long scan from your phone. Only admins see it.

It is **off** until you turn it on: with the main switch off, Downtify makes no connection and sends nothing. The messages are in English, whatever language the app is in.

## What it tells you

| Task | What it covers |
| --- | --- |
| Doctor | Every [Doctor](doctor.md) job: the health check, the slskd check and cleanup, duplicate merges, playlist and Navidrome repairs. |
| Library upgrade (cover art, lyrics, tags) | The [Library upgrade](library-upgrade.md) scan, then the run that repairs cover art, lyrics, tags or ISRC codes. The finish message says how many songs were updated and, for lyrics, how many got some. |
| Star ratings | Each [Ratings from Deezer](navidrome-ratings.md) run and preview, scheduled or started by hand. |
| Wanted catch-up | **Check all now** and **Download all** on the Wanted list of the [artist watches](playlist-monitor.md). |
| Backups | Each [backup](backups.md), automatic or **Back up now**. |

For each task you pick the moments you want to hear about: **Started**, **Progress**, **Finished** and **Failed**.

| Other event | When |
| --- | --- |
| Download failed | A song in the queue could not be downloaded, with the reason. |
| Songs downloaded | A song finished downloading (off by default: a big playlist sends a lot). |
| New releases found | An artist watch found releases it did not have, with their names. |
| Watch downloads | A watch's automatic check downloaded new songs. |

A burst of the same event is grouped: Downtify waits 30 seconds and sends one message such as "12 downloads failed" with the first ten songs listed, not twelve messages.

### Progress without the spam

On Discord each running task gets **one message that is edited in place**: the progress bar moves, the step changes, and when the task ends the same message shows the result. A separate short message then says it finished or failed, because Discord does not notify anyone about an edit. **Progress updates** sets how often that message may change (30 seconds to 15 minutes, default 1 minute).

ntfy, Gotify and webhooks cannot edit what they sent, so they get a progress line only at each quarter (25%, 50%, 75%) instead.

## Channels

Each channel has its own switch, its own **What to send** choices and a **Send test** button that sends one message right away with what is filled in, saved or not. When a channel's last message failed, the reason (for example `Discord answered HTTP 404`) is shown under it.

Webhook URLs, the bot token and access tokens are kept in `notifications.json` beside `settings.json` in the data folder, readable by Downtify only. They are not part of `GET /api/settings` or of the [backups](backups.md), and the page never shows them again: a saved one reads **Saved (type to replace)**, and **Remove** deletes it.

### Discord

Pick how Downtify connects:

- **Webhook (send only)**: in Discord, open the channel's settings → **Integrations** → **Webhooks** → **New Webhook** → **Copy Webhook URL**, and paste it in **Webhook URL**. That is all it needs, but a webhook cannot read anything, so there are no commands.
- **Bot (send + commands)**: Downtify posts as a bot and answers commands.
  1. Open the [Discord Developer Portal](https://discord.com/developers/applications), **New Application**, give it a name.
  2. On **Bot**, press **Reset Token** and copy the token into **Bot token**. The bot needs no privileged intents.
  3. In Discord, turn on **Developer Mode** (User Settings → Advanced), right-click the channel → **Copy Channel ID**, and paste it in **Channel ID**.
  4. Save. Once the bot shows **Connected**, use **Invite the bot to your server** and pick your server: the link asks only to view the channel, send messages and embed links.

The bot connects to Discord's gateway from your server (an outgoing connection, so nothing has to be opened in your firewall) and registers its commands. New commands can take a minute to appear in Discord.

### ntfy

Fill in the **Topic** (and the **Server**, if you run your own; the default is `https://ntfy.sh`) and subscribe to the same topic in the ntfy app. On ntfy.sh anyone who knows a topic can read it, so pick a name that is hard to guess, or set an **Access token** for a protected topic.

### Gotify

Fill in your Gotify **Server** address and an **App token** (Gotify → **Apps** → **Create application**). Failures are sent with a higher priority.

### Webhook

Downtify sends a JSON `POST` to the URL for every message:

```json
{
  "source": "downtify",
  "event": "download_failed",
  "level": "error",
  "type": "failure",
  "title": "Download failed: Artist - Song",
  "body": "No match on any source",
  "text": "No match on any source",
  "fields": {},
  "progress": null
}
```

`title`, `body` and `type` are what an [Apprise API](https://github.com/caronc/apprise-api) server's `/notify/<key>` takes, so pointing the webhook at one reaches every service Apprise supports. `progress` is `[done, total]` while a task runs.

## Discord commands

With **Answer commands** on, the bot answers these in its channel:

| Command | Answer |
| --- | --- |
| `/help` | The list of commands. |
| `/status` | Every long task running now with its progress, and the download queue's counts. |
| `/progress task` | One task: Doctor, Library upgrade, Star ratings, Wanted catch-up or Download queue. |
| `/queue` | The download queue: downloading, waiting, done, failed, and what is downloading. |
| `/doctor` | The Doctor's running or last job. |
| `/upgrade` | The Library upgrade's running or last run. |
| `/lyrics` | What the lyrics part of the last Library upgrade found: added, none found, failed, still to go. |
| `/ratings` | The running or last star ratings run, and when the next scheduled one is due. |
| `/wanted` | The Wanted catch-up job. |

The commands only **read**: nobody in Discord can start, stop or change anything in Downtify. The bot answers only in the channel set in **Channel ID** (elsewhere it replies, visible only to the asker, that it is not listening there). To limit it to some people, list their Discord user IDs in **Allowed users** (right-click a user → **Copy User ID** with Developer Mode on).

::: tip
If the bot shows **Stopped** with "Discord rejected the bot token", the token was reset or mistyped: paste a new one and save.
:::

## API

All admin only:

| Request | What it does |
| --- | --- |
| `GET /api/notifications` | The settings (each secret only as `<name>_set`), the last error of each channel and the bot's state. |
| `PUT /api/notifications` | Save `{settings, clear}`. A blank secret keeps the saved one; `clear` lists secrets to remove, such as `discord.bot_token`. |
| `POST /api/notifications/test/{channel}` | Send a test message on `discord`, `ntfy`, `gotify` or `webhook`, with `{channel: {...}}` as unsaved values. |
