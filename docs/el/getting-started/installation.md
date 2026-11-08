---
icon: lucide/download
---

# Εγκατάσταση

Ο ταχύτερος τρόπος να τρέξεις το Downtify είναι μία μόνο εντολή `docker run`. Δεν χρειάζεται Python, Node.js ή άλλες εξαρτήσεις συστήματος στον κεντρικό υπολογιστή — όλα είναι ενσωματωμένα στην εικόνα.

## Προαπαιτούμενα

- Το [Docker](https://docs.docker.com/get-docker/) εγκατεστημένο και σε λειτουργία

## Docker run

```bash
docker run -d \
  --name downtify \
  -p 8000:8000 \
  -v /path/to/music:/downloads \
  -v downtify_data:/data \
  --restart unless-stopped \
  ghcr.io/henriquesebastiao/downtify
```

Αντικατέστησε το `/path/to/music` με τον κατάλογο όπου θέλεις να αποθηκεύεται η μουσική σου.

Όταν ξεκινήσει το κοντέινερ, άνοιξε το **[http://localhost:8000](http://localhost:8000)** στον browser σου.

## Τόμοι

| Τόμος | Σκοπός |
|--------|---------|
| `/downloads` | Αρχεία ήχου που έχουν κατέβει |
| `/data` | Βάση δεδομένων της εφαρμογής και μόνιμες ρυθμίσεις |

Και οι δύο τόμοι διατηρούνται μέσα από επανεκκινήσεις και αναβαθμίσεις του κοντέινερ. Ο τόμος `/downloads` μπορεί να είναι οποιοσδήποτε κατάλογος του κεντρικού σου υπολογιστή ή ένας επώνυμος τόμος Docker.

## Προσαρμοσμένη θύρα

Για να εκθέσεις το Downtify σε άλλη θύρα του υπολογιστή, άλλαξε την αριστερή πλευρά του `-p`:

```bash
docker run -d \
  --name downtify \
  -p 9090:8000 \           # υπολογιστής:κοντέινερ
  -v /path/to/music:/downloads \
  -v downtify_data:/data \
  ghcr.io/henriquesebastiao/downtify
```

Μετά άνοιξε το **[http://localhost:9090](http://localhost:9090)**.

## Ενημέρωση

Κατέβασε την τελευταία εικόνα και ξαναδημιούργησε το κοντέινερ:

```bash
docker pull ghcr.io/henriquesebastiao/downtify
docker stop downtify && docker rm downtify
docker run -d --name downtify -p 8000:8000 \
  -v /path/to/music:/downloads \
  -v downtify_data:/data \
  --restart unless-stopped \
  ghcr.io/henriquesebastiao/downtify
```

Η μουσική και οι ρυθμίσεις σου διατηρούνται στους τόμους.

## Και τώρα;

- **[Docker Compose](docker-compose.md)** — πιο εύκολος τρόπος διαχείρισης του κοντέινερ μακροπρόθεσμα
- **[Μεταβλητές περιβάλλοντος](environment-variables.md)** — ρύθμισε τη συμπεριφορά anti-bot και άλλες προηγμένες επιλογές
- **[Ρυθμίσεις λήψης](../features/download-settings.md)** — διάλεξε μορφή και bitrate
