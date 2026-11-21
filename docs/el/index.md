---
layout: home
title: Downtify
titleTemplate: "Πρόγραμμα λήψης Spotify και player που φιλοξενείς εσύ"
description: "Λήψη από Spotify στον δικό σου διακομιστή, με player. Επικόλλησε σύνδεσμο Spotify, YouTube Music, Deezer ή SoundCloud, πάρε MP3 ή FLAC με ετικέτες. Χωρίς κλειδιά API."
icon: lucide/house
hero:
  eyebrow: Λήψη μουσικής που φιλοξενείς μόνος σου
  headline:
    - Επικόλλησε έναν σύνδεσμο.
    - Πάρε τη μουσική.
  lead: Ένα πρόγραμμα λήψης μουσικής που φιλοξενείς μόνος σου, με ενσωματωμένο player. Επικόλλησε έναν σύνδεσμο από Spotify, YouTube Music, Deezer ή SoundCloud και πάρε μια τέλεια επισημασμένη βιβλιοθήκη, έτοιμη να παίξει στον browser, στο κινητό ή στον διακομιστή πολυμέσων σου.
  note: Χωρίς λογαριασμό Spotify, χωρίς κλειδιά API, χωρίς Premium.
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
      src: https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fghcr-badge.elias.eu.org%2Fapi%2Fhenriquesebastiao%2Fdowntify%2Fdowntify&query=downloadCount&label=docker%20pulls&color=1AD05C
      link: https://github.com/henriquesebastiao/downtify/pkgs/container/downtify
    - alt: Αστέρια στο GitHub
      src: https://img.shields.io/github/stars/henriquesebastiao/downtify?style=flat&label=stars&color=1AD05C
      link: https://star-history.com/#henriquesebastiao/downtify&Date
    - alt: Άδεια
      src: https://img.shields.io/github/license/henriquesebastiao/downtify?color=1AD05C
      link: https://github.com/henriquesebastiao/downtify/blob/main/LICENSE
video:
  src: /assets/media/downtify-demo.mp4
  poster: /assets/media/downtify-demo-poster.webp
  label: 'Το Downtify σε 44 δευτερόλεπτα: επικόλλησε τον σύνδεσμο μιας λίστας, κατέβασέ τη με ένα κλικ, κράτα τη συγχρονισμένη και άκουσέ τη με συγχρονισμένους στίχους, στον υπολογιστή και στο κινητό.'
why:
  - icon: link
    title: Ένας σύνδεσμος αρκεί
    text: Επικόλλησε ένα τραγούδι, ένα άλμπουμ, μια ολόκληρη λίστα ή έναν καλλιτέχνη από Spotify, YouTube Music, Deezer ή SoundCloud, ή απλώς γράψε τι θέλεις να ακούσεις. Το Downtify βρίσκει τον ήχο και τα φέρνει όλα σπίτι.
    link: /el/how-it-works/
  - icon: tag
    title: Αρχεία που αξίζει να κρατήσεις
    text: Κάθε αρχείο έχει το εξώφυλλο, όλους τους καλλιτέχνες που αναφέρονται, το άλμπουμ, τη χρονιά, τον αριθμό κομματιού και τους στίχους, συγχρονισμένους όταν υπάρχουν. MP3, FLAC, M4A, OGG ή Opus, ή ο ήχος της πηγής ακριβώς όπως ήρθε.
    link: /el/features/download-settings/
  - icon: music
    title: Η δική σου υπηρεσία streaming
    text: Ένα πλήρες player στον browser, με συγχρονισμένους στίχους, καραόκε, ουρά, αγαπημένα τραγούδια, λίστες και podcasts. Οι εφαρμογές για Android και iOS παίρνουν τη βιβλιοθήκη σου μαζί, ακόμη και χωρίς σύνδεση.
    link: /el/features/player/
  - icon: radar
    title: Ρύθμισέ το και ξέχασέ το
    text: Παρακολούθησε λίστες και καλλιτέχνες. Τα νέα τραγούδια και οι νέες κυκλοφορίες κατεβαίνουν μόνα τους, με τη συχνότητα που επιλέγεις.
    link: /el/features/playlist-monitor/
  - icon: server
    title: Φτιαγμένο για τον οικιακό σου διακομιστή
    text: Μία εικόνα Docker για amd64 και arm64, SQLite ή PostgreSQL, λογαριασμοί για όλο το σπίτι με προαιρετική ενιαία σύνδεση και λίστες που αναγνωρίζουν τα Jellyfin, Navidrome και Plex.
    link: /el/getting-started/
  - icon: shield
    title: Χωρίς δεσμεύσεις
    text: Χωρίς κλειδί API του Spotify, χωρίς λογαριασμό προγραμματιστή, χωρίς Premium. Η εφαρμογή δεν έχει διαφημίσεις, ούτε στατιστικά χρήσης, ούτε τίποτα επί πληρωμή. Είναι ελεύθερη και ανοιχτού κώδικα.
    link: /el/contributing/
showcase:
  - shot: now-playing
    label: Παίζει τώρα
    caption: Οι στίχοι ακολουθούν το τραγούδι, γραμμή γραμμή, δίπλα στο εξώφυλλο και σε ό,τι ακολουθεί.
    alt: Η προβολή Παίζει τώρα σε πλήρη οθόνη, με το εξώφυλλο του άλμπουμ, συγχρονισμένους στίχους με την τρέχουσα γραμμή τονισμένη και την ουρά.
  - shot: karaoke
    label: Καραόκε
    caption: Μεγάλοι στίχοι που γεμίζουν καθώς τραγουδιέται κάθε γραμμή, έτοιμοι να ανοίξουν σε δεύτερη οθόνη.
    alt: Η προβολή καραόκε, με μεγάλους στίχους που γεμίζουν πάνω από ένα κινούμενο φόντο στα χρώματα του εξωφύλλου.
  - shot: home
    label: Αρχική
    caption: Επικόλλησε έναν σύνδεσμο ή ψάξε κάτι καινούργιο, και συνέχισε από εκεί που σταμάτησες.
    alt: Η αρχική σελίδα, με ένα πλαίσιο για επικόλληση συνδέσμου ή αναζήτηση, στατιστικά της βιβλιοθήκης, το άλμπουμ που παίζει και τα άλμπουμ που προστέθηκαν πρόσφατα.
  - shot: library
    label: Βιβλιοθήκη
    caption: Άλμπουμ, καλλιτέχνες, λίστες και κομμάτια, ταξινομημένα και φιλτραρισμένα όπως θέλεις.
    alt: Η σελίδα Βιβλιοθήκη, με ένα πλέγμα από εξώφυλλα άλμπουμ και καρτέλες για άλμπουμ, καλλιτέχνες, λίστες και κομμάτια.
  - shot: playlist
    label: Λίστες
    caption: Δικές σου λίστες, με δικό τους εξώφυλλο, για να τις παίζεις, να τις μοιράζεσαι ή να τις κατεβάζεις ως ZIP.
    alt: Μια σελίδα λίστας, με το εξώφυλλο, τα κουμπιά της και τα τραγούδια με άλμπουμ, μορφή και ημερομηνία κυκλοφορίας.
  - shot: phones
    label: Στο κινητό
    caption: Η ίδια εφαρμογή στο κινητό σου, με εγκατάσταση από τον browser.
    alt: Το Downtify σε τρία κινητά, με την αρχική σελίδα, το Παίζει τώρα και τη Βιβλιοθήκη.
pipeline:
  - icon: link
    title: Επικόλλησε έναν σύνδεσμο
    text: Spotify, YouTube Music, Deezer ή SoundCloud. Ή απλώς γράψε ένα τραγούδι.
  - icon: search
    title: Βρίσκει τον ήχο
    text: Το πιο κοντινό αποτέλεσμα στο YouTube Music, ελεγμένο με βάση τη διάρκεια. Άλλες πηγές, αν τις θέλεις.
  - icon: download
    title: Λήψη και ετικέτες
    text: Το yt-dlp και το ffmpeg τον κατεβάζουν. Εξώφυλλο, στίχοι και ετικέτες μπαίνουν μέσα στο αρχείο.
  - icon: music
    title: Άκου παντού
    text: Στον browser, στο κινητό ή στα Jellyfin, Navidrome και Plex.
quickStart:
  - text: Οδηγός εγκατάστασης
    link: /el/getting-started/installation/
    primary: true
  - text: Docker Compose
    link: /el/getting-started/docker-compose/
  - text: Εγκατάσταση με ένα κλικ
    link: /el/getting-started/one-click/
apps:
  - icon: smartphone
    title: Downtify για Android
    text: Η επίσημη εφαρμογή. Βρίσκει τον διακομιστή σου στο δίκτυο, μεταδίδει σε αρχική ποιότητα στο Wi-Fi και σε μικρότερη στα δεδομένα κινητής, κρατά τραγούδια εκτός σύνδεσης και δουλεύει με το Android Auto. Ακόμη σε δοκιμές, στα GitHub Releases και στο Obtainium.
    link: https://github.com/henriquesebastiao/downtify-android
  - icon: tablet-smartphone
    title: Downtify για iOS
    text: Φτιαγμένη από μέλος της κοινότητας για iPhone και iPad (iOS 17 ή νεότερο), με τραγούδια εκτός σύνδεσης και χειριστήρια στην οθόνη κλειδώματος. Η δημόσια beta είναι στο TestFlight.
    link: https://github.com/michaelmoskie/Downtify-IOS-Client
community:
  - text: Αστέρι στο GitHub
    link: https://github.com/henriquesebastiao/downtify
    icon: star
    primary: true
  - text: Χορηγία
    link: https://github.com/sponsors/henriquesebastiao
    icon: heart
  - text: Μετάφρασε
    link: /el/features/internationalization/
    icon: languages
  - text: Συνεισφορά
    link: /el/contributing/
    icon: git-pull-request
---

## Γιατί Downtify

<HomeHighlights :items="$frontmatter.why" />

## Μια πιο κοντινή ματιά

<HomeShowcase :items="$frontmatter.showcase" />

## Πώς λειτουργεί

Το Downtify δεν χρειάζεται κλειδί API του Spotify και δεν κατεβάζει ποτέ τίποτα από το Spotify. Διαβάζει από δημόσιες πηγές πού δείχνει ένας σύνδεσμος, διαλέγει τον ήχο του YouTube Music με τη διάρκεια που ταιριάζει καλύτερα, τον κατεβάζει με το `yt-dlp`, τον μετατρέπει με το `ffmpeg` και τον επισημαίνει με το `mutagen`, όλα σε ένα μόνο κοντέινερ Docker. Το YouTube μπαίνει όταν τίποτα δεν ταιριάζει καλά, και τα SoundCloud, Soulseek και Deemix προστίθενται αν τα ενεργοποιήσεις. [Κάθε βήμα αναλυτικά](how-it-works.md).

<HomePipeline :steps="$frontmatter.pipeline" />

## Τι μπορείς να επικολλήσεις

| Πηγή          | Τι λειτουργεί                            | Παράδειγμα                          |
| ------------- | ---------------------------------------- | ----------------------------------- |
| Spotify       | Κομμάτια, άλμπουμ, λίστες, καλλιτέχνες   | `open.spotify.com/playlist/…`       |
| YouTube Music | Τραγούδια, άλμπουμ, λίστες, καλλιτέχνες  | `music.youtube.com/playlist?list=…` |
| YouTube       | Βίντεο                                   | `youtube.com/watch?v=…`             |
| Deezer        | Κομμάτια, άλμπουμ, λίστες, καλλιτέχνες   | `deezer.com/album/…`                |
| SoundCloud    | Κομμάτια                                 | `soundcloud.com/artist/track`       |
| Αναζήτηση     | Ό,τι θα πληκτρολογούσες                  | `The Night Owls Do I Still Recall`  |
| CSV           | Εξαγωγές βιβλιοθήκης                     | Soundiiz, TuneMyMusic, Exportify    |

## Όλα όσα κάνει

Κάθε λειτουργία έχει τη δική της σελίδα, με όλες τις επιλογές εξηγημένες. [Όλες οι λειτουργίες με μια ματιά](features/index.md).

<HomeFeatures />

## Σε λειτουργία μέσα σε ένα λεπτό

```bash
docker run -d -p 8000:8000 --name downtify \
  -v /path/to/music:/downloads \
  -v downtify_data:/data \
  --restart unless-stopped \
  ghcr.io/henriquesebastiao/downtify
```

Άνοιξε το [`localhost:8000`](http://localhost:8000), συνδέσου ως **admin** με τον κωδικό **downtify** και επικόλλησε έναν σύνδεσμο. Άλλαξε αυτόν τον κωδικό στις **Ρυθμίσεις → Γενικά** αμέσως. Η μουσική σου φτάνει στο `/path/to/music`, μαζί με τις ετικέτες της.

<HomeActions :actions="$frontmatter.quickStart" />

## Συχνές ερωτήσεις

::: details Χρειάζομαι λογαριασμό Spotify, Premium ή κλειδί API;
Όχι. Το Downtify διαβάζει τα στοιχεία κομματιών, άλμπουμ και λιστών από τις δημόσιες σελίδες ενσωμάτωσης (embed) του Spotify, οπότε δεν χρειάζεται κανένα διαπιστευτήριο, και ο ήχος δεν έρχεται ποτέ από το Spotify. Δες το [Πώς λειτουργεί](how-it-works.md).
:::

::: details Από πού έρχεται ο ήχος και πόσο καλός είναι;
Από το YouTube Music από προεπιλογή: το αποτέλεσμα με τη διάρκεια που ταιριάζει καλύτερα στο τραγούδι, με το YouTube ως εναλλακτική. Διάλεξε MP3, FLAC, M4A, OGG ή Opus στο bitrate που θέλεις, ή κράτα τον καλύτερο ήχο της πηγής χωρίς επανακωδικοποίηση. Τα αρχεία χωρίς απώλειες έρχονται από πηγές που προσθέτεις εσύ: τον δικό σου διακομιστή [Soulseek (slskd)](features/slskd-navidrome.md), του οποίου τα αρχεία κρατούν την αρχική τους μορφή, ή έναν διακομιστή [Deemix](features/deemix.md). Δες τις [Ρυθμίσεις λήψης](features/download-settings.md).
:::

::: details Λειτουργεί με Jellyfin, Navidrome ή Plex;
Ναι. Τα αρχεία επισημαίνονται όπως περιμένουν οι διακομιστές πολυμέσων, μπαίνουν σε φακέλους `Καλλιτέχνης/Άλμπουμ/` και κάθε λίστα παίρνει ένα τυπικό αρχείο M3U που αναγνωρίζουν. Το Navidrome μπορεί επίσης να πάρει τις λίστες συγχρονισμένες και βαθμολογίες από το Deezer. Δες την [Οργάνωση αρχείων](features/file-organization.md) και την [Εξαγωγή M3U](features/m3u-export.md).
:::

::: details Τρέχει σε Raspberry Pi ή σε NAS;
Η εικόνα δημοσιεύεται για `amd64` και `arm64`, και τα Umbrel, CasaOS και HomeDock OS την εγκαθιστούν με ένα κλικ. Δες την [Εγκατάσταση με ένα κλικ](getting-started/one-click.md).
:::

::: details Το YouTube λέει «Sign in to confirm you're not a bot». Τι κάνω;
Ανέβασε ένα `cookies.txt` στις **Ρυθμίσεις → Cookies YouTube**· το Downtify κρατά μετά αυτή τη συνεδρία συνδεδεμένη μόνο του. Αν το YouTube σε περιορίζει ακόμη, αύξησε την _Παύση μεταξύ λήψεων_, μείωσε τις _Ταυτόχρονες λήψεις_ και μετά δοκίμασε `DOWNTIFY_FORCE_IPV4=1`. Δες την [Αντιμετώπιση προβλημάτων](troubleshooting.md) και τα [Cookies του YouTube](features/youtube-cookies.md).
:::

## Πάρ' το μαζί σου

<HomeHighlights :items="$frontmatter.apps" />

Οποιοσδήποτε άλλος πελάτης μπορεί να χρησιμοποιήσει το ίδιο API: δες το [συμβόλαιο πελάτη κινητού](mobile-client-contract.md).

<div class="home-cta">

## Φτιαγμένο ανοιχτά

Το Downtify είναι ελεύθερο και ανοιχτού κώδικα. Πάνω από 35 άτομα έχουν συνεισφέρει κώδικα, μεταφραστές της κοινότητας το έφεραν σε 12 γλώσσες, και πολλές λειτουργίες ξεκίνησαν ως μια ιδέα που κάποιος άνοιξε σε ένα issue. Αν κέρδισε μια θέση στον διακομιστή σου, δώσ' του ένα αστέρι στο GitHub, πες το σε έναν φίλο που φιλοξενεί τις δικές του υπηρεσίες, ή γίνε χορηγός της ανάπτυξής του: βοηθά να πληρωθεί ο χρόνος που μπαίνει σε κάθε έκδοση.

<HomeActions :actions="$frontmatter.community" />

</div>
