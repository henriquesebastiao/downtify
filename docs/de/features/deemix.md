---
title: Deemix
icon: lucide/music
---

# Deemix als Audioquelle

Deemix ist eine optionale Audioquelle und standardmäßig deaktiviert. Konfiguriere sie unter
**Einstellungen → Audioquellen**, unterhalb von slskd, und aktiviere sie in der Quellenreihenfolge.
Sie setzt deinen eigenen kompatiblen Deemix-Server und ein Deezer-Konto mit Anspruch
auf die gewünschte Qualität voraus. Sie bietet kein Abonnement und umgeht auch keines.

## Zugangsdaten und gemeinsame Ordner

Behalte den normalen sitzungsbasierten Anmeldemodus von Deemix bei. Aktiviere den
Einzelnutzermodus nicht auf einem ungeschützten Server: Sein Verbindungs-Endpunkt gibt den gemeinsamen ARL zurück.

Binde eine private Datei mit deinem Deezer-ARL in Downtify ein, nur lesbar
für sein Dienstkonto, und setze `DOWNTIFY_DEEMIX_ARL_FILE` auf diesen Pfad.
Der ARL wird nur beim Öffnen einer Cookie-Sitzung gelesen. Er wird nie in den
Einstellungen gespeichert, an den Browser zurückgegeben oder protokolliert. Behandle ihn wie ein Passwort;
beschaffe und ersetze ihn privat, nicht in Issues oder Chats. Die Integration
ändert nie die serverweiten Anmelde- oder Download-Einstellungen von Deemix.
Der Verbindungstest stellt keine Downloads in die Warteschlange.

| Einstellung                   | Zweck                                                              |
| ----------------------------- | ------------------------------------------------------------------ |
| Server-URL                    | Interne Adresse von Deemix, z. B. `http://deemix:6595`             |
| Download-Ordner in Deemix     | Meist `/downloads`                                                 |
| Derselbe Ordner in Downtify   | Gemeinsamer Bind-Mount, z. B. `/deemix`; schreibgeschützt wird unterstützt |
| Qualität                      | MP3 128, MP3 320 oder FLAC; nicht unterstützte Berechtigungen schlagen ausdrücklich fehl |

Der gemeinsame Ordner wird beim Speichern als externer Bibliotheksordner registriert.
Die Dateien bleiben dort in der Künstler-/Album-Organisation von Deemix. Downtify bewahrt
ihr Format, ihre Tags, ihr Artwork und ihre `.lrc`-Begleitdateien, ohne sie neu zu schreiben.
Vorhandene eingebettete Songtexte und gleichnamige `.lrc`-Dateien liest der Player.
Diese Integration löscht, verschiebt oder erzeugt weder Audio noch Songtexte.

Ein Deezer-Titellink wählt genau diese Aufnahme aus. Katalogübergreifende Downloads erfordern
eine eindeutige, exakte Übereinstimmung von Künstler/Titel, bei Angabe auch von Album und Länge.
Eine mehrdeutige Übereinstimmung fällt auf die nächste aktivierte Quelle zurück.
Nach Abschluss der Deemix-Warteschlange folgt eine Datei- sowie Längen-/Qualitätsprüfung.
Die Integration leert, bricht ab oder ändert nie manuelle Deemix-Aufträge.
Explizite YouTube-Links behalten ihr bisheriges Direktdownload-Verhalten.

Diese Quelle ersetzt oder löscht nicht automatisch einen vorhandenen Titel der
Bibliothek. Bibliotheks-Deduplizierung und manuelles Ersetzen von Audio bleiben getrennt.
