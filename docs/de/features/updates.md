---
icon: lucide/download
---

# Update-Benachrichtigungen

Downtify prüft seine eigene [GitHub-Releases-Seite](https://github.com/henriquesebastiao/downtify/releases) einmal pro Stunde. Gibt es eine neuere Version, erscheint auf jeder Seite unten in der Seitenleiste ein Hinweis — auf dem Smartphone ein Punkt am Tab **Mehr** und eine Zeile oben in dessen Fenster — sowie unter **Einstellungen → Über**:

> ✦ Update 3.0.1 verfügbar

Ein Klick öffnet dieses Release auf GitHub.

## Neuigkeiten nach einem Update

Beim ersten Öffnen der Web-App nach einem Downtify-Update zeigt ein Dialog **Neu in Downtify 3.12.0** die Highlights der Version, mit einer Schaltfläche **Vollständiges Änderungsprotokoll**, die die Version auf GitHub öffnet, und einer dezenten Zeile, um dem Repository einen Stern zu geben. **Verstanden** (oder Schließen) blendet ihn bis zum nächsten Update aus. **Einstellungen → Über → Neuigkeiten** öffnet ihn erneut.

- Das wird pro Browser gespeichert: Jeder Browser (und jede darin angemeldete Person) sieht ihn einmal pro Update. Ein Browser, der Downtify noch nie geöffnet hat — eine Neuinstallation — bekommt ihn nicht.
- Die Highlights sind in der App enthalten, der Dialog funktioniert also ohne Internet; nur die beiden Links führen zu GitHub. Eine Version ohne geschriebene Highlights zeigt nur den Link zu ihrem Änderungsprotokoll.
- Er wartet auf die Anmeldung und öffnet sich nicht über der Aufforderung, das Standardpasswort zu ändern.

## So funktioniert es

- Eine Hintergrundaufgabe im Backend (`downtify/update_check.py`) holt das neueste Release über die GitHub-API einmal direkt beim Start und danach jede Stunde. Sie läuft nach dem Prinzip „abschicken und vergessen“: In der Oberfläche wartet nichts darauf.
- Die Weboberfläche liest das zwischengespeicherte Ergebnis einmal pro Stunde über `GET /api/check_update` (siehe [API-Referenz](../api-reference.md)) und zeigt den Hinweis, sobald eine neuere Version gefunden wird.
- Versionen werden numerisch verglichen (`2.10.0` < `2.9.0` ist falsch, anders als bei einem einfachen Zeichenkettenvergleich); ein optionales `v` vor dem Release-Tag wird ignoriert.

## Wenn GitHub nicht erreichbar ist

Eine fehlgeschlagene Prüfung (Host offline, GitHub-Ratenlimit) wird protokolliert und beim nächsten stündlichen Durchlauf einfach wiederholt — das vorherige Ergebnis, falls vorhanden, bleibt bis dahin gültig. Die Prüfung blockiert nie etwas anderes in Downtify; es gibt dafür keine Fehlermeldung für den Nutzer.

## Es wird nichts automatisch heruntergeladen

Das *meldet* nur, dass es eine neue Version gibt — Downtify aktualisiert sich nicht selbst. Zum tatsächlichen Aktualisieren ziehst du das neue Image und erstellst den Container neu:

```bash
docker compose pull
docker compose up -d
```
