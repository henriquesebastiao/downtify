---
icon: lucide/heart-handshake
---

# Support the Artist

Downtify downloads music from YouTube. When you find something you love, **Support the artist** shows where to buy it, so the money reaches the people who made it.

## Where to find it

| Where | What it opens |
|-------|---------------|
| Search results and charts | The **tag** button on a song row, next to the link to YouTube Music (it shows on hover on a large screen) |
| A song's **⋯** menu in the Library, and the now playing screen | That song |
| An album's **⋯** menu | The album |
| An artist's **⋯** menu | Everything by the artist |

## The links

For a song, an album or an artist the dialog lists:

| Store | Link |
|-------|------|
| **iTunes Store** | The item itself, with its price, when the store clearly has it — the same artist and title. Otherwise a search on Apple Music. |
| **Bandcamp** | A search. Bandcamp passes most of each sale on to the artist, and many artists sell there directly. |
| **Qobuz** | A search. Qobuz sells lossless (and hi-res) downloads. |
| **Official website** | The artist's own site, when their [artist profile](artist-images.md) has one. |

The iTunes Store link opens the store of your country, taken from the browser's language (`pt-BR` opens the Brazilian store, with prices in reais; a language without a region opens the US store). A song that is only sold as part of its album shows no price of its own.

Bandcamp and Qobuz have no public way to look something up, so their links are searches for the artist and the title (or the album, or the artist alone): check the result is the right release before you buy.

::: info Plain links
Downtify doesn't sell anything and doesn't earn from these links. To fill in the dialog it makes one request to Apple's public iTunes Search API, with the artist and title only, and remembers the answer while the server runs. Nothing else leaves your server until you open a link.
:::

## In the apps

The apps get the same links from [`GET /api/buy`](../api-reference.md#get-apibuy).
