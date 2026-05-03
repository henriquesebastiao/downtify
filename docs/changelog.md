---
icon: lucide/history
---

# Changelog

## [2.6.0](https://github.com/henriquesebastiao/downtify/tree/2.6.0) — 2026-05-03

**Enhancements**

- Organize by artist: save music into per-artist subfolders ([#151](https://github.com/henriquesebastiao/downtify/pull/151))
- Option to disable lyrics downloads ([#148](https://github.com/henriquesebastiao/downtify/pull/148))
- Fix download history clearing ([#150](https://github.com/henriquesebastiao/downtify/pull/150))

**Bug fixes**

- Download history persisting after clearing ([#146](https://github.com/henriquesebastiao/downtify/issues/146))
- Settings not persisting across restarts ([#142](https://github.com/henriquesebastiao/downtify/issues/142))

---

## [2.5.0](https://github.com/henriquesebastiao/downtify/tree/2.5.0) — 2026-05-02

**Enhancements**

- Support for playlists with over 100 songs ([#147](https://github.com/henriquesebastiao/downtify/pull/147))

---

## [2.4.3](https://github.com/henriquesebastiao/downtify/tree/2.4.3) — 2026-04-30

**Enhancements**

- Persist settings to disk so they survive container restarts ([#143](https://github.com/henriquesebastiao/downtify/pull/143))

---

## [2.4.2](https://github.com/henriquesebastiao/downtify/tree/2.4.2) — 2026-04-30

**Enhancements**

- Structured logging with loguru ([#141](https://github.com/henriquesebastiao/downtify/pull/141))

---

## [2.4.1](https://github.com/henriquesebastiao/downtify/tree/2.4.1) — 2026-04-29

**Enhancements**

- Move SQLite database from `/downloads` to `/data` — a separate named volume ([#140](https://github.com/henriquesebastiao/downtify/pull/140))

---

## [2.4.0](https://github.com/henriquesebastiao/downtify/tree/2.4.0) — 2026-04-29

[Full changelog](https://github.com/henriquesebastiao/downtify/compare/2.3.0...2.4.0)

---

## [2.3.0](https://github.com/henriquesebastiao/downtify/tree/2.3.0) — 2026-04-28

**Enhancements**

- Settings toggle to enable/disable M3U generation; Playlist Monitor integration ([#127](https://github.com/henriquesebastiao/downtify/pull/127))

---

## [2.2.0](https://github.com/henriquesebastiao/downtify/tree/2.2.0) — 2026-04-28

**Enhancements**

- Automatic `EXTM3U` playlist file generation for Spotify playlists ([#126](https://github.com/henriquesebastiao/downtify/pull/126))

---

## [2.1.1](https://github.com/henriquesebastiao/downtify/tree/2.1.1) — 2026-04-28

**Bug fixes**

- Album details (year, album cover) missing from embedded metadata ([#125](https://github.com/henriquesebastiao/downtify/issues/125))

---

## [2.1.0](https://github.com/henriquesebastiao/downtify/tree/2.1.0) — 2026-04-28

**Enhancements**

- Rewrite: replace Spotify Web API (spotdl/spotipy) with public embed scraping — no credentials or Premium required ([#124](https://github.com/henriquesebastiao/downtify/pull/124))
- Configurable output bitrate
- Playlist Monitor (watch playlists and auto-download new tracks)
- Lyrics via lrclib

**Bug fixes**

- Spotify direct links returning wrong results ([#104](https://github.com/henriquesebastiao/downtify/issues/104))

---

## [2.0.0](https://github.com/henriquesebastiao/downtify/tree/2.0.0) — 2026-04-23

[Full changelog](https://github.com/henriquesebastiao/downtify/compare/1.1.4...2.0.0)

---

## [1.1.4](https://github.com/henriquesebastiao/downtify/tree/1.1.4) — 2026-02-19

**Bug fixes**

- Search engine not returning results ([#102](https://github.com/henriquesebastiao/downtify/issues/102))
- HTTP 500 errors with the Spotify API ([#97](https://github.com/henriquesebastiao/downtify/issues/97))

---

## [1.1.3](https://github.com/henriquesebastiao/downtify/tree/1.1.3) — 2026-02-18

**Bug fixes**

- Updated spotDL to reflect changes in the Spotify API ([#100](https://github.com/henriquesebastiao/downtify/pull/100))

---

## [1.1.1](https://github.com/henriquesebastiao/downtify/tree/1.1.1) — 2025-10-28

**Enhancements**

- yt-dlp updated to 2025.10.22 ([#53](https://github.com/henriquesebastiao/downtify/pull/53))

---

[Full changelog on GitHub →](https://github.com/henriquesebastiao/downtify/blob/main/CHANGELOG)
