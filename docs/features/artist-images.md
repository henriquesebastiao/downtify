---
icon: lucide/image
---

# Artist photo, banner & bio

Downtify can show a real profile photo, a banner and a biography for each artist in your Library, instead of a generated initial and no text at all. This fills itself in automatically the first time you open a new artist's page, or as soon as one of their tracks finishes downloading; after that, pick a different photo/banner yourself, re-fetch or write your own bio, and fill in social links by hand.

The edit affordance is always available on every artist's Library page, no setting to turn on first.

::: info About "Save artist photo" / "Save artist banner" in Settings
**Settings → Downloads & files → Save artist photo / Save artist banner** decide whether Downtify may save an artist's photo/banner on its own — that happens the first time you open an artist's page and when one of their tracks finishes downloading (see [The first time you open a new artist](#the-first-time-you-open-a-new-artist) and [When a download finishes](#when-a-download-finishes)). Both are off by default. They never limit the edit modal: you can always pick a photo or banner by hand, whatever these say.
:::

## The edit modal

**When an artist has a banner set, their round photo is hidden from the page header** — the banner alone is usually enough, and showing both felt cluttered. The photo isn't gone, though: it's still there to edit, just one tab away.

On an artist's Library page (`/library/artist?name=…`), hover the round photo (when shown) for an **Edit photo** button, or the banner area for an **Edit artist** button — both open the same modal: the artist's current photo at the top, and a menu below it with four tabs. It opens on **Profile** or **Banner** matching whichever button you clicked (defaults to **Banner** otherwise, since the photo itself may not always be visible to click).

- **Profile** / **Banner** — pick an image the same way for either:
  - **Search by name** — checks YouTube Music and Deezer for a matching artist photo (Deezer artists that only have its generic placeholder picture are left out). Type something else to search a different name, or a direct `http(s)://` image link to use it as a one-off candidate instead.
  - **Upload from your computer** — any image file.
  - **Remove photo / Remove banner** — only shown once the active tab's image is saved; asks for confirmation, then deletes the sidecar file.

  Every search result card is badged with where it came from. Picking one downloads and saves it immediately. The card whose image is the one currently saved is marked with a green border and a check, on the Profile and Banner tabs separately - so you can see at a glance which of the candidates you're using. A photo you uploaded, or one saved before Downtify started remembering this, has no card to mark.
- **Bio** — a plain text box with whatever bio is currently saved (blank if none), for writing or editing it yourself. Saving overwrites the current text directly. A ⚡ **Fetch bio from Streams** button above the box can fill it in from Apple Music/Deezer instead of typing it by hand — see [Fetching a bio automatically](#fetching-a-bio-automatically) below.
- **Social** — Twitter/X, Instagram, Facebook, YouTube and website links, editable directly. Saving always replaces all five fields with what the form has, even a field you leave blank. Fetching a bio never touches a link you've filled in: Deezer's social links only fill fields that are still empty (Deezer doesn't know every network, so complete the rest by hand and it stays that way).

## The first time you open a new artist

Opening a Library artist page seeds their profile automatically, but only if nothing has been saved for them yet - every visit after the first is a fast no-op, so this never repeats or slows anything down once it's run.

- **Photo and banner** — from Spotify (see [Spotify](#spotify) below), falling back to an exact YouTube Music name match when Spotify has nothing. Only when you've turned on **Save artist photo** and/or **Save artist banner** in Settings (both are off by default, and each one is independent); the edit modal can always set either by hand.
- **Bio, origin, formation year, genre, group flag, banner colour, social links, related artists and platform ids** — fetched from Apple Music and Deezer the way [Fetching a bio automatically](#fetching-a-bio-automatically) describes below.

If Apple Music or Deezer **fails** while this runs (unreachable, or over its request limit), nothing is saved at all - not the bio, not a photo - and the page simply shows no profile yet, so the next visit tries again. Only a service answering that it doesn't know the artist counts as an answer: the profile is then made with what the other one had. Spotify's part (the related artists) never stops a profile from being made.

## When a download finishes

The same seeding runs in the background when one of an artist's tracks finishes downloading - whether you started it in the app or a [Playlist Monitor](playlist-monitor.md) sweep did - if that artist has no profile yet, so artists you download are ready before you ever open their page. It never slows the download down: the artist is queued and filled in a few seconds later, two artists at a time, and one that is already queued isn't queued again however many of their tracks come down (a playlist of fifty songs by one artist seeds them once). Songs that were already in your library aren't downloaded again and start nothing.

- **Which artist** — the one the file is filed under: the album artist, else the first credited artist. `Various Artists` is skipped.
- **Language** — the bio and genre come in the language of the web UI, which the page keeps on the server (see [Internationalization](internationalization.md)); until a page has told it, English.
- **Photo and banner** — only as **Save artist photo** / **Save artist banner** allow, read at that moment, so changing a setting applies to the very next track.
- **Top songs** — not made this way; they wait for the artist's page (see [Top songs](top-songs.md)).

If nothing could be found anywhere for a given artist, this still only ever runs once - it doesn't retry on every later visit. Use the edit modal to pick a photo/banner by hand or try the fetch button again at any time afterwards.

## The Links tab

An artist with at least one saved link gets a **Links** tab, just before **Bio** (which stays the last tab), with a counter of how many. It lists them as cards, on any screen and whether or not the artist has a banner: **Streaming platforms** first, then **Social networks**. Each card shows the site's name and address and opens it in a new tab. Only what is actually saved is listed, and an artist with no links has no Links tab (`?tab=links` for them opens the first tab instead).

- **Streaming platforms** — Spotify, YouTube Music, Deezer and Apple Music, built from the profile's `platforms_id`: each saved id turned into a link (e.g. a saved Deezer id becomes a link to that artist's Deezer page). The ids are all resolved automatically the first time a bio is fetched, by exact name match on each platform (Spotify's comes from one of the artist's own Spotify tracks when there is one, which can't pick a namesake). You can also add or correct one by hand in the artist's profile JSON (see below).
- **Social networks** — Twitter/X, Instagram, Facebook, YouTube and website: one card per non-empty field from the Social tab above. Only web addresses are opened: a link typed without `https://` gets it, and anything with another kind of address (a `javascript:` one, say) is ignored.

## Spotify

Spotify never appears as a free-text search source, but both the picker and the automatic first-visit seeding (see above) still find the artist there. They first check a few of the artist's own already-downloaded tracks: if one was downloaded from Spotify, Downtify already knows that track's Spotify id and resolves the image directly - the most reliable route, since it can't land on a different artist with the same name. When no track came from Spotify (say they were downloaded from YouTube), the artist is looked up by exact name instead (case-insensitive - a near match is never used). In the picker, this candidate appears first, labeled **Spotify**.

The name lookup uses the search box of Spotify's own web player, so it depends on an internal identifier that Spotify can change; if that happens, Downtify falls back to YouTube Music for the photo/banner and leaves the Spotify id empty, rather than failing.

Photo and banner are genuinely different Spotify images, resolved differently: the square photo comes from the artist's public embed page, while the wide banner comes from Spotify's own artist-page data (not exposed by the embed at all). Not every artist has a banner set - when they don't, no Spotify candidate is offered for the banner picker, rather than falling back to the square photo.

An artist with no Spotify-sourced tracks yet simply doesn't get a Spotify candidate at all — search YouTube Music/Deezer, paste a link, or upload instead.

## Fetching a bio automatically

Below the header, the artist page shows a short biography, read-only — empty until one is saved. To fill it in, open the edit modal's **Bio** tab and click **Fetch from Apple Music** or **Fetch from Deezer** above the text box (see [Choosing the source](#choosing-the-source)), which loads that service's bio into the box for you to review and save. The automatic first-visit seeding, which saves on its own, looks the artist up on Apple Music by exact name match (using the same name search Apple's own Music app uses) and fetches their bio, origin, formation year, genre, group flag and banner accent colour - the text (bio and genre) in your current interface language - and saves the result. The genre (Apple Music gives one per artist, e.g. "Hard rock") is shown as a small pill at the top of the artist page's Bio tab, next to the origin and formation year. Apple Music says whether the artist is a group: for a group that date reads "Formed in 1995", and for a solo artist - whose date is usually a birth date - "Born 27 September 1984" (translated in every interface language; an artist whose group flag isn't known stays "Formed in"). The date itself is shown the way Apple Music gave it, so it keeps the language of the fetch. If Apple Music has no exact match, or matches but has no bio text in your language, Deezer is tried next as a secondary bio source - it also brings social links and "fans also like" related-artist names (related artists are saved to the artist's profile file but not shown anywhere yet, reserved for a future addition), filling the Social tab too. Only if neither source has anything at all do you see an error instead of a guessed/wrong bio.

Apple Music's own editorial bios aren't written for every artist in every language - when a language is missing for a specific artist, Deezer's bio (if it has one) is used instead, while origin/formation year/group flag still come from Apple Music since those facts aren't translated text (the genre is only ever Apple Music's, so it stays empty when Apple has no match). A handful of languages (Bulgarian, at the time of writing) aren't offered by Apple Music at all and always fall back to its default-language bio.

A bio is stored in the artist's JSON as plain text - no HTML tags and no bullet characters: a blank line separates paragraphs, and each `•` bullet in an Apple Music bio (which Apple separates with a single line break) becomes a paragraph of its own. Deezer's HTML bios are flattened the same way (each paragraph becomes a blank-line-separated one, every other tag is dropped). The artist page shows each paragraph on its own and keeps single line breaks inside it, and the Bio tab's text box edits exactly that text.

Re-fetching like this only runs when you click the button - it won't overwrite anything on its own past the automatic first visit described above. Only the first time (whether that's the automatic seed or a manual click) does it need to search by name: the resolved Apple Music and Deezer artist ids are cached in the artist's profile file afterwards, so fetching again just re-reads the same artists directly.

To clear a saved bio, open the Bio tab, empty the text box and Save - origin, formation year, genre, group flag, social links, related artists and the cached platform ids are left untouched.

## Choosing the source

The Bio tab has two links above the text box, so you can pick which biography reads better:

- **Fetch from Apple Music** — loads Apple Music's editorial bio into the text box. If Apple Music has none for this artist in your language, you get an error instead of a substitute.
- **Fetch from Deezer** — loads Deezer's bio, even when Apple Music has one. If Deezer has none, you get an error.

Clicking a link **only fills the text box** - nothing is saved until you press **Save**, so you can read it, edit it, or try the other service first, and closing the modal without saving leaves the current bio as it was. Only the bio text is loaded: the origin, formation year, genre, social links, related artists and platform ids aren't touched by these links (the automatic first-visit seeding is what fills those in). The seeding doesn't ask you which service: it uses Apple Music's bio and falls back to Deezer's only when Apple Music has none.

## Where the files go

```
<downloads>/Metadata/ArtistImage/<Artist>.jpg
<downloads>/Metadata/ArtistBannerImage/<Artist>.banner.jpg
<downloads>/Metadata/ArtistData/<Artist>.json
<downloads>/Metadata/ArtistTopSongs/<Artist>.topsongs.json
```

One file per artist, named after them (sanitized the same way track filenames are) — no database record, so the file's presence on disk is what the artist page checks. Saving a new photo/banner overwrites the previous one (the web UI keeps its own copy of the old one from showing: each saved image's URL carries the file's modified time, so a replaced photo is fetched again while an untouched one stays cached), and `ArtistData/<Artist>.json` holds the bio/social/related-artist/platform-id data described above, plus, in `current_cover` and `current_cover_banner`, which image the current photo/banner is: the path of the URL it was downloaded from (host and query left out, so the same image from another CDN address still matches), or `upload` for one you uploaded. It's what the edit modal compares each candidate against to mark the one in use. These are plain files under your downloads folder, so services like Navidrome can read them directly if you point them at the same location.

Artist names are matched the way the disk keeps them: Downtify files `AC/DC` as `ACDC`, because a file name can't hold a `/`, and a track with no artist tag takes its artist from that file name - so the same artist can show up as `AC/DC` or `ACDC`. Every lookup by name (Spotify, Deezer, YouTube Music and Apple Music) ignores case and the characters a file name can't hold, so both spellings find the same artist, and both share the same files above. A name that differs in anything else - `AC/DC Tribute`, say - is still a different artist and never matches.

`platforms_id` recognizes the keys `spotify`, `youtubemusic`, `deezer` and `applemusic`, all resolved automatically - Spotify from one of the artist's own Spotify tracks or, failing that, by exact name; the others by exact name. Fetching the bio fills in a missing Spotify id too, so an artist opened before this existed gets its Spotify icon after one fetch. An id already saved is never replaced, and you can still edit the JSON file directly to set one by hand.

## Out of scope

Choosing a photo/banner here never touches the download pipeline — it has no effect on what gets embedded in your audio files' own tags, and downloading a track never fetches an artist image automatically.

The *Related* tab shows a photo for artists you don't own too, and so do the Library's *Artists* grid, an artist's own page and the Monitor's *Artists* tab (the artist you are watching, in the list and in its edit dialog), for every artist you haven't picked a photo for (the Library and an artist's own page use one of the artist's track covers when Deezer has none; the Monitor has no track, so it shows the initials) - only a real one: an artist Deezer has no photo for (it serves a generic placeholder) gets the usual initial instead - but it is display-only: the server relays Deezer's picture to your browser (which caches it for three hours) without saving it, and it never becomes an artist's photo or banner. Only real answers are kept: if Deezer can't be reached or you're over its request limit at that moment, the tile shows the initial (or the track's cover) for now and nothing is remembered, so the photo appears the next time you open the page. Photos are only written to disk for artists you set one for yourself, or whose photo/banner was saved on first visit as described above (when the Settings allow it). See [`GET /api/artists/photo-proxy`](../api-reference.md#get-apiartistsphoto-proxy).
