---
icon: lucide/file-code
---

# Docker Compose

Το Docker Compose είναι ο προτεινόμενος τρόπος για να τρέχεις το Downtify σε μόνιμες οικιακές εγκαταστάσεις διακομιστή. Κάνει εύκολες τις ενημερώσεις, τα αντίγραφα ασφαλείας και τις αλλαγές διαμόρφωσης.

## Ελάχιστη εγκατάσταση

Δημιούργησε ένα αρχείο `docker-compose.yml`:

```yaml
services:
  downtify:
    container_name: downtify
    image: ghcr.io/henriquesebastiao/downtify:latest
    ports:
      - '8000:8000'
    volumes:
      - ./downloads:/downloads
      - downtify_data:/data
    restart: unless-stopped

volumes:
  downtify_data:
```

Ξεκίνα το:

```bash
docker compose up -d
```

Άνοιξε το **[http://localhost:8000](http://localhost:8000)**.

## Με slskd (Soulseek)

Για να χρησιμοποιήσεις το [slskd ως πηγή ήχου](../features/slskd-navidrome.md), προσάρτησε στο Downtify και τον φάκελο λήψεων του slskd — τον **ίδιο φάκελο του υπολογιστή** στον οποίο γράφει το κοντέινερ του slskd:

```yaml
services:
  downtify:
    # ...
    volumes:
      - ./downloads:/downloads
      - /path/to/slskd/downloads:/slskd
      - downtify_data:/data
```

Έπειτα, στο **Ρυθμίσεις → Πηγές ήχου → slskd**, ενεργοποίησε το slskd, δώσε το URL του (π.χ. `http://slskd:5030` όταν και τα δύο κοντέινερ μοιράζονται δίκτυο Docker) και το κλειδί API, και όρισε τον φάκελο λήψεων σε `/slskd`.

## Υπάρχοντες φάκελοι μουσικής

Για να πάρει η Βιβλιοθήκη μια συλλογή που ήδη κρατάς στον υπολογιστή, [προσάρτησέ την](../features/external-library.md) με τον ίδιο τρόπο και πληκτρολόγησε τη διαδρομή **του κοντέινερ** στο **Ρυθμίσεις → Βιβλιοθήκη**:

```yaml
    volumes:
      - ./downloads:/downloads
      - /path/on/host/to/mp3s:/music/collection
      - downtify_data:/data
```

## Εύρεση του διακομιστή από τις εφαρμογές

Οι [εφαρμογές κινητού](../features/mobile-apps.md#finding-the-server-on-your-network) απαριθμούν τους διακομιστές Downtify του δικτύου σου μέσω mDNS. Στο προεπιλεγμένο δίκτυο bridge του Docker αυτή η αναγγελία δεν βγαίνει ποτέ από το Docker, οπότε τα κινητά δεν τη βλέπουν. Για να εμφανιστεί, τρέξε το κοντέινερ στο δίκτυο του υπολογιστή — η αντιστοίχιση `ports:` τότε δεν ισχύει και το Downtify ακούει απευθείας στο `DOWNTIFY_PORT`:

```yaml
services:
  downtify:
    image: ghcr.io/henriquesebastiao/downtify:latest
    network_mode: host
    environment:
      - DOWNTIFY_PORT=8000
    volumes:
      - ./downloads:/downloads
      - downtify_data:/data
    restart: unless-stopped
```

Διαφορετικά πληκτρολόγησε απλώς τη διεύθυνση του διακομιστή στην εφαρμογή (`http://<IP του υπολογιστή>:8000`)· τίποτα άλλο δεν εξαρτάται από την ανακάλυψη.

## Προσαρμοσμένη θύρα

Αν η θύρα 8000 χρησιμοποιείται ήδη, αντιστοίχισε άλλη θύρα του υπολογιστή και όρισε τη μεταβλητή περιβάλλοντος `DOWNTIFY_PORT` ώστε το κοντέινερ να ακούει εσωτερικά στην ίδια θύρα:

```yaml
services:
  downtify:
    image: ghcr.io/henriquesebastiao/downtify:latest
    ports:
      - '9090:30321'
    environment:
      - DOWNTIFY_PORT=30321
    volumes:
      - ./downloads:/downloads
      - downtify_data:/data
    restart: unless-stopped
```

Μπορείς επίσης να επιλέξεις τη θύρα στο **Ρυθμίσεις → Διακομιστής → Θύρα** αντί να ορίσεις το `DOWNTIFY_PORT` (που, όταν ορίζεται, υπερισχύει των Ρυθμίσεων). Στο προεπιλεγμένο δίκτυο bridge, άλλαξε την αντιστοίχιση `ports:` στην ίδια θύρα και ξαναδημιούργησε το κοντέινερ — δες [Αλλαγή θύρας](../features/server.md#changing-the-port).

## Με προσαρμοσμένο DNS (προτείνεται)

Ορισμένοι πάροχοι και εταιρικά δίκτυα μπλοκάρουν το YouTube. Η προσθήκη ρητών επιλυτών DNS βελτιώνει την αξιοπιστία:

```yaml
services:
  downtify:
    image: ghcr.io/henriquesebastiao/downtify:latest
    ports:
      - '8000:8000'
    volumes:
      - ./downloads:/downloads
      - downtify_data:/data
    dns:
      - 1.1.1.1
      - 1.0.0.1
    restart: unless-stopped
```

## Ενημέρωση

```bash
docker compose pull
docker compose up -d
```

Η μουσική και οι ρυθμίσεις σου διατηρούνται στους τόμους.

## Τόμοι

| Διαδρομή στο αρχείο compose | Σκοπός |
|------------------------------|---------|
| `./downloads:/downloads` | Αρχεία ήχου που έχουν κατέβει (τοπικός κατάλογος) |
| `downtify_data:/data` | Βάση δεδομένων και ρυθμίσεις της εφαρμογής (επώνυμος τόμος) |

Μπορείς να αντικαταστήσεις τον επώνυμο τόμο με τοπική διαδρομή (`./data:/data`) αν προτιμάς να τον διαχειρίζεσαι μόνος σου.
