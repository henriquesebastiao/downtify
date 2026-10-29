---
icon: lucide/hand-heart
---

# Συνεισφορά

Οι συνεισφορές είναι ευπρόσδεκτες — αναφορές σφαλμάτων, αιτήματα λειτουργιών, κώδικας και μεταφράσεις βοηθούν όλα. Οι μεταφράσεις μπορεί να αφορούν την εφαρμογή, αυτή την τεκμηρίωση ή και τα δύο: δες [Μετάφραση](#translating).

## Issues και αιτήματα λειτουργιών

Χρησιμοποίησε το [σύστημα παρακολούθησης issues του GitHub](https://github.com/henriquesebastiao/downtify/issues). Πριν ανοίξεις νέο issue, ψάξε στα υπάρχοντα για να αποφύγεις διπλότυπα.

Στις αναφορές σφαλμάτων, συμπεριέλαβε:

- Έκδοση Downtify
- Πώς το εγκατέστησες (Docker run, Docker Compose, Umbrel, …)
- Βήματα αναπαραγωγής
- Τι περίμενες και τι συνέβη
- Τυχόν σχετικά αρχεία καταγραφής

## Περιβάλλον ανάπτυξης

### Προαπαιτούμενα

- Python 3.15+
- Node.js 20+
- [uv](https://github.com/astral-sh/uv) (διαχειριστής πακέτων Python)
- ffmpeg (πρέπει να βρίσκεται στο `PATH`)

### Κλωνοποίηση και εγκατάσταση

```bash
git clone https://github.com/henriquesebastiao/downtify.git
cd downtify

# Python dependencies
uv sync

# Frontend dependencies
cd frontend && npm install && cd ..
```

### Εκτέλεση σε λειτουργία ανάπτυξης

```bash
# Terminal 1 — backend
uv run python main.py

# Terminal 2 — frontend dev server (hot reload)
cd frontend && npm run dev
```

Ο διακομιστής ανάπτυξης του frontend προωθεί τα αιτήματα API στο backend, οπότε χρειάζεται μόνο να ανοίξεις το URL του Vite (συνήθως `http://localhost:5173`).

### Εκτέλεση των δοκιμών

```bash
uv run pytest
```

### Μεταγλώττιση του frontend για παραγωγή

```bash
cd frontend && npm run build
```

Τα μεταγλωττισμένα αρχεία καταλήγουν στο `frontend/dist/` και σερβίρονται από το backend.

### Εργασία στην τεκμηρίωση

Η τεκμηρίωση είναι αρχεία Markdown στο `docs/`, που χτίζονται σε στατικό ιστότοπο με το [VitePress](https://vitepress.dev/) και ένα προσαρμοσμένο θέμα (στο `docs/.vitepress/`) που μοιράζεται τα design tokens του με τη web εφαρμογή.

```bash
make doc         # dev server with hot reload
make doc-build   # production build into docs/.vitepress/dist
```

Συνδέσου σε άλλες σελίδες με σχετικές διαδρομές `.md` (`[Στίχοι](lyrics.md)`) και χρησιμοποίησε `::: tip Τίτλος` … `:::` για πλαίσια επισήμανσης (`info`, `tip`, `warning`, `danger`). Οι νέες σελίδες μπαίνουν στην πλαϊνή μπάρα στο `docs/.vitepress/nav.mjs` (με τον τίτλο τους στο αρχείο κάθε γλώσσας στο `docs/.vitepress/locales/`). Η μεταγλώττιση αποτυγχάνει με νεκρούς συνδέσμους και με συνδέσμους σε επικεφαλίδες που δεν υπάρχουν.

Οι αγγλικές σελίδες στο `docs/` είναι η πηγή· κάθε άλλη γλώσσα τις αντικατοπτρίζει σε δικό της φάκελο (`docs/pt-BR/…`). Δεν χρειάζεται να ενημερώσεις τις μεταφράσεις όταν αλλάζεις μια αγγλική σελίδα — οι μεταφραστές ακολουθούν —, αλλά τρέξε `npm test` στο `docs/`: μια νέα σελίδα χρειάζεται ένα μόνο αγγλικό προσχέδιο σε κάθε γλώσσα (`npm run i18n -- stubs`), και τα τεστ το λένε αν λείπει.

## Δομή του έργου

```
downtify/
├── downtify/          # Python backend
│   ├── api.py         # FastAPI router
│   ├── downloader.py  # yt-dlp + mutagen pipeline
│   ├── spotify.py     # Spotify embed scraping
│   ├── providers.py   # YouTube Music search
│   ├── monitor.py     # Playlist monitor
│   ├── lyrics.py      # lrclib integration
│   └── m3u.py         # M3U generation
├── frontend/          # Vue 3 + Vite frontend
│   └── src/
│       └── i18n/      # Translation files
├── docs/              # This documentation (Markdown + VitePress site)
│   ├── <page>.md      # English, the source
│   ├── pt-BR/ …       # One folder per translated language, same file names
│   └── .vitepress/
│       └── locales/   # Each language's site text and sidebar titles
├── main.py            # Entry point
├── Dockerfile
└── docker-compose.yml
```

## Μετάφραση

Το Downtify έχει δύο πράγματα προς μετάφραση, και μπορείς να πάρεις όποιο θες — ή και τα δύο:

| Μεταφράζεις | Πού | Οδηγός |
|---------------|-------|-------|
| **Την εφαρμογή** (τη διεπαφή της) | `frontend/src/i18n/locales/<code>.js` | [Μετάφραση της εφαρμογής](features/internationalization.md#translating-the-app) |
| **Την τεκμηρίωση** (αυτές τις σελίδες) | `docs/<code>/` και `docs/.vitepress/locales/<code>.mjs` | [Μετάφραση της τεκμηρίωσης](features/internationalization.md#translating-the-documentation) |

Είναι ανεξάρτητα: μια γλώσσα μπορεί να είναι στο ένα και όχι ακόμη στο άλλο, και ένα pull request μπορεί να περιέχει μόνο μετάφραση της εφαρμογής, μόνο τεκμηρίωση ή και τα δύο. Η μερική δουλειά είναι ευπρόσδεκτη — τα αμετάφραστα κείμενα επιστρέφουν στα αγγλικά στην εφαρμογή, και οι αμετάφραστες σελίδες μένουν αγγλικές στην τεκμηρίωση.

Γρήγορη εκκίνηση για την τεκμηρίωση, από το `docs/`:

```bash
npm run i18n -- status pt-BR                    # coverage of a language
npm run i18n -- start pt-BR features/users.md   # copy an English page to translate
npm test                                        # check the structure of what you translated
```

Δες τη σελίδα [Διεθνοποίηση](features/internationalization.md) για λεπτομέρειες: τι να κρατήσεις ως έχει, πώς να προσθέσεις ολόκληρη νέα γλώσσα και πώς να μεταφράσεις τα ονόματα των κουμπιών ώστε να ταιριάζουν με της εφαρμογής.

## Pull requests

- Κάνε fork το αποθετήριο και δημιούργησε ένα branch από το `main`
- Κράτα τις αλλαγές εστιασμένες — μία λειτουργία ή διόρθωση ανά PR
- Πρόσθεσε ή ενημέρωσε δοκιμές όταν αγγίζεις τη λογική του backend
- Τρέξε `uv run pytest` πριν στείλεις
- Άνοιξε το PR προς το `main`

Αν το Downtify σού φάνηκε χρήσιμο, σκέψου να αφήσεις ένα αστέρι στο GitHub — βοηθά το έργο να μεγαλώσει.
