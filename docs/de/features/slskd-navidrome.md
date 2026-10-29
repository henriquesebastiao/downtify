---
icon: lucide/share-2
---

# slskd und Navidrome

Zwei optionale Integrationen für selbst gehostete Bibliotheken:

- **[slskd](https://github.com/slskd/slskd)** — lade Titel aus dem Soulseek-Netzwerk über deinen eigenen slskd-Server herunter, als zusätzliche Audioquelle neben YouTube Music und YouTube.
- **[Navidrome](https://www.navidrome.org/)** — spiegle die Playlists, die du herunterlädst, nach Navidrome, damit sie in jedem Subsonic-Client erscheinen.

Beide sind standardmäßig aus und werden in den **Einstellungen** konfiguriert.

## Audioquellen und Rückfallreihenfolge

**Einstellungen → Audioquellen** ist eine geordnete Liste. Tippe auf eine Quelle, um sie hinzuzufügen oder zu entfernen; sind mehrere ausgewählt, ordne sie mit den Pfeilen um. Jeder Titel probiert die Quellen in dieser Reihenfolge und hört bei der ersten auf, die Audio liefert:

| Quelle | Was sie tut |
|--------|-------------|
| **YouTube Music** | Der Standard. Durchsucht YouTube Music und fällt auf normales YouTube zurück, wenn es keinen akzeptablen Treffer gibt — siehe [So funktioniert es](../how-it-works.md#fallback-to-standard-youtube). |
| **YouTube** | Durchsucht nur normales YouTube. |
| **slskd** | Durchsucht Soulseek über slskd und lädt die am besten passende Datei herunter. |

Wird slskd aktiviert, steht es an erster Stelle der Liste. Ist slskd am Ende die einzige Quelle, werden YouTube Music und YouTube trotzdem danach probiert, sodass ein Titel, den slskd nicht findet, trotzdem heruntergeladen wird. Die Download-Warteschlange zeigt, welche Quelle jeden Titel geliefert hat.

## slskd

### Einrichtung

1. Starte slskd und erstelle einen API-Schlüssel für Downtify (siehe die Dokumentation von slskd).
2. Binde den Download-Ordner von slskd in den Downtify-Container ein — denselben Host-Ordner, in den slskd schreibt. Siehe [Docker Compose → Mit slskd](../getting-started/docker-compose.md#with-slskd-soulseek).
3. Aktiviere unter **Einstellungen → slskd (Soulseek)** slskd und fülle aus:
    - **slskd-URL** — z. B. `http://slskd:5030`, wenn beide Container ein Docker-Netzwerk teilen.
    - **API-Schlüssel**.
    - **Download-Ordner** — der Pfad *im Downtify-Container*, in den dieser Ordner eingebunden ist (Standard `/slskd`), nicht der Host-Pfad.

Das Speichern wird mit einer Fehlermeldung abgelehnt, wenn slskd ohne URL oder API-Schlüssel aktiviert ist.

### Die Verbindung testen

Drücke unter den Feldern auf **Verbindung testen**, um sie vor dem Speichern zu prüfen — es nutzt, was im Formular steht, gespeichert oder nicht, und ändert nichts. Es meldet:

| Ergebnis | Was es bedeutet |
|--------|---------------|
| **Mit slskd 0.21.4 verbunden.** | Die Adresse stimmt und der API-Schlüssel wurde akzeptiert |
| **slskd ist bei Soulseek angemeldet.** / **nicht angemeldet** | Ob slskd selbst im Soulseek-Netzwerk angemeldet ist. Wenn nicht, finden Suchen nichts, bis es so ist — eine Warnung, da die Einstellungen selbst stimmen |
| **Downtify kann `/slskd` lesen.** / **kann nicht lesen** | Ob der obige Download-Ordner in *diesem* Container existiert und lesbar ist. Die übliche Ursache einer Warnung ist ein nicht eingebundener Ordner — siehe [Einrichtung](#setup) |
| **slskd hat den API-Schlüssel abgelehnt.** | Der Server hat geantwortet, aber nicht auf diesen Schlüssel |
| **… nicht erreichbar / hat nicht rechtzeitig geantwortet.** | Falsche Adresse oder falscher Port, der Server ist aus oder vom Downtify-Container nicht erreichbar |
| **Sieht nicht nach slskd aus.** | Etwas hat geantwortet, aber nicht slskd — oft ein falscher Port oder ein in der Adresse fehlender Basispfad |
| **Dem HTTPS-Zertifikat wird nicht vertraut.** | Nutze `http://` im eigenen Netzwerk oder ein Zertifikat einer vertrauenswürdigen Stelle; Downtify überspringt keine Zertifikatsprüfungen |

Das Bearbeiten eines Felds löscht das letzte Ergebnis, da es nicht mehr beschreibt, was im Formular steht. Die Schaltfläche bleibt deaktiviert, bis Adresse und Schlüssel ausgefüllt sind.

### Wie ein Titel zugeordnet wird

Downtify durchsucht slskd mit Titel und Künstler des Titels und ordnet die Ergebnisse danach, wie gut Dateiname und Länge zum Titel passen. Bei gleich guten Treffern bevorzugt es MP3, dann FLAC, und überspringt Dateien, die eine Bitrate unter 256 kbps melden. Es probiert bis zu fünf Kandidaten nacheinander. Wenn eine Übertragung endet, prüft Downtify Tags und Länge der Datei gegen den Titel, bevor es sie behält.

Findet sich nichts Akzeptables, endet die Übertragung nicht innerhalb des **Gesamtzeitlimits**, oder sie hängt länger als das **Zeitlimit in Warteschlange** ohne Fortschritt in der Warteschlange des entfernten Peers, geht Downtify zur nächsten Audioquelle über.

### Dateien an Ort und Stelle lassen

Ist **slskd-Dateien an Ort und Stelle lassen** an (Standard), bleibt die heruntergeladene Datei im slskd-Ordner: Downtify schreibt Metadaten, Cover und Songtext direkt dort hinein und registriert sie in der Bibliothek unter einem `slskd/…`-Pfad. Bibliothek, Player und M3U-Dateien nutzen diesen Pfad, und er wird über `/media/slskd/…` ausgeliefert.

Schalte es aus, um die Datei stattdessen neben deine anderen Downloads zu kopieren, gemäß deiner Dateinamenvorlage und den Einstellungen zur [Dateiorganisation](file-organization.md).
Die Übertragung selbst bleibt im slskd-Ordner; [Speicher und Nutzung](storage-usage.md#the-library-not-its-working-copies) zählt diese Kopien getrennt von der Bibliothek als *Arbeitskopien von slskd*, damit du siehst, wie viel Platz sie belegen.

::: info
slskd-Dateien behalten ihr Originalformat — sie werden nicht in das in den Einstellungen gewählte Format transkodiert.
:::

## Navidrome

### Einrichtung

1. Stelle sicher, dass der Musikordner von Navidrome den Download-Ordner von Downtify einschließt (und den slskd-Ordner, wenn du slskd-Dateien an Ort und Stelle lässt). Navidrome kann Titel einer Playlist erst hinzufügen, wenn es sie gescannt hat.
2. Aktiviere unter **Einstellungen → Navidrome** Navidrome und gib URL, Benutzername und Passwort ein.
3. Optional: Füge einen **Admin**-Benutzernamen und ein Passwort hinzu. Downtify bittet Navidrome dann, die Bibliothek zu scannen, bevor neue Titel zugeordnet werden, statt auf den eigenen geplanten Scan von Navidrome zu warten.

### Die Verbindung testen

Drücke unter den Feldern auf **Verbindung testen**, um sie vor dem Speichern zu prüfen — es nutzt, was im Formular steht, gespeichert oder nicht, und ändert nichts. Es meldet:

| Ergebnis | Was es bedeutet |
|--------|---------------|
| **Mit navidrome 0.53.3 verbunden.** | Die Adresse stimmt und Benutzername und Passwort wurden akzeptiert |
| **Dieses Konto kann Bibliotheksscans starten.** | Das für Scans genutzte Konto ist ein Admin. Das ist der eingegebene Admin-Benutzername oder der normale, wenn du ihn leer gelassen hast |
| **Dieses Konto kann keine Bibliotheksscans starten.** | Navidrome lässt nur Admins einen Scan starten und sagt das nicht, wenn Downtify es versucht — neue Songs erscheinen einfach verspätet. Gib einen Admin-Benutzernamen und ein Passwort ein |
| **Das Admin-Konto ist kein Admin.** | Die eingegebene Admin-Anmeldung funktioniert, gehört aber zu einem normalen Benutzer |
| **Navidrome hat den Admin-Benutzernamen oder das Passwort abgelehnt.** | Die Anmeldung des Scan-Kontos ist falsch; die Hauptanmeldung wird separat gemeldet |
| **Navidrome hat den Benutzernamen oder das Passwort abgelehnt.** | Der Server hat geantwortet, aber nicht auf diese Anmeldung |
| **… nicht erreichbar / hat nicht rechtzeitig geantwortet.** | Falsche Adresse oder falscher Port, der Server ist aus oder vom Downtify-Container nicht erreichbar |
| **Sieht nicht nach Navidrome aus.** | Etwas hat geantwortet, aber nicht die Subsonic-API — oft ein falscher Port oder eine in der Adresse fehlende Basis-URL |
| **Dem HTTPS-Zertifikat wird nicht vertraut.** | Nutze `http://` im eigenen Netzwerk oder ein Zertifikat einer vertrauenswürdigen Stelle; Downtify überspringt keine Zertifikatsprüfungen |

Die Scan-Rechte werden nur abgefragt — der Test startet nie einen Scan. Das Bearbeiten eines Felds löscht das letzte Ergebnis, und die Schaltfläche bleibt deaktiviert, bis Adresse, Benutzername und Passwort ausgefüllt sind.

::: info Nichts wird an die Seite zurückgesendet
Die Antwort trägt nur, was gefunden wurde — eine Version, einen Pfad, einen Status — nie dein Passwort oder die Anfrage, die Downtify gestellt hat.
:::

### Playlist-Synchronisierung

Das Spiegeln wird von Admins konfiguriert (Einstellungen → Navidrome); normale Konten können keine Spiegel erstellen, ihre Downloads werden aber wie die aller anderen gespiegelt, sobald die Integration an ist.

Ist **Playlists in Navidrome erstellen** an, erstellt (oder aktualisiert) Downtify eine Navidrome-Playlist mit demselben Namen, nachdem:

- ein Spotify-Playlist-Download fertig ist,
- ein Durchlauf der [Playlist-Überwachung](playlist-monitor.md) Titel hinzufügt,
- Titel aus der Bibliothek gelöscht oder [Bibliothekspfade korrigiert](library-catalog.md#fix-library-paths) werden.

Titel werden Navidrome-Songs zuerst über den Pfad, dann über die Tags zugeordnet. **Navidrome-Playlists öffentlich machen** steuert die Sichtbarkeit der Playlist in Navidrome.

::: warning Dateien, deren Tags nicht zur Playlist passen, werden gelöscht
Wird eine Playlist aktualisiert (nach Löschungen, **Bibliothekspfade korrigieren** oder **Fehlende herunterladen** bei einer bereits vollständigen Playlist), wird eine für einen Spotify-Titel registrierte Bibliotheksdatei **von der Festplatte gelöscht**, wenn ihr eingebetteter Titel/Künstler erkennbar nicht zu diesem Titel passt — Downtify behandelt sie als falschen Download. Denk daran, wenn du Tags von Hand bearbeitest.
:::

### Playlist-Cover

Nichts einzurichten: Ist [Playlist-Cover speichern](playlist-cover-art.md) an, nimmt Navidrome das `.jpg`, das Downtify neben die M3U der Playlist schreibt, als **Sidecar-Bild** auf — seine eigene Art, Playlist-Artwork aufzulösen —, solange sein Musikordner diese Datei abdeckt. Downtify macht dafür keinen API-Aufruf.

## Playlist-Downloads

Die **Bibliothek**-Seite listet die über Downtify heruntergeladenen Spotify-Playlists unter **Playlist-Downloads** auf. Klappe sie auf, um für jede Playlist zu sehen, wie viele Titel in deiner Bibliothek sind im Vergleich zur aktuellen Spotify-Titelliste. Von dort kannst du:

- **Fehlende herunterladen** — nur die Titel einreihen, die noch nicht in deiner Bibliothek sind.
- Die bereits heruntergeladenen Titel **abspielen**.
- Eine Playlist aufklappen, um einzelne fehlende Titel zu sehen und herunterzuladen.
- Die Playlist **löschen** — siehe unten.

### Eine Playlist löschen

Das Löschen einer Playlist (aus diesem Panel oder mit **Playlist löschen** neben dem Playlist-Filter der Bibliothek) entfernt jeden für sie registrierten Titel von der Festplatte — **auch Titel, die andere Playlists ebenfalls enthalten** —, dazu ihre M3U-Datei und das daneben gespeicherte [Cover](playlist-cover-art.md), und hört auf, sie zu verfolgen. Andere Playlists, die diese Titel teilten, bekommen ihre M3U und ihre Navidrome-Playlist im Hintergrund neu geschrieben.
