---
icon: lucide/image
---

# Künstlerfoto, Banner und Biografie

Downtify kann für jeden Künstler in deiner Bibliothek ein echtes Profilfoto, einen Banner und eine Biografie anzeigen – statt eines generierten Anfangsbuchstabens und keinem Text. Das füllt sich von selbst, wenn du die Seite eines neuen Künstlers zum ersten Mal öffnest oder sobald einer seiner Songs fertig heruntergeladen ist; danach wählst du selbst ein anderes Foto/einen anderen Banner, holst alles erneut oder schreibst deine eigene Biografie und trägst die Social-Links von Hand ein.

Die Bearbeitung ist auf der Seite jedes Künstlers in der Bibliothek immer verfügbar, ohne dass du vorher eine Einstellung aktivieren musst.

::: info Zu „Künstlerfotos automatisch laden“ / „Künstlerbanner automatisch laden“ in den Einstellungen
**Einstellungen → Downloads und Dateien → Künstlerfotos automatisch laden / Künstlerbanner automatisch laden** legen fest, ob Downtify das Foto/den Banner eines Künstlers von selbst speichern darf – das passiert, wenn du die Seite eines Künstlers zum ersten Mal öffnest und wenn einer seiner Songs fertig heruntergeladen ist (siehe [Wenn du einen neuen Künstler zum ersten Mal öffnest](#the-first-time-you-open-a-new-artist) und [Wenn ein Download fertig ist](#when-a-download-finishes)). Fotos sind standardmäßig an, Banner aus. Sie schränken den Bearbeitungsdialog nie ein: Du kannst immer von Hand ein Foto oder einen Banner wählen, egal wie sie stehen.
:::

## Der Bearbeitungsdialog

**Hat ein Künstler einen Banner, wird sein rundes Foto im Seitenkopf ausgeblendet** – der Banner allein reicht meist, und beides zusammen wirkte überladen. Das Foto ist aber nicht weg: Es steht weiterhin zum Bearbeiten bereit, einen Tab entfernt.

Fahre auf der Seite eines Künstlers in der Bibliothek (`/library/artist?name=…`) mit der Maus über das runde Foto (wenn es angezeigt wird), um die Schaltfläche **Foto bearbeiten** zu sehen, oder über den Banner-Bereich für die Schaltfläche **Künstler bearbeiten** – beide öffnen denselben Dialog: oben das aktuelle Foto des Künstlers und darunter ein Menü mit vier Tabs. Er öffnet sich je nach angeklickter Schaltfläche auf **Profile** oder **Banner** (standardmäßig **Banner**, da das Foto nicht immer zum Anklicken sichtbar ist).

- **Profile** / **Banner** – ein Bild wählst du in beiden auf dieselbe Weise:
  - **Nach Namen suchen** – sucht auf YouTube Music und Deezer nach einem passenden Künstlerfoto (Deezer-Künstler, die nur dessen generisches Platzhalterbild haben, werden ausgelassen). Gib etwas anderes ein, um nach einem anderen Namen zu suchen, oder einen direkten `http(s)://`-Bildlink, um ihn als einzelnen Kandidaten zu verwenden.
  - **Von deinem Gerät hochladen** – jede beliebige Bilddatei.
  - **Foto entfernen / Banner entfernen** – wird erst angezeigt, wenn das Bild des aktiven Tabs gespeichert ist; fragt nach einer Bestätigung und löscht dann die Begleitdatei (Sidecar).

  Jede Suchergebnis-Karte trägt ein Abzeichen mit ihrer Herkunft. Wählst du eine aus, wird sie sofort heruntergeladen und gespeichert. Die Karte, deren Bild gerade gespeichert ist, ist mit grünem Rand und Häkchen markiert, getrennt für die Tabs Profile und Banner – so siehst du auf einen Blick, welchen der Kandidaten du verwendest. Ein hochgeladenes Foto oder eines, das gespeichert wurde, bevor Downtify sich das merkte, hat keine Karte, die markiert werden könnte.
- **Biografie** – ein einfaches Textfeld mit der aktuell gespeicherten Biografie (leer, wenn es keine gibt), die du selbst schreiben oder bearbeiten kannst. Speichern überschreibt den aktuellen Text direkt. Eine Schaltfläche ⚡ **Biografie von Streams holen** über dem Feld kann es mit Daten von Apple Music/Deezer füllen, statt es von Hand einzutippen – siehe [Eine Biografie automatisch holen](#fetching-a-bio-automatically) weiter unten.
- **Soziale Netzwerke** – Links zu Twitter/X, Instagram, Facebook, YouTube und Website, direkt bearbeitbar. Speichern ersetzt immer alle fünf Felder durch den Stand des Formulars, auch ein leer gelassenes Feld. Das Holen einer Biografie fasst nie einen Link an, den du eingetragen hast: Deezers Social-Links füllen nur noch leere Felder (Deezer kennt nicht jedes Netzwerk, also ergänze den Rest von Hand, und er bleibt so).

## Wenn du einen neuen Künstler zum ersten Mal öffnest

Das Öffnen der Seite eines Künstlers in der Bibliothek legt sein Profil automatisch an, aber nur, wenn für ihn noch nichts gespeichert wurde – jeder Besuch nach dem ersten ist ein schnelles No-op, sodass sich das nie wiederholt und nach dem Durchlauf nichts verlangsamt.

- **Foto und Banner** – von Spotify (siehe [Spotify](#spotify) weiter unten), mit Rückgriff auf einen exakten Namenstreffer auf YouTube Music, wenn Spotify nichts hat. Nur wenn du in den Einstellungen **Künstlerfotos automatisch laden** und/oder **Künstlerbanner automatisch laden** aktiviert hast (beide sind standardmäßig aus, und jedes ist unabhängig); der Bearbeitungsdialog kann jedes von beiden immer von Hand setzen.
- **Biografie, Herkunft, Gründungsjahr, Genre, Gruppen-Kennzeichen, Bannerfarbe, Social-Links, ähnliche Künstler und Plattform-IDs** – von Apple Music und Deezer geholt, wie in [Eine Biografie automatisch holen](#fetching-a-bio-automatically) weiter unten beschrieben.

Wenn Apple Music oder Deezer dabei **fehlschlägt** (nicht erreichbar oder über dem Anfragelimit), wird nichts gespeichert – weder Biografie noch Foto – und die Seite zeigt einfach noch kein Profil, sodass der nächste Besuch es erneut versucht. Nur wenn ein Dienst antwortet, den Künstler nicht zu kennen, zählt das als Antwort: Das Profil wird dann aus dem erstellt, was der andere hatte. Der Spotify-Teil (die ähnlichen Künstler) verhindert nie, dass ein Profil erstellt wird.

## Wenn ein Download fertig ist

Dieselbe Anlage läuft im Hintergrund, wenn ein Song eines Künstlers fertig heruntergeladen ist – ob du ihn in der App gestartet hast oder ein Durchlauf des [Playlist-Monitors](playlist-monitor.md) –, falls dieser Künstler noch kein Profil hat, sodass die Künstler, die du herunterlädst, bereit sind, noch bevor du ihre Seite öffnest. Das bremst den Download nie: Der Künstler wird in die Warteschlange gestellt und ein paar Sekunden später gefüllt, zwei Künstler gleichzeitig, und ein Künstler, der schon in der Warteschlange ist, wird nicht erneut eingereiht, egal wie viele seiner Songs eintreffen (eine Playlist mit fünfzig Songs eines Künstlers legt ihn einmal an). Songs, die schon in deiner Bibliothek sind, werden nicht erneut heruntergeladen und lösen nichts aus.

- **Welcher Künstler** – der, unter dem die Datei abgelegt wird: der Album-Künstler, sonst der erste genannte Künstler. `Various Artists` wird übersprungen.
- **Sprache** – Biografie und Genre kommen in der Sprache der Web-Oberfläche an, die die Seite auf dem Server hinterlegt (siehe [Internationalisierung](internationalization.md)); bis eine Seite sie mitgeteilt hat, auf Englisch.
- **Foto und Banner** – nur so, wie **Künstlerfotos automatisch laden** / **Künstlerbanner automatisch laden** es erlauben, zu diesem Zeitpunkt gelesen, sodass eine geänderte Einstellung schon für den nächsten Song gilt.
- **Top songs** – werden so nicht angelegt; sie warten auf die Künstlerseite (siehe [Top songs](top-songs.md)).

Wenn für einen Künstler nirgends etwas gefunden werden konnte, läuft das trotzdem nur einmal – es versucht es nicht bei jedem weiteren Besuch erneut. Nutze den Bearbeitungsdialog, um später von Hand ein Foto/einen Banner zu wählen oder die Schaltfläche zum Holen erneut zu versuchen.

## Der Tab Links

Ein Künstler mit mindestens einem gespeicherten Link bekommt einen Tab **Links**, direkt vor **Biografie** (der weiterhin der letzte Tab bleibt), mit einem Zähler. Er listet sie als Karten auf, auf jedem Bildschirm und ob der Künstler einen Banner hat oder nicht: zuerst **Streamingdienste**, dann **Soziale Netzwerke**. Jede Karte zeigt den Namen und die Adresse der Seite und öffnet sie in einem neuen Tab. Es wird nur aufgelistet, was tatsächlich gespeichert ist, und ein Künstler ohne Links hat keinen Tab Links (`?tab=links` öffnet für ihn den ersten Tab).

- **Streamingdienste** – Spotify, YouTube Music, Deezer und Apple Music, aufgebaut aus der `platforms_id` des Profils: Jede gespeicherte ID wird zu einem Link (z. B. wird eine gespeicherte Deezer-ID zu einem Link auf die Deezer-Seite dieses Künstlers). Die IDs werden alle automatisch aufgelöst, wenn zum ersten Mal eine Biografie geholt wird, per exaktem Namenstreffer auf jeder Plattform (die von Spotify kommt von einem der eigenen Spotify-Songs des Künstlers, wenn es einen gibt, wodurch kein Namensvetter gewählt werden kann). Du kannst auch eine von Hand im JSON des Künstlerprofils ergänzen oder korrigieren (siehe unten).
- **Soziale Netzwerke** – Twitter/X, Instagram, Facebook, YouTube und Website: eine Karte pro nicht leerem Feld des Tabs Soziale Netzwerke oben. Nur Webadressen werden geöffnet: Ein ohne `https://` eingegebener Link bekommt es dazu, und alles mit einer anderen Adressart (z. B. ein `javascript:`) wird ignoriert.

## Spotify

Spotify erscheint nie als Freitext-Suchquelle, aber sowohl die Auswahl als auch die automatische Anlage beim ersten Besuch (siehe oben) finden den Künstler dort trotzdem. Sie prüfen zuerst ein paar der bereits heruntergeladenen Songs des Künstlers: Wurde einer von Spotify heruntergeladen, kennt Downtify schon dessen Spotify-ID und löst das Bild direkt auf – der verlässlichste Weg, da er nicht bei einem anderen Künstler mit demselben Namen landen kann. Stammt kein Song von Spotify (sagen wir, sie wurden von YouTube heruntergeladen), wird der Künstler nach exaktem Namen gesucht (ohne Beachtung der Groß-/Kleinschreibung – ein unscharfer Treffer wird nie verwendet). In der Auswahl erscheint dieser Kandidat zuerst, beschriftet mit **Spotify**.

Die Namenssuche nutzt das Suchfeld von Spotifys eigenem Web-Player und hängt daher von einer internen Kennung ab, die Spotify ändern kann; passiert das, greift Downtify für Foto/Banner auf YouTube Music zurück und lässt die Spotify-ID leer, statt zu scheitern.

Foto und Banner sind bei Spotify wirklich verschiedene Bilder und werden unterschiedlich aufgelöst: Das quadratische Foto kommt von der öffentlichen Embed-Seite des Künstlers, der breite Banner dagegen aus den Daten von Spotifys eigener Künstlerseite (die das Embed gar nicht preisgibt). Nicht jeder Künstler hat einen Banner – hat er keinen, wird für die Banner-Auswahl kein Spotify-Kandidat angeboten, statt auf das quadratische Foto zurückzugreifen.

Ein Künstler ohne Songs von Spotify bekommt schlicht keinen Spotify-Kandidaten – suche auf YouTube Music/Deezer, füge einen Link ein oder lade ein Bild hoch.

## Eine Biografie automatisch holen

Unter dem Seitenkopf zeigt die Künstlerseite eine kurze, schreibgeschützte Biografie – leer, bis eine gespeichert ist. Um sie zu füllen, öffne den Tab **Biografie** im Bearbeitungsdialog und klicke über dem Textfeld auf **Von Apple Music laden** oder **Von Deezer laden** (siehe [Die Quelle wählen](#choosing-the-source)); das lädt die Biografie dieses Dienstes ins Feld, damit du sie prüfst und speicherst. Die automatische Anlage beim ersten Besuch, die von selbst speichert, sucht den Künstler auf Apple Music per exaktem Namenstreffer (mit derselben Namenssuche, die Apples eigene Musik-App verwendet) und holt seine Biografie, Herkunft, sein Gründungsjahr, Genre, Gruppen-Kennzeichen und die Akzentfarbe des Banners – den Text (Biografie und Genre) in der aktuellen Sprache deiner Oberfläche – und speichert das Ergebnis. Das Genre (Apple Music nennt eines pro Künstler, z. B. „Hard rock“) erscheint als kleine Pille oben im Tab Biografie der Künstlerseite, neben Herkunft und Gründungsjahr. Apple Music sagt, ob der Künstler eine Gruppe ist: Bei einer Gruppe liest sich dieses Datum als „Gegründet 1995“, bei einem Solokünstler – dessen Datum meist ein Geburtsdatum ist – „Geboren am 27. September 1984“ (in alle Oberflächensprachen übersetzt; ein Künstler, dessen Gruppen-Kennzeichen unbekannt ist, bleibt bei „Gegründet“). Das Datum selbst wird so gezeigt, wie Apple Music es geliefert hat, behält also die Sprache des Abrufs. Hat Apple Music keinen exakten Treffer oder einen ohne Biografietext in deiner Sprache, wird als Nächstes Deezer als zweite Biografiequelle versucht – es bringt auch Social-Links und Namen ähnlicher Künstler („Fans mögen auch“) mit (die ähnlichen Künstler werden in der Profildatei des Künstlers gespeichert, aber noch nirgends angezeigt, für eine künftige Ergänzung vorgehalten) und füllt auch den Tab Soziale Netzwerke. Nur wenn keine der beiden Quellen etwas hat, siehst du einen Fehler statt einer geratenen/falschen Biografie.

Die redaktionellen Biografien von Apple Music gibt es nicht für jeden Künstler in jeder Sprache – fehlt eine Sprache für einen bestimmten Künstler, wird stattdessen die Biografie von Deezer (falls vorhanden) verwendet, während Herkunft/Gründungsjahr/Gruppen-Kennzeichen weiterhin von Apple Music kommen, da diese Fakten kein übersetzter Text sind (das Genre stammt immer nur von Apple Music, bleibt also leer, wenn Apple keinen Treffer hat). Einige wenige Sprachen (Bulgarisch, zum Zeitpunkt des Schreibens) bietet Apple Music gar nicht an, und sie fallen immer auf dessen Biografie in der Standardsprache zurück.

Eine Biografie wird im JSON des Künstlers als reiner Text gespeichert – ohne HTML-Tags und ohne Aufzählungszeichen: Eine Leerzeile trennt die Absätze, und jedes `•`-Aufzählungszeichen einer Apple-Music-Biografie (die Apple mit einem einfachen Zeilenumbruch trennt) wird zu einem eigenen Absatz. Die HTML-Biografien von Deezer werden auf dieselbe Weise geglättet (jeder Absatz wird zu einem durch Leerzeile getrennten, jedes andere Tag wird verworfen). Die Künstlerseite zeigt jeden Absatz einzeln und behält einfache Zeilenumbrüche darin bei, und das Textfeld im Tab Biografie bearbeitet genau diesen Text.

Ein erneutes Holen auf diese Weise läuft nur, wenn du auf die Schaltfläche klickst – es überschreibt nach der oben beschriebenen automatischen Anlage beim ersten Besuch nichts von selbst. Nur beim ersten Mal (ob automatische Anlage oder manueller Klick) muss nach dem Namen gesucht werden: Die aufgelösten Künstler-IDs von Apple Music und Deezer werden danach in der Profildatei des Künstlers zwischengespeichert, sodass ein erneutes Holen dieselben Künstler nur direkt neu liest.

Um eine gespeicherte Biografie zu löschen, öffne den Tab Biografie, leere das Textfeld und speichere – Herkunft, Gründungsjahr, Genre, Gruppen-Kennzeichen, Social-Links, ähnliche Künstler und die zwischengespeicherten Plattform-IDs bleiben unberührt.

## Die Quelle wählen

Der Tab Biografie hat über dem Textfeld zwei Links, damit du wählen kannst, welche Biografie sich besser liest:

- **Von Apple Music laden** – lädt die redaktionelle Biografie von Apple Music ins Textfeld. Hat Apple Music für diesen Künstler in deiner Sprache keine, bekommst du einen Fehler statt eines Ersatzes.
- **Von Deezer laden** – lädt die Biografie von Deezer, auch wenn Apple Music eine hat. Hat Deezer keine, bekommst du einen Fehler.

Ein Klick auf einen Link **füllt nur das Textfeld** – nichts wird gespeichert, bis du **Speichern** drückst, sodass du sie lesen, bearbeiten oder erst den anderen Dienst ausprobieren kannst, und das Schließen des Dialogs ohne Speichern lässt die aktuelle Biografie, wie sie war. Es wird nur der Biografietext geladen: Herkunft, Gründungsjahr, Genre, Social-Links, ähnliche Künstler und Plattform-IDs werden von diesen Links nicht angefasst (die automatische Anlage beim ersten Besuch füllt sie). Die Anlage fragt nicht, welcher Dienst: Sie nimmt die Biografie von Apple Music und greift nur auf die von Deezer zurück, wenn Apple Music keine hat.

## Wohin die Dateien gehen

```
<downloads>/.metadata/ArtistImage/<Artist>.jpg
<downloads>/.metadata/ArtistBannerImage/<Artist>.banner.jpg
<downloads>/.metadata/ArtistData/<Artist>.json
<downloads>/.metadata/ArtistTopSongs/<Artist>.topsongs.json
```

Eine Datei pro Künstler, nach seinem Namen benannt (bereinigt wie die Dateinamen der Songs) – kein Datenbankeintrag, die Anwesenheit der Datei auf der Platte ist also das, was die Künstlerseite prüft. Ein neues Foto/ein neuer Banner überschreibt das vorherige (die Web-Oberfläche verhindert, dass weiter ihre Kopie des alten angezeigt wird: Die URL jedes gespeicherten Bildes trägt das Änderungsdatum der Datei, sodass ein ersetztes Foto neu geholt wird, ein unverändertes aber im Cache bleibt), und `ArtistData/<Artist>.json` enthält die oben beschriebenen Daten zu Biografie/Social-Links/ähnlichen Künstlern/Plattform-IDs sowie in `current_cover` und `current_cover_banner`, welches Bild das aktuelle Foto/der aktuelle Banner ist: den URL-Pfad, von dem es heruntergeladen wurde (ohne Host und Query, damit dasselbe Bild von einer anderen CDN-Adresse trotzdem passt), oder `upload` für ein von dir hochgeladenes. Damit vergleicht der Bearbeitungsdialog jeden Kandidaten, um den verwendeten zu markieren. Es sind normale Dateien in deinem Download-Ordner, sodass Dienste wie Navidrome sie direkt lesen können, wenn du sie auf denselben Ort zeigen lässt.

Künstlernamen werden so abgeglichen, wie die Platte sie hält: Downtify legt `AC/DC` als `ACDC` ab, weil ein Dateiname kein `/` enthalten kann, und ein Song ohne Künstler-Tag übernimmt seinen Künstler aus diesem Dateinamen – derselbe Künstler kann also als `AC/DC` oder `ACDC` auftauchen. Jede Namenssuche (Spotify, Deezer, YouTube Music und Apple Music) ignoriert Groß-/Kleinschreibung und die Zeichen, die ein Dateiname nicht enthalten kann, sodass beide Schreibweisen denselben Künstler finden und dieselben Dateien oben teilen. Ein Name, der sich in irgendetwas anderem unterscheidet – etwa `AC/DC Tribute` –, ist weiterhin ein anderer Künstler und passt nie.

`platforms_id` kennt die Schlüssel `spotify`, `youtubemusic`, `deezer` und `applemusic`, alle automatisch aufgelöst – Spotify aus einem der eigenen Spotify-Songs des Künstlers oder, falls keiner da ist, per exaktem Namen; die anderen per exaktem Namen. Das Holen der Biografie füllt auch eine fehlende Spotify-ID, sodass ein Künstler, der geöffnet wurde, bevor es das gab, nach einem Holen sein Spotify-Symbol bekommt. Eine bereits gespeicherte ID wird nie ersetzt, und du kannst die JSON-Datei weiterhin direkt bearbeiten, um eine von Hand zu setzen.

## Außerhalb des Umfangs

Ein hier gewähltes Foto/ein hier gewählter Banner berührt nie die Download-Pipeline – es hat keine Wirkung darauf, was in die Tags deiner eigenen Audiodateien eingebettet wird, und das Herunterladen eines Songs holt nie automatisch ein Künstlerbild.

Der Tab *Ähnliche* zeigt auch für Künstler, die du nicht hast, ein Foto, und dasselbe tun das Raster *Künstler* der Bibliothek, die Seite des Künstlers selbst, der Tab *Künstler* des Monitors (der Künstler, den du überwachst, in der Liste und in seinem Bearbeitungsdialog) und die Künstler in [Entdecken](discover.md) und im [Finder](finder.md) – wo die Seite bereits das Deezer-Bild des Künstlers hat, sodass keine Namenssuche nötig ist und stattdessen ein Foto erscheint, das du für den Künstler gespeichert hast – für jeden Künstler, für den du kein Foto gewählt hast (die Bibliothek und die Seite des Künstlers selbst nehmen eines der Songcover des Künstlers, wenn Deezer keines hat; der Monitor hat keinen Song, zeigt also Initialen) – nur ein echtes: Ein Künstler, für den Deezer kein Foto hat (es liefert ein generisches Platzhalterbild), bekommt den üblichen Anfangsbuchstaben – aber das dient nur der Anzeige: Der Server reicht das Deezer-Bild an deinen Browser weiter (der es drei Stunden lang zwischenspeichert), ohne es zu speichern, und es wird nie zum Foto oder Banner eines Künstlers. Nur echte Antworten bleiben erhalten: Ist Deezer nicht erreichbar oder liegst du gerade über dem Anfragelimit, zeigt die Kachel vorerst den Anfangsbuchstaben (oder das Songcover) und nichts wird gemerkt, sodass das Foto beim nächsten Öffnen der Seite erscheint. Fotos werden nur für Künstler auf die Platte geschrieben, für die du selbst eines gesetzt hast oder deren Foto/Banner beim ersten Besuch wie oben beschrieben gespeichert wurde (wenn die Einstellungen es erlauben). Siehe [`GET /api/artists/photo-proxy`](../api-reference.md#get-apiartistsphoto-proxy).
