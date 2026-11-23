---
icon: lucide/star
---

# Ratings from Deezer

Give the songs in your [Navidrome](https://www.navidrome.org/) library 0–5 stars from how popular they are on Deezer, so the hits float to the top in any Subsonic client. Start it with a button, or repeat it on a schedule.

It is a port of [dztnr](https://github.com/scatolo/dztnr) (MIT licence), itself a fork of [sptnr](https://github.com/krestaino/sptnr) by Kevin Restaino. The search, the star scale and the options work the way they do there.

It lives in **Settings → Navidrome**, in the **Ratings from Deezer** group below the login. Only admins see it, and only while **Use Navidrome** is on (see [slskd & Navidrome](slskd-navidrome.md)). It uses the Navidrome login saved there.

::: info Where the stars live
The stars belong to that Navidrome account and are kept in Navidrome's database, not in your music files. Other Navidrome accounts don't see them.
:::

## How a song is rated

1. Downtify reads your Navidrome library: artists, then their albums, then the songs. An album listed under two album artists is rated once.
2. Each song is searched on Deezer as "album artist + title", and the popularity (Deezer calls it `rank`) of the first result is used.
3. The popularity becomes stars with the scale below and is saved to Navidrome.

A song that Deezer can't find is left as it is and counted as not found.

### Worldwide popularity

The default **Grading**, **Worldwide popularity**, uses Deezer's number as it is:

| Deezer popularity | Stars |
|-------------------|-------|
| Under 10,000 | 0 (removes stars when **Skip songs that have stars** is off) |
| 10,000–99,999 | 1 |
| 100,000–299,999 | 2 |
| 300,000–599,999 | 3 |
| 600,000–849,999 | 4 |
| 850,000 and up | 5 |

### Against the top song

**Against the artist's top song** and **Against the album's top song** compare each song with the most popular one, so a niche artist's hits get 5 stars too. The song's popularity is divided by the top song's:

| Share of the top song | Stars |
|-----------------------|-------|
| 80 % and up | 5 |
| 60 % and up | 4 |
| 40 % and up | 3 |
| 20 % and up | 2 |
| Anything above 0 | 1 |

The top song is the highest popularity among the artist's top 100 songs on Deezer, or among the album's tracks on Deezer. The artist is the Deezer artist with exactly that name (ignoring capitals and punctuation) and the most fans, and the album is the Deezer album with exactly that title. Downtify differs from dztnr here: dztnr takes Deezer's first search result, which is often a namesake. For "Drake" the first result is an unrelated artist with 201 fans, so every real Drake song would get 5 stars. When Deezer has nothing to compare with for an artist or album, **Worldwide popularity** is used for it.

## Options

| Option | Default | What it does |
|--------|---------|--------------|
| **Repeat** | **Off** | **Off**, **Every day**, **Every week** or **Every month**. See [Repeating](#repeating). |
| **Skip songs that have stars** | On | Stars you set by hand stay, and later runs skip every song that already has stars. Turn it off to rate everything again: that can also clear the stars of songs Deezer ranks under 10,000. |
| **Skip favourites** | Off | Leaves the songs you have marked as favourites alone. |
| **Grading** | **Worldwide popularity** | How popularity becomes stars, as above. |

The options are saved with the page's **Save** button. **Run now** and **Preview** use the options currently on the page, saved or not.

## Running it

- **Run now** rates your songs.
- **Preview** looks everything up and lists the stars each song would get, changing nothing in Navidrome. It takes as long as a real run.
- **Stop** ends a run that is going. Stars already given are kept.

While it runs the page shows **{done} of {total} songs**. After a run it shows how many songs were rated, skipped and not found on Deezer. A finished preview lists the songs with their Deezer popularity and the stars they would get, and the songs **Not found on Deezer**.

::: tip Try a Preview first
A Preview shows what a real run would do, so you can try the **Grading** and **Skip** options before any star changes.
:::

### How long it takes

Downtify waits 0.2 seconds after every Deezer request, and rests for 10 seconds after every 100, to stay well within Deezer's rate limit on long runs. A Deezer search takes about 0.3 to 0.5 seconds, so looking up one song takes roughly 0.5 to 0.7 seconds, and a first run over 10,000 songs takes about 1.5 to 2 hours. With **Skip songs that have stars** on, later runs skip every song that already has stars. They look up again the songs Deezer didn't find and the songs that were given 0 stars (Navidrome stores 0 as no rating), so they are much shorter. Comparing with the top song adds two Deezer requests for every artist or album that has a song to rate.

## Repeating

With **Repeat** set to anything but **Off**, Downtify checks once an hour (the first check comes 10 minutes after it starts). A run starts when all of these are true:

- Navidrome is on and its login is saved;
- [library-only mode](library-only.md) is off;
- no ratings run is going;
- the last real run started at least a day, a week or a month ago. A Preview doesn't count as a run.

If it has never run, the first check starts one. A run that failed is tried again 6 hours later.

## When something goes wrong

- If Deezer stops answering or says it is busy or over its limit, Downtify waits and tries again: after 5, 15, 30, 60 and 120 seconds, about four minutes in all. Only if Deezer still doesn't answer does the run stop, with "Deezer didn't answer for several minutes. Stars already given are kept, and the next run carries on where this one stopped." The next run, including the automatic retry 6 hours later, skips the albums that run finished, as long as the options are the same. Stopping a run keeps its place the same way; a run that finishes starts the next one from the beginning. **Stop** also works during the waits.
- If Deezer refuses one request for another reason, such as having no data for an artist or album, only that item is affected: a song counts as not found, and a missing reference falls back to the worldwide stars.
- If Navidrome answers with an error, the run stops and shows a short message, never the address or login details. A song or album removed while the run goes is skipped.
- If the Navidrome login isn't saved, **Run now** asks you to save it first.
- While [library-only mode](library-only.md) is on, **Run now** is refused and the schedule doesn't start, because the ratings contact Deezer.

For the HTTP endpoints, see the [API reference](../api-reference.md#get-apinavidromeratings).
