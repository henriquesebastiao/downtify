---
icon: lucide/sparkles
---

# Ähnliche Titel

**Ähnliche Titel** findet Titel, die so klingen wie einer, den du nennst — aus dem Radio-Mix von YouTube Music selbst, also dem, was YouTube nach deinem Titel spielt. Ohne API-Schlüssel, ohne Einrichtung.

## So nutzt du es

Öffne **Ähnliche Titel** in der Seitenleiste (unter **Charts**, auf dem Smartphone im Fenster **Mehr**). Gib den **Künstler** oder den **Titel** ein (eines von beidem genügt — bei einem Künstler allein dient sein größter Hit als Ausgangspunkt) und klicke auf **Ähnliche finden**:

Du musst auch nichts eintippen: Jede Titelzeile in der App hat eine Schaltfläche **Ähnliche Titel** (das Zauberstab-Symbol neben der Download-Schaltfläche, in Suche, Charts und Entdecken wie diese gefüllt — bei Top-Songs und eingefügten Links als schlichtes Symbol, und als Kontextmenü-Eintrag bei Titeln in Bibliothek, Album, Künstler und Playlist). Sie öffnet diese Seite und sucht gleich nach diesem Titel. Suchergebnisse lassen sich außerdem direkt aus der Zeile vollständig abspielen, ohne etwas herunterzuladen.

- **Vollständig abspielen** — tippe auf das Cover, und der Titel wird von diesem Server direkt in den integrierten Player gestreamt, ob heruntergeladen oder nicht.
- **Herunterladen** — jede Zeile bringt ihr Video schon mit und lädt sofort herunter: Downtify stellt den Treffer über dieselbe [Zuordnungs-Pipeline](../how-it-works.md) in die Warteschlange wie jeder andere Download. Danach zeigt die Zeile den Fortschritt dieses Downloads und, sobald der Song in deiner Bibliothek ist, ein Häkchen.
- **Endlose Liste** — Scrollen bis zum Ende lädt die nächste Seite aus dem Mix des letzten Titels, und die Wiedergabe über die letzte Zeile hinaus erweitert die Warteschlange auf dieselbe Weise, ohne Ende.

## API

Siehe [`GET /api/similar/tracks`](../api-reference.md#get-apisimilartracks) in der API-Referenz.
