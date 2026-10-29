---
layout: home
title: Downtify
titleTemplate: Λήψη μουσικής που φιλοξενείς μόνος σου
description: Λήψη μουσικής που φιλοξενείς μόνος σου. Επικόλλησε έναν σύνδεσμο Spotify και πάρε ένα άψογα επισημασμένο αρχείο ήχου — χωρίς κλειδιά API, χωρίς λογαριασμό, χωρίς κόπο.
icon: lucide/house
hero:
  eyebrow: Λήψη μουσικής που φιλοξενείς μόνος σου
  lead:
    - Το πρόγραμμα λήψης μουσικής που μπορείς να φιλοξενήσεις στο δικό σου μηχάνημα.
    - Ρίξε έναν σύνδεσμο Spotify και πάρε ένα αρχείο ήχου με tags. Χωρίς λογαριασμό, χωρίς κλειδί API, χωρίς Premium.
  actions:
    - text: Ξεκίνα
      link: /el/getting-started/installation/
      primary: true
    - text: Πηγαίος κώδικας στο GitHub
      link: https://github.com/henriquesebastiao/downtify
      icon: github
  shields:
    - alt: Έκδοση
      src: https://img.shields.io/github/v/release/henriquesebastiao/downtify?color=1AD05C&label=release
      link: https://github.com/henriquesebastiao/downtify/releases
    - alt: Λήψεις Docker
      src: https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fghcr-badge.elias.eu.org%2Fapi%2Fhenriquesebastiao%2Fdowntify%2Fdowntify&query=downloadCount&style=flat&label=docker%20pulls
      link: https://github.com/henriquesebastiao/downtify/pkgs/container/downtify
    - alt: Άδεια
      src: https://img.shields.io/github/license/henriquesebastiao/downtify?color=1AD05C
      link: https://github.com/henriquesebastiao/downtify/blob/main/LICENSE
pipeline:
  - title: Spotify embed
    text: μεταδεδομένα
  - title: YouTube Music
    text: ταίριασμα ήχου
  - title: yt-dlp · ffmpeg · mutagen
    text: λήψη και tags
highlights:
  - icon: eye
    title: Παρακολούθηση λιστών
    text: Παρακολουθεί μια λίστα και κατεβάζει αθόρυβα νέα κομμάτια καθώς προστίθενται.
    link: /el/features/playlist-monitor/
  - icon: sliders-horizontal
    title: Πέντε μορφές
    text: MP3, FLAC, M4A, OGG και OPUS — στο bitrate της επιλογής σου.
    link: /el/features/download-settings/
  - icon: mic-vocal
    title: Ενσωματωμένοι στίχοι
    text: Απλοί και συγχρονισμένοι με τον χρόνο στίχοι από το lrclib, ενσωματωμένοι στο αρχείο.
    link: /el/features/lyrics/
  - icon: headphones
    title: Web player
    text: Τυχαία σειρά, επανάληψη, ένταση και εξώφυλλο άλμπουμ — κατευθείαν από τον browser.
    link: /el/features/player/
  - icon: list-music
    title: Εξαγωγή M3U
    text: Τυπικά αρχεία EXTM3U που το Jellyfin, το Navidrome και το Plex αναγνωρίζουν αυτόματα.
    link: /el/features/m3u-export/
  - icon: folder
    title: Οργάνωση βιβλιοθήκης
    text: Όλα σε έναν φάκελο ή ένας φάκελος ανά καλλιτέχνη — ό,τι προτιμά ο διακομιστής πολυμέσων σου.
    link: /el/features/file-organization/
  - icon: import
    title: Εισαγωγή CSV
    text: Φέρε μια εξαγωγή από Soundiiz, TuneMyMusic ή Exportify και βάλε τα πάντα στην ουρά.
    link: /el/features/library-import/
quickStart:
  - text: Οδηγός εγκατάστασης
    link: /el/getting-started/installation/
    primary: true
  - text: Docker Compose
    link: /el/getting-started/docker-compose/
---

## Πώς λειτουργεί στην πραγματικότητα

Το επίσημο API του Spotify δεσμεύει τις λήψεις πίσω από συνδρομή Premium. Το Downtify παίρνει τη πλαϊνή πόρτα — διαβάζει τα μεταδεδομένα που το Spotify ήδη εκθέτει στις δημόσιες σελίδες ενσωμάτωσής του, ζητά από το YouTube Music τον πιο κοντινό ήχο, δίνει το αρχείο στα `yt-dlp` και `ffmpeg` και γράφει τα σωστά tags με το `mutagen`. Όλη η διαδικασία ζει σε ένα μόνο κοντέινερ Docker.

<HomePipeline :steps="$frontmatter.pipeline" />

## Τι μπορείς να επικολλήσεις

|                    |                                    |
| ------------------ | ---------------------------------- |
| Κομμάτι Spotify    | `open.spotify.com/track/…`         |
| Άλμπουμ Spotify    | `open.spotify.com/album/…`         |
| Λίστα Spotify      | `open.spotify.com/playlist/…`      |
| YouTube / YT Music | `youtube.com/watch?v=…`            |
| Αναζήτηση ελεύθερου κειμένου | `The Night Owls Do I Still Recall` |

## Βασικά σημεία

<HomeHighlights :items="$frontmatter.highlights" />

## Μία εντολή και τελείωσες

```bash
docker run -d -p 8000:8000 --name downtify \
  -v /path/to/music:/downloads \
  -v downtify_data:/data \
  ghcr.io/henriquesebastiao/downtify
```

Άνοιξε το [`localhost:8000`](http://localhost:8000), επικόλλησε έναν σύνδεσμο, πάτα λήψη. Τα αρχεία καταλήγουν στο `/path/to/music` με τα tags ήδη στη θέση τους.

<HomeActions :actions="$frontmatter.quickStart" />
