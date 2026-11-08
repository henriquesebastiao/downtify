---
icon: lucide/hard-drive
---

# Servereinstellungen

Unter **Einstellungen → Server** steht, wie der Server selbst läuft. Nur Admins sehen den Bereich (siehe [Benutzer und Anmeldung](users.md#admins-and-users)).

## Port ändern

Downtify lauscht auf Port **8000**. Ein Admin kann unter **Einstellungen → Server → Port** einen anderen wählen (1024–65535):

- **Speichern** merkt ihn sich für den nächsten Serverstart.
- **Speichern und neu starten** startet den Server sofort auf diesem Port neu. Laufende Downloads werden abgebrochen, Seiten und Apps verbinden sich neu. Eine Seite, die über die Adresse des Servers selbst geöffnet wurde (z. B. `http://nas:8000`), wartet auf den Server und öffnet die neue Adresse von allein; du bleibst angemeldet.

Stammt der Port aus der Umgebungsvariable `DOWNTIFY_PORT` (oder `PORT`) oder aus `--port` auf der Kommandozeile — diese haben immer Vorrang —, zeigt das Feld den verwendeten Port an, lässt sich aber nicht bearbeiten, und die Seite sagt, welche Einstellung ihn festlegt. Entferne sie (und starte neu), um den Port in den Einstellungen zu wählen.

::: warning Das Bridge-Netzwerk von Docker bildet einen festen Port ab
Im Standard-Docker-Setup (`ports: - '8000:8000'`) muss der Port des Containers zur Zuordnung passen. Ändere nach der Umstellung in den Einstellungen auch die Zuordnung auf den neuen Port (`'9000:9000'`) und erstelle den Container neu — oder starte mit `network_mode: host`. Sonst ist Downtify nicht erreichbar. Um wieder hineinzukommen, setze `DOWNTIFY_PORT` auf den alten Port: Er hat Vorrang vor den Einstellungen.
:::

Hinter einem [Reverse-Proxy](mobile-apps.md#behind-a-reverse-proxy) musst du auch den Proxy auf den neuen Port richten. [Gekoppelte Apps](mobile-apps.md) nutzen die Adresse, die sie erhalten haben: Gib nach einer Portänderung die neue in der App ein.
