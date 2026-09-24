---
icon: lucide/image
---

# Artist photo, banner & bio

Downtify can show a real profile photo, a banner and a biography for each artist in your Library, instead of a generated initial and no text at all. The first time you open a new artist's page, this fills itself in automatically; after that, pick a different photo/banner yourself, re-fetch or write your own bio, and fill in social links by hand.

The edit affordance is always available on every artist's Library page, no setting to turn on first.

::: info About "Save artist photo" / "Save artist banner" in Settings
**Settings → Tags & lyrics → Save artist photo/banner** decide whether Downtify may save an artist's photo/banner on its own — today that only happens the first time you open an artist's page (see [The first time you open a new artist](#the-first-time-you-open-a-new-artist)). Both are off by default. They never limit the edit modal: you can always pick a photo or banner by hand, whatever these say.
:::

## The edit modal

**When an artist has a banner set, their round photo is hidden from the page header** — the banner alone is usually enough, and showing both felt cluttered. The photo isn't gone, though: it's still there to edit, just one tab away.

On an artist's Library page (`/library/artist?name=…`), hover the round photo (when shown) for an **Edit photo** button, or the banner area for an **Edit artist** button — both open the same modal: the artist's current photo at the top, and a menu below it with four tabs. It opens on **Profile** or **Banner** matching whichever button you clicked (defaults to **Banner** otherwise, since the photo itself may not always be visible to click).

- **Profile** / **Banner** — pick an image the same way for either:
  - **Search by name** — checks YouTube Music and Deezer for a matching artist photo. Type something else to search a different name, or a direct `http(s)://` image link to use it as a one-off candidate instead.
  - **Upload from your computer** — any image file.
  - **Remove photo / Remove banner** — only shown once the active tab's image is saved; asks for confirmation, then deletes the sidecar file.

  Every search result card is badged with where it came from. Picking one downloads and saves it immediately.
- **Bio** — a plain text box with whatever bio is currently saved (blank if none), for writing or editing it yourself. Saving overwrites the current text directly. A ⚡ **Fetch bio from Streams** button above the box can fill it in from Apple Music/Deezer instead of typing it by hand — see [Fetching a bio automatically](#fetching-a-bio-automatically) below.
- **Social** — Twitter/X, Instagram, Facebook, YouTube and website links, editable directly. Saving always replaces all five fields with what the form has, even a field you leave blank.

## The first time you open a new artist

Opening a Library artist page seeds their profile automatically, but only if nothing has been saved for them yet - every visit after the first is a fast no-op, so this never repeats or slows anything down once it's run.

- **Photo and banner** — from Spotify (see [Spotify](#spotify) below), falling back to an exact YouTube Music name match when Spotify has nothing. Only when you've turned on **Save artist photo** and/or **Save artist banner** in Settings (both are off by default, and each one is independent); the edit modal can always set either by hand.
- **Bio, origin, formation year, genre, group flag, banner colour, social links, related artists and platform ids** — exactly what the Bio tab's two fetch links would get when they aren't told which service to use, see [Fetching a bio automatically](#fetching-a-bio-automatically) below.

If nothing could be found anywhere for a given artist, this still only ever runs once - it doesn't retry on every later visit. Use the edit modal to pick a photo/banner by hand or try the fetch button again at any time afterwards.

## Icons on the banner

When an artist has a banner set, two rows of small icon links appear in its bottom-right corner: social links on top, streaming platforms below. Only the ones actually saved are shown — an artist with just a Twitter link gets one icon, not five greyed-out placeholders.

- **Social** — one icon per non-empty field from the Social tab above.
- **Streaming platforms** — built from the profile's `platforms_id`, each id turned into a link (e.g. a saved Deezer id becomes a link to that artist's Deezer page). Spotify, Apple Music, Deezer and YouTube Music ids are all resolved automatically the first time a bio is fetched, by exact name match on each platform (Spotify's comes from one of the artist's own Spotify tracks when there is one, which can't pick a namesake). You can also add or correct one by hand in the artist's profile JSON (see below).

## Spotify

Spotify never appears as a free-text search source, but both the picker and the automatic first-visit seeding (see above) still find the artist there. They first check a few of the artist's own already-downloaded tracks: if one was downloaded from Spotify, Downtify already knows that track's Spotify id and resolves the image directly - the most reliable route, since it can't land on a different artist with the same name. When no track came from Spotify (say they were downloaded from YouTube), the artist is looked up by exact name instead (case-insensitive - a near match is never used). In the picker, this candidate appears first, labeled **Spotify**.

The name lookup uses the search box of Spotify's own web player, so it depends on an internal identifier that Spotify can change; if that happens, Downtify falls back to YouTube Music for the photo/banner and leaves the Spotify id empty, rather than failing.

Photo and banner are genuinely different Spotify images, resolved differently: the square photo comes from the artist's public embed page, while the wide banner comes from Spotify's own artist-page data (not exposed by the embed at all). Not every artist has a banner set - when they don't, no Spotify candidate is offered for the banner picker, rather than falling back to the square photo.

An artist with no Spotify-sourced tracks yet simply doesn't get a Spotify candidate at all — search YouTube Music/Deezer, paste a link, or upload instead.

## Fetching a bio automatically

Below the header, the artist page shows a short biography, read-only — empty until one is saved. To fill it in, open the edit modal's **Bio** tab and click **Fetch from Apple Music** or **Fetch from Deezer** above the text box (see [Choosing the source](#choosing-the-source)). Without a choice - which is what the automatic first-visit seeding does - it looks the artist up on Apple Music by exact name match (using the same name search Apple's own Music app uses) and fetches their bio, origin, formation year, genre, group flag and banner accent colour - the text (bio and genre) in your current interface language - and fills the Bio tab with the result. The genre (Apple Music gives one per artist, e.g. "Hard rock") is shown as a small pill at the top of the artist page's Bio tab, next to the origin and formation year. If Apple Music has no exact match, or matches but has no bio text in your language, Deezer is tried next as a secondary bio source - it also brings social links and "fans also like" related-artist names (related artists are saved to the artist's profile file but not shown anywhere yet, reserved for a future addition), filling the Social tab too. Only if neither source has anything at all do you see an error instead of a guessed/wrong bio.

Apple Music's own editorial bios aren't written for every artist in every language - when a language is missing for a specific artist, Deezer's bio (if it has one) is used instead, while origin/formation year/group flag still come from Apple Music since those facts aren't translated text (the genre is only ever Apple Music's, so it stays empty when Apple has no match). A handful of languages (Bulgarian, at the time of writing) aren't offered by Apple Music at all and always fall back to its default-language bio.

A bio is stored in the artist's JSON as plain text - no HTML tags and no bullet characters: a blank line separates paragraphs, and each `•` bullet in an Apple Music bio (which Apple separates with a single line break) becomes a paragraph of its own. Deezer's HTML bios are flattened the same way (each paragraph becomes a blank-line-separated one, every other tag is dropped). The artist page shows each paragraph on its own and keeps single line breaks inside it, and the Bio tab's text box edits exactly that text.

Re-fetching like this only runs when you click the button - it won't overwrite anything on its own past the automatic first visit described above. Only the first time (whether that's the automatic seed or a manual click) does it need to search by name: the resolved Apple Music and Deezer artist ids are cached in the artist's profile file afterwards, so fetching again just re-reads the same artists directly.

To clear a saved bio, open the Bio tab, empty the text box and Save - origin, formation year, genre, group flag, social links, related artists and the cached platform ids are left untouched.

## Choosing the source

The Bio tab has two links above the text box, so you can pick which biography reads better:

- **Fetch from Apple Music** — saves Apple Music's editorial bio. If Apple Music has none for this artist in your language, you get an error instead of a substitute.
- **Fetch from Deezer** — saves Deezer's bio, even when Apple Music has one. If Deezer has none, you get an error.

Either way the saved bio is replaced by the chosen one (still editable in the text box before you save your own changes), and if the chosen service has no bio the current one is kept untouched. Everything else - origin, formation year, genre, social links, related artists, platform ids - is refreshed the same way whichever link you use. The automatic first-visit seeding doesn't ask you: it uses Apple Music's bio and falls back to Deezer's only when Apple Music has none.

## Where the files go

```
<downloads>/Metadata/ArtistImage/<Artist>.jpg
<downloads>/Metadata/ArtistBannerImage/<Artist>.banner.jpg
<downloads>/Metadata/ArtistData/<Artist>.json
```

One file per artist, named after them (sanitized the same way track filenames are) — no database record, so the file's presence on disk is what the artist page checks. Saving a new photo/banner overwrites the previous one, and `ArtistData/<Artist>.json` holds the bio/social/related-artist/platform-id data described above, plus which source (Spotify, YouTube Music, Deezer, a pasted link, or an upload) the current photo/banner came from. These are plain files under your downloads folder, so services like Navidrome can read them directly if you point them at the same location.

`platforms_id` recognizes the keys `spotify`, `youtubemusic`, `deezer` and `applemusic`, all resolved automatically - Spotify from one of the artist's own Spotify tracks or, failing that, by exact name; the others by exact name. Fetching the bio fills in a missing Spotify id too, so an artist opened before this existed gets its Spotify icon after one fetch. An id already saved is never replaced, and you can still edit the JSON file directly to set one by hand.

## Out of scope

Choosing a photo/banner here never touches the download pipeline — it has no effect on what gets embedded in your audio files' own tags, and downloading a track never fetches an artist image automatically.

The *Related* tab shows a photo for artists you don't own too, but it is display-only: the server relays Deezer's picture to your browser (which caches it for three hours) without saving it, and it never becomes an artist's photo or banner. Photos are only written to disk for artists you set one for yourself, or whose photo/banner was saved on first visit as described above (when the Settings allow it). See [`GET /api/artists/photo-proxy`](../api-reference.md#get-apiartistsphoto-proxy).
