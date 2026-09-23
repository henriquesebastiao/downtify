---
icon: lucide/image
---

# Artist photo, banner & bio

Downtify can show a real profile photo, a banner and a biography for each artist in your Library, instead of a generated initial and no text at all. Pick the photo/banner yourself, and fetch the bio on demand — Downtify never chooses or downloads any of this on its own.

The edit affordance is always available on every artist's Library page, no setting to turn on first.

::: info About "Save artist photo" / "Save artist banner" in Settings
**Settings → Tags & lyrics → Save artist photo/banner** are reserved for a possible future feature — automatically fetching an artist's photo/banner during the download pipeline. They currently do nothing and don't affect this page.
:::

## Editing a photo or banner

On an artist's Library page (`/library/artist?name=…`), hover the round photo for an **Edit photo** button, or the banner area for **Edit banner**. Both open the same picker and search for the artist's name right away, even though the field itself starts empty:

- **Search by name** — checks YouTube Music and Deezer for a matching artist photo. Type something else to search a different name, or a direct `http(s)://` image link to use it as a one-off candidate instead.
- **Upload from your computer** — any image file.
- **Remove photo / Remove banner** — only shown once one is saved; asks for confirmation, then deletes the sidecar file.

Every search result card is badged with where it came from. Picking one downloads and saves it immediately.

## Spotify

Spotify has no public search-by-name API, so it never appears as a text search source. Instead, when the picker opens it checks a few of the artist's own already-downloaded tracks: if one was downloaded from Spotify, Downtify already knows that track's Spotify id and can resolve a real image directly from Spotify - no search needed. This candidate, when found, appears first and is labeled **Spotify**.

Photo and banner are genuinely different Spotify images, resolved differently: the square photo comes from the artist's public embed page, while the wide banner comes from Spotify's own artist-page data (not exposed by the embed at all). Not every artist has a banner set - when they don't, no Spotify candidate is offered for the banner picker, rather than falling back to the square photo.

An artist with no Spotify-sourced tracks yet simply doesn't get a Spotify candidate at all — search YouTube Music/Deezer, paste a link, or upload instead.

## Bio

Below the header, the artist page shows a short biography — empty at first, with a ⚡ button next to the "Bio" heading. Clicking it looks the artist up on Deezer by exact name match and fetches their bio, social links and "fans also like" related-artist names (the last two are saved to the artist's profile file but not shown on the page yet, reserved for a future addition) - all in your current interface language. If Deezer has no exact match, or matches but has no bio text, YouTube Music's own artist "About" description is tried as a bio-only fallback (no social links or related artists there). Only if neither source has anything do you see an error instead of a guessed/wrong bio.

YouTube Music's fallback bio is usually a Wikipedia excerpt in your language - it only supports as many languages as `ytmusicapi` ships, so a language it doesn't have (like Bulgarian, Greek or Hungarian) falls back to English there.

This never happens automatically - it only runs when you click the button, and only the first time does it need to search by name: the resolved Deezer artist id is cached in the artist's profile file afterwards, so fetching again just re-reads the same artist directly.

Once a bio is saved, the button switches to a trash icon - click it to clear just the saved bio text (with a confirmation first). Social links, related artists and the cached Deezer id are left untouched, so fetching again afterwards doesn't need to search by name.

## Where the files go

```
<downloads>/Metadata/ArtistImage/<Artist>.jpg
<downloads>/Metadata/ArtistBannerImage/<Artist>.banner.jpg
<downloads>/Metadata/ArtistData/<Artist>.json
```

One file per artist, named after them (sanitized the same way track filenames are) — no database record, so the file's presence on disk is what the artist page checks. Saving a new photo/banner overwrites the previous one, and `ArtistData/<Artist>.json` holds the bio/social/related-artist/platform-id data described above, plus which source (Spotify, YouTube Music, Deezer, a pasted link, or an upload) the current photo/banner came from. These are plain files under your downloads folder, so services like Navidrome can read them directly if you point them at the same location.

## Out of scope

Choosing a photo/banner here never touches the download pipeline — it has no effect on what gets embedded in your audio files' own tags, and downloading a track never fetches an artist image automatically.
