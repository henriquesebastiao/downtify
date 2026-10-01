---
icon: lucide/compass
---

# Discover

Artists you don't have yet, suggested from the ones you do. Open **Discover** from the sidebar (on phones: **More → Discover**). The search box at the top is the [Finder](finder.md), a Deezer-only search: searching shows its results in place of the suggestions, and clearing it brings them back.

No account or API key is needed: the suggestions come from [Deezer](https://www.deezer.com/)'s public "similar artists" list, which works without signing in.

## How the suggestions are picked

1. **Your artists are weighed.** Every artist in your library counts for something, and counts more for each of these, most to least:
    - how often you **listen** to them in Downtify's player (recent listening counts more than listening months ago),
    - how many of their songs you have **liked**,
    - how many of their songs are **in your library**.

    The weight flattens out as it grows, so an artist with a 400-song discography doesn't drown out one you play every day.
2. **The top 15 are looked up on Deezer**, which returns the artists its listeners also like for each of them.
3. **Every suggested artist gets points** from each of your artists that suggests it — more from a heavier artist, and more the higher it sits on Deezer's list. An artist several of your favourites point to ranks above one that only one of them mentions. Under each suggestion, *Because you like …* names the artists it came from.

Artists already in your library and artists you've [hidden](#hiding-artists) are never suggested.

Click a suggestion's photo to open the artist in the [Finder](finder.md)'s columns — their profile, whole discography and any album's tracks, all from Deezer. The **⋯** menu on a suggestion also has **Find songs** (the artist's songs, shown as a [Finder](finder.md) search), **Open on Deezer** and **Not interested**. The page shows the best 12 artists; **Show all** lists every suggestion (up to 48).

## Albums and playlists

Below the artists, built on them:

| Section | What's in it |
|---------|--------------|
| **Albums for you** | The best-known album of each of the top 12 suggested artists |
| **More from your artists** | Up to two popular albums from each of your 6 heaviest artists that aren't in your library yet |
| **Playlists for you** | The essentials of each suggested artist: Deezer's own **`100% <artist>`** playlist (picked by Deezer's editors), then Spotify's own **`This Is <artist>`** |

They come in two steps:

1. **Deezer first.** Each artist's discography is read from Deezer: a full album comes before a single or EP, and among them the one with the most fans. This answer is quick, and fills the shelves.
2. **Then Spotify.** A few seconds later, Spotify's own picks for the same artists (from its search) are added **at the end** of each shelf — placeholders show where they'll appear while they load, and nothing already on the page moves. An album both services pick appears once. Each Spotify album is looked up on Deezer by artist and title; when Deezer has it, it opens in the Finder like the rest.

A small icon in the bottom-left corner of each album and playlist cover says which service it comes from:

- **Deezer** — an album opens in the [Finder](finder.md)'s columns, with its tracks ready to preview and download.
- **Spotify** — Deezer doesn't have that album, so it opens the same page a pasted Spotify link does.

Playlists — Deezer's as well as Spotify's — always open that page, where you can **preview** their songs before downloading any of them (see [Previewing songs before downloading](top-songs.md#previewing-songs-before-downloading)), then download all of it, just the new songs, or a selection.

Everything is kept for a week like the similar artists, and a Spotify album's match on Deezer for a month (a week when Deezer didn't have it, in case it's added). An album already in your library (matched by artist and title, so `Dummy (Deluxe Edition)` counts as `Dummy`) and a playlist you've already downloaded are left out; hiding an artist also takes their album and playlists away.

## What counts as a listen

A song counts once per play, after **half of it** (or **four minutes**, for long songs) has actually played — skipping ahead to the middle doesn't count, and songs shorter than 30 seconds never do. Podcast episodes don't count.

Listens are kept on the server, so what you play on your phone shapes the suggestions on your desktop too. To start over, open **Hidden artists → Clear listening history**; your library and liked songs stay as they are.

## Hiding artists

**⋯ → Not interested** on a suggestion hides that artist from Discover for good (the toast that appears has an **Undo**). To hide an artist before it's ever suggested — one you just don't want to hear about — open **Hidden artists** and type the name in.

The same list shows every hidden artist, with **Show again** to take one back. Names are matched ignoring case and the characters a file name can't hold, so hiding `AC/DC` also hides `ACDC`.

## Good to know

- **Suggestions are cached for a week.** Deezer's and Spotify's answers for each of your artists are kept for 7 days, so opening Discover again is instant and doesn't cost a round of requests. **Refresh** re-ranks with your latest library, likes and listens; an artist whose week is up is looked up again.
- **If Deezer can't be reached** (or rate-limits the requests) for some of your artists, the page still shows what it could build and says the list is shorter than usual — try again later. A failed lookup is never remembered as "no similar artists".
- **An artist Deezer doesn't know** simply adds nothing; it isn't searched for again until its week is up.
- Only artist and album *names* ever leave your server (as Deezer and Spotify searches). Nothing about what you play is sent anywhere.

## API

See [Discover](../api-reference.md#discover) in the API reference.
