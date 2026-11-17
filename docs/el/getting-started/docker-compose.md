---
icon: lucide/file-code
---

# Docker Compose

Το Docker Compose είναι ο προτεινόμενος τρόπος για να τρέχεις το Downtify σε μόνιμες οικιακές εγκαταστάσεις διακομιστή. Κάνει εύκολες τις ενημερώσεις, τα αντίγραφα ασφαλείας και τις αλλαγές διαμόρφωσης.

## Ελάχιστη εγκατάσταση

Δημιούργησε ένα αρχείο `docker-compose.yml`. Τρέχει το Downtify με PostgreSQL, με τη βάση δεδομένων σε μια υπηρεσία `postgres` δίπλα του (δες [Βάση δεδομένων](../database.md)):

```yaml
services:
  downtify:
    container_name: downtify
    image: ghcr.io/henriquesebastiao/downtify:latest
    restart: unless-stopped
    depends_on:
      postgres:
        condition: service_healthy
    ports:
      - '8000:8000'
    volumes:
      - ./downloads:/downloads
      - downtify_data:/data
    environment:
      DATABASE_URL: postgresql://downtify:${POSTGRES_PASSWORD:-downtify}@postgres:5432/downtify

  postgres:
    container_name: downtify-postgres
    image: 'postgres:17-alpine'
    restart: unless-stopped
    environment:
      POSTGRES_USER: downtify
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-downtify}
      POSTGRES_DB: downtify
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ['CMD-SHELL', 'pg_isready -U downtify -d downtify']
      interval: 5s
      timeout: 5s
      retries: 10
      start_period: 10s

volumes:
  downtify_data:
  pgdata:
```

Όρισε το `POSTGRES_PASSWORD` σε ένα αρχείο `.env` δίπλα στο αρχείο Compose πριν από την πρώτη εκκίνηση (δες [Μεταβλητές περιβάλλοντος](environment-variables.md#database)). Για να κρατήσεις τα αρχεία SQLite, αφαίρεσε το `DATABASE_URL`, την υπηρεσία `postgres` και το μπλοκ `depends_on`.

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
| `downtify_data:/data` | Ρυθμίσεις, cache και τα αρχεία SQLite (επώνυμος τόμος) |
| `pgdata:/var/lib/postgresql/data` | Η βάση δεδομένων PostgreSQL, στην υπηρεσία `postgres` |

Μπορείς να αντικαταστήσεις τον επώνυμο τόμο με τοπική διαδρομή (`./data:/data`) αν προτιμάς να τον διαχειρίζεσαι μόνος σου.
