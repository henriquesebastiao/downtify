---
icon: lucide/image
---

# Artist photo, banner & bio

Downtify can show a real profile photo, a banner and a biography for each artist in your Library, instead of a generated initial and no text at all. Pick the photo/banner yourself, fetch the bio on demand or write your own, and fill in social links by hand — Downtify never chooses or downloads any of this on its own.

The edit affordance is always available on every artist's Library page, no setting to turn on first.

::: info About "Save artist photo" / "Save artist banner" in Settings
**Settings → Tags & lyrics → Save artist photo/banner** are reserved for a possible future feature — automatically fetching an artist's photo/banner during the download pipeline. They currently do nothing and don't affect this page.
:::

## The edit modal

**When an artist has a banner set, their round photo is hidden from the page header** — the banner alone is usually enough, and showing both felt cluttered. The photo isn't gone, though: it's still there to edit, just one tab away.

On an artist's Library page (`/library/artist?name=…`), hover the round photo (when shown) for an **Edit photo** button, or the banner area for an **Edit artist** button — both open the same modal: the artist's current photo at the top, and a menu below it with four tabs. It opens on **Profile** or **Banner** matching whichever button you clicked (defaults to **Banner** otherwise, since the photo itself may not always be visible to click).

- **Profile** / **Banner** — pick an image the same way for either:
  - **Search by name** — checks YouTube Music and Deezer for a matching artist photo. Type something else to search a different name, or a direct `http(s)://` image link to use it as a one-off candidate instead.
  - **Upload from your computer** — any image file.
  - **Remove photo / Remove banner** — only shown once the active tab's image is saved; asks for confirmation, then deletes the sidecar file.

  Every search result card is badged with where it came from. Picking one downloads and saves it immediately.
- **Bio** — a plain text box with whatever bio is currently saved (blank if none), for writing or editing it yourself. Saving overwrites the current text directly. A ⚡ **Fetch bio from Streams** button above the box can fill it in from Deezer/YouTube Music instead of typing it by hand — see [Fetching a bio automatically](#fetching-a-bio-automatically) below.
- **Social** — Twitter/X, Instagram, Facebook, YouTube and website links, editable directly. Saving always replaces all five fields with what the form has, even a field you leave blank.

## Icons on the banner

When an artist has a banner set, two rows of small icon links appear in its bottom-right corner: social links on top, streaming platforms below. Only the ones actually saved are shown — an artist with just a Twitter link gets one icon, not five greyed-out placeholders.

- **Social** — one icon per non-empty field from the Social tab above.
- **Streaming platforms** — built from the profile's `platforms_id`, each id turned into a link (e.g. a saved Deezer id becomes a link to that artist's Deezer page). The Deezer id is the only one Downtify resolves on its own, cached the first time a bio is fetched — Spotify and YouTube Music ids aren't looked up automatically yet, but are recognized and linked if you add them to the artist's profile JSON (see below) by hand.

## Spotify

Spotify has no public search-by-name API, so it never appears as a text search source. Instead, when the picker opens it checks a few of the artist's own already-downloaded tracks: if one was downloaded from Spotify, Downtify already knows that track's Spotify id and can resolve a real image directly from Spotify - no search needed. This candidate, when found, appears first and is labeled **Spotify**.

Photo and banner are genuinely different Spotify images, resolved differently: the square photo comes from the artist's public embed page, while the wide banner comes from Spotify's own artist-page data (not exposed by the embed at all). Not every artist has a banner set - when they don't, no Spotify candidate is offered for the banner picker, rather than falling back to the square photo.

An artist with no Spotify-sourced tracks yet simply doesn't get a Spotify candidate at all — search YouTube Music/Deezer, paste a link, or upload instead.

## Fetching a bio automatically

Below the header, the artist page shows a short biography, read-only — empty until one is saved. To fill it in, open the edit modal's **Bio** tab and click the ⚡ **Fetch bio from Streams** button above the text box. It looks the artist up on Deezer by exact name match and fetches their bio, social links and "fans also like" related-artist names (related artists are saved to the artist's profile file but not shown anywhere yet, reserved for a future addition) - all in your current interface language, and fills both the Bio and Social tabs with the result. If Deezer has no exact match, or matches but has no bio text, YouTube Music's own artist "About" description is tried as a bio-only fallback (no social links or related artists there). Only if neither source has anything do you see an error instead of a guessed/wrong bio.

YouTube Music's fallback bio is usually a Wikipedia excerpt in your language - it only supports as many languages as `ytmusicapi` ships, so a language it doesn't have (like Bulgarian, Greek or Hungarian) falls back to English there.

This never happens automatically - it only runs when you click the button, and saves right away. Only the first time does it need to search by name: the resolved Deezer artist id is cached in the artist's profile file afterwards, so fetching again just re-reads the same artist directly.

To clear a saved bio, open the Bio tab, empty the text box and Save - social links, related artists and the cached Deezer id are left untouched.

## Where the files go

```
<downloads>/Metadata/ArtistImage/<Artist>.jpg
<downloads>/Metadata/ArtistBannerImage/<Artist>.banner.jpg
<downloads>/Metadata/ArtistData/<Artist>.json
```

One file per artist, named after them (sanitized the same way track filenames are) — no database record, so the file's presence on disk is what the artist page checks. Saving a new photo/banner overwrites the previous one, and `ArtistData/<Artist>.json` holds the bio/social/related-artist/platform-id data described above, plus which source (Spotify, YouTube Music, Deezer, a pasted link, or an upload) the current photo/banner came from. These are plain files under your downloads folder, so services like Navidrome can read them directly if you point them at the same location.

`platforms_id` recognizes the keys `spotify`, `youtubemusic` and `deezer` — editing the JSON file directly to add a `spotify`/`youtubemusic` id (there's no form for these yet) makes its icon appear in the banner's platform row right away, same as a Deezer id fetched automatically.

## Out of scope

Choosing a photo/banner here never touches the download pipeline — it has no effect on what gets embedded in your audio files' own tags, and downloading a track never fetches an artist image automatically.
