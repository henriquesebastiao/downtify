---
icon: lucide/star
---

# Top Songs

Manche Künstler haben riesige Kataloge, in denen nur eine Handvoll Titel zählt. Statt Links Titel für Titel zu holen oder eine „This is…“-Playlist mit 50+ Titeln für die wenigen Songs herunterzuladen, die du wirklich willst, füge den Link des Künstlers selbst ein und wähle aus seinen beliebtesten Songs.

## So geht’s

1. Füge einen Künstlerlink in das Suchfeld oder auf der Startseite ein:
   - **Spotify**: `https://open.spotify.com/artist/…`
   - **YouTube Music**: `https://music.youtube.com/channel/UC…` oder `https://music.youtube.com/@handle`
   - **Deezer**: `https://www.deezer.com/artist/…`
2. Die **Künstlerseite** öffnet sich mit Foto und Name und listet die Veröffentlichungen (Alben, Singles, EPs und Compilations, wo der Dienst sie hat), bei Spotify und Deezer die neuesten zuerst; klicke auf eine, um ihre Titel zu sehen oder sie herunterzuladen. Neben einer **Top Songs**-Schaltfläche haben Spotify- und YouTube-Music-Künstler auch **Auf neue Veröffentlichungen achten** — Deezer-Künstler nicht, da die [Playlist-Überwachung](playlist-monitor.md) Deezer nicht unterstützt.
3. **Top Songs** öffnet die Liste ihrer beliebtesten Songs, in der Reihenfolge, in der der Dienst sie einordnet. Bei Spotify und YouTube Music zeigt ein Abzeichen mit einem Auge, wie oft jeder Song gespielt wurde, gekürzt so, wie es deine Sprache tut (`1,5 bi` auf Portugiesisch, `1.5B` auf Englisch) — das von Spotify ist grün, das von YouTube Music rot. YouTube Music meldet nur eine gerundete Zahl (`1.2B plays`), seine Zahl ist also eine Näherung; Downtify liest sie aus derselben YouTube-Music-Anfrage, die die Songs listet, plus einer weiteren Anfrage für die Wiedergabezahlen. Deezers eigenes „Top“-Ranking hat keine öffentliche Wiedergabezahl, die sich zeigen ließe, seine Songs erscheinen also ohne Abzeichen. Die ersten fünf sind schon angehakt; hake weitere an oder ab und drücke dann **Ausgewählte herunterladen**.

### Songs vor dem Herunterladen anhören

Auf der Top-Songs-Seite und auf der Seite, die ein eingefügter **Album**- oder **Playlist**-Link öffnet, wird jeder Song vollständig abgespielt: Fahre über seine Zeile, und die Nummer wird zu einer Play-Schaltfläche (am Handy ist die Play-Schaltfläche immer da); drücke sie, und der Song wird von YouTube direkt in den eingebauten Player gestreamt. Drücke erneut zum Pausieren oder die Schaltfläche einer anderen Zeile zum Wechseln. Ein Song, der schon in deiner Bibliothek ist, spielt stattdessen aus der Bibliothek, mit den übrigen heruntergeladenen Songs der Liste in der Warteschlange dahinter.

Ein Stream wird von diesem Server ausgeliefert, nie vom Browser direkt zu YouTube: Die Zeile wird zu ihrem YouTube-Video aufgelöst (dem eigenen bei einem YouTube-Music-Song, sonst dem nächsten Suchtreffer), und der Server lädt das Audio einmal in seinen Stream-Cache und spielt dann die gecachte Datei ab (siehe [`GET /api/stream/file`](../api-reference.md#get-apistreamfile)). Nur der Server braucht eine Verbindung zu YouTube, und ein altersbeschränkter Titel braucht YouTube-Cookies (siehe [YouTube-Cookies](youtube-cookies.md)) wie ein Download.

## Quellen

| Quelle | Was „Top Songs“ bedeutet | Aufgelistete Songs |
|--------|------------------------|--------------|
| Spotify | Das **Beliebt**-Regal des Künstlers selbst, dieselben Titel wie oben auf seiner Spotify-Seite | Bis zu 10 |
| YouTube Music | Die **Top songs**-Playlist des Künstlers, nach Beliebtheit geordnet | Die ersten 50 |
| Deezer | Das eigene **Top**-Ranking des Künstlers (dasselbe Regal, das `deezer.com` auf seiner Seite zeigt) | Die ersten 50 |

Spotifys öffentliches Embed hat keine Diskografie, daher liest Downtify die Veröffentlichungen aus der Diskografie-Abfrage des Spotify-Webplayers, derselben nicht öffentlichen API, die es für die Albumnamen nutzt. Ändert Spotify sie, fällt Downtify auf eine kürzere Liste zurück (alle Alben, aber nur die zehn neuesten Singles) und zeigt notfalls keine Veröffentlichungen. Spotify-Songs durchlaufen die übliche Pipeline aus Metadaten und anschließendem Audio-Matching, mit vorab angehängtem Albumnamen; der Download füllt den Rest (Titelnummer, Jahr) wie bei jedem Spotify-Song. YouTube-Music-Songs sind an ihr eigenes Video gebunden, wie jeder andere YouTube-Music-Link. Deezer hat einen echten, öffentlichen Diskografie-Endpunkt, seine Veröffentlichungsliste braucht also keinen Rückfall; seine Songs durchlaufen dieselbe Pipeline aus Metadaten und Audio-Matching wie die von Spotify, mit einem 30-Sekunden-Vorschauclip, wenn Deezer einen anbietet.

## Auf der Künstlerseite in der Bibliothek

Ein Künstler, den Downtify bei Spotify kennt (siehe [Künstlerfoto, Banner und Bio](artist-images.md)), bekommt auf seiner Seite in deiner Bibliothek auch einen Tab **Top songs**, neben Titel und Fans hören auch. Er listet die ersten **5** seiner Spotify-Top-Songs als minimale Liste wie die Suchergebnisse unter Spaltenüberschriften (#, Titel, Album, Länge): Nummer, Cover, Titel, Künstler, Album und Länge. Ein Song, der nicht in deiner Bibliothek ist, hat rechts eine **Download**-Schaltfläche (mit seinem Fortschritt beim Herunterladen); ist er heruntergeladen, wird daraus das Label **In der Bibliothek**, und der Song lässt sich abspielen wie auf einer Albumseite: Die Nummer wird beim Darüberfahren zur Play-Schaltfläche, das Cover spielt, und ein Doppelklick oder Tippen spielt ebenfalls. Beim Abspielen eines Songs werden die übrigen heruntergeladenen Songs der Liste danach in Ranking-Reihenfolge eingereiht, und der laufende Song ist hervorgehoben. Ein noch nicht heruntergeladener Song wird stattdessen **vollständig gestreamt**: Fahre über seine Zeile, und dort, wo die Nummer steht, erscheint eine Play-Schaltfläche; drücke sie (oder das Cover), und er spielt im eingebauten Player wie ein heruntergeladener (siehe [Songs vor dem Herunterladen anhören](#playing-songs-before-downloading)). Unter der Liste öffnet **Weitere beliebte Titel anzeigen** diesen Künstler auf der oben beschriebenen Top-Songs-Seite, wo Auswahl, der **Playlist erstellen**-Schalter und das gleichzeitige Herunterladen mehrerer zu Hause sind. Der Tab erscheint erst, wenn die Spotify-ID des Künstlers bekannt ist, was beim ersten Öffnen seiner Seite geschieht; die Songs werden genau dann angefragt, daher füllt sich die Zahl am Tab nach ein paar Sekunden von selbst, wo auch immer du auf der Seite bist.

Das Lesen von Cover, Album und Wiedergabezahl eines Songs dauert ein paar Sekunden, daher hält Downtify die fünf Songs in einer Datei pro Künstler, `<downloads>/.metadata/ArtistTopSongs/<Künstler>.topsongs.json`, die beim ersten Öffnen der Künstlerseite im Hintergrund erstellt wird. Ihr wird **7 Tage** vertraut: Das Öffnen des Tabs liest die Datei sofort, und ist sie älter, wird die alte Liste gleich angezeigt, während im Hintergrund eine frische geholt wird — die Seite tauscht sie nach ein paar Sekunden von selbst aus, ohne einen gerade herunterladenden oder spielenden Song zu stören. Die Datei enthält nur die Songs, ihr Cover-Artwork, Clip-Links und Wiedergabezahlen — nie das Audio oder die Bilder, und nie, ob ein Song in deiner Bibliothek ist, was live ermittelt wird. Sie ist ein Cache: Lösche sie, wann du willst, und sie wird neu erstellt.

## Eine Playlist erstellen

Der Schalter **Playlist erstellen** auf der Top-Songs-Seite ist beim ersten Öffnen eines Künstlers **aus** und **an**, sobald in deiner Bibliothek bereits eine Playlist namens **Top Songs of {artist}** existiert, damit spätere Downloads weiter zu ihr hinzugefügt werden. Lege den Schalter um, und deine Wahl bleibt, solange du auf dieser Seite bist. Ist er aus, werden die Songs wie alle anderen Einzelsongs heruntergeladen: direkt in deinen Download-Ordner oder, wenn die [Dateiorganisation](file-organization.md) an ist, in deine Künstler-/Albumordner, ohne eigenen Ordner, ohne M3U und ohne Künstlerfoto.

Schalte ihn ein, und Downtify behandelt sie als Playlist namens **Top Songs of {artist}**. Wohin sie kommt, hängt von der Dateiorganisation ab:

| Nach Künstler / Album sortieren | Songs | M3U und Cover |
|---|---|---|
| Beide aus | In einem Ordner namens `Top Songs of {artist}` | Im selben Ordner |
| Eines oder beide an | Nach diesen Einstellungen abgelegt: `<Künstler>/`, `<Album>/` oder `<Künstler>/<Album>/`. Es gibt keinen Ordner `Top Songs of {artist}`. | In `Playlists/`, als `Top Songs of {artist}.m3u` und `.jpg` |

In beiden Fällen:

- die [M3U-Playlist](m3u-export.md) listet die Songs **in der Ranking-Reihenfolge des Künstlers**, auch wenn du nur einige angehakt hast;
- das Künstlerfoto wird neben der M3U als ihr Cover gespeichert, wenn **Playlist-Cover speichern** aktiviert ist (siehe [Playlist-Cover](playlist-cover-art.md)). Dafür gibt es keine eigene Einstellung.

## Bekannte Einschränkungen

::: warning Spotify und YouTube Music für denselben Künstler mischen
Die M3U von **Top Songs of {artist}** wird aus dem [Playlist-Katalog](library-catalog.md) synchron gehalten, der nach Spotify-Titel-IDs geführt wird. Lädst du die Top Songs eines Künstlers von **Spotify** und später von **YouTube Music** herunter (oder umgekehrt), werden die Dateien der zweiten Runde korrekt heruntergeladen, aber die nächste M3U-Aktualisierung wirft sie aus der Playlist-Datei, weil YouTube-Music-IDs nicht in dieses Format passen. Weitere Songs aus **derselben** Quelle hinzuzufügen, ist davon nicht betroffen.
:::

::: info Albumnamen für Spotify-Songs
Spotifys Künstlerseite sagt nicht, aus welchem Album ein Song stammt. Downtify holt die Albumnamen und die Wiedergabezahlen aus derselben Spotify-Player-API, die es zum Lesen vollständiger Playlists nutzt: eine zusätzliche Anfrage pro Künstler, plus eine für jedes Album, das diese Anfrage nicht auflistet. Diese API ist nicht öffentlich; ändert Spotify sie, bleibt die Spalte **Album** bei Spotify-Songs leer und das Wiedergabezahl-Abzeichen verschwindet; die Songs werden weiterhin heruntergeladen, aber Downtify muss das Album dann aus seinem YouTube-Music-Treffer zurückgewinnen, was oft scheitert und die Datei ohne Album-Tag lässt und, bei aktivem [Nach Album sortieren](file-organization.md), in einem Albumordner `unknown`. YouTube-Music-Top-Songs bringen ihr Album schon mit. Kommen die Wiedergabezahlen, bei einer der beiden Quellen, nicht mehr an, erscheint das Abzeichen einfach nicht.
:::

## API

Siehe [`GET /api/artists/top_songs/url`](../api-reference.md#get-apiartiststop_songsurl) in der API-Referenz.
