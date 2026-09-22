---
icon: lucide/image
---

# Artist photo & banner

Downtify can show a real profile photo and a banner for each artist in your Library, instead of a generated initial. Pick them yourself on the artist page — Downtify never chooses or downloads one on its own.

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

Spotify has no public search-by-name API, so it never appears as a text search source. Instead, when the picker opens it checks a few of the artist's own already-downloaded tracks: if one was downloaded from Spotify, Downtify already knows that track's Spotify id and can resolve its artist's photo directly from Spotify's public embed page — no search needed. This candidate, when found, appears first and is labeled **Spotify**.

An artist with no Spotify-sourced tracks yet simply doesn't get a Spotify candidate — search YouTube Music/Deezer, paste a link, or upload instead.

## Where the files go

```
<downloads>/Metadata/ArtistImage/<Artist>.jpg
<downloads>/Metadata/ArtistBannerImage/<Artist>.banner.jpg
```

One file per artist, named after them (sanitized the same way track filenames are) — no database record, so the file's presence on disk is what the artist page checks. Saving a new photo/banner overwrites the previous one. These are plain files under your downloads folder, so services like Navidrome can read them directly if you point them at the same location.

## Out of scope

Choosing a photo/banner here never touches the download pipeline — it has no effect on what gets embedded in your audio files' own tags, and downloading a track never fetches an artist image automatically.
