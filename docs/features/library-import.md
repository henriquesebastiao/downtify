---
icon: lucide/import
---

# Library Import (CSV)

Already exported your library from another service? Import the CSV and queue every track for download in one go, instead of re-adding songs one at a time.

## Supported exporters

| Tool | Notes |
|------|-------|
| [Soundiiz](https://soundiiz.com/) | |
| [TuneMyMusic](https://www.tunemymusic.com/) | |
| [Exportify](https://github.com/watsonbox/exportify) | |

Downtify doesn't hard-code any one tool's exact column schema. Instead, it matches the CSV's header row case-insensitively against a set of known aliases (`Title` / `Track` / `Track Title` / `Track Name` / `Song` / …, and `Artist` / `Artists` / `Artist Name` / `Artist Name(s)` / …), so exports from any of the three — or a hand-made CSV using the same column names — work without renaming anything.

Only the title and artist columns are read. Other columns some exporters include (album, ISRC, a Spotify track URI, duration) are ignored; each row is resolved the same way a free-text search is, via YouTube Music.

## How to import

1. On the home page, click **Import a library CSV** below the search box.
2. Pick your exported `.csv` file.

The file is read entirely in your browser and sent to the server as plain text — it is never uploaded anywhere else. Downtify parses it, queues every recognized row, and you'll land on the Download Queue where progress streams in over WebSocket exactly like any other batch download.

The imported batch is named after the file (its name minus `.csv`) and, like any other playlist download, gets an [M3U file](m3u-export.md) if that setting is enabled.

## Limits and error handling

- Up to **2,000 rows** per file. Split larger exports into multiple files.
- Rows missing a title or artist are silently skipped.
- Multiple artists in one cell (separated by `,` or `;`) are split into a list.
- If the header doesn't contain a recognizable title/artist column, the whole import is rejected up front with an error naming the columns it did find — nothing is queued.

## Avoiding rate limits

Importing a large library queues a lot of YouTube Music searches and downloads in a short time, which is an easy way to get rate-limited. Before importing a big file, consider lowering **[Parallel downloads](download-settings.md#parallel-downloads)** and turning on **[Delay between downloads](download-settings.md#delay-between-downloads)** in Settings.

## API

See [`POST /api/download/csv`](../api-reference.md#post-apidownloadcsv) in the API reference for the underlying endpoint.
