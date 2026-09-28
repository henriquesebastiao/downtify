---
icon: lucide/users
---

# Users & Sign-in

Everyone who uses Downtify signs in with a **username and password**, and each person can have an account of their own. An admin manages the accounts in **Settings → Users** and sees what everyone does in **Settings → Activity**.

## Signing in for the first time

A new server has one account:

| Username | Password |
|----------|----------|
| `admin` | `downtify` |

Sign in with it and **change the password** in **Settings → General → Account**: anyone who knows Downtify knows the default one. Until you do, Downtify reminds you after signing in and shows a warning in Settings.

::: warning Change the default password before exposing the server
The default password protects nothing. Change it before you make Downtify reachable from outside your home network — and use HTTPS there (see [Behind a reverse proxy](mobile-apps.md#behind-a-reverse-proxy)).
:::

### Upgrading from an older version

A server that ran a version without accounts gets the same `admin` account, and the sign-in page says so once — until an admin signs in — with the username and password to use:

- If you had set a password under the old **Require sign-in** option, that password keeps working for `admin`.
- Otherwise it's `downtify`.

Browsers signed in before the upgrade sign in again. Phones paired before it stay paired, and now belong to `admin`.

## Admins and users

| | Admin | User |
|---|---|---|
| Listen, search, download, like, Discover, Charts, Finder, podcasts | ✓ | ✓ |
| Pair phone apps (to their own account) | ✓ | ✓ |
| Settings → General (their own account and preferences), Apps, About | ✓ | ✓ |
| Every other setting (sources, files, tags, Navidrome, library, server), renaming the server | ✓ | |
| Delete files and playlists, replace a track's audio, change playlist watches and podcast subscriptions, edit artist photos | ✓ | |
| Manage users, see the activity log | ✓ | |

A user who tries something that needs an admin gets a message saying so.

## Your account and preferences

**Settings → General** starts with your **Account**: change your username or password, or sign out. You can also sign out from the sidebar (or **More** on a phone).

The rest of **General** — theme, language, showing lyrics in the player, albums in search results — is **yours**: it follows your account to every browser you sign in to, and changes nothing for anyone else.

**Settings → Apps** lists the phones paired to your account (an admin sees everyone's, with their owner). **Sign out everywhere** unpairs your apps and signs you out of every browser.

## Managing users

In **Settings → Users** an admin can:

- **Add a user** — username (3 to 32 letters, digits, `.`, `-` or `_`), password (at least 8 characters) and role.
- **Edit** a user — rename them, make them an admin or a user, or give them a new password (which signs them out of their browsers; their apps stay paired).
- **Delete** a user — their apps are unpaired and their browsers signed out. What they downloaded stays in the library.
- **Sign out everyone** — every app of every user is unpaired and every browser signed out, yours too.

There's always at least one admin: the last one can't be deleted or made a user, and you can't delete your own account.

## Activity

**Settings → Activity** (admins) shows, like Jellyfin's dashboard:

- **Playing now** — what each browser and app is playing, by whom, where it is in the song, and whether it's paused. It refreshes every few seconds.
- **History** — sign-ins (and failed ones, with the address they came from), sign-outs, songs played, downloads, likes, deleted files, apps paired and unpaired, accounts added, changed or deleted, passwords and settings changed. Filter by user or by kind. Saved settings are listed by name only, never their values. Entries are kept for 90 days.

Apps report what they play too — see the [mobile client contract](../mobile-client-contract.md#8-report-plays).

## Turning accounts off

A server only you can reach — on your own computer, or behind something that already asks for a password — may not need accounts at all. Set `DOWNTIFY_DISABLE_AUTH=true` (see [Environment Variables](../getting-started/environment-variables.md#mobile-apps-and-sign-in)):

```yaml
environment:
  - DOWNTIFY_DISABLE_AUTH=true
```

Then:

- There's no sign-in page: whoever opens Downtify uses it as the first admin (`admin` on a new server).
- The sign-out buttons, **Settings → Users**, the **Account** part of **Settings → General** and **Sign out everywhere** in **Settings → Apps** are gone.
- Phones can still be paired (to that admin), and **Settings → Activity** still shows what plays where.
- Theme, language and the other **General** preferences are kept as that admin's.

::: warning Anyone who can reach the server can do everything
With accounts off, nothing asks who you are: everyone on your network — or on the internet, if the port is exposed — can change settings, delete music and pair a phone. Don't turn accounts off on a server others can reach.
:::

Set it to `false` (or remove it) and sign-in is required again, with the accounts, passwords and apps as they were.

## Forgot the password?

Run this on the server — `admin` gets the password `downtify` back (and is recreated as an admin if it was renamed or deleted); other accounts and paired apps are left alone:

```bash
docker exec downtify python main.py auth-reset
```

Outside Docker, run `python main.py auth-reset` (or `uv run python main.py auth-reset`) in Downtify's folder. Then sign in and change the password.

## Scripts and the API

Every API call needs credentials now (see the [API reference](../api-reference.md#server-and-sign-in)). A script can sign in with `POST /api/auth/login` and keep the `downtify_session` cookie, or use a paired device's token.
