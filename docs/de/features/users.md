---
icon: lucide/users
---

# Benutzer und Anmeldung

Alle, die Downtify nutzen, melden sich mit **Benutzername und Passwort** an, und jede Person kann ein eigenes Konto haben. Ein Admin verwaltet die Konten unter **Einstellungen → Benutzer** und sieht unter **Einstellungen → Aktivität**, was jeder tut.

## Das erste Mal anmelden

Ein neuer Server hat ein Konto:

| Benutzername | Passwort |
|----------|----------|
| `admin` | `downtify` |

Melde dich damit an und **ändere das Passwort** unter **Einstellungen → Allgemein → Konto**: Wer Downtify kennt, kennt das Standardpasswort. Solange du es nicht tust, erinnert dich Downtify nach der Anmeldung daran und zeigt eine Warnung in den Einstellungen.

::: warning Ändere das Standardpasswort, bevor du den Server öffentlich machst
Das Standardpasswort schützt nichts. Ändere es, bevor du Downtify von außerhalb deines Heimnetzes erreichbar machst — und nutze dort HTTPS (siehe [Hinter einem Reverse-Proxy](mobile-apps.md#behind-a-reverse-proxy)).
:::

### Von einer älteren Version aktualisieren

Ein Server, der eine Version ohne Konten betrieb, bekommt dasselbe `admin`-Konto, und die Anmeldeseite sagt das einmal — bis sich ein Admin anmeldet — mit Benutzername und Passwort zum Verwenden:

- Hattest du unter der alten Option **Anmeldung verlangen** ein Passwort gesetzt, gilt dieses Passwort weiter für `admin`.
- Andernfalls ist es `downtify`.

Browser, die vor dem Update angemeldet waren, melden sich erneut an. Vor dem Update gekoppelte Handys bleiben gekoppelt und gehören jetzt `admin`.

## Admins und Benutzer

| | Admin | Benutzer |
|---|---|---|
| Hören, suchen, herunterladen, liken, Entdecken, Charts, Finder, Podcasts | ✓ | ✓ |
| Handy-Apps koppeln (mit dem eigenen Konto) | ✓ | ✓ |
| Einstellungen → Allgemein (das eigene Konto und Präferenzen), Apps, Über | ✓ | ✓ |
| Jede andere Einstellung (Quellen, Dateien, Tags, Navidrome, Bibliothek, Server), den Server umbenennen | ✓ | |
| [Eigene Playlists teilen](#sharing-playlists) (nur ansehen), öffentliche folgen, Kopien speichern | ✓ | ✓ (wenn der Admin es erlaubt) |
| Dateien und Playlists löschen (ein Benutzer nur [was er heruntergeladen hat](#deleting-songs) und seine eigenen Playlists), eigene Playlist-Beobachtungen und Podcast-Abonnements verwalten, das Audio eines Titels ersetzen, Künstlerfotos bearbeiten | ✓ | ✓ (nur eigene) |
| [Songs, Alben und Künstler vor Benutzern verbergen](#hiding-from-users) | ✓ | |
| Benutzer verwalten, das Aktivitätsprotokoll sehen | ✓ | |

Ein Benutzer, der etwas versucht, das einen Admin braucht, bekommt eine entsprechende Meldung.

## Deine Bibliothek

Die Bibliothek ist geteilt: Jedes Konto sieht jeden Song, den jemand heruntergeladen hat — in der Bibliothek, in Suchergebnissen, die als heruntergeladen markiert sind, und auf einem gekoppelten Handy. Dateien werden nie doppelt gespeichert: Laden zwei Personen denselben Song herunter, landet er einmal auf der Festplatte, mit je einem Besitzer.

Likes, Playlists (heruntergeladene und in der Bibliothek erstellte) und die Download-Warteschlange bleiben deine, außer du bist Admin — oder du [teilst eine Playlist](#sharing-playlists), damit andere sie sehen. Das Hören ist geteilt — jeder kann jeden Titel abspielen, anhören oder streamen und alles zu seinen eigenen Playlists hinzufügen. Einen Titel anzufordern, den jemand anderes gerade herunterlädt, schließt sich dessen Auftrag an, statt ihn doppelt abzurufen: eine Warteschlangenzeile, ein Download und je eine Besitzerschaft — jeder Wartende sieht seinen Platz in der Warteschlange.

Podcasts, Playlist-Beobachtungen und der Verlauf von Entdecken funktionieren genauso: Jedes Konto abonniert seine eigenen Sendungen, folgt seinen eigenen Playlists und Künstlern und trainiert seine eigenen Vorschläge. Ein Admin sieht die Zeilen aller Konten. Das Hören selbst bleibt geteilt — jeder kann jeden Titel abspielen, anhören oder streamen.

### Playlists teilen

Eine Playlist ist für ihren Besitzer (und Admins) privat, bis der Besitzer sie teilt, über **Teilen…** auf der Playlist-Seite oder in ihrem **⋯**-Menü. Die Wiedergabe ist zwischen Konten ohnehin geteilt; hier geht es nur darum, wer eine Liste *sehen* kann. Jede Playlist lässt sich teilen außer *Lieblingssongs*, auch importierte.

| Sichtbarkeit | Wer sie sieht |
|------------|-------------|
| **Privat** | Nur der Besitzer und Admins — der Standard |
| **Bestimmte Personen** | Die vom Besitzer gewählten Benutzernamen |
| **Öffentlich** | Alle auf dem Server |

Playlists anderer mischen sich nie unter deine eigenen. Der Tab **Playlists** der Bibliothek listet sie in zwei Abschnitten unter deinen eigenen, jeder Eintrag mit seinem Besitzer beschriftet:

- **Mit mir geteilt** — Playlists, die namentlich an dich gerichtet sind, immer sichtbar. Eine frisch geteilte trägt eine **Neu**-Markierung, bis du sie öffnest.
- **Öffentliche Playlists** — die öffentlichen aller, nach Besitzer und Name sortiert, mit dem Filter des Tabs durchsuchbar, mit Besitzer, Anzahl der Songs und ob du ihr folgst. Der Abschnitt startet zugeklappt, und du kannst ihn mit **Einstellungen › Allgemein › Öffentliche Playlists anzeigen** ganz ausblenden (standardmäßig an; es ist deins, wie das Thema).

Die Seitenleiste zeigt außerdem einige der mit dir geteilten und der öffentlichen Playlists, denen du folgst.

**Was ein Betrachter tun kann:** abspielen, mischen, zur Warteschlange hinzufügen, als ZIP herunterladen (oder auf eine Handy- oder Desktop-App), einer öffentlichen Playlist **folgen**, damit sie in seinen Listen bleibt — auch bei ausgeschaltetem *Öffentliche Playlists anzeigen* — und den Änderungen ihres Besitzers folgen, und **Kopie speichern**: eine private, bearbeitbare eigene Playlist mit den Songs, die er sehen kann. Ein Betrachter kann die Playlist eines anderen nicht bearbeiten, umbenennen, löschen, teilen oder lösen. Der Besitzer einer Bibliotheks-Playlist kann einige der Personen, mit denen er sie teilt, zu Bearbeitern machen, die auch Titel hinzufügen und entfernen – siehe [Gemeinsam bearbeitete Playlists](collaborative-playlists.md).

**Teilen beenden:** Macht der Besitzer eine Playlist wieder privat oder entfernt jemanden aus der Liste, verschwindet sie sofort aus den Listen dieser Person (gefolgt oder nicht); eine Playlist, die nicht mehr öffentlich ist, wird nicht mehr gefolgt. Kopien, die Leute schon gespeichert haben, bleiben bei ihnen. Das Umbenennen einer geteilten Playlist lässt sie geteilt; das Löschen nimmt das Teilen mit. Songs, die ein Admin [vor Benutzern verbirgt](#hiding-from-users), sind für sie aus den Titeln einer geteilten Playlist ausgenommen, wie überall.

Ein Admin kann das Ganze mit **Einstellungen › Bibliothek › Benutzern das Teilen von Playlists erlauben** ausschalten (standardmäßig an). Solange es aus ist, ist jede Freigabe verborgen und niemand kann teilen oder folgen — die Freigaben kehren zurück, wenn es wieder eingeschaltet wird.

Gekoppelte Apps bekommen dieselben Listen: [`GET /api/v1/playlists`](../api-reference.md#get-apiv1playlists) sagt, wem jede gehört und ob sie nur ansehbar ist, und `playlists_changed` auf dem WebSocket weist sie an, zu aktualisieren.

### Vor Benutzern verbergen

Admins entscheiden, was die anderen Konten sehen. Alles ist für alle sichtbar, bis ein Admin etwas verbirgt: einen **Song**, ein ganzes **Album** oder einen ganzen **Künstler**. Verborgene Elemente verschwinden aus der Bibliothek, aus den „in der Bibliothek“-Markierungen der Suche, aus den Titellisten der Playlists und aus dem, was ein gekoppeltes Handy synchronisiert — für Benutzer, nicht für Admins.

- **In der Bibliothek** öffne das `…`-Menü eines Songs, Albums oder Künstlers und wähle **Vor Nutzern verbergen** (oder **Nutzern zeigen**, um es rückgängig zu machen). Wähle im Tab Titel mehrere Songs aus und nutze **Vor Nutzern verbergen** in der Auswahlleiste.
- Admins sehen weiterhin alles. Verborgenes trägt ein kleines durchgestrichenes Auge, und sein Tooltip sagt, warum: für sich verborgen, mit seinem Album oder mit seinem Künstler.
- **Einstellungen › Benutzer › Vor Nutzern verborgen** listet jeden verborgenen Künstler, jedes Album und jeden Song, mit **Nutzern zeigen** daneben.
- Ein verborgener Song bleibt verborgen, wenn er in einen anderen Ordner verschoben wird und wenn [Bibliothek verbessern](library-upgrade.md) oder [Audio ersetzen](replace-audio.md) seine Datei neu schreiben. Das Löschen der Datei vergisst die Regel.
- Eine Albumregel passt auf Künstler und Titel des Albums, eine Künstlerregel auf den Künstler, unter dem die Bibliothek den Song gruppiert — dieselben Namen, die die Tabs Alben und Künstler der Bibliothek nutzen.

::: info Verbergen betrifft, was aufgelistet wird
Es steuert, was Konten in der App sehen, nicht wer eine Datei abrufen kann, deren Adresse er schon kennt. Nutze es nicht, um sensible Dateien zu schützen.
:::

Verbergen und Zeigen werden im [Aktivitätsprotokoll](#activity) festgehalten.

### Songs löschen

Das Löschen eines Songs nimmt ihn für alle von der Festplatte, daher folgt es dem, der ihn heruntergeladen hat. Ein Admin kann alles löschen. Ein Benutzer kann einen Song löschen, den er selbst heruntergeladen hat; hat jemand anderes denselben Song ebenfalls heruntergeladen, gibt das Löschen nur den eigenen Anspruch auf, und der Song bleibt in der geteilten Bibliothek. Einen Song, den niemand über ein Konto heruntergeladen hat (ein Durchlauf der Playlist-Überwachung, ein Download aus der Zeit vor den Konten, ein [zusätzlicher Ordner](external-library.md)), kann nur ein Admin löschen. Das Löschen einer deiner Playlists nimmt nie die Dateien anderer mit.

### Nutzung pro Konto

**Einstellungen › Benutzer** listet unter jedem Konto auf, was es hält: Titel und ihre Größe, Likes, Playlists, bestellte Downloads und Datenverkehr in beide Richtungen (von upstream abgerufen vs. an Clients ausgeliefert), mit den Summen über alle darunter. „Titel“ zählt die Songs, die ein Konto heruntergeladen hat, nicht was es sehen kann.

## Dein Konto und deine Präferenzen

**Einstellungen → Allgemein** beginnt mit deinem **Konto**: Ändere deinen Benutzernamen oder dein Passwort oder melde dich ab. Du kannst dich auch über die Seitenleiste abmelden (oder **Mehr** am Handy).

Der Rest von **Allgemein** — Thema, Sprache, Songtexte im Player zeigen, Alben in Suchergebnissen — ist **deins**: Er folgt deinem Konto in jeden Browser, in dem du dich anmeldest, und ändert nichts für andere.

**Einstellungen → Apps** listet die mit deinem Konto gekoppelten Handys (ein Admin sieht die aller, mit ihrem Besitzer). **Überall abmelden** trennt deine Apps und meldet dich in jedem Browser ab.

## Benutzer verwalten

Unter **Einstellungen → Benutzer** kann ein Admin:

- **Einen Benutzer hinzufügen** — Benutzername (3 bis 32 Buchstaben, Ziffern, `.`, `-` oder `_`), Passwort (mindestens 8 Zeichen) und Rolle.
- Einen Benutzer **bearbeiten** — umbenennen, zum Admin oder Benutzer machen oder ihm ein neues Passwort geben (was ihn in seinen Browsern abmeldet; seine Apps bleiben gekoppelt).
- Einen Benutzer **löschen** — seine Apps werden getrennt und seine Browser abgemeldet. Seine Dateien bleiben auf der Festplatte (Admins sehen sie weiterhin); seine Likes, Playlists, Podcast-Abonnements, Beobachtungen, Vorschlagsverlauf und Datenverkehrszähler gehen mit ihm.
- **Alle abmelden** — jede App jedes Benutzers wird getrennt und jeder Browser abgemeldet, deiner auch.

Es gibt immer mindestens einen Admin: Der letzte kann nicht gelöscht oder zum Benutzer gemacht werden, und du kannst dein eigenes Konto nicht löschen.

## Aktivität

**Einstellungen → Aktivität** (Admins) zeigt, wie Jellyfins Dashboard:

- **Wird gerade abgespielt** — was jeder Browser und jede App abspielt, von wem, wo im Song sie ist und ob pausiert. Aktualisiert sich alle paar Sekunden.
- **Verlauf** — Anmeldungen (und fehlgeschlagene, mit der Adresse, von der sie kamen), Abmeldungen, gespielte Songs, Downloads, Likes, gelöschte Dateien, vor Benutzern verborgene oder ihnen gezeigte Songs, gekoppelte und getrennte Apps, hinzugefügte, geänderte oder gelöschte Konten, geänderte Passwörter und Einstellungen. Filtere nach Benutzer oder Art. Gespeicherte Einstellungen werden nur mit Namen aufgeführt, nie mit ihren Werten. Einträge werden 90 Tage aufbewahrt.

Auch Apps melden, was sie abspielen — siehe den [Vertrag für mobile Clients](../mobile-client-contract.md#8-report-plays).

## Konten ausschalten

Ein Server, den nur du erreichst — auf deinem eigenen Computer oder hinter etwas, das schon nach einem Passwort fragt —, braucht vielleicht gar keine Konten. Setze `DOWNTIFY_DISABLE_AUTH=true` (siehe [Umgebungsvariablen](../getting-started/environment-variables.md#mobile-apps-and-sign-in)):

```yaml
environment:
  - DOWNTIFY_DISABLE_AUTH=true
```

Dann:

- Es gibt keine Anmeldeseite: Wer Downtify öffnet, nutzt es als erster Admin (`admin` auf einem neuen Server).
- Die Abmelde-Schaltflächen, **Einstellungen → Benutzer**, der **Konto**-Teil von **Einstellungen → Allgemein** und **Überall abmelden** unter **Einstellungen → Apps** verschwinden.
- Handys können weiterhin gekoppelt werden (an diesen Admin), und **Einstellungen → Aktivität** zeigt weiterhin, was wo abgespielt wird.
- Thema, Sprache und die anderen **Allgemein**-Präferenzen bleiben als die dieses Admins erhalten.

::: warning Jeder, der den Server erreicht, kann alles tun
Bei ausgeschalteten Konten fragt nichts, wer du bist: Alle in deinem Netzwerk — oder im Internet, wenn der Port offen ist — können Einstellungen ändern, Musik löschen und ein Handy koppeln. Schalte Konten nicht auf einem Server aus, den andere erreichen.
:::

Setze es auf `false` (oder entferne es), und die Anmeldung ist wieder Pflicht, mit den Konten, Passwörtern und Apps wie zuvor.

## Passwort vergessen?

Führe das auf dem Server aus — `admin` bekommt das Passwort `downtify` zurück (und wird als Admin neu angelegt, wenn er umbenannt oder gelöscht wurde); andere Konten und gekoppelte Apps bleiben unberührt:

```bash
docker exec downtify python main.py auth-reset
```

Außerhalb von Docker führe `python main.py auth-reset` (oder `uv run python main.py auth-reset`) im Downtify-Ordner aus. Dann melde dich an und ändere das Passwort.

## Skripte und die API

Jeder API-Aufruf braucht jetzt Zugangsdaten (siehe die [API-Referenz](../api-reference.md#server-and-sign-in)). Ein Skript kann sich mit `POST /api/auth/login` anmelden und das Cookie `downtify_session` behalten oder das Token eines gekoppelten Geräts nutzen.
